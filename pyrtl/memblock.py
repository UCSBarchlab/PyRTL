"""
Defines MemBlock, a block of memory that can be read (async) and written (sync)
"""

from block import *
from wirevector import *


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

        self.block = working_block(block)

        if bitwidth <= 0:
            raise PyrtlError
        if addrwidth <= 0:
            raise PyrtlError
        if name is None:
            name = Block.next_tempvar_name()

        self.bitwidth = bitwidth
        self.name = name
        self.addrwidth = addrwidth
        self.stored_net = None
        self.id = Block.next_memid()
        self.read_addr = []  # arg
        self.read_data = []  # dest
        self.write_addr = []  # arg
        self.write_data = []  # arg
        self.write_enable = []  # arg

    def __getitem__(self, item):
        if not isinstance(item, WireVector):
            raise PyrtlError('error, index to a memblock must be a WireVector (or derived) type')
        if len(item) != self.addrwidth:
            raise PyrtlError('error, width of memblock index "%s" is %d, '
                             'addrwidth is %d' % (item.name, len(item), self.addrwidth))

        data = WireVector(bitwidth=self.bitwidth)
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
        net = LogicNet(
            op='m',
            op_param=(self.id, len(self.read_addr), len(self.write_addr)),
            args=tuple(self.read_addr + flattened_write_args),
            dests=tuple(self.read_data))
        self.block.add_net(net)
        self.stored_net = net

    def __setitem__(self, item, val):
        # check that 'item' is a valid address vector
        if not isinstance(item, WireVector):
            raise PyrtlError
        if len(item) != self.addrwidth:
            raise PyrtlError
        addr = item

        # check that 'val' is a valid datavector
        if isinstance(val, WireVector):
            data = val
            enable = Const(1, bitwidth=1)
        elif isinstance(val, MemBlock.EnabledWrite):
            data = val.data
            enable = val.enable
        else:
            raise PyrtlError
        if len(data) != self.bitwidth:
            raise PyrtlError
        if len(enable) != 1:
            raise PyrtlError

        self.write_data.append(data)
        self.write_addr.append(addr)
        self.write_enable.append(enable)
        self._update_net()
