"""
Helper functions for viewing the block visually.

Each of the functions in visualization take a block and a file descriptor.
The functions provided write the block as a given visual format to the file.
"""

from __future__ import print_function, unicode_literals
import collections

from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .core import working_block, LogicNet
from .wire import WireVector, Input, Output, Const, Register


def net_graph(block=None, split_state=False):
    """ Return a graph representation of the given block.

    :param block: block to use (defaults to current working block)
    :param split_state: if True, split connections to/from a register update net; this
        means that registers will be appear as source nodes of the network, and
        'r' nets (i.e. the logic for setting a register's next value) will
        be treated as sink nodes of the network.

    The graph has the following form:
        { node1: { nodeA: [edge1A_1, edge1A_2], nodeB: [edge1B]},
          node2: { nodeB: [edge2B],             nodeC: [edge2C_1, edge2C_2]},
          ...
        }

    aka: edges = graph[source][dest]

    Each node can be either a logic net or a WireVector (e.g. an Input, an Output, a
    Const or even an undriven WireVector (which acts as a source or sink in the network).
    Each edge is a WireVector or derived type (Input, Output, Register, etc.).
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
    for w in (dest_set | arg_set):
        try:
            _from = wire_src_dict[w]
        except Exception:
            _from = w  # e.g. an Input/Const
        if split_state and isinstance(w, Register):
            _from = w

        try:
            _to_list = wire_dst_dict[w]
        except Exception:
            graph[_from][w] = [w]  # e.g. an Output
        else:
            for _to in _to_list:
                graph[_from][_to] = list(filter(lambda arg: arg is w, _to.args))

    return graph


# -----------------------------------------------------------------
#    ___  __   ___
#     |  / _` |___
#     |  \__> |

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


def output_to_trivialgraph(file, namer=_trivialgraph_default_namer, block=None, split_state=False):
    """ Walk the block and output it in trivial graph format to the open file.

    :param file: Open file to write to
    :param namer: A function that takes in an object (a wire or logicnet) as the first argument and
        a boolean `is_edge` as the second that is set True if the object is a wire, and returns
        a string representing that object.
    :param block: Block to use (defaults to current working block)
    :param split_state: if True, split connections to/from a register update net; this
        means that registers will be appear as source nodes of the network, and
        'r' nets (i.e. the logic for setting a register's next value) will
        be treated as sink nodes of the network.
    """
    graph = net_graph(block, split_state)
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
            for edge in graph[_from][_to]:
                print('%d %d %s' % (from_index, to_index, namer(edge)), file=file)


# -----------------------------------------------------------------
#     __   __        __              __
#    / _` |__)  /\  |__) |__| \  / |  /
#    \__> |  \ /~~\ |    |  |  \/  | /__

def _default_edge_namer(edge, is_to_splitmerge=False, extra_edge_info=None):
    """
    A function for naming an edge for use in the graphviz graph.

    :param edge: the edge (i.e. WireVector or deriving class)
    :param is_to_splitmerge: if the node to which the edge points
        is a select or concat operation
    :param extra_edge_info: a map from edge to any additional data you want
        to print associated with it (e.g. timing data)
    :return: a function that can be called by graph namer function you pass
        in to block_to_graphviz_string
    """

    name = '' if edge.name is None else '/'.join([edge.name, str(len(edge))])
    if extra_edge_info and edge in extra_edge_info:
        # Always label an edge if present in the extra_edge_info map
        name = name + " (" + str(extra_edge_info[edge]) + ")"
    elif (edge.name is None
          or edge.name.startswith('tmp')
          or isinstance(edge, (Input, Output, Const, Register))):
        name = ''

    penwidth = 2 if len(edge) == 1 else 6
    arrowhead = 'none' if is_to_splitmerge else 'normal'
    return '[label="%s", penwidth="%d", arrowhead="%s"]' % (name, penwidth, arrowhead)


def _default_node_namer(node, split_state=False, extra_node_info=None):
    """
    A function for naming a node for use in the graphviz graph.

    :param node: the node (i.e. WireVector or deriving class, or a logic net)
    :param split_state: if True, split connections to/from a register update net; this
        means that registers will be appear as source nodes of the network, and
        'r' nets (i.e. the logic for setting a register's next value) will
        be treated as sink nodes of the network.
    :param extra_node_info: a map from node to any additional data you want
        to print associated with it (e.g. delay data)
    :return: a function that can be called by graph namer function you pass
        in to block_to_graphviz_string
    """
    def label(v):
        if extra_node_info and node in extra_node_info:
            v = v + " (" + str(extra_node_info[node]) + ")"
        return v

    if isinstance(node, Const):
        name = node.name + ': ' if not node.name.startswith('const_') else ''
        return '[label="%s", shape=circle, fillcolor=lightgrey]' % label(name + str(node.val))
    elif isinstance(node, Input):
        return '[label="%s", shape=invhouse, fillcolor=coral]' % label(node.name)
    elif isinstance(node, Output):
        return '[label="%s", shape=house, fillcolor=lawngreen]' % label(node.name)
    elif isinstance(node, Register):
        return '[label="%s", shape=square, fillcolor=gold]' % label(node.name)
    elif isinstance(node, WireVector):
        return '[label="%s", shape=circle, fillcolor=none]' % label(node.name)
    else:
        try:
            if node.op == '&':
                return '[label="%s"]' % label("and")
            elif node.op == '|':
                return '[label="%s"]' % label("or")
            elif node.op == '^':
                return '[label="%s"]' % label("xor")
            elif node.op == '~':
                return '[label="%s", shape=invtriangle]' % label("not")
            elif node.op == 'x':
                return '[label="%s", shape=invtrapezium]' % label("mux")
            elif node.op == 's':
                # node.op_param is a tuple of the selected bits to pull from the argument wire,
                # so it could look something like (0,0,0,0,0,0,0), meaning dest wire is going
                # to be a concatenation of the zero-th bit of the argument wire, 7 times.
                selLower = node.op_param[0]
                selUpper = node.op_param[-1]
                if len(node.op_param) == 1:
                    bits = "[%d]" % selLower
                elif node.op_param == tuple(range(selLower, selUpper + 1)):  # consecutive
                    bits = "[%d:%d]" % (selUpper, selLower)
                elif all([ix == node.op_param[0] for ix in node.op_param[1:]]):  # all the same
                    bits = "[%d]*%d" % (node.op_param[0], len(node.op_param))
                else:
                    bits = "bits" + str(tuple(reversed(node.op_param)))
                return '[label="%s", fillcolor=azure1, height=.25, width=.25]' % label(bits)
            elif node.op in 'c':
                return '[label="%s", height=.1, width=.1]' % label("concat")
            elif node.op == 'r':
                name = node.dests[0].name or ''
                name = ("%s.next" % name) if split_state else name
                return '[label="%s", shape=square, fillcolor=gold]' % label(name)
            elif node.op == 'w':
                return '[label="%s", height=.1, width=.1]' % label("")
            elif node.op in 'm@':
                name = node.op_param[1].name
                if name.startswith("tmp"):
                    name = ""
                else:
                    name = "(" + name + ")"
                return '[label="%s"]' % label(node.op + name)
            else:
                return '[label="%s"]' % label(node.op + str(node.op_param or ''))
        except AttributeError:
            raise PyrtlError('no naming rule for "%s"' % str(node))


def _graphviz_default_namer(
        thing,
        is_edge,
        is_to_splitmerge,
        split_state,
        node_namer=_default_node_namer,
        edge_namer=_default_edge_namer):
    """ Returns a "good" Graphviz label for thing.

    :param thing: The edge (wire) or node (logic net or Input/Output/Const) to name
    :param is_edge: True if thing is an edge
    :param is_to_splitmerge: if the node to which the edge points
        is a select or concat operation
    :param split_state: If True, visually split the connections to/from a register update net.
    :param node_namer: A function mapping a node to a label; one of its arguments
        is a dict mapping nodes to nodes to additional user-supplied information.
    :param edge_namer: A function mapping an edge to a label; one of its arguments
        is a dict mapping nodes to nodes to additional user-supplied information.
    :return: A function that knows how to label each element in the graph, which
        can be passed to 'output_to_graphviz' or 'block_to_graphviz_string'
    """
    if is_edge:
        return edge_namer(thing, is_to_splitmerge=is_to_splitmerge)
    else:
        return node_namer(thing, split_state=split_state)


def graphviz_detailed_namer(
        extra_node_info=None,
        extra_edge_info=None):
    """ Returns a detailed Graphviz namer that prints extra information
    about nodes/edges in the given maps.

    :param extra_node_info: A dict from node to some object about that node
        (its string representation will be printed next to the node's label)
    :param extra_edge_info: A dict from edge to some object about that edge
        (its string representation will be printed next to the edge's label)
    :return: A function that knows how to label each element in the graph, which
        can be passed to 'output_to_graphviz' or 'block_to_graphviz_string'

    If both dict arguments are None, the returned namer behaves identically
    to the default Graphviz namer.
    """

    def node_namer(node, split_state):
        return _default_node_namer(node, split_state, extra_node_info)

    def edge_namer(edge, is_to_splitmerge):
        return _default_edge_namer(edge, is_to_splitmerge, extra_edge_info)

    def namer(thing, is_edge, is_to_splitmerge, split_state):
        return _graphviz_default_namer(
            thing, is_edge, is_to_splitmerge, split_state,
            node_namer=node_namer, edge_namer=edge_namer)
    return namer


def output_to_graphviz(file, block=None, namer=_graphviz_default_namer,
                       split_state=True, maintain_arg_order=False):
    """ Walk the block and output it in Graphviz format to the open file.

    :param file: Open file to write to
    :param block: Block to use (defaults to current working block)
    :param namer: Function used to label each edge and node; see 'block_to_graphviz_string'
        for more information.
    :param split_state: If True, visually split the connections to/from a register update net.
    :param maintain_arg_order: If True, will add ordering constraints so that that incoming edges
        are ordered left-to-right for nets where argument order matters (e.g. '<'). Keeping this
        as False results in a cleaner, though less visually precise, graphical output.
    """
    print(block_to_graphviz_string(block, namer, split_state, maintain_arg_order), file=file)


def block_to_graphviz_string(block=None, namer=_graphviz_default_namer,
                             split_state=True, maintain_arg_order=False):
    """ Return a Graphviz string for the block.

    :param namer: A function mapping graph objects (wires/logic nets) to labels.
        If you want a more detailed namer, pass in a call to `graphviz_detailed_namer` (see below).
    :param block: Block to use (defaults to current working block)
    :param split_state: If True, split connections to/from a register update net; this
        means that registers will be appear as source nodes of the network, and
        'r' nets (i.e. the logic for setting a register's next value) will
        be treated as sink nodes of the network.
    :param maintain_arg_order: If True, will add ordering constraints so that that incoming edges
        are ordered left-to-right for nets where argument order matters (e.g. '<'). Keeping this
        as False results in a cleaner, though less visually precise, graphical output.

    The normal namer function will label user-named wires with their names and label the nodes
    (logic nets or Input/Output/Const terminals) with their operator symbol or name/value,
    respectively. If custom information about each node in the graph is desired, you can pass
    in a custom namer function which must have the same signature as the default namer,
    `_graphviz_default_namer`. However, we recommend you instead pass in a call to
    `graphviz_detailed_namer`, supplying it with your own dicts mapping wires and nodes to labels.
    For any wire/node found in these maps, that additional information will be printed in
    parentheses alongside the node in the graphviz graph.

    For example, if you wanted to print the delay of each wire and the fanout of each
    gate, you could pass in two maps to the `graphviz_detailed_namer` call, which returns a namer
    function that can subsequently be passed to 'output_to_graphviz' or
    'block_to_graphviz_string'. ::

        node_fanout = {n: "Fanout: %d" % my_fanout_func(n) for n in working_block().logic}
        wire_delay = {w: "Delay: %.2f" % my_delay_func(w) for w in working_block().wirevector_set}

        with open("out.gv", "w") as f:
            output_to_graphviz(f, namer=graphviz_detailed_namer(node_fanout, wire_delay))
    """
    graph = net_graph(block, split_state)
    node_index_map = {}  # map node -> index

    rstring = """\
digraph g {
    graph [splines="spline", outputorder="edgesfirst"];
    node [shape=circle, style=filled, fillcolor=lightblue1,
        fontcolor=black, fontname=helvetica, penwidth=0,
        fixedsize=shape];
    edge [labelfloat=false, penwidth=2, color=deepskyblue, arrowsize=.5];
"""
    from .importexport import _natural_sort_key

    def _node_sort_key(node):
        if isinstance(node, LogicNet):
            if node.op == '@':
                key = str(node.args[2])
            else:
                key = node.dests[0].name
        else:
            key = node.name
        return _natural_sort_key(key)

    # print the list of nodes
    for index, node in enumerate(sorted(graph.keys(), key=_node_sort_key)):
        label = namer(node, False, False, split_state)
        rstring += '    n%s %s;\n' % (index, label)
        node_index_map[node] = index

    # print the list of edges
    srcs = collections.defaultdict(list)
    for _from in sorted(graph.keys(), key=_node_sort_key):
        for _to in sorted(graph[_from].keys(), key=_node_sort_key):
            from_index = node_index_map[_from]
            to_index = node_index_map[_to]
            for edge in graph[_from][_to]:
                is_to_splitmerge = True if hasattr(_to, 'op') and _to.op in 'cs' else False
                label = namer(edge, True, is_to_splitmerge, False)
                rstring += '    n%d -> n%d %s;\n' % (from_index, to_index, label)
                srcs[_to].append((_from, edge))

    # Maintain left-to-right order of incoming wires for nets where order matters.
    # This won't be visually perfect sometimes (especially for a wire used twice
    # in a net's argument list), but for the majority of cases this will improve
    # the visualization.
    def index_of(w, args):
        # Special helper so we compare id rather than using builtin operators
        ix = 0
        for arg in args:
            if w is arg:
                return ix
            ix += 1
        raise PyrtlInternalError('Expected to find wire in set of args')

    if maintain_arg_order:
        block = working_block(block)
        for net in sorted(block.logic_subset(op='c-<>x@'), key=_node_sort_key):
            args = [(node_index_map[n], wire) for (n, wire) in srcs[net]]
            args.sort(key=lambda t: index_of(t[1], net.args))
            s = ' -> '.join(['n%d' % n for n, _ in args])
            rstring += '    {\n'
            rstring += '        rank=same;\n'
            rstring += '        edge[style=invis];\n'
            rstring += '        ' + s + ';\n'
            rstring += '        rankdir=LR;\n'
            rstring += '    }\n'

    rstring += '}\n'
    return rstring


# -----------------------------------------------------------------
#     __        __
#    /__` \  / / _`
#    .__/  \/  \__>

def output_to_svg(file, block=None, split_state=True):
    """ Output the block as an SVG to the open file.

    :param file: Open file to write to
    :param block: Block to use (defaults to current working block)
    :param split_state: If True, visually split the connections to/from a register update net.
    """
    print(block_to_svg(block, split_state), file=file)


def block_to_svg(block=None, split_state=True, maintain_arg_order=False):
    """ Return an SVG for the block.

    :param block: Block to use (defaults to current working block)
    :param split_state: If True, visually split the connections to/from a register update net.
    :param maintain_arg_order: If True, will add ordering constraints so that that incoming edges
        are ordered left-to-right for nets where argument order matters (e.g. '<'). Keeping this
        as False results in a cleaner, though less visually precise, graphical output.
    :return: The SVG representation of the block
    """
    try:
        from graphviz import Source
        return Source(block_to_graphviz_string(block, split_state=split_state,
                                               maintain_arg_order=maintain_arg_order))._repr_svg_()
    except ImportError:
        raise PyrtlError('need graphviz installed (try "pip install graphviz")')


# -----------------------------------------------------------------
#         ___
#    |__|  |  |\/| |
#    |  |  |  |  | |___

def trace_to_html(simtrace, trace_list=None, sortkey=None):
    """ Return a HTML block showing the trace.

    :param simtrace: A SimulationTrace object
    :param trace_list: (optional) A list of wires to display
    :param sortkey: (optional) The key with which to sort the trace_list
    :return: An HTML block showing the trace
    """

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
