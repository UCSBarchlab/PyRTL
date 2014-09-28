"""
Defines MemBlock, a block of memory that can be read (async) and written (sync)
"""

import collections
import core
import wire
import helperfuncs


#------------------------------------------------------------------------
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

        if bitwidth <= 0:
            raise core.PyrtlError('error, bitwidth must be >= 1')
        if addrwidth <= 0:
            raise core.PyrtlError('error, addrwidth must be >= 1')
        if name is None:
            name = core.Block.next_tempvar_name()

        self.bitwidth = bitwidth
        self.name = name
        self.addrwidth = addrwidth
        self.stored_net = None
        self.id = core.Block.next_memid()
        self.read_addr = []  # arg
        self.read_data = []  # dest
        self.write_addr = []  # arg
        self.write_data = []  # arg
        self.write_enable = []  # arg

    def __getitem__(self, item):
        if not isinstance(item, wire.WireVector):
            raise core.PyrtlError('error, index to memblock must be WireVector (or derived) type')
        if len(item) != self.addrwidth:
            raise core.PyrtlError('error, width of memblock index "%s" is %d, '
                                  'addrwidth is %d' % (item.name, len(item), self.addrwidth))

        data = wire.WireVector(bitwidth=self.bitwidth, block=self.block)
        self.read_data.append(data)
        self.read_addr.append(item)
        self._update_net()
        return data

    def _update_net(self):
        if self.stored_net:
            self.block.logic.remove(self.stored_net)
        assert len(self.write_addr) == len(self.write_data)  # not sure about this one

        # construct the arg list from reads and writes
        coupled_write_args = zip(self.write_addr, self.write_data, self.write_enable)
        flattened_write_args = [item for sublist in coupled_write_args for item in sublist]
        net = core.LogicNet(
            op='m',
            op_param=(self.id, len(self.read_addr), len(self.write_addr)),
            args=tuple(self.read_addr + flattened_write_args),
            dests=tuple(self.read_data))
        self.block.add_net(net)
        self.stored_net = net

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

        self.write_data.append(data)
        self.write_addr.append(addr)
        self.write_enable.append(enable)
        self._update_net()
