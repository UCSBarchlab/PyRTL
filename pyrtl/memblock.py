"""
Defines MemBlock, a block of memory that can be read (async) and written (sync)
"""

import collections
import core
import wire
import helperfuncs


# ------------------------------------------------------------------------
#
#         ___        __   __          __        __   __
#   |\/| |__   |\/| /  \ |__) \ /    |__) |    /  \ /  ` |__/
#   |  | |___  |  | \__/ |  \  |     |__) |___ \__/ \__, |  \
#

# MemBlock supports any number of the following operations:
# read: d = mem[address]
# write: mem[address] = d
# write with an enable: mem[address] = MemBlock.EnabledWrite(d,enable=we)
# Based on the number of reads and writes a memory will be inferred
# with the correct number of ports to support that

class MemBlock(object):
    """ An object for specifying block memories """

    EnabledWrite = collections.namedtuple('EnabledWrite', 'data, enable')

    # data = memory[addr]  (infer read port)
    # memory[addr] = data  (infer write port)
    # Not currently implemented:  memory[addr] <<= data (infer write port)
    def __init__(self,  bitwidth, addrwidth, name=None, block=None):

        self.block = core.working_block(block)
        name = self.block.next_tempvar_name(name)

        if bitwidth <= 0:
            raise core.PyrtlError('error, bitwidth must be >= 1')
        if addrwidth <= 0:
            raise core.PyrtlError('error, addrwidth must be >= 1')

        self.bitwidth = bitwidth
        self.name = name
        self.addrwidth = addrwidth
        self.readport_nets = []
        self.writeport_nets = []
        self.id = core.Block.next_memid()

    def __getitem__(self, item):
        if not isinstance(item, wire.WireVector):
            raise core.PyrtlError('error, index to memblock must be WireVector (or derived) type')
        if len(item) != self.addrwidth:
            raise core.PyrtlError('error, width of memblock index "%s" is %d, '
                                  'addrwidth is %d' % (item.name, len(item), self.addrwidth))

        addr = item
        data = wire.WireVector(bitwidth=self.bitwidth, block=self.block)
        readport_net = core.LogicNet(
            op='m',
            op_param=(self.id, self),
            args=(addr,),
            dests=(data,))
        self.block.add_net(readport_net)
        self.readport_nets.append(readport_net)
        return data

    def __setitem__(self, item, val):
        # check that 'item' is a valid address vector
        if not isinstance(item, wire.WireVector):
            raise core.PyrtlError('error, address not a valide WireVector')
        if len(item) != self.addrwidth:
            raise core.PyrtlError('error, address width passed different from declaration')
        addr = item

        # check that 'val' is a valid datavector
        if isinstance(val, wire.WireVector):
            data = val
            enable = wire.Const(1, bitwidth=1, block=self.block)
        elif isinstance(val, MemBlock.EnabledWrite):
            data = val.data
            enable = val.enable
        else:
            raise core.PyrtlError('error, write data must be WireVector or EnabledWrite')
        if len(data) != self.bitwidth:
            raise core.PyrtlError('error, write data not of the correct bitwidth')
        if len(enable) != 1:
            raise core.PyrtlError('error, enable signal not exactly 1 bit')

        writeport_net = core.LogicNet(
            op='@',
            op_param=(self.id, self),
            args=(addr, data, enable),
            dests=tuple())
        self.block.add_net(writeport_net)
        self.writeport_nets.append(writeport_net)
