"""
Defines MemBlock, a block of memory that can be read (async) and written (sync)
"""

import collections
import core
import wire
import helperfuncs
import conditional


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

# _MemAssignment is the type returned from assignment by |= or <<=
_MemAssignment = collections.namedtuple('_MemAssignment', 'rhs, is_conditional')


class _MemIndexed(collections.namedtuple('_MemIndexed', 'mem, index')):
    """ Object used internally to route memory assigns correctly. """

    def __ilshift__(self, other):
        return _MemAssignment(rhs=other, is_conditional=False)

    def __ior__(self, other):
        return _MemAssignment(rhs=other, is_conditional=True)


class MemBlock(object):
    """ An object for specifying block memories """

    EnabledWrite = collections.namedtuple('EnabledWrite', 'data, enable')

    # data <<= memory[addr]  (infer read port)
    # memory[addr] <<= data  (infer write port)
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
        from helperfuncs import as_wires
        item = as_wires(item, bitwidth=self.addrwidth, truncating=False, block=self.block)
        if len(item) > self.addrwidth:
            raise core.PyrtlError('error, memory index bitwidth > addrwidth')
        return _MemIndexed(mem=self, index=item)

    def _readaccess(self, addr):
        # FIXME: add conditional read ports
        return self._build_read_port(addr)

    def __setitem__(self, item, assignment):
        if isinstance(assignment, _MemAssignment):
            self._assignment(item, assignment.rhs, is_conditional=assignment.is_conditional)
        else:
            raise core.PyrtlError('error, assigment to memories should use "<<=" not "=" operator')

    def _assignment(self, item, val, is_conditional):
        from helperfuncs import as_wires
        item = as_wires(item, bitwidth=self.addrwidth, truncating=False, block=self.block)
        if len(item) > self.addrwidth:
            raise core.PyrtlError('error, memory index bitwidth > addrwidth')
        addr = item

        if isinstance(val, MemBlock.EnabledWrite):
            data, enable = val.data, val.enable
        else:
            data, enable = val, wire.Const(1, bitwidth=1, block=self.block)
        data = as_wires(data, bitwidth=self.bitwidth, truncating=False, block=self.block)
        enable = as_wires(enable, bitwidth=1, truncating=False, block=self.block)

        if len(data) != self.bitwidth:
            raise core.PyrtlError('error, write data larger than memory  bitwidth')
        if len(enable) != 1:
            raise core.PyrtlError('error, enable signal not exactly 1 bit')

        if is_conditional:
            conditional.ConditionalUpdate._build_write_port(self, addr, data, enable)
        else:
            self._build_write_port(addr, data, enable)

    def _build_read_port(self, addr):
        data = wire.WireVector(bitwidth=self.bitwidth, block=self.block)
        readport_net = core.LogicNet(
            op='m',
            op_param=(self.id, self),
            args=(addr,),
            dests=(data,))
        self.block.add_net(readport_net)
        self.readport_nets.append(readport_net)
        return data

    def _build_write_port(self, addr, data, enable):
        writeport_net = core.LogicNet(
            op='@',
            op_param=(self.id, self),
            args=(addr, data, enable),
            dests=tuple())
        self.block.add_net(writeport_net)
        self.writeport_nets.append(writeport_net)

    def __oldgetitem__(self, item):
        item = helperfuncs.as_wires(item, block=self.block)
        if len(item) != self.addrwidth:
            raise core.PyrtlError('error, width of memblock index "%s" is %d, '
                                  'addrwidth is %d' % (item.name, len(item), self.addrwidth))
        addr = item
        if conditional.ConditionalUpdate.currently_under_condition():
            return conditional.ConditionalUpdate._build_read_port(self, addr)
        else:
            return self._build_read_port(addr)

    def __oldsetitem__(self, item, val):
        # TODO: use "as_wires" to convert item and val if needed

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

        if conditional.ConditionalUpdate.currently_under_condition():
            conditional.ConditionalUpdate._build_write_port(self, addr, data, enable)
        else:
            self._build_write_port(addr, data, enable)
