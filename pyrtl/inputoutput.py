"""
Helper functions for reading and writing hardware files.

Each of the functions in inputoutput take a block and a file descriptor.
The functions provided either read the file and update the Block
accordingly, or write information from the Block out to the file.
"""

from __future__ import print_function, unicode_literals
import re
import collections

from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .core import working_block, _NameSanitizer
from .wire import WireVector, Input, Output, Const, Register
from .corecircuits import concat_list
from .memory import RomBlock


# -----------------------------------------------------------------
#            __       ___
#    | |\ | |__) |  |  |
#    | | \| |    \__/  |


def input_from_blif(blif, block=None, merge_io_vectors=True):
    """ Read an open blif file or string as input, updating the block appropriately

    Assumes the blif has been flattened and their is only a single module.
    Assumes that there is only one single shared clock and reset
    Assumes that output is generated by Yosys with formals in a particular order
    Ignores reset signal (which it assumes is input only to the flip flops)
    """
    import pyparsing
    import six
    from pyparsing import (Word, Literal, OneOrMore, ZeroOrMore,
                           Suppress, Group, Keyword, Optional, oneOf)

    block = working_block(block)

    try:
        blif_string = blif.read()
    except AttributeError:
        if isinstance(blif, six.string_types):
            blif_string = blif
        else:
            raise PyrtlError('input_blif expecting either open file or string')

    def SKeyword(x):
        return Suppress(Keyword(x))

    def SLiteral(x):
        return Suppress(Literal(x))

    def twire(x):
        """ find or make wire named x and return it """
        s = block.get_wirevector_by_name(x)
        if s is None:
            s = WireVector(bitwidth=1, name=x)
        return s

    # Begin BLIF language definition
    signal_start = pyparsing.alphas + '$:[]_<>\\\/'
    signal_middle = pyparsing.alphas + pyparsing.nums + '$:[]_<>\\\/.'
    signal_id = Word(signal_start, signal_middle)
    header = SKeyword('.model') + signal_id('model_name')
    input_list = Group(SKeyword('.inputs') + OneOrMore(signal_id))('input_list')
    output_list = Group(SKeyword('.outputs') + OneOrMore(signal_id))('output_list')

    cover_atom = Word('01-')
    cover_list = Group(ZeroOrMore(cover_atom))('cover_list')
    namesignal_list = Group(OneOrMore(signal_id))('namesignal_list')
    name_def = Group(SKeyword('.names') + namesignal_list + cover_list)('name_def')

    # asynchronous Flip-flop
    dffas_formal = (SLiteral('C=') + signal_id('C') +
                    SLiteral('R=') + signal_id('R') +
                    SLiteral('D=') + signal_id('D') +
                    SLiteral('Q=') + signal_id('Q'))
    dffas_keyword = SKeyword('$_DFF_PN0_') | SKeyword('$_DFF_PP0_')
    dffas_def = Group(SKeyword('.subckt') + dffas_keyword + dffas_formal)('dffas_def')

    # synchronous Flip-flop
    dffs_init_val = Optional(oneOf("0 1 2 3"), default=Literal("0"))
    # TODO I think <type> and <control> ('re' and 'C') below are technically optional too
    dffs_def = Group(SKeyword('.latch') +
                     signal_id('D') +
                     signal_id('Q') +
                     SLiteral('re') +
                     signal_id('C') +
                     dffs_init_val('I'))('dffs_def')
    command_def = name_def | dffas_def | dffs_def
    command_list = Group(OneOrMore(command_def))('command_list')

    footer = SKeyword('.end')
    model_def = Group(header + input_list + output_list + command_list + footer)
    model_list = OneOrMore(model_def)
    parser = model_list.ignore(pyparsing.pythonStyleComment)

    # Begin actually reading and parsing the BLIF file
    result = parser.parseString(blif_string, parseAll=True)
    # Blif file with multiple models (currently only handles one flattened models)
    assert(len(result) == 1)
    clk_set = set([])
    ff_clk_set = set([])

    def extract_inputs(model):
        start_names = [re.sub(r'\[([0-9]+)\]$', '', x) for x in model['input_list']]
        name_counts = collections.Counter(start_names)
        for input_name in name_counts:
            bitwidth = name_counts[input_name]
            if input_name == 'clk':
                clk_set.add(input_name)
            elif not merge_io_vectors or bitwidth == 1:
                block.add_wirevector(Input(bitwidth=1, name=input_name))
            else:
                wire_in = Input(bitwidth=bitwidth, name=input_name, block=block)
                for i in range(bitwidth):
                    bit_name = input_name + '[' + str(i) + ']'
                    bit_wire = WireVector(bitwidth=1, name=bit_name, block=block)
                    bit_wire <<= wire_in[i]

    def extract_outputs(model):
        start_names = [re.sub(r'\[([0-9]+)\]$', '', x) for x in model['output_list']]
        name_counts = collections.Counter(start_names)
        for output_name in name_counts:
            bitwidth = name_counts[output_name]
            if not merge_io_vectors or bitwidth == 1:
                block.add_wirevector(Output(bitwidth=1, name=output_name))
            else:
                wire_out = Output(bitwidth=bitwidth, name=output_name, block=block)
                bit_list = []
                for i in range(bitwidth):
                    bit_name = output_name + '[' + str(i) + ']'
                    bit_wire = WireVector(bitwidth=1, name=bit_name, block=block)
                    bit_list.append(bit_wire)
                wire_out <<= concat_list(bit_list)

    def extract_commands(model):
        # for each "command" (dff or net) in the model
        for command in model['command_list']:
            # if it is a net (specified as a cover)
            if command.getName() == 'name_def':
                extract_cover(command)
            # else if the command is a d flop flop
            elif command.getName() == 'dffas_def' or command.getName() == 'dffs_def':
                extract_flop(command)
            else:
                raise PyrtlError('unknown command type')

    def extract_cover(command):
        netio = command['namesignal_list']
        if len(command['cover_list']) == 0:
            output_wire = twire(netio[0])
            output_wire <<= Const(0, bitwidth=1, block=block)  # const "FALSE"
        elif command['cover_list'].asList() == ['1']:
            output_wire = twire(netio[0])
            output_wire <<= Const(1, bitwidth=1, block=block)  # const "TRUE"
        elif command['cover_list'].asList() == ['1', '1']:
            # Populate clock list if one input is already a clock
            if(netio[1] in clk_set):
                clk_set.add(netio[0])
            elif(netio[0] in clk_set):
                clk_set.add(netio[1])
            else:
                output_wire = twire(netio[1])
                output_wire <<= twire(netio[0])  # simple wire
        elif command['cover_list'].asList() == ['0', '1']:
            output_wire = twire(netio[1])
            output_wire <<= ~ twire(netio[0])  # not gate
        elif command['cover_list'].asList() == ['11', '1']:
            output_wire = twire(netio[2])
            output_wire <<= twire(netio[0]) & twire(netio[1])  # and gate
        elif command['cover_list'].asList() == ['00', '1']:
            output_wire = twire(netio[2])
            output_wire <<= ~ (twire(netio[0]) | twire(netio[1]))  # nor gate
        elif command['cover_list'].asList() == ['1-', '1', '-1', '1']:
            output_wire = twire(netio[2])
            output_wire <<= twire(netio[0]) | twire(netio[1])  # or gate
        elif command['cover_list'].asList() == ['10', '1', '01', '1']:
            output_wire = twire(netio[2])
            output_wire <<= twire(netio[0]) ^ twire(netio[1])  # xor gate
        elif command['cover_list'].asList() == ['1-0', '1', '-11', '1']:
            output_wire = twire(netio[3])
            output_wire <<= (twire(netio[0]) & ~ twire(netio[2])) \
                | (twire(netio[1]) & twire(netio[2]))   # mux
        elif command['cover_list'].asList() == ['-00', '1', '0-0', '1']:
            output_wire = twire(netio[3])
            output_wire <<= (~twire(netio[1]) & ~twire(netio[2])) \
                | (~twire(netio[0]) & ~twire(netio[2]))
        else:
            raise PyrtlError('Blif file with unknown logic cover set "%s"'
                             '(currently gates are hard coded)' % command['cover_list'])

    def extract_flop(command):
        if(command['C'] not in ff_clk_set):
            ff_clk_set.add(command['C'])

        # Create register and assign next state to D and output to Q
        regname = command['Q'] + '_reg'
        flop = Register(bitwidth=1, name=regname)
        flop.next <<= twire(command['D'])
        flop_output = twire(command['Q'])
        init_val = command['I']
        if init_val == "1":
            # e.g. in Verilog: `initial reg <= 1;`
            raise PyrtlError("Initializing latches to 1 is not supported. "
                              "Acceptable values are: 0, 2 (don't care), and 3 (unknown); in any case, "
                              "PyRTL will ensure all stateful elements come up 0. "
                              "For finer control over the initial value, use specialized reset logic.")
        flop_output <<= flop

    for model in result:
        extract_inputs(model)
        extract_outputs(model)
        extract_commands(model)


# ----------------------------------------------------------------
#    __       ___  __       ___
#   /  \ |  |  |  |__) |  |  |
#   \__/ \__/  |  |    \__/  |
#

def output_to_firrtl(open_file, rom_blocks=None, block=None):
    """ Output the block as firrtl code to the output file.

    Output_to_firrtl(open_file, rom_block, block)
    If rom is intialized in pyrtl code, you can pass in the rom_blocks as a list [rom1, rom2, ...]
    """
    block = working_block(block)
    f = open_file
    # write out all the implicit stuff
    f.write("circuit Example : \n")
    f.write("  module Example : \n")
    f.write("    input clock : Clock\n    input reset : UInt<1>\n")
    # write out IO signals, wires and registers
    wireRegDefs = ""
    for wire in list(block.wirevector_subset()):
        if type(wire) == Input:
            f.write("    input %s : UInt<%d>\n" % (wire.name, wire.bitwidth))
        elif type(wire) == Output:
            f.write("    output %s : UInt<%d>\n" % (wire.name, wire.bitwidth))
        elif type(wire) == WireVector:
            wireRegDefs += "    wire {} : UInt<{}>\n".format(wire.name, wire.bitwidth)
        elif type(wire) == Register:
            wireRegDefs += "    reg {} : UInt<{}>, clock\n".format(wire.name, wire.bitwidth)
        elif type(wire) == Const:
            # some const is in the form like const_0_1'b1, is this legal operation?
            wire.name = wire.name.split("'").pop(0)
            wireRegDefs += "    node {} = UInt<{}>({})\n".format(wire.name, wire.bitwidth, wire.val)
        else:
            return 1
    f.write(wireRegDefs)
    f.write("\n")

    # write "Main"
    node_cntr = 0
    initializedMem = []
    for log_net in list(block.logic_subset()):
        if log_net.op == '&':
            f.write("    %s <= and(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                 log_net.args[1].name))
        elif log_net.op == '|':
            f.write("    %s <= or(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                log_net.args[1].name))
        elif log_net.op == '^':
            f.write("    %s <= xor(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                 log_net.args[1].name))
        elif log_net.op == 'n':
            f.write("    node T_%d = and(%s, %s)\n" % (node_cntr, log_net.args[0].name,
                                                       log_net.args[1].name))
            f.write("    %s <= not(T_%d)\n" % (log_net.dests[0].name, node_cntr))
            node_cntr += 1
        elif log_net.op == '~':
            f.write("    %s <= not(%s)\n" % (log_net.dests[0].name, log_net.args[0].name))
        elif log_net.op == '+':
            f.write("    %s <= add(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                 log_net.args[1].name))
        elif log_net.op == '-':
            f.write("    %s <= sub(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                 log_net.args[1].name))
        elif log_net.op == '*':
            f.write("    %s <= mul(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                 log_net.args[1].name))
        elif log_net.op == '=':
            f.write("    %s <= eq(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                log_net.args[1].name))
        elif log_net.op == '<':
            f.write("    %s <= lt(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                log_net.args[1].name))
        elif log_net.op == '>':
            f.write("    %s <= gt(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                log_net.args[1].name))
        elif log_net.op == 'w':
            f.write("    %s <= %s\n" % (log_net.dests[0].name, log_net.args[0].name))
        elif log_net.op == 'x':
            f.write("    %s <= mux(%s, %s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                     log_net.args[2].name, log_net.args[1].name))
        elif log_net.op == 'c':
            f.write("    %s <= cat(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                 log_net.args[1].name))
        elif log_net.op == 's':
            selEnd = log_net.op_param[0]
            if len(log_net.op_param) < 2:
                selBegin = selEnd
            else:
                selBegin = log_net.op_param[len(log_net.op_param)-1]
            f.write("    %s <= bits(%s, %s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                      selBegin, selEnd))
        elif log_net.op == 'r':
            f.write("    %s <= mux(reset, UInt<%s>(0), %s)\n" %
                    (log_net.dests[0].name, log_net.dests[0].bitwidth, log_net.args[0].name))
        elif log_net.op == 'm':
            # if there are rom blocks, need to be initialized
            if rom_blocks is not None:
                if not log_net.op_param[0] in initializedMem:
                    initializedMem.append(log_net.op_param[0])

                    # find corresponding rom block according to memid
                    curr_rom = next((x for x in rom_blocks if x.id == log_net.op_param[0]), None)
                    f.write("    wire %s : UInt<%s>[%s]\n" %
                            (log_net.op_param[1].name, log_net.op_param[1].bitwidth,
                             2**log_net.op_param[1].addrwidth))

                    # if rom data is a function, calculate the data first
                    if callable(curr_rom.data):
                        romdata = [curr_rom.data(i) for i in range(2**curr_rom.addrwidth)]
                        curr_rom.data = romdata

                    # write rom block initialization data
                    for i in range(len(curr_rom.data)):
                        f.write("    %s[%s] <= UInt<%s>(%s)\n" %
                                (log_net.op_param[1].name, i, log_net.op_param[1].bitwidth,
                                 curr_rom.data[i]))

                # write the connection
                f.write("    %s <= %s[%s]\n" % (log_net.dests[0].name, log_net.op_param[1].name,
                                                log_net.args[0].name))

            else:
                if not log_net.op_param[0] in initializedMem:
                    initializedMem.append(log_net.op_param[0])
                    f.write("    cmem %s_%s : UInt<%s>[%s]\n" %
                            (log_net.op_param[1].name, log_net.op_param[0],
                             log_net.op_param[1].bitwidth, 2**log_net.op_param[1].addrwidth))
                f.write("    infer mport T_%d  = %s_%s[%s], clock\n" %
                        (node_cntr, log_net.op_param[1].name, log_net.op_param[0],
                         log_net.args[0].name))
                f.write("    %s <= T_%d\n" % (log_net.dests[0].name, node_cntr))
                node_cntr += 1
        elif log_net.op == '@':
            if not log_net.op_param[0] in initializedMem:
                initializedMem.append(log_net.op_param[0])
                f.write("    cmem %s_%s : UInt<%s>[%s]\n" %
                        (log_net.op_param[1].name, log_net.op_param[0],
                         log_net.op_param[1].bitwidth, 2**log_net.op_param[1].addrwidth))
            f.write("    when %s :\n" % log_net.args[2].name)
            f.write("      infer mport T_%d  = %s_%s[%s], clock\n" %
                    (node_cntr, log_net.op_param[1].name, log_net.op_param[0],
                     log_net.args[0].name))
            f.write("      T_%d <= %s\n" % (node_cntr, log_net.args[1].name))
            f.write("      skip\n")
            node_cntr += 1
        else:
            pass

    f.close()
    return 0


def _trivialgraph_default_namer(thing, is_edge=True):
    """ Returns a "good" string for thing in printed graphs. """
    if is_edge:
        if thing.name is None or thing.name.startswith('tmp'):
            return ''
        else:
            return '/'.join([thing.name, str(len(thing))])
    elif isinstance(thing, Const):
        return str(thing.val)
    elif isinstance(thing, WireVector):
        return thing.name or '??'
    else:
        try:
            return thing.op + str(thing.op_param or '')
        except AttributeError:
            raise PyrtlError('no naming rule for "%s"' % str(thing))


def net_graph(block=None, split_state=False):
    """ Return a graph representation of the current block.

    Graph has the following form:
        { node1: { nodeA: edge1A, nodeB: edge1B},
          node2: { nodeB: edge2B, nodeC: edge2C},
          ...
        }

    aka: edge = graph[source][dest]

    Each node can be either a logic net or a WireVector (e.g. an Input, and Output, a
    Const or even an undriven WireVector (which acts as a source or sink in the network)
    Each edge is a WireVector or derived type (Input, Output, Register, etc.)
    Note that inputs, consts, and outputs will be both "node" and "edge".
    WireVectors that are not connected to any nets are not returned as part
    of the graph.
    """
    # FIXME: make it not try to add unused wires (issue #204)
    block = working_block(block)
    from .wire import Register
    # self.sanity_check()
    graph = {}

    # add all of the nodes
    for net in block.logic:
        graph[net] = {}

    wire_src_dict, wire_dst_dict = block.net_connections()
    dest_set = set(wire_src_dict.keys())
    arg_set = set(wire_dst_dict.keys())
    dangle_set = dest_set.symmetric_difference(arg_set)
    for w in dangle_set:
        graph[w] = {}
    if split_state:
        for w in block.wirevector_subset(Register):
            graph[w] = {}

    # add all of the edges
    for w in (dest_set & arg_set):
        try:
            _from = wire_src_dict[w]
        except Exception:
            _from = w
        if split_state and isinstance(w, Register):
            _from = w

        try:
            _to_list = wire_dst_dict[w]
        except Exception:
            _to_list = [w]

        for _to in _to_list:
            graph[_from][_to] = w

    return graph


def output_to_trivialgraph(file, namer=_trivialgraph_default_namer, block=None):
    """ Walk the block and output it in trivial graph format to the open file. """
    graph = net_graph(block)
    node_index_map = {}  # map node -> index

    # print the list of nodes
    for index, node in enumerate(graph):
        print('%d %s' % (index, namer(node, is_edge=False)), file=file)
        node_index_map[node] = index

    print('#', file=file)

    # print the list of edges
    for _from in graph:
        for _to in graph[_from]:
            from_index = node_index_map[_from]
            to_index = node_index_map[_to]
            edge = graph[_from][_to]
            print('%d %d %s' % (from_index, to_index, namer(edge)), file=file)


def _graphviz_default_namer(thing, is_edge=True, is_to_splitmerge=False):
    """ Returns a "good" graphviz label for thing. """
    if is_edge:
        if (thing.name is None or
                thing.name.startswith('tmp') or
                isinstance(thing, (Input, Output, Const, Register))):
            name = ''
        else:
            name = '/'.join([thing.name, str(len(thing))])
        penwidth = 2 if len(thing) == 1 else 6
        arrowhead = 'none' if is_to_splitmerge else 'normal'
        return '[label="%s", penwidth="%d", arrowhead="%s"]' % (name, penwidth, arrowhead)

    elif isinstance(thing, Const):
        return '[label="%d", shape=circle, fillcolor=lightgrey]' % thing.val
    elif isinstance(thing, (Input, Output)):
        return '[label="%s", shape=circle, fillcolor=none]' % thing.name
    elif isinstance(thing, Register):
        return '[label="%s", shape=square, fillcolor=gold]' % thing.name
    elif isinstance(thing, WireVector):
        return '[label="", shape=circle, fillcolor=none]'
    else:
        try:
            if thing.op == '&':
                return '[label="and"]'
            elif thing.op == '|':
                return '[label="or"]'
            elif thing.op == '^':
                return '[label="xor"]'
            elif thing.op == '~':
                return '[label="not"]'
            elif thing.op == 'x':
                return '[label="mux"]'
            elif thing.op in 'sc':
                return '[label="", height=.1, width=.1]'
            elif thing.op == 'r':
                name = thing.dests[0].name or ''
                return '[label="%s.next", shape=square, fillcolor=gold]' % name
            elif thing.op == 'w':
                return '[label="buf"]'
            else:
                return '[label="%s"]' % (thing.op + str(thing.op_param or ''))
        except AttributeError:
            raise PyrtlError('no naming rule for "%s"' % str(thing))


def output_to_graphviz(file, namer=_graphviz_default_namer, block=None):
    """ Walk the block and output it in graphviz format to the open file. """
    print(block_to_graphviz_string(block, namer), file=file)


def block_to_graphviz_string(block=None, namer=_graphviz_default_namer):
    """ Return a graphviz string for the block. """
    graph = net_graph(block, split_state=True)
    node_index_map = {}  # map node -> index

    rstring = """\
              digraph g {\n
              graph [splines="spline"];
              node [shape=circle, style=filled, fillcolor=lightblue1,
                    fontcolor=grey, fontname=helvetica, penwidth=0,
                    fixedsize=true];
              edge [labelfloat=false, penwidth=2, color=deepskyblue, arrowsize=.5];
              """

    # print the list of nodes
    for index, node in enumerate(graph):
        label = namer(node, is_edge=False)
        rstring += '    n%s %s;\n' % (index, label)
        node_index_map[node] = index

    # print the list of edges
    for _from in graph:
        for _to in graph[_from]:
            from_index = node_index_map[_from]
            to_index = node_index_map[_to]
            edge = graph[_from][_to]
            is_to_splitmerge = True if hasattr(_to, 'op') and _to.op in 'cs' else False
            label = namer(edge, is_to_splitmerge=is_to_splitmerge)
            rstring += '   n%d -> n%d %s;\n' % (from_index, to_index, label)

    rstring += '}\n'
    return rstring


def block_to_svg(block=None):
    """ Return an SVG for the block. """
    block = working_block(block)
    try:
        from graphviz import Source
        return Source(block_to_graphviz_string())._repr_svg_()
    except ImportError:
        raise PyrtlError('need graphviz installed (try "pip install graphviz")')


def trace_to_html(simtrace, trace_list=None, sortkey=None):
    """ Return a HTML block showing the trace. """

    from .simulation import SimulationTrace, _trace_sort_key
    if not isinstance(simtrace, SimulationTrace):
        raise PyrtlError('first arguement must be of type SimulationTrace')

    trace = simtrace.trace
    if sortkey is None:
        sortkey = _trace_sort_key

    if trace_list is None:
        trace_list = sorted(trace, key=sortkey)

    wave_template = (
        """\
        <script type="WaveDrom">
        { signal : [
        %s
        ]}
        </script>

        """
        )

    def extract(w):
        wavelist = []
        datalist = []
        last = None
        for i, value in enumerate(trace[w]):
            if last == value:
                wavelist.append('.')
            else:
                if len(w) == 1:
                    wavelist.append(str(value))
                else:
                    wavelist.append('=')
                    datalist.append(value)
                last = value

        wavestring = ''.join(wavelist)
        datastring = ', '.join(['"%d"' % data for data in datalist])
        if len(w) == 1:
            return bool_signal_template % (w, wavestring)
        else:
            return int_signal_template % (w, wavestring, datastring)

    bool_signal_template = '{ name: "%s",  wave: "%s" },'
    int_signal_template = '{ name: "%s",  wave: "%s", data: [%s] },'
    signals = [extract(w) for w in trace_list]
    all_signals = '\n'.join(signals)
    wave = wave_template % all_signals
    # print(wave)
    return wave
