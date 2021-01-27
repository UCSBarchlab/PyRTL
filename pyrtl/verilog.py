"""
Helper functions creating verilog implementations and testbenches.

Each of the functions in inputoutput take a block and a file descriptor.
The functions provided either read the file and update the Block
accordingly, or write information from the Block out to the file.
"""

from __future__ import print_function, unicode_literals
import re

from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .core import working_block, _NameSanitizer
from .wire import WireVector, Input, Output, Const, Register
from .corecircuits import concat
from .memory import RomBlock
from .inputoutput import _name_sorted, _net_sorted


# ----------------------------------------------------------------
#         ___  __          __   __
#   \  / |__  |__) | |    /  \ / _`
#    \/  |___ |  \ | |___ \__/ \__>
#

def output_to_verilog(dest_file, block=None):
    """ A function to walk the block and output it in verilog format to the open file. """

    block = working_block(block)
    file = dest_file
    internal_names = _VerilogSanitizer('_ver_out_tmp_')

    for wire in block.wirevector_set:
        internal_names.make_valid_string(wire.name)

    def varname(wire):
        return internal_names[wire.name]

    _to_verilog_header(file, block, varname)
    _to_verilog_combinational(file, block, varname)
    _to_verilog_sequential(file, block, varname)
    _to_verilog_memories(file, block, varname)
    _to_verilog_footer(file)


def OutputToVerilog(dest_file, block=None):
    """ A deprecated function to output verilog, use "output_to_verilog" instead. """
    return output_to_verilog(dest_file, block)


class _VerilogSanitizer(_NameSanitizer):
    _ver_regex = r'[_A-Za-z][_a-zA-Z0-9\$]*$'

    _verilog_reserved = \
        """always and assign automatic begin buf bufif0 bufif1 case casex casez cell cmos
        config deassign default defparam design disable edge else end endcase endconfig
        endfunction endgenerate endmodule endprimitive endspecify endtable endtask
        event for force forever fork function generate genvar highz0 highz1 if ifnone
        incdir include initial inout input instance integer join large liblist library
        localparam macromodule medium module nand negedge nmos nor noshowcancelledno
        not notif0 notif1 or output parameter pmos posedge primitive pull0 pull1
        pulldown pullup pulsestyle_oneventglitch pulsestyle_ondetectglitch remos real
        realtime reg release repeat rnmos rpmos rtran rtranif0 rtranif1 scalared
        showcancelled signed small specify specparam strong0 strong1 supply0 supply1
        table task time tran tranif0 tranif1 tri tri0 tri1 triand trior trireg unsigned
        use vectored wait wand weak0 weak1 while wire wor xnor xor
        """

    def __init__(self, internal_prefix='_sani_temp', map_valid_vals=True):
        self._verilog_reserved_set = frozenset(self._verilog_reserved.split())
        super(_VerilogSanitizer, self).__init__(self._ver_regex, internal_prefix,
                                                map_valid_vals, self._extra_checks)

    def _extra_checks(self, str):
        return(str not in self._verilog_reserved_set  # is not a Verilog reserved keyword
               and str != 'clk'                       # not the clock signal
               and len(str) <= 1024)                  # not too long to be a Verilog id


def _verilog_vector_size_decl(n):
    return '' if n == 1 else '[{:d}:0]'.format(n - 1)


def _verilog_vector_decl(w):
    return _verilog_vector_size_decl(len(w))


def _verilog_block_parts(block):
    inputs = block.wirevector_subset(Input)
    outputs = block.wirevector_subset(Output)
    registers = block.wirevector_subset(Register)
    wires = block.wirevector_subset() - (inputs | outputs | registers)
    memories = {n.op_param[1] for n in block.logic_subset('m@')}
    return inputs, outputs, registers, wires, memories


def _to_verilog_header(file, block, varname):
    """ Print the header of the verilog implementation. """

    def name_sorted(wires):
        return _name_sorted(wires, name_mapper=varname)

    def name_list(wires):
        return [varname(w) for w in wires]

    print('// Generated automatically via PyRTL', file=file)
    print('// As one initial test of synthesis, map to FPGA with:', file=file)
    print('//   yosys -p "synth_xilinx -top toplevel" thisfile.v\n', file=file)

    inputs, outputs, registers, wires, memories = _verilog_block_parts(block)

    # module name
    io_list = ['clk'] + name_list(name_sorted(inputs)) + name_list(name_sorted(outputs))
    if any(w.startswith('tmp') for w in io_list):
        raise PyrtlError('input or output with name starting with "tmp" indicates unnamed IO')
    io_list_str = ', '.join(io_list)
    print('module toplevel({:s});'.format(io_list_str), file=file)

    # inputs and outputs
    print('    input clk;', file=file)
    for w in name_sorted(inputs):
        print('    input{:s} {:s};'.format(_verilog_vector_decl(w), varname(w)), file=file)
    for w in name_sorted(outputs):
        print('    output{:s} {:s};'.format(_verilog_vector_decl(w), varname(w)), file=file)
    print('', file=file)

    # memories and registers
    for m in sorted(memories, key=lambda m: m.id):
        memwidth_str = _verilog_vector_size_decl(m.bitwidth)
        memsize_str = _verilog_vector_size_decl(1 << m.addrwidth)
        print('    reg{:s} mem_{}{:s}; //{}'.format(memwidth_str, m.id,
                                                    memsize_str, m.name), file=file)
    for w in name_sorted(registers):
        print('    reg{:s} {:s};'.format(_verilog_vector_decl(w), varname(w)), file=file)
    if (memories or registers):
        print('', file=file)

    # wires
    for w in name_sorted(wires):
        print('    wire{:s} {:s};'.format(_verilog_vector_decl(w), varname(w)), file=file)
    print('', file=file)

    # Write the initial values for read-only memories.
    # If we ever add support outside of simulation for initial values
    #  for MemBlocks, that would also go here.
    roms = {m for m in memories if isinstance(m, RomBlock)}
    for m in sorted(roms, key=lambda m: m.id):
        print('    initial begin', file=file)
        for i in range(1 << m.addrwidth):
            mem_elem_str = 'mem_{}[{:d}]'.format(m.id, i)
            mem_data_str = "{:d}'h{:x}".format(m.bitwidth, m._get_read_data(i))
            print('        {:s}={:s};'.format(mem_elem_str, mem_data_str), file=file)
        print('    end', file=file)
        print('', file=file)


def _to_verilog_combinational(file, block, varname):
    """ Print the combinational logic of the verilog implementation. """

    def name_sorted(wires):
        return _name_sorted(wires, name_mapper=varname)

    print('    // Combinational', file=file)

    # assign constants (these could be folded for readability later)
    for const in name_sorted(block.wirevector_subset(Const)):
        print('    assign {:s} = {:d};'.format(varname(const), const.val), file=file)

    # walk the block and output combination logic
    for net in _net_sorted(block.logic, varname):
        if net.op in 'w~':  # unary ops
            opstr = '' if net.op == 'w' else net.op
            t = (varname(net.dests[0]), opstr, varname(net.args[0]))
            print('    assign %s = %s%s;' % t, file=file)
        elif net.op in '&|^+-*<>':  # binary ops
            t = (varname(net.dests[0]), varname(net.args[0]),
                 net.op, varname(net.args[1]))
            print('    assign %s = %s %s %s;' % t, file=file)
        elif net.op == '=':
            t = (varname(net.dests[0]), varname(net.args[0]),
                 varname(net.args[1]))
            print('    assign %s = %s == %s;' % t, file=file)
        elif net.op == 'x':
            # note that the argument order for 'x' is backwards from the ternary operator
            t = (varname(net.dests[0]), varname(net.args[0]),
                 varname(net.args[2]), varname(net.args[1]))
            print('    assign %s = %s ? %s : %s;' % t, file=file)
        elif net.op == 'c':
            catlist = ', '.join([varname(w) for w in net.args])
            t = (varname(net.dests[0]), catlist)
            print('    assign %s = {%s};' % t, file=file)
        elif net.op == 's':
            # someone please check if we need this special handling for scalars
            catlist = ', '.join([varname(net.args[0]) + '[%s]' % str(i)
                                if len(net.args[0]) > 1 else varname(net.args[0])
                                for i in reversed(net.op_param)])
            t = (varname(net.dests[0]), catlist)
            print('    assign %s = {%s};' % t, file=file)
        elif net.op in 'rm@':
            pass  # do nothing for registers and memories
        else:
            raise PyrtlInternalError("nets with op '{}' not supported".format(net.op))
    print('', file=file)


def _to_verilog_sequential(file, block, varname):
    """ Print the sequential logic of the verilog implementation. """
    if not block.logic_subset(op='r'):
        return

    print('    // Registers', file=file)
    print('    always @( posedge clk )', file=file)
    print('    begin', file=file)
    for net in _net_sorted(block.logic, varname):
        if net.op == 'r':
            dest, src = (varname(net.dests[0]), varname(net.args[0]))
            print('        {:s} <= {:s};'.format(dest, src), file=file)
    print('    end', file=file)
    print('', file=file)


def _to_verilog_memories(file, block, varname):
    """ Print the memories of the verilog implementation. """
    memories = {n.op_param[1] for n in block.logic_subset('m@')}
    for m in sorted(memories, key=lambda m: m.id):
        print('    // Memory mem_{}: {}'.format(m.id, m.name), file=file)
        print('    always @( posedge clk )', file=file)
        print('    begin', file=file)
        for net in _net_sorted(block.logic_subset('@'), varname):
            if net.op_param[1] == m:
                t = (varname(net.args[2]), net.op_param[0],
                     varname(net.args[0]), varname(net.args[1]))
                print(('        if (%s) begin\n'
                       '                mem_%s[%s] <= %s;\n'
                       '        end') % t, file=file)
        print('    end', file=file)
        for net in _net_sorted(block.logic_subset('m'), varname):
            if net.op_param[1] == m:
                dest = varname(net.dests[0])
                m_id = net.op_param[0]
                index = varname(net.args[0])
                print('    assign {:s} = mem_{}[{:s}];'.format(dest, m_id, index), file=file)
        print('', file=file)


def _to_verilog_footer(file):
    print('endmodule\n', file=file)


# ----------------------------------------------------------------
#   ___  ___  __  ___  __   ___       __
#    |  |__  /__`  |  |__) |__  |\ | /  ` |__|
#    |  |___ .__/  |  |__) |___ | \| \__, |  |
#

def output_verilog_testbench(dest_file, simulation_trace=None, toplevel_include=None,
                             vcd="waveform.vcd", cmd=None, block=None):
    """Output a Verilog testbench for the block/inputs used in the simulation trace.

    :param dest_file: an open file to which the test bench will be printed.
    :param simulation_trace: a simulation trace from which the inputs will be extracted
        for inclusion in the test bench.  The test bench generated will just replay the
        inputs played to the simulation cycle by cycle.
    :param toplevel_include: name of the file containing the toplevel module this testbench
        is testing.  If not None, an '`include' directive will be added to the top.
    :param vcd: By default the testbench generator will include a command in the testbench
        to write the output of the testbench execution to a .vcd file (via $dumpfile), and
        this parameter is the string of the name of the file to use.  If None is specified
        instead, then no dumpfile will be used.
    :param cmd: The string passed as cmd will be copied verbatim into the testbench at the
        just before the end of each cycle. This is useful for doing things like printing
        specific values out during testbench evaluation (e.g. cmd='$display("%d", out);'
        will instruct the testbench to print the value of 'out' every cycle which can then
        be compared easy with a reference.

    The test bench does not return any values.

    Example 1 (writing testbench to a string)::

        with io.StringIO() as tbfile:
            pyrtl.output_verilog_testbench(dest_file=tbfile, simulation_trace=sim_trace)

    Example 2 (testbench in same file as verilog)::

        with open('hardware.v', 'w') as fp:
            output_to_verilog(fp)
            output_verilog_testbench(fp, sim.tracer, vcd=None, cmd='$display("%d", out);')

    """
    block = working_block(block)

    inputs, outputs, registers, wires, memories = _verilog_block_parts(block)

    ver_name = _VerilogSanitizer('_ver_out_tmp_')
    for wire in block.wirevector_set:
        ver_name.make_valid_string(wire.name)

    # Output an include, if given
    if toplevel_include:
        print('`include "{:s}"'.format(toplevel_include), file=dest_file)
        print('', file=dest_file)

    # Output header
    print('module tb();', file=dest_file)

    # Declare all block inputs as reg
    print('    reg clk;', file=dest_file)
    for w in inputs:
        print('    reg {:s} {:s};'.format(_verilog_vector_decl(w), ver_name[w.name]),
              file=dest_file)

    # Declare all block outputs as wires
    for w in outputs:
        print('    wire {:s} {:s};'.format(_verilog_vector_decl(w), ver_name[w.name]),
              file=dest_file)
    print('', file=dest_file)

    # Declare an integer used for init of memories
    print('    integer tb_iter;', file=dest_file)

    # Instantiate logic block
    io_list = [ver_name[w.name] for w in block.wirevector_subset((Input, Output))]
    io_list.append('clk')
    io_list_str = ['.{0:s}({0:s})'.format(w) for w in io_list]
    print('    toplevel block({:s});\n'.format(', '.join(io_list_str)), file=dest_file)

    # Generate clock signal
    print('    always', file=dest_file)
    print('        #5 clk = ~clk;\n', file=dest_file)

    # Move through all steps of trace, writing out input assignments per cycle
    print('    initial begin', file=dest_file)

    # If a VCD output is requested, set that up
    if vcd:
        print('        $dumpfile ("%s");' % vcd, file=dest_file)
        print('        $dumpvars;\n', file=dest_file)

    # Initialize clk, and all the registers and memories
    print('        clk = 0;', file=dest_file)
    for r in registers:
        print('        block.%s = 0;' % ver_name[r.name], file=dest_file)
    for m in memories:
        print('        for(tb_iter=0;tb_iter<%d;tb_iter++) begin block.mem_%s[tb_iter] = 0; end' %
              (1 << m.addrwidth, m.id), file=dest_file)

    if simulation_trace:
        tracelen = max(len(t) for t in simulation_trace.trace.values())
        for i in range(tracelen):
            for w in inputs:
                print('        {:s} = {:s}{:d};'.format(
                    ver_name[w.name],
                    "{:d}'d".format(len(w)),
                    simulation_trace.trace[w][i]), file=dest_file)
            if cmd:
                print('        %s' % cmd, file=dest_file)
            print('\n        #10', file=dest_file)

    # Footer
    print('        $finish;', file=dest_file)
    print('    end', file=dest_file)
    print('endmodule', file=dest_file)
