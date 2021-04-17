"""
Function for creating FIRRTL from a Block, emitting it to a given file descriptor.
"""

from __future__ import print_function, unicode_literals

from ..pyrtlexceptions import PyrtlInternalError
from ..core import working_block
from ..wire import Input, Output, Const, Register
from ..passes import two_way_concat, one_bit_selects
from .graphs import _name_sorted, _net_sorted


def output_to_firrtl(open_file, rom_blocks=None, block=None):
    """ Output the block as FIRRTL code to the output file.

    :param open_file: File to write to
    :param rom_blocks: List of ROM blocks to be initialized
    :param block: Block to use (defaults to working block)

    If ROM is initialized in PyRTL code, you can pass in the rom_blocks as a list [rom1, rom2, ...].
    """
    block = working_block(block)

    # FIRRTL only allows 'bits' operations to have two parameters: a high and low
    # index representing the inclusive bounds of a contiguous range. PyRTL uses
    # slice syntax, which aren't always contiguous, so we need to convert them.
    one_bit_selects(block=block)  # pylint: disable=no-value-for-parameter,unexpected-keyword-arg

    # FIRRTL only allows 'concatenate' operations to have two arguments,
    # but PyRTL's 'c' op allows an arbitrary number of wires. We need to convert
    # these n-way concats to series of two-way concats accordingly.
    two_way_concat(block=block)  # pylint: disable=no-value-for-parameter,unexpected-keyword-arg

    f = open_file
    # write out all the implicit stuff
    f.write("circuit Example :\n")
    f.write("  module Example :\n")
    f.write("    input clock : Clock\n    input reset : UInt<1>\n")
    # write out IO signals, wires and registers
    for wire in _name_sorted(block.wirevector_subset(Input)):
        f.write("    input %s : UInt<%d>\n" % (wire.name, wire.bitwidth))
    for wire in _name_sorted(block.wirevector_subset(Output)):
        f.write("    output %s : UInt<%d>\n" % (wire.name, wire.bitwidth))
    for wire in _name_sorted(block.wirevector_subset(exclude=(Input, Output, Register, Const))):
        f.write("    wire %s : UInt<%d>\n" % (wire.name, wire.bitwidth))
    for wire in _name_sorted(block.wirevector_subset(Register)):
        f.write("    reg %s : UInt<%d>, clock\n" % (wire.name, wire.bitwidth))
    for wire in _name_sorted(block.wirevector_subset(Const)):
        # some const is in the form like const_0_1'b1, is this legal operation?
        wire.name = wire.name.split("'").pop(0)
        f.write("    node %s = UInt<%d>(%d)\n" % (wire.name, wire.bitwidth, wire.val))
    f.write("\n")

    # write "Main"
    node_cntr = 0
    initializedMem = []
    for log_net in _net_sorted(block.logic_subset()):
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
            if len(log_net.args) != 2:
                raise PyrtlInternalError(
                    "Expected concat net to have only two "
                    "argument wires; has %d" % len(log_net.args)
                )
            f.write("    %s <= cat(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                 log_net.args[1].name))
        elif log_net.op == 's':
            if len(log_net.op_param) != 1:
                raise PyrtlInternalError(
                    "Expected select net to have single "
                    "select bit; has %d" % len(log_net.op_param)
                )
            f.write("    %s <= bits(%s, %s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name,
                                                      log_net.op_param[0], log_net.op_param[0]))
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

    return 0
