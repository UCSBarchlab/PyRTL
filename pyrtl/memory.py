"""
Defines PyRTL memories. These blocks of memories can be read (potentially async) and
written (sync)

MemBlocks supports any number of the following operations:

- read: `d = mem[address]`

- write: `mem[address] <<= d`

- write with an enable: `mem[address] <<= MemBlock.EnabledWrite(d, enable=we)`

Based on the number of reads and writes a memory will be inferred with the correct
number of ports to support that
"""

from __future__ import annotations

import collections
import numbers
import types
from typing import NamedTuple

from pyrtl.core import Block, LogicNet, _NameIndexer, working_block
from pyrtl.corecircuits import as_wires
from pyrtl.helperfuncs import infer_val_and_bitwidth
from pyrtl.pyrtlexceptions import PyrtlError
from pyrtl.wire import Const, WireVector, WireVectorLike, next_tempvar_name

# ------------------------------------------------------------------------
#
#         ___        __   __          __        __   __
#   |\/| |__   |\/| /  \ |__) \ /    |__) |    /  \ /  ` |__/
#   |  | |___  |  | \__/ |  \  |     |__) |___ \__/ \__, |  \
#


_memIndex = _NameIndexer()

_MemAssignment = collections.namedtuple("_MemAssignment", "rhs, is_conditional")
"""_MemAssignment is the type returned from assignment by |= or <<="""


def _reset_memory_indexer():
    global _memIndex
    _memIndex = _NameIndexer()


class _MemIndexed(WireVector):
    """Object used internally to route memory assigns correctly.

    The normal PyRTL user should never need to be aware that this class exists, hence
    the underscore in the name. It presents a very similar interface to WireVectors (all
    of the normal wirevector operations should still work), but if you try to *set* the
    value with <<= or |= then it will generate a _MemAssignment object rather than the
    normal wire assignment.
    """

    def __init__(self, mem, index):
        self.mem = mem
        self.index = index
        self.wire = None

    def __ilshift__(self, other):
        return _MemAssignment(rhs=other, is_conditional=False)

    def __ior__(self, other):
        return _MemAssignment(rhs=other, is_conditional=True)

    def _two_var_op(self, other, op):
        return as_wires(self)._two_var_op(other, op)

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

    @property
    def name(self):
        return as_wires(self).name

    @name.setter
    def name(self, n):
        as_wires(self).name = n


class MemBlock:
    """``MemBlock`` is the object for specifying block memories.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    ``MemBlock`` can be indexed like an array for reads and writes. Example::

        >>> mem = pyrtl.MemBlock(bitwidth=8, addrwidth=2)

        >>> # Write to each address, starting from address 1.
        >>> write_addr = pyrtl.Register(name="write_addr", bitwidth=2, reset_value=1)
        >>> write_addr.next <<= write_addr + 1

        >>> # Read from each address, starting from address 0.
        >>> read_addr = pyrtl.Register(name="read_addr", bitwidth=2)
        >>> read_addr.next <<= read_addr + 1

        >>> read_data = pyrtl.Output(name="read_data")
        >>> read_data <<= mem[read_addr]  # Creates a read port.
        >>> mem[write_addr] <<= write_addr + 10  # Creates a write port.

        >>> sim = pyrtl.Simulation()
        >>> sim.step_multiple(nsteps=6)
        >>> sim.tracer.trace["write_addr"]
        [1, 2, 3, 0, 1, 2]
        >>> sim.tracer.trace["read_addr"]
        [0, 1, 2, 3, 0, 1]
        >>> sim.tracer.trace["read_data"]
        [0, 11, 12, 13, 10, 11]

    .. doctest only::

        >>> pyrtl.reset_working_block()

    When the address of a memory is assigned to using an :class:`EnabledWrite` object,
    data will only be written to the memory when the ``EnabledWrite``'s
    :attr:`~EnabledWrite.enable` ``WireVector`` is set to high (``1``). In the following
    example, the ``MemBlock`` is only written when ``write_addr`` is odd::

        >>> mem = pyrtl.MemBlock(bitwidth=8, addrwidth=2)

        >>> write_addr = pyrtl.Register(name="write_addr", bitwidth=2)
        >>> write_addr.next <<= write_addr + 1
        >>> mem[write_addr] <<= pyrtl.MemBlock.EnabledWrite(
        ...     enable=write_addr[0], data=write_addr + 10)

        >>> sim = pyrtl.Simulation()
        >>> sim.step_multiple(nsteps=6)
        >>> sorted(sim.inspect_mem(mem).items())
        [(1, 11), (3, 13)]

    Writes under :ref:`conditional_assignment` are automatically converted to
    :class:`EnabledWrites<EnabledWrite>`.

    .. _asynchronous_memories:

    Asynchronous Memories
    ---------------------

    It is best practice to have memory operations start on a rising clock edge if you
    want them to synthesize into efficient hardware, so ``MemBlocks`` are `synchronous`
    by default (``asynchronous=False``). ``MemBlocks`` will enforce this by checking
    that all their inputs are ready at each rising clock edge. This implies that all
    ``MemBlock`` inputs - the address to read/write, the data to write, and the
    write-enable bit - must be registers, inputs, or constants, unless you explicitly
    declare the memory as `asynchronous` with ``asynchronous=True``.

    Asynchronous memories can be convenient and tempting, but they are rarely a good
    idea. They can't be mapped to block RAMs in FPGAs and will be converted to registers
    by most design tools. They are not a realistic option for memories with more than a
    few hundred elements.

    Read and Write Ports
    --------------------

    Each read or write to the memory will create a new `port` (either a read port or
    write port respectively). By default memories are limited to 2 read ports and 1
    write port, to keep designs efficient by default, but those values can be changed
    with ``max_read_ports`` and ``max_write_ports``. Note that memories with many ports
    may not map to physical memories such as block RAMs or existing memory hardware
    macros.

    Default Values
    --------------

    In PyRTL :class:`Simulation`, all ``MemBlocks`` are zero-initialized by default.
    Initial data can be specified for each MemBlock in :meth:`Simulation.__init__`'s
    ``memory_value_map``.

    Simultaneous Read and Write
    ---------------------------

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    In PyRTL :class:`Simulation`, if the same address is read and written in the same
    cycle, the read will return the `last` value stored in the ``MemBlock``, not the
    newly written value. Example::

        >>> mem = pyrtl.MemBlock(addrwidth=1, bitwidth=1)
        >>> mem[0] <<= 1
        >>> read_data = pyrtl.Output(name="read_data", bitwidth=1)
        >>> read_data <<= mem[0]

        >>> # In the first cycle, read_data will be the default MemBlock data value
        >>> # (0), not the newly written value (1).
        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> sim.inspect("read_data")
        0

        # In the second cycle, read_data will be the newly written value (1).
        >>> sim.step()
        >>> sim.inspect("read_data")
        1

    Mapping ``MemBlocks`` to Hardware
    ---------------------------------

    Synchronous ``MemBlocks`` can generally be mapped to FPGA block RAMs and similar
    hardware, but there are many pitfalls:

    #. ``asynchronous=False`` is generally necessary, but may not be sufficient, for
       mapping a design to FPGA block RAMs. Block RAMs may have additional timing
       constraints, like requiring register outputs for each block RAM.
       ``asynchronous=False`` only requires register inputs.

    #. Block RAMs may offer more or less read and write ports than ``MemBlock``'s
       defaults.

    #. Block RAMs may not zero-initialize by default.

    #. Block RAMs may implement simultaneous reads and writes in different ways.
    """

    # FIXME: write ports assume that only one port is under control of the conditional
    class EnabledWrite(NamedTuple):
        """Generates logic to conditionally enable a write port."""

        data: WireVector
        """Data to write."""
        enable: WireVector
        """Single-bit ``WireVector`` indicating if a write should occur."""

    def __init__(
        self,
        bitwidth: int,
        addrwidth: int,
        name: str = "",
        max_read_ports: int = 2,
        max_write_ports: int = 1,
        asynchronous: bool = False,
        block: Block = None,
    ):
        """Create a PyRTL read-write memory.

        :param bitwidth: The bitwidth of each element in the memory.
        :param addrwidth: The number of bits used to address an element in the memory.
            The memory can store ``2 ** addrwidth`` elements.
        :param name: Name of the memory. Defaults to an autogenerated name.
        :param max_read_ports: limits the number of read ports each block can create;
            passing ``None`` indicates there is no limit.
        :param max_write_ports: limits the number of write ports each block can create;
            passing ``None`` indicates there is no limit.
        :param asynchronous: If ``False``, ensure that all memory inputs are registers,
            inputs, or constants. See :ref:`asynchronous_memories`.
        :param block: The block to add the MemBlock to, defaults to the
            :ref:`working_block`.
        """
        self.max_read_ports = max_read_ports
        self.num_read_ports = 0
        self.block = working_block(block)
        name = next_tempvar_name(name)

        if bitwidth <= 0:
            msg = "bitwidth must be >= 1"
            raise PyrtlError(msg)
        if addrwidth <= 0:
            msg = "addrwidth must be >= 1"
            raise PyrtlError(msg)

        self.bitwidth = bitwidth
        self.name = name
        self.addrwidth = addrwidth
        self.readport_nets = []
        self.id = _memIndex.next_index()
        self.asynchronous = asynchronous
        self.block._add_memblock(self)

        self.max_write_ports = max_write_ports
        self.num_write_ports = 0
        self.writeport_nets = []

    @property
    def read_ports(self):
        msg = "read_ports now called num_read_ports for clarity"
        raise PyrtlError(msg)

    def __getitem__(self, addr: WireVectorLike) -> WireVector:
        """Create a read port to read data from the ``MemBlock``.

        :param addr: ``MemBlock`` address to read. A ``WireVector``, or any type that
            can be coerced to ``WireVector`` by :func:`as_wires`.

        :return: A ``WireVector`` containing the data read from the ``MemBlock`` at
                 address ``addr``.
        """
        addr = as_wires(addr, bitwidth=self.addrwidth, truncating=False)
        if len(addr) > self.addrwidth:
            msg = "memory index bitwidth > addrwidth"
            raise PyrtlError(msg)
        return _MemIndexed(mem=self, index=addr)

    def __setitem__(
        self, addr: WireVectorLike, data: MemBlock.EnabledWrite | WireVectorLike
    ):
        """Create a write port to write data to the ``MemBlock``.

        :param addr: ``MemBlock`` address to write. A ``WireVector``, or any type that
            can be coerced to ``WireVector`` by :func:`as_wires`.
        :param data: ``MemBlock`` data to write. An :class:`EnabledWrite`,
            ``WireVector``, or any type that can be coerced to ``WireVector`` by
            :func:`as_wires`.
        """
        if isinstance(data, _MemAssignment):
            self._assignment(addr, data.rhs, is_conditional=data.is_conditional)
        else:
            msg = 'error, assigment to memories should use "<<=" not "=" operator'
            raise PyrtlError(msg)

    def _readaccess(self, addr):
        # FIXME: add conditional read ports
        return self._build_read_port(addr)

    def _build_read_port(self, addr):
        if self.max_read_ports is not None:
            self.num_read_ports += 1
            if self.num_read_ports > self.max_read_ports:
                msg = f"maximum number of read ports ({self.max_read_ports}) exceeded"
                raise PyrtlError(msg)
        data = WireVector(bitwidth=self.bitwidth)
        readport_net = LogicNet(
            op="m", op_param=(self.id, self), args=(addr,), dests=(data,)
        )
        working_block().add_net(readport_net)
        self.readport_nets.append(readport_net)
        return data

    def _assignment(self, item, val, is_conditional):
        from pyrtl.conditional import _build

        # Even though as_wires is already called on item already in the __getitem__
        # method, we need to call it again here because __setitem__ passes the original
        # item to _assignment.
        addr = as_wires(item, bitwidth=self.addrwidth, truncating=False)

        if isinstance(val, MemBlock.EnabledWrite):
            data, enable = val.data, val.enable
        else:
            data, enable = val, Const(1, bitwidth=1)
        data = as_wires(data, bitwidth=self.bitwidth, truncating=False)
        enable = as_wires(enable, bitwidth=1, truncating=False)

        if len(data) != self.bitwidth:
            msg = "error, write data larger than memory bitwidth"
            raise PyrtlError(msg)
        if len(enable) != 1:
            msg = "error, enable signal not exactly 1 bit"
            raise PyrtlError(msg)

        if is_conditional:
            _build(self, (addr, data, enable))
        else:
            self._build(addr, data, enable)

    def _build(self, addr, data, enable):
        """Builds a write port."""
        if self.max_write_ports is not None:
            self.num_write_ports += 1
            if self.num_write_ports > self.max_write_ports:
                msg = f"maximum number of write ports ({self.max_write_ports}) exceeded"
                raise PyrtlError(msg)
        writeport_net = LogicNet(
            op="@", op_param=(self.id, self), args=(addr, data, enable), dests=()
        )
        working_block().add_net(writeport_net)
        self.writeport_nets.append(writeport_net)

    def _make_copy(self, block=None):
        block = working_block(block)
        return MemBlock(
            bitwidth=self.bitwidth,
            addrwidth=self.addrwidth,
            name=self.name,
            max_read_ports=self.max_read_ports,
            max_write_ports=self.max_write_ports,
            asynchronous=self.asynchronous,
            block=block,
        )


class RomBlock(MemBlock):
    """PyRTL Read Only Memory (ROM).

    ``RomBlocks`` are PyRTL's read only memory block. They support the same read
    interface as :class:`MemBlock`, but they cannot be written to (i.e. there are no
    write ports). The ROM's contents are specified when the ROM is constructed.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example that creates and reads a 4-element ROM::

        >>> rom = pyrtl.RomBlock(bitwidth=3, addrwidth=2, romdata=[4, 5, 6, 7])
        >>> read_addr = pyrtl.Register(name="read_addr", bitwidth=2)
        >>> read_addr.next <<= read_addr + 1
        >>> data = pyrtl.Output(name="data")
        >>> data <<= rom[read_addr]

        >>> sim = pyrtl.Simulation()
        >>> sim.step_multiple(nsteps=6)
        >>> sim.tracer.trace["read_addr"]
        [0, 1, 2, 3, 0, 1]
        >>> sim.tracer.trace["data"]
        [4, 5, 6, 7, 4, 5]
    """

    def __init__(
        self,
        bitwidth: int,
        addrwidth: int,
        romdata,
        name: str = "",
        max_read_ports: int = 2,
        build_new_roms: bool = False,
        asynchronous: bool = False,
        pad_with_zeros: bool = False,
        block: Block = None,
    ):
        """Create a PyRTL Read Only Memory.

        :param bitwidth: The bitwidth of each element in the ROM.
        :param addrwidth: The number of bits used to address an element in the ROM. The
            ROM can store ``2 ** addrwidth`` elements.
        :param romdata: Specifies the data stored in the ROM. This can either be a
            function or an array (iterable) that maps from address to data.
        :param name: The identifier for the memory.
        :param max_read_ports: Limits the number of read ports each block can create;
            passing ``None`` indicates there is no limit.
        :param build_new_roms: Indicates whether :meth:`RomBlock.__getitem__` should
            create copies of the ``RomBlock`` to avoid exceeding ``max_read_ports``.
        :param asynchronous: If ``False``, ensure that all ``RomBlock`` inputs are
            registers, inputs, or constants. See :ref:`asynchronous_memories`.
        :param pad_with_zeros: If ``True``, fill any missing ``romdata`` with zeros so
            all accesses to the ROM are well defined. Otherwise, :class:`Simulation`
            will raise an exception when accessing unintialized data. If you are
            generating Verilog, you will need to specify a value for every address (in
            which case setting this to ``True`` will help), however for testing and
            simulation it useful to know if you are accessing an unspecified value
            (which is why it is ``False`` by default).
        :param block: The block to add to, defaults to the :ref:`working_block`.
        """

        super().__init__(
            bitwidth=bitwidth,
            addrwidth=addrwidth,
            name=name,
            max_read_ports=max_read_ports,
            max_write_ports=0,
            asynchronous=asynchronous,
            block=block,
        )
        self.data = romdata
        self.build_new_roms = build_new_roms
        self.current_copy = self
        self.pad_with_zeros = pad_with_zeros

    def __getitem__(self, addr: WireVector) -> WireVector:
        """Create a read port to read data from the ``RomBlock``.

        If ``build_new_roms`` was specified, create a new copy of the ``RomBlock`` if
        the number of read ports exceeds ``max_read_ports``.

        :param addr: ``MemBlock`` address to read.

        :raises PyrtlError: If ``addr`` is an ``int``. ``RomBlocks`` hold constant data,
            so they don't need to be read when the read address is statically known.
            Create a :class:`Const` with the data at the read address instead.

        :return: A ``WireVector`` containing the data read from the ``RomBlock`` at
                 address ``addr``.
        """
        if isinstance(addr, numbers.Number):
            msg = (
                "There is no point in indexing into a RomBlock with an int. Instead, "
                "get the value from the source data for this Rom"
            )
            raise PyrtlError(msg)
            # If you really know what you are doing, use a Const WireVector instead.
        return super().__getitem__(addr)

    def __setitem__(self, item, assignment):
        msg = "no writing to a read-only memory"
        raise PyrtlError(msg)

    def _get_read_data(self, address: int):
        """_get_read_data is called by the simulator to fetch RomBlock data.

        :param address: address is a dynamic run-time value (an integer), *not* a
            WireVector.

        """
        try:
            if address < 0 or address > 2**self.addrwidth - 1:
                raise PyrtlError("Invalid address, " + str(address) + " specified")
        except TypeError as exc:
            msg = f"Address: {address} with invalid type specified"
            raise PyrtlError(msg) from exc
        if isinstance(self.data, types.FunctionType):
            try:
                value = self.data(address)
            except Exception as exc:
                msg = "Invalid data function for RomBlock"
                raise PyrtlError(msg) from exc
        else:
            try:
                value = self.data[address]
            except KeyError as exc:
                if self.pad_with_zeros:
                    value = 0
                else:
                    msg = (
                        f"RomBlock key {address} is invalid, consider using "
                        "pad_with_zeros=True for defaults"
                    )
                    raise PyrtlError(msg) from exc
            except IndexError as exc:
                if self.pad_with_zeros:
                    value = 0
                else:
                    msg = (
                        f"RomBlock index {address} is invalid, consider using "
                        "pad_with_zeros=True for defaults"
                    )
                    raise PyrtlError(msg) from exc
            except Exception as exc:
                msg = "invalid type for RomBlock data object"
                raise PyrtlError(msg) from exc

        try:
            value = infer_val_and_bitwidth(value, bitwidth=self.bitwidth).value
        except TypeError as exc:
            msg = f"Value: {value} from rom {self} has an invalid type"
            raise PyrtlError(msg) from exc
        return value

    def _build_read_port(self, addr):
        if self.build_new_roms and (
            self.current_copy.num_read_ports >= self.current_copy.max_read_ports
        ):
            self.current_copy = self._make_copy()
        return super(RomBlock, self.current_copy)._build_read_port(addr)

    def _make_copy(
        self,
        block=None,
    ):
        block = working_block(block)
        return RomBlock(
            bitwidth=self.bitwidth,
            addrwidth=self.addrwidth,
            romdata=self.data,
            name=self.name,
            max_read_ports=self.max_read_ports,
            asynchronous=self.asynchronous,
            pad_with_zeros=self.pad_with_zeros,
            block=block,
        )
