"""
Defines PyRTL memories.
These blocks of memories can be read (potentially async) and written (sync)

MemBlocks supports any number of the following operations:
read: d = mem[address]
write: mem[address] = d
write with an enable: mem[address] = MemBlock.EnabledWrite(d,enable=we)
Based on the number of reads and writes a memory will be inferred
with the correct number of ports to support that
"""

from __future__ import print_function, unicode_literals
import collections

from .pyrtlexceptions import PyrtlError
from .core import working_block, LogicNet
from .wire import WireVector, Const, wvIndexer
from .helperfuncs import as_wires

# ------------------------------------------------------------------------
#
#         ___        __   __          __        __   __
#   |\/| |__   |\/| /  \ |__) \ /    |__) |    /  \ /  ` |__/
#   |  | |___  |  | \__/ |  \  |     |__) |___ \__/ \__, |  \
#


_MemAssignment = collections.namedtuple('_MemAssignment', 'rhs, is_conditional')
"""_MemAssignment is the type returned from assignment by |= or <<="""


class _MemIndexed(WireVector):
    """ Object used internally to route memory assigns correctly.

    The normal PyRTL user should never need to be aware that this class exists,
    hence the underscore in the name.  It presents a very similar interface to
    wiresVectors (all of the normal wirevector operations should still work),
    but if you try to *set* the value with <<= or |= then it will generate a
    _MemAssignment object rather than the normal wire assignment. """

    def __init__(self, mem, index):
        self.mem = mem
        self.index = index

    def __ilshift__(self, other):
        return _MemAssignment(rhs=other, is_conditional=False)

    def __ior__(self, other):
        return _MemAssignment(rhs=other, is_conditional=True)

    def logicop(self, other, op):
        return as_wires(self).logicop(other, op)

    def __invert__(self):
        return as_wires(self).__invert__()

    def __getitem__(self, item):
        return as_wires(self).__getitem__(item)

    def __len__(self):
        return self.mem.bitwidth

    def sign_extended(self, bitwidth):
        return as_wires(self).sign_extended(bitwidth)

    def zero_extended(self, bitwidth):
        return as_wires(self).zero_extended(bitwidth)


class _MemReadBase(object):
    """This is the base class for the memories and ROM blocks and
    it implements the read and initialization operations needed for
    both of them"""

    # FIXME: right now read port is built unconditionally (no read enable)

    def __init__(self,  bitwidth, addrwidth, name, asynchronous, block):
        self.block = working_block(block)
        name = wvIndexer.next_tempvar_name(name)

        if bitwidth <= 0:
            raise PyrtlError('bitwidth must be >= 1')
        if addrwidth <= 0:
            raise PyrtlError('addrwidth must be >= 1')

        self.bitwidth = bitwidth
        self.name = name
        self.addrwidth = addrwidth
        self.readport_nets = []
        self.id = wvIndexer.next_memid()
        self.asynchronous = asynchronous

    def __getitem__(self, item):
        """ Builds circuitry to retrieve an item from the memory
        """
        from .helperfuncs import as_wires
        item = as_wires(item, bitwidth=self.addrwidth, truncating=False)
        if len(item) > self.addrwidth:
            raise PyrtlError('memory index bitwidth > addrwidth')
        return _MemIndexed(mem=self, index=item)

    def _readaccess(self, addr):
        # FIXME: add conditional read ports
        return self._build_read_port(addr)

    def _build_read_port(self, addr):
        data = WireVector(bitwidth=self.bitwidth)
        readport_net = LogicNet(
            op='m',
            op_param=(self.id, self),
            args=(addr,),
            dests=(data,))
        working_block().add_net(readport_net)
        self.readport_nets.append(readport_net)
        return data

    def __setitem__(self, key, value):
        """ Not legal on a object that only allows for reads"""
        raise PyrtlError("error, invalid call __setitem__ made on _MemReadBase")

    def _make_copy(self, block):
        pass


class MemBlock(_MemReadBase):
    """ An object for specifying read and write enabled block memories """
    # FIXME: write ports assume that only one port is under control of the conditional

    EnabledWrite = collections.namedtuple('EnabledWrite', 'data, enable')
    """ Allows for an enable bit for each write port

    Usage:
    mem[address] = MemBlock.EnabledWrite(d,enable=we)

    When the address of a memory is assigned to using a EnableWrite object
    items will only be written to the memory when the enable WireVector is
    set to high (1)
    """

    # data <<= memory[addr]  (infer read port)
    # memory[addr] <<= data  (infer write port)
    def __init__(self, bitwidth, addrwidth, name=None, asynchronous=False, block=None):
        """
        Create a PyRTL read-write memory.

        :param int bitwidth: Defines the bitwidth of each element in the memory
        :param int addrwidth: The number of bits used to address an element of the
         memory. This also defines the size of the memory
        :param bool asynchronous: if false check that memories only indexed by registers
        :param basestring or None name: Name of the memory. Defaults to an autogenerated
         name
        :param block: the block to add it to. Defaults to the working block

        It is best practice to make sure your block memory/fifos read/write
        operations start on a clock edge.  MemBlocks will enforce this by making sure that
        you only address them with a register or input, unless you explicitly declare
        the memory as asynchronous with that flag.  Note that asynchronous mems are
        harder to synthesize (and can't be mapped to block rams in FPGAs).
        """
        super(MemBlock, self).__init__(bitwidth, addrwidth, name, asynchronous, block)
        self.writeport_nets = []

    def __setitem__(self, item, assignment):
        """ Builds circuitry to set an item in the memory """
        if isinstance(assignment, _MemAssignment):
            self._assignment(item, assignment.rhs, is_conditional=assignment.is_conditional)
        else:
            raise PyrtlError('error, assigment to memories should use "<<=" not "=" operator')

    def _assignment(self, item, val, is_conditional):
        from .helperfuncs import as_wires
        from .conditional import _build

        item = as_wires(item, bitwidth=self.addrwidth, truncating=False)
        if len(item) > self.addrwidth:
            raise PyrtlError('error, memory index bitwidth > addrwidth')
        addr = item

        if isinstance(val, MemBlock.EnabledWrite):
            data, enable = val.data, val.enable
        else:
            data, enable = val, Const(1, bitwidth=1)
        data = as_wires(data, bitwidth=self.bitwidth, truncating=False)
        enable = as_wires(enable, bitwidth=1, truncating=False)

        if len(data) != self.bitwidth:
            raise PyrtlError('error, write data larger than memory  bitwidth')
        if len(enable) != 1:
            raise PyrtlError('error, enable signal not exactly 1 bit')

        if is_conditional:
            _build(self, (addr, data, enable))
        else:
            self._build(addr, data, enable)

    def _build(self, addr, data, enable):
        """ Builds a write port. """
        writeport_net = LogicNet(
            op='@',
            op_param=(self.id, self),
            args=(addr, data, enable),
            dests=tuple())
        working_block().add_net(writeport_net)
        self.writeport_nets.append(writeport_net)

    def _make_copy(self, block=None):
        block = working_block(block)
        return MemBlock(bitwidth=self.bitwidth,
                        addrwidth=self.addrwidth,
                        name=self.name,
                        asynchronous=self.asynchronous,
                        block=block)


class RomBlock(_MemReadBase):
    """ PyRTL Read Only Memory.

    RomBlocks are the read only memory format in PyRTL
    """
    def __init__(self, bitwidth, addrwidth, romdata, name=None, asynchronous=False, block=None):
        """
        Create a Python Read Only Memory

        :param int bitwidth: The bitwidth of each item stored in the ROM
        :param int addrwidth: The bitwidth of the address bus (determines number of addresses)
        :param function or iterable romdata: This can either be a function or an array that maps
          an address as an input to a result as an output
        :param str name: The identifier for the memory
        :param bool asynchronous: If False, check that memory reads start on clock edge

        It is best practice to make sure your block memory/fifos read/write
        operations start on a clock edge.  MemBlocks will enforce this by making sure that
        you only address them with a register or input, unless you explicitly declare
        the memory as asynchronous with that flag.  Note that asynchronous mems are
        harder to synthesize (and can't be mapped to block rams in FPGAs).
        """

        super(RomBlock, self).__init__(bitwidth, addrwidth, name, asynchronous, block)
        self.data = romdata

    def __getitem__(self, item):
        import numbers
        if isinstance(item, numbers.Number):
            raise PyrtlError("There is no point in indexing into a RomBlock with an int "
                             "Instead, get the value from the source data for this Rom")
            # If you really know what you are doing, use a Const WireVector instead.
        return super(RomBlock, self).__getitem__(item)

    def _get_read_data(self, address):
        import types
        try:
            if address < 0 or address > 2**self.addrwidth - 1:
                raise PyrtlError("Invalid address, " + str(address) + " specified")
        except TypeError:
            raise PyrtlError("Address: {} with invalid type specified".format(address))
        if isinstance(self.data, types.FunctionType):
            try:
                value = self.data(address)
            except Exception:
                raise PyrtlError("Invalid data function for RomBlock")
        else:
            try:
                value = self.data[address]
            except KeyError:
                value = 0
            except:
                raise PyrtlError("invalid type for RomBlock data object")

        try:
            if value < 0 or value >= 2**self.bitwidth:
                raise PyrtlError("invalid value for RomBlock data")
        except TypeError:
            raise PyrtlError("Value: {} from rom {} has an invalid type"
                             .format(value, self))
        return value

    def _make_copy(self, block=None):
        block = working_block(block)
        return RomBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                        romdata=self.data, name=self.name,
                        asynchronous=self.asynchronous, block=block)
