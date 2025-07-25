"""The core abstraction for hardware in PyRTL.

Included in this file you will find:

* `LogicNet` -- the core class holding a "net" in the netlist
* `Block` -- a collection of nets with associated access and error checking
* `working_block` -- the "current" Block to which, by default, all created nets are
                     added
* `modes` -- access methods for "modes" such as debug

"""

from __future__ import annotations

import collections
import inspect
import keyword
import re
from typing import TYPE_CHECKING, NamedTuple

from pyrtl.pyrtlexceptions import PyrtlError, PyrtlInternalError

if TYPE_CHECKING:
    from pyrtl.memory import MemBlock
    from pyrtl.wire import Register, WireVector


# -----------------------------------------------------------------
#    __        __   __
#   |__) |    /  \ /  ` |__/
#   |__) |___ \__/ \__, |  \
#
class LogicNet(NamedTuple):
    """The basic immutable datatype for storing a "net" in a netlist.

    ``LogicNet`` is part of PyRTL's internal representation. What it is, and how it is
    used are only required for advanced PyRTL users.

    A "net" is a Python representation of a hardware logic operation. These operations
    include binary operations like `and` `or` and `not`, arithmetic operations like `+`
    and `-`, and other operations like concatenating wires, splitting wires,
    reading/writing memory, and register logic:

    ===== ========== ========== ======== ====
    op    op_param   args       dests
    ===== ========== ========== ======== ====
    ``&`` ``None``   ``a1, a2`` ``out``  AND two wires together, put result
                                         into ``out``
    ``|`` ``None``   ``a1, a2`` ``out``  OR two wires together, put result into
                                         ``out``
    ``^`` ``None``   ``a1, a2`` ``out``  XOR two wires together, put result
                                         into ``out``
    ``n`` ``None``   ``a1, a2`` ``out``  NAND two wires together, put result
                                         into ``out``
    ``~`` ``None``   ``a1``     ``out``  invert one wire, put result into
                                         ``out``
    ``+`` ``None``   ``a1, a2`` ``out``  add ``a1`` and ``a2``, put result into
                                         ``out``

                                         ``len(out) == max(len(a1), len(a2)) + 1``

                                         Performs *unsigned* addition. Use
                                         :func:`signed_add` for signed
                                         addition.
    ``-`` ``None``   ``a1, a2`` ``out``  subtract ``a2`` from ``a1``, put
                                         result into ``out``

                                         ``len(out) == max(len(a1), len(a2)) + 1``

                                         Performs *unsigned* subtraction. Use
                                         :func:`signed_sub` for signed
                                         subtraction.
    ``*`` ``None``   ``a1, a2`` ``out``  multiply ``a1`` & ``a2``, put result
                                         into ``out``

                                         ``len(out) == len(a1) + len(a2)``

                                         Performs *unsigned* multiplication.
                                         Use :func:`signed_mult` for signed
                                         multiplication.
    ``=`` ``None``   ``a1, a2`` ``out``  check ``a1`` & ``a2`` equal, put
                                         result into ``out`` (0 | 1)
    ``<`` ``None``   ``a1, a2`` ``out``  check ``a1`` less than ``a2``, put
                                         result into ``out``. ``out`` has
                                         bitwidth 1.

                                         Performs *unsigned* comparison. Use
                                         :func:`signed_lt` for signed less
                                         than.
    ``>`` ``None``   ``a1, a2`` ``out``  check ``a1`` greater than ``a2``, put
                                         result into ``out`` ``out`` has
                                         bitwidth 1.

                                         Performs *unsigned* comparison. Use
                                         :func:`signed_gt` for signed greater
                                         than.
    ``w`` ``None``   ``w1``     ``w2``   connects ``w1`` to ``w2``

                                         directional wire with no logical
                                         operation
    ``x`` ``None``   ``x``,     ``out``  multiplexer:

                                         when ``x`` == 0 connect ``a1`` to
                                         ``out``

                                         when ``x`` == 1 connect ``a2`` to
                                         ``out``

                                         ``x`` must be 1-bit and ``len(a1) == len(a2)``
                     ``a1, a2``
    ``c`` ``None``   ``*args``  ``out``  concatenates ``*args`` (wires) into
                                         single WireVector

                                         puts first arg at MSB, last arg at LSB
    ``s`` ``sel``    ``wire``   ``out``  selects bits from wire based on
                                         ``sel`` (slicing syntax)

                                         puts selected bits into ``out``
    ``r`` ``None``   ``next``   ``r1``   on positive clock edge: copies
                                         ``next`` to ``r1``
    ``m`` ``memid``, ``addr``   ``data`` read address addr of mem (with id
                                         ``memid``), put it into ``data``

          ``mem``
    ``@`` ``memid``, ``addr``            write data to mem (with id ``memid``)
                                         at address ``addr``

                                         request write enable (``wr_en``)

          ``mem``    ``data``,

                     ``wr_en``
    ===== ========== ========== ======== ====

    """

    op: str
    """Operation performed by the ``LogicNet``."""
    op_param: tuple
    """Static parameters for the operation."""
    args: tuple[WireVector]
    """Input arguments to the operation."""
    dests: tuple[WireVector]
    """Output of the operation."""

    def __str__(self):
        rhs = ", ".join(str(x) for x in self.args)
        lhs = ", ".join(str(x) for x in self.dests)
        options = "" if self.op_param is None else "(" + str(self.op_param) + ")"

        from pyrtl.helperfuncs import _currently_in_jupyter_notebook

        if _currently_in_jupyter_notebook():
            # Output the working block as a Latex table
            # Escape all Underscores
            rhs = rhs.replace("_", "\\_")
            lhs = lhs.replace("_", "\\_")
            options = options.replace("_", "\\_")
            if self.op in "&|":
                return f"{lhs} & \\leftarrow \\{self.op} \\, - & {rhs} {options} \\\\"
            if self.op in "wn+-*<>xcsr":
                return f"{lhs} & \\leftarrow {self.op} \\, - & {rhs} {options} \\\\"
            if self.op in "=":
                return f"{lhs} & \\leftarrow \\, {self.op} \\, - & {rhs} {options} \\\\"
            if self.op in "^":
                return f"{lhs} & \\leftarrow \\oplus \\, - & {rhs} {options} \\\\"
            if self.op in "~":
                return f"{lhs} & \\leftarrow \\sim \\, - & {rhs} {options} \\\\"

            if self.op in "m@":
                memid, memblock = self.op_param
                extrainfo = "memid=" + str(memid)
                extrainfo = extrainfo.replace("_", "\\_")
                name = memblock.name
                name = name.replace("_", "\\_")
                if self.op == "m":
                    return (
                        f"{lhs} & \\leftarrow m \\, - &  "
                        f"{name}[{rhs}]({extrainfo}) \\\\"
                    )
                addr, data, we = (str(x) for x in self.args)
                addr = addr.replace("_", "\\_")
                data = data.replace("_", "\\_")
                we = we.replace("_", "\\_")
                return (
                    f"{name}[{addr}] & \\leftarrow @ \\, - & "
                    f"{data} we={we} ({extrainfo}) \\\\"
                )
            msg = f'error, unknown op "{self.op}"'
            raise PyrtlInternalError(msg)

        # not in ipython
        if self.op in "w~&|^n+-*<>=xcsr":
            options = " " + options if options else ""
            return f"{lhs} <-- {self.op} -- {rhs}{options}"
        if self.op in "m@":
            memid, memblock = self.op_param
            extrainfo = "memid=" + str(memid)
            if self.op == "m":
                return f"{lhs} <-- m --  {memblock.name}[{rhs}]({extrainfo})"
            addr, data, we = (str(x) for x in self.args)
            return f"{memblock.name}[{addr}] <-- @ -- {data} we={we} ({extrainfo})"
        msg = f'error, unknown op "{self.op}"'
        raise PyrtlInternalError(msg)

    def __hash__(self):
        # it seems that namedtuple is not always hashable
        return hash(tuple(self))

    def __eq__(self, other):
        # We can't be going and calling __eq__ recursively on the logic nets for all of
        # the args and dests because that will actually *create* new logic nets which is
        # very much not what people would expect to happen. Instead we define equality
        # as the immutable fields being equal and the list of args and dests being
        # references to the same objects.
        return (
            self.op == other.op
            and self.op_param == other.op_param
            and len(self.args) == len(other.args)
            and len(self.dests) == len(other.dests)
            and all(self.args[i] is other.args[i] for i in range(len(self.args)))
            and all(self.dests[i] is other.dests[i] for i in range(len(self.dests)))
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def _compare_error(self, _other):
        """Throw error when LogicNets are compared.

        Comparisons get you in a bad place between while you can compare op and op_param
        safely, the args and dests are references to mutable objects with comparison
        operators overloaded.
        """
        msg = (
            "Greater than and less than comparisons between LogicNets are not supported"
        )
        raise PyrtlError(msg)

    __lt__ = _compare_error
    __gt__ = _compare_error
    __le__ = _compare_error
    __ge__ = _compare_error


class Block:
    """``Block`` encapsulates a `netlist <https://en.wikipedia.org/wiki/Netlist>`_.

    A ``Block`` in PyRTL is the class that stores a netlist and provides basic access
    and error checking members. Each ``Block`` has well defined :class:`Inputs<Input>`
    and :class:`Outputs<Output>`, and contains both the basic logic elements and
    references to the :class:`WireVectors<WireVector>` and :class:`MemBlocks<MemBlock>`
    that connect them together.

    The logic structure is primarily contained in :attr:`~Block.logic` which holds a
    :class:`set` of :class:`LogicNets <LogicNet>`. Each :class:`LogicNet` describes a
    primitive operation (such as an adder or memory), a 4-tuple of:

    1. The :attr:`~LogicNet.op` (a single character describing the operation such as
       ``+`` or ``r``).

    2. A set of static :attr:`~LogicNet.op_param` for the operation, such as the bit
       slices to select for the ``s`` "selection" operation.

    3. A tuple :attr:`~LogicNet.args` containing the :class:`WireVectors<WireVector>`
       connected as inputs to the :class:`LogicNet`.

    4. A tuple :attr:`~LogicNet.dests` containing the :class:`WireVectors<WireVector>`
       connected as outputs from the :class:`LogicNet`.

    Below is a list of the basic operations. These properties (more formally specified)
    should all be checked by :meth:`sanity_check`.

    - Most logical and arithmetic :class:`ops<LogicNet.op>` are pretty self explanatory.
      Each takes exactly two :class:`~LogicNet.args`, and they should perform the
      arithmetic or logical operation specified.

      :class:`ops<LogicNet.op>`: ``&``, ``|``, ``^``, ``n``, ``~``, ``+``, ``-``,
      ``*``.

      All inputs must be the same :attr:`~WireVector.bitwidth`.  Logical operations
      produce as many bits as are in the input, while ``+`` and ``-`` produce ``n + 1``
      bits, and ``*`` produces ``2 * n`` bits.

    - In addition there are some operations for performing comparisons that should
      perform the operation specified. The ``=`` :class:`~LogicNet.op` is checking to
      see if the bits of the :class:`~LogicNet.args` vectors are equal, while ``<`` and
      ``>`` do *unsigned* arithmetic comparison. All comparisons generate a single bit
      :class:`dest<LogicNet.dests>` (``1`` for ``True``, ``0`` for ``False``).

    - The ``w`` :class:`~LogicNet.op` is simply a directional wire that connects
      :class:`~LogicNet.args` to :class:`~LogicNet.dests`. It has no logic function.

    - The ``x`` :class:`~LogicNet.op` is a multiplexer which takes a select bit and two
      signals as :class:`~LogicNet.args`. If the value of the select bit is ``0`` it
      selects the second :class:`arg<LogicNet.args>`; if it is ``1`` it selects the
      third :class:`arg<LogicNet.args>`. Select must be a single bit, while the other
      two :class:`~LogicNet.args` must be the same length.

    - The ``c`` :class:`~LogicNet.op` is the concatenation operator and combines any
      number of :class:`WireVector` :class:`~LogicNet.args` (``a``, ``b``, ..., ``z``)
      into a single new :class:`WireVector` with ``a`` in the MSB and ``z`` (or whatever
      is last) in the LSB position.

    - The ``s`` :class:`~LogicNet.op` is the selection operator and chooses, based on
      the :class:`~LogicNet.op_param` specified, a subset of the logic bits from a
      :class:`WireVector` to select. Repeats are accepted.

    - The ``r`` :class:`~LogicNet.op` is a register and on posedge, simply copies the
      value from :class:`arg<LogicNet.args>` to the register's
      :class:`dest<LogicNet.dests>`.

    - The ``m`` :class:`~LogicNet.op` is a memory block read port, which supports async
      reads (acting like combinational logic). Multiple read (and write) ports are
      possible to the same memory but each ``m`` defines only one of those. The
      :class:`~LogicNet.op_param` is a tuple containing two references: the ``memid``,
      and a reference to the :class:`MemBlock` containing this port. The
      :class:`MemBlock` should only be used for debug and sanity checks. Each read port
      has one ``addr`` (an :class:`arg<LogicNet.args>`) and one ``data`` (a
      :class:`dest<LogicNet.dests>`).

    - The ``@`` (update) :class:`~LogicNet.op` is a memory block write port, which
      supports synchronous writes (writes are "latched" at positive edge). Multiple
      write (and read) ports are possible to the same memory but each ``@`` defines only
      one of those. The :class:`~LogicNet.op_param` is a tuple containing two
      references: the ``memid``, and a reference to the :class:`MemBlock`. Writes have
      three :class:`~LogicNet.args` (``addr``, ``data``, and write enable ``we_en``).
      The :class:`~LogicNet.dests` should be an empty tuple. You will not see a written
      value change until the following cycle. If multiple writes happen to the same
      address in the same cycle the behavior is currently undefined.

    The connecting elements (:class:`~LogicNet.args` and :class:`~LogicNet.dests`)
    should be :class:`WireVectors<WireVector>` or derived from :class:`WireVector`, and
    should be registered with the ``Block`` using :meth:`add_wirevector`.
    :class:`LogicNets<LogicNet>` should be registered using :meth:`add_net`.

    In addition, there is a member :attr:`~Block.legal_ops` which defines the set of
    operations that can be legally added to the ``Block``. By default it is set to all
    of the above defined operations, but it can be useful in certain cases to only allow
    a subset of operations (such as when transforms are being done that are "lowering"
    the ``Block`` to more primitive ops).

    See :class:`LogicNet` for a complete list of defined operations.
    """

    logic: set[LogicNet]
    """Set of :class:`LogicNets<LogicNet>` belonging to this ``Block``."""

    legal_ops: set[str]
    """Set of allowed :attr:`ops<LogicNet.op>` in this block."""

    def __init__(self):
        """Creates an empty hardware block."""
        self.logic = set()  # set of nets, each is a LogicNet named tuple
        self.wirevector_set = set()  # set of all WireVectors
        self.wirevector_by_name = {}  # map from name->WireVector, used for performance
        # pre-synthesis WireVectors to post-synthesis vectors
        self.legal_ops = set("w~&|^n+-*<>=xcsrm@")  # set of legal OPS
        # map from WireVectors -> exceptions, used by rtl_assert
        self.rtl_assert_dict = {}
        # map from name->memblock, for easy access to memblock objs
        self.memblock_by_name = {}

    def __str__(self):
        """String form has one LogicNet per line."""
        from pyrtl.helperfuncs import (
            _currently_in_jupyter_notebook,
            _print_netlist_latex,
        )

        if _currently_in_jupyter_notebook():
            _print_netlist_latex(list(self))
            return " "
        return "\n".join(str(net) for net in self)

    def add_wirevector(self, wirevector: WireVector):
        """
        :param wirevector: :class:`WireVector` to add to ``self``.
        """
        self.sanity_check_wirevector(wirevector)
        self.wirevector_set.add(wirevector)
        self.wirevector_by_name[wirevector.name] = wirevector

    def remove_wirevector(self, wirevector: WireVector):
        """
        :param wirevector: :class:`WireVector` to remove from ``self``.
        """
        self.wirevector_set.remove(wirevector)
        del self.wirevector_by_name[wirevector.name]

    def add_net(self, net: LogicNet):
        """Add logic to the ``Block``.

        The passed :class:`LogicNet` is checked and added to the ``Block``. No
        :class:`WireVectors<WireVector>` are added; they must be added seperately with
        :meth:`add_wirevector`.

        :param net: :class:`LogicNet` to add to ``self``.
        """

        self.sanity_check_net(net)
        self.logic.add(net)

    def _add_memblock(self, mem):
        """Registers a memory to the block.

        Note that this is done automatically when a memory block is created and isn't
        intended for use by PyRTL end users. This is so non-local memories can be
        accessed later on (e.g. for instantiating during a simulation).
        """
        self.sanity_check_memblock(mem)
        self.memblock_by_name[mem.name] = mem

    def get_memblock_by_name(self, name: str, strict: bool = False) -> MemBlock:
        """Get a :class:`MemBlock` from the ``Block``, by name.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Useful for getting access to internal :class:`MemBlocks<MemBlock>` for testing.
        For example, the :class:`Simulation` constructor requires a :class:`MemBlock`
        reference for its ``memory_value_map``. Instead of passing the :class:`MemBlock`
        around in your code, you can get a reference to the :class:`MemBlock` from the
        global :func:`working_block`::

            >>> def read_hidden_mem(read_addr: pyrtl.WireVector) -> pyrtl.WireVector:
            ...     mem = pyrtl.MemBlock(bitwidth=8, addrwidth=4, name='hidden_mem')
            ...     return mem[read_addr]

            >>> read_addr = pyrtl.Input(4, 'read_addr')
            >>> data = pyrtl.Output(8, 'data')
            >>> data <<= read_hidden_mem(read_addr)

            >>> hidden_mem = pyrtl.working_block().get_memblock_by_name('hidden_mem')
            >>> sim = pyrtl.Simulation(memory_value_map={hidden_mem: {3: 7}})
            >>> sim.step(provided_inputs={read_addr.name: 3})
            >>> sim.inspect(data.name)
            7

        Returns ``None`` if no matching :class:`MemBlock` can be found. However, if
        ``strict=True``, then this will instead throw a :class:`PyrtlError` when no
        match is found.

        :param name: Name of the :class:`MemBlock` to retrieve.
        :param strict: When ``True``, raises an exception when no match is found.
            Defaults to ``False``.

        :raise PyrtlError: When ``strict=True`` and no match is found.

        :return: The :class:`MemBlock` object with specified name
        """
        if name in self.memblock_by_name:
            return self.memblock_by_name[name]
        if strict:
            msg = f"error, block does not have a memblock named {name}"
            raise PyrtlError(msg)
        return None

    def wirevector_subset(
        self, cls: tuple[type] | None = None, exclude: tuple[type] = ()
    ) -> set[WireVector]:
        """Return a subset of the ``Block's`` :class:`WireVectors<WireVector>`.

        Filters :class:`WireVectors<WireVector>` by type.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        If ``cls`` is ``None``, returns all the :class:`WireVectors<WireVector>`
        associated with the ``Block``. If ``cls`` is a single type, or a tuple of types,
        only :class:`WireVectors<WireVector>` of the matching types will be returned.
        This is helpful for getting all of a ``Block``'s :class:`Inputs<Input>`,
        :class:`Outputs<Output>`, or :class:`Registers<Register>` for example::

            >>> len([pyrtl.Input(bitwidth=4) for _ in range(2)])
            2
            >>> len([pyrtl.Output(bitwidth=4) for _ in range(3)])
            3
            >>> block = pyrtl.working_block()

            >>> inputs = block.wirevector_subset(pyrtl.Input)
            >>> len(inputs)
            2
            >>> all(isinstance(input, pyrtl.Input) for input in inputs)
            True

            >>> non_inputs = block.wirevector_subset(exclude=pyrtl.Input)
            >>> len(non_inputs)
            3
            >>> any(isinstance(non_input, pyrtl.Input) for non_input in non_inputs)
            False

        :param cls: Type of :class:`WireVector` objects to include in the returned
            :class:`set`.
        :param exclude: Type of :class:`WireVector` objects to exclude from the returned
            :class:`set`.

        :return: :class:`WireVectors<WireVector>` in the ``Block`` that are both a
                 ``cls`` type and not an ``excluded`` type.
        """
        if cls is None:
            initial_set = self.wirevector_set
        else:
            initial_set = (x for x in self.wirevector_set if isinstance(x, cls))
        if exclude == ():
            return set(initial_set)
        return {x for x in initial_set if not isinstance(x, exclude)}

    def logic_subset(self, op: tuple[str] | None = None) -> set[LogicNet]:
        """Return a subset of the ``Block's`` :class:`LogicNets<LogicNet>`.

        Filters :class:`LogicNets<LogicNet>` by their :attr:`~LogicNet.op`.

        If :class:`~LogicNet.op` is ``None``, returns all the
        :class:`LogicNets<LogicNet>` associated with the ``Block``. Otherwise, returns a
        set of the :class:`LogicNets<LogicNet>` with one of the specified
        :class:`ops<LogicNet.op>`. This is helpful for getting all memories of a block
        for example.

        :param op: :attr:`LogicNet.op` to filter on. Defaults to ``None``.

        :return: :class:`LogicNets<LogicNet>` in the ``Block`` with the corresponding
                 :class:`~LogicNet.op`.
        """
        if op is None:
            return self.logic
        return {x for x in self.logic if x.op in op}

    def get_wirevector_by_name(self, name: str, strict: bool = False) -> WireVector:
        """Return the :class:`WireVector` with matching ``name``.

        :param name: Name of :class:`WireVector`.
        :param strict: If ``True``, raise an exception when no matching
            :class:`WireVector` is found. Defaults to False.

        :raise PyrtlError: if ``strict=True`` and no matching :class:`WireVector` is
            found.

        :return: The :class:`WireVector` with the specified ``name``.
        """
        if name in self.wirevector_by_name:
            return self.wirevector_by_name[name]
        if strict:
            msg = f"error, block does not have a WireVector named {name}"
            raise PyrtlError(msg)
        return None

    class _NetConnectionsDict(dict):
        """Dictionary wrapper for returning the results of the enclosing function.

        User doesn't need to know about this class; it's only for delivering a nice
        error message when _MemIndexed is used as a lookup key.
        """

        def __missing__(self, key):
            from pyrtl.memory import _MemIndexed

            if isinstance(key, _MemIndexed):
                msg = (
                    "Cannot look up a _MemIndexed object's source or destination net. "
                    "Try using its '.wire' attribute as the lookup key instead."
                )
                raise PyrtlError(msg)
            raise KeyError(key)

    def net_connections(
        self, include_virtual_nodes: bool = False
    ) -> tuple[dict[WireVector, LogicNet], dict[WireVector, list[LogicNet]]]:
        """Returns `sources` and `sinks` for each :class:`WireVector` in the ``Block``.

        A :class:`WireVector`'s `source` is the :class:`LogicNet` that sets the
        :class:`WireVector`'s value.

        A :class:`WireVector`'s `sinks` are the :class:`LogicNets<LogicNet>` that use
        the :class:`WireVector`'s value.

        This information helps when building a graph representation for the ``Block``.
        See :func:`net_graph` for an example.

        .. note::

            Consider using :ref:`gate_graphs` instead.

        :param include_virtual_nodes: If ``True``, external `sources` (such as an
            :class:`Inputs<Input>` and :class:`Consts<Const>`) will be represented as
            wires that set themselves, and external `sinks` (such as
            :class:`Outputs<Output>`) will be represented as wires that use themselves.
            If ``False``, these nodes will be excluded from the results.

        :return: Two dictionaries. The first maps :class:`WireVectors<WireVector>` to
                 the :class:`LogicNet` that creates their signal (``wire_src_dict``).
                 The second maps :class:`WireVectors<WireVector>` to a list of
                 :class:`LogicNets<LogicNet>` that use their signal
                 (``wire_sink_dict``).
        """
        src_list = {}
        dst_list = {}

        def add_wire_src(edge, node):
            if edge in src_list:
                msg = (
                    f'Wire "{edge}" has multiple drivers: '
                    f"[{str(src_list[edge]).strip()}] and [{str(node).strip()}] "
                    '(check for multiple assignments with "<<=" or accidental mixing '
                    'of "|=" and "<<=")'
                )
                raise PyrtlError(msg)
            src_list[edge] = node

        def add_wire_dst(edge, node):
            if edge in dst_list:
                # if node in dst_list[edge]:
                #     raise PyrtlError("The net already exists in the graph")
                dst_list[edge].append(node)
            else:
                dst_list[edge] = [node]

        if include_virtual_nodes:
            from pyrtl.wire import Const, Input, Output

            for wire in self.wirevector_subset((Input, Const)):
                add_wire_src(wire, wire)

            for wire in self.wirevector_subset(Output):
                add_wire_dst(wire, wire)

        for net in self.logic:
            for arg in set(
                net.args
            ):  # prevents unexpected duplicates when doing b <<= a & a
                add_wire_dst(arg, net)
            for dest in net.dests:
                add_wire_src(dest, net)

        return Block._NetConnectionsDict(src_list), Block._NetConnectionsDict(dst_list)

    def _repr_svg_(self):
        """IPython display support for Block."""
        from pyrtl.visualization import block_to_svg

        return block_to_svg(self)

    def __iter__(self):
        """BlockIterator iterates over the block passed on init in topographic order.
        The input is a Block, and when a LogicNet is returned it is always the case that
        all of its "parents" have already been returned earlier in the iteration.

        Note: this method will throw an error if there are loops in the logic that do
        not involve registers. Also, the order of the nets is not guaranteed to be the
        same over multiple iterations.
        """
        from pyrtl.wire import Const, Input, Register

        src_dict, dest_dict = self.net_connections()
        to_clear = self.wirevector_subset((Input, Const, Register))
        cleared = set()
        remaining = self.logic.copy()
        try:
            while len(to_clear):
                wire_to_check = to_clear.pop()
                cleared.add(wire_to_check)
                if wire_to_check in dest_dict:
                    for gate in dest_dict[
                        wire_to_check
                    ]:  # loop over logicnets not yet returned
                        if all(
                            arg in cleared for arg in gate.args
                        ):  # if all args ready
                            yield gate
                            remaining.remove(gate)
                            if gate.op != "r":
                                to_clear.update(gate.dests)
        except KeyError as e:
            msg = "Cannot Iterate through malformed block"
            raise PyrtlError(msg) from e

        if len(remaining) != 0:
            from pyrtl.helperfuncs import find_and_print_loop

            find_and_print_loop(self)
            msg = "Failure in Block Iterator due to non-register loops"
            raise PyrtlError(msg)

    def sanity_check(self):
        """Verify the ``Block``'s integrity. Raise an exception if there is an issue.

        ``sanity_check`` does not change any of the ``Block``'s state. It only verifies
        that the ``Block``'s data structures are internally consistent.

        :raise PyrtlError: If the ``Block`` is malformed.
        """
        from pyrtl.helperfuncs import get_stack, get_stacks
        from pyrtl.wire import Const, Input, Output

        # check for valid LogicNets (and wires)
        for net in self.logic:
            self.sanity_check_net(net)

        for w in self.wirevector_subset():
            if w.bitwidth is None:
                msg = (
                    f'error, missing bitwidth for WireVector "{w.name}" \n\n '
                    f"{get_stack(w)}"
                )
                raise PyrtlError(msg)

        # check for unique names
        wirevector_names_set = {x.name for x in self.wirevector_set}
        if len(self.wirevector_set) != len(wirevector_names_set):
            wirevector_names_list = [x.name for x in self.wirevector_set]
            for w in wirevector_names_set:
                wirevector_names_list.remove(w)
            msg = (
                "Duplicate wire names found for the following different signals: "
                f'{wirevector_names_list} (make sure you are not using "tmp" or '
                '"const_" as a signal name because those are reserved for internal use)'
            )
            raise PyrtlError(msg)

        # The following line also checks for duplicate wire drivers
        wire_src_dict, wire_dst_dict = self.net_connections()
        dest_set = set(wire_src_dict.keys())
        arg_set = set(wire_dst_dict.keys())
        full_set = dest_set | arg_set
        connected_minus_allwires = full_set.difference(self.wirevector_set)
        if len(connected_minus_allwires) > 0:
            bad_wire_names = "\n    ".join(str(x) for x in connected_minus_allwires)
            msg = (
                f"Unknown wires found in net:\n {bad_wire_names} \n\n "
                f"{get_stacks(*connected_minus_allwires)}"
            )
            raise PyrtlError(msg)

        all_input_and_consts = self.wirevector_subset((Input, Const))

        # Check for wires that aren't connected to anything (inputs and consts can be
        # unconnected)
        allwires_minus_connected = self.wirevector_set.difference(full_set)
        allwires_minus_connected = allwires_minus_connected.difference(
            all_input_and_consts
        )
        if len(allwires_minus_connected) > 0:
            bad_wire_names = "\n    ".join(str(x) for x in allwires_minus_connected)
            msg = (
                f"Wires declared but not connected:\n {bad_wire_names} \n\n "
                f"{get_stacks(*allwires_minus_connected)}"
            )
            raise PyrtlError(msg)

        # Check for wires that are inputs to a logicNet, but are not block inputs and
        # are never driven.
        ins = arg_set.difference(dest_set)
        undriven = ins.difference(all_input_and_consts)
        if len(undriven) > 0:
            msg = (
                f"Wires used but never driven: {[w.name for w in undriven]} \n\n "
                f"{get_stacks(*undriven)}"
            )
            raise PyrtlError(msg)

        # Check for async memories not specified as such
        self.sanity_check_memory_sync(wire_src_dict)

        # Check that all mappings in wirevector_by_name are consistent
        bad_wv_by_name = [w for n, w in self.wirevector_by_name.items() if n != w.name]
        if bad_wv_by_name:
            raise PyrtlInternalError(
                "Wires with inconsistent entry in wirevector_by_name "
                "dict: %s" % [w.name for w in bad_wv_by_name]
            )

        # Check that all wires are in wirevector_by_name
        wv_by_name_set = set(self.wirevector_by_name.keys())
        missing_wires = wirevector_names_set.difference(wv_by_name_set)
        if missing_wires:
            msg = (
                "Missing entries in wirevector_by_name for the "
                f"following wires: {missing_wires}"
            )
            raise PyrtlInternalError(msg)

        unknown_wires = wv_by_name_set.difference(wirevector_names_set)
        if unknown_wires:
            msg = f"Unknown wires found in wirevector_by_name: {unknown_wires}"
            raise PyrtlInternalError(msg)

        if debug_mode:
            # Check for wires that are destinations of a logicNet, but are not outputs
            # and are never used as args.
            outs = dest_set.difference(arg_set)
            unused = outs.difference(self.wirevector_subset(Output))
            if len(unused) > 0:
                names = [w.name for w in unused]
                print(f"Warning: Wires driven but never used {{ {names} }} ")
                print(get_stacks(*unused))

    def sanity_check_memory_sync(self, wire_src_dict=None):
        """Check that all memories are synchronous unless explicitly specified as async.

        While the semantics of 'm' memories reads is asynchronous, if you want your
        design to use a block ram (on an FPGA or otherwise) you want to make sure the
        index is available at the beginning of the clock edge. This check will walk the
        logic structure and throw an error on any memory if finds that has an index that
        is not ready at the beginning of the cycle.
        """
        sync_mems = {
            m for m in self.logic_subset("m") if not m.op_param[1].asynchronous
        }
        if not sync_mems:
            return  # nothing to check here

        if wire_src_dict is None:
            wire_src_dict, wdd = self.net_connections()

        from pyrtl.wire import Const, Input

        sync_src = "r"
        sync_prop = "wcs"
        for net in sync_mems:
            wires_to_check = list(net.args)
            while wires_to_check:
                wire = wires_to_check.pop()
                if isinstance(wire, (Input, Const)):
                    continue
                src_net = wire_src_dict[wire]
                if src_net.op == sync_src:
                    continue
                if src_net.op in sync_prop:
                    wires_to_check.extend(src_net.args)
                else:
                    msg = (
                        f'memory "{net.op_param[1].name}" is not specified as '
                        f'asynchronous but has an index "{net.args[0].name}" that is '
                        f'not ready at the start of the cycle due to net "{src_net}"'
                    )
                    raise PyrtlError(msg)

    def sanity_check_wirevector(self, w):
        """Check that w is a valid WireVector type."""
        from pyrtl.wire import WireVector

        if not isinstance(w, WireVector):
            msg = (
                f'error attempting to pass an input of type "{type(w)}" instead of '
                "WireVector"
            )
            raise PyrtlError(msg)

    def sanity_check_memblock(self, m):
        """Check that m is a valid memblock type."""
        from pyrtl.memory import MemBlock

        if not isinstance(m, MemBlock):
            msg = (
                f'error attempting to pass an input of type "{type(m)}" instead of '
                "MemBlock"
            )
            raise PyrtlError(msg)

    def sanity_check_net(self, net):
        """Check that net is a valid LogicNet."""
        from pyrtl.memory import MemBlock
        from pyrtl.wire import Const, Input, Output, Register

        # general sanity checks that apply to all operations
        if not isinstance(net, LogicNet):
            msg = "error, net must be of type LogicNet"
            raise PyrtlInternalError(msg)
        if not isinstance(net.args, tuple):
            msg = "error, LogicNet args must be tuple"
            raise PyrtlInternalError(msg)
        if not isinstance(net.dests, tuple):
            msg = "error, LogicNet dests must be tuple"
            raise PyrtlInternalError(msg)
        for w in net.args + net.dests:
            self.sanity_check_wirevector(w)
            if w._block is not self:
                msg = "error, net references different block"
                raise PyrtlInternalError(msg)
            if w not in self.wirevector_set:
                msg = f'error, net with unknown source "{w.name}"'
                raise PyrtlInternalError(msg)

        # checks that input and output WireVectors are not misused
        bad_dests = set(filter(lambda w: isinstance(w, (Input, Const)), net.dests))
        if bad_dests:
            msg = "error, Inputs, Consts cannot be destinations to a net ({})".format(
                ",".join(map(str, bad_dests))
            )
            raise PyrtlInternalError(msg)
        bad_args = set(filter(lambda w: isinstance(w, (Output)), net.args))
        if bad_args:
            msg = "error, Outputs cannot be arguments for a net ({})".format(
                ",".join(map(str, bad_args))
            )
            raise PyrtlInternalError(msg)

        if net.op not in self.legal_ops:
            msg = f'error, net op "{net.op}" not from acceptable set {self.legal_ops}'
            raise PyrtlInternalError(msg)

        # operation-specific checks on arguments
        if net.op in "w~rsm" and len(net.args) != 1:
            msg = "error, op only allowed 1 argument"
            raise PyrtlInternalError(msg)
        if net.op in "&|^n+-*<>=" and len(net.args) != 2:
            msg = "error, op only allowed 2 arguments"
            raise PyrtlInternalError(msg)
        if net.op == "x":
            if len(net.args) != 3:
                msg = "error, op only allowed 3 arguments"
                raise PyrtlInternalError(msg)
            if net.args[1].bitwidth != net.args[2].bitwidth:
                msg = "error, args have mismatched bitwidths"
                raise PyrtlInternalError(msg)
            if net.args[0].bitwidth != 1:
                msg = "error, mux select must be a single bit"
                raise PyrtlInternalError(msg)
        if net.op == "@" and len(net.args) != 3:
            msg = "error, op only allowed 3 arguments"
            raise PyrtlInternalError(msg)
        if net.op in "&|^n+-*<>=" and net.args[0].bitwidth != net.args[1].bitwidth:
            msg = "error, args have mismatched bitwidths"
            raise PyrtlInternalError(msg)
        if net.op in "m@" and net.args[0].bitwidth != net.op_param[1].addrwidth:
            msg = "error, mem addrwidth mismatch"
            raise PyrtlInternalError(msg)
        if net.op == "@" and net.args[1].bitwidth != net.op_param[1].bitwidth:
            msg = "error, mem bitwidth mismatch"
            raise PyrtlInternalError(msg)
        if net.op == "@" and net.args[2].bitwidth != 1:
            msg = "error, mem write enable must be 1 bit"
            raise PyrtlInternalError(msg)

        # operation-specific checks on op_params
        if net.op in "w~&|^n+-*<>=xcr" and net.op_param is not None:
            msg = "error, op_param should be None"
            raise PyrtlInternalError(msg)
        if net.op == "s":
            if not isinstance(net.op_param, tuple):
                msg = "error, select op requires tuple op_param"
                raise PyrtlInternalError(msg)
            for p in net.op_param:
                if not isinstance(p, int):
                    msg = "error, select op_param requires ints"
                    raise PyrtlInternalError(msg)
                if p < 0 or p >= net.args[0].bitwidth:
                    msg = "error, op_param out of bounds"
                    raise PyrtlInternalError(msg)
        if net.op in "m@":
            if not isinstance(net.op_param, tuple):
                msg = "error, mem op requires tuple op_param"
                raise PyrtlInternalError(msg)
            if len(net.op_param) != 2:
                msg = "error, mem op requires 2 op_params in tuple"
                raise PyrtlInternalError(msg)
            if not isinstance(net.op_param[0], int):
                msg = "error, mem op requires first operand as int"
                raise PyrtlInternalError(msg)
            if not isinstance(net.op_param[1], MemBlock):
                msg = "error, mem op requires second operand of a memory type"
                raise PyrtlInternalError(msg)

        # operation-specific checks on destinations
        if net.op in "w~&|^n+-*<>=xcsrm" and len(net.dests) != 1:
            msg = "error, op only allowed 1 destination"
            raise PyrtlInternalError(msg)
        if net.op == "@" and net.dests != ():
            msg = "error, mem write dest should be empty tuple"
            raise PyrtlInternalError(msg)
        if net.op == "r" and not isinstance(net.dests[0], Register):
            msg = "error, dest of next op should be a Register"
            raise PyrtlInternalError(msg)

        # check destination validity
        if net.op in "w~&|^nr" and net.dests[0].bitwidth > net.args[0].bitwidth:
            msg = "error, upper bits of destination unassigned"
            raise PyrtlInternalError(msg)
        if net.op in "<>=" and net.dests[0].bitwidth != 1:
            msg = "error, destination should be of bitwidth=1"
            raise PyrtlInternalError(msg)
        if net.op in "+-" and net.dests[0].bitwidth > net.args[0].bitwidth + 1:
            msg = "error, upper bits of destination unassigned"
            raise PyrtlInternalError(msg)
        if net.op == "*" and net.dests[0].bitwidth > 2 * net.args[0].bitwidth:
            msg = "error, upper bits of destination unassigned"
            raise PyrtlInternalError(msg)
        if net.op == "x" and net.dests[0].bitwidth > net.args[1].bitwidth:
            msg = "error, upper bits of mux output undefined"
            raise PyrtlInternalError(msg)
        if net.op == "c" and net.dests[0].bitwidth > sum(x.bitwidth for x in net.args):
            msg = "error, upper bits of concat output undefined"
            raise PyrtlInternalError(msg)
        if net.op == "s" and net.dests[0].bitwidth > len(net.op_param):
            msg = "error, upper bits of select output undefined"
            raise PyrtlInternalError(msg)
        if net.op == "m" and net.dests[0].bitwidth != net.op_param[1].bitwidth:
            msg = "error, mem read dest bitwidth mismatch"
            raise PyrtlInternalError(msg)


class PostSynthBlock(Block):
    """This is a block with extra metadata required to maintain the pre-synthesis
    interface during post-synthesis.
    """

    io_map: dict[WireVector, list[WireVector]]
    """
    A map from old IO :class:`WireVector` to a :class:`list` of new IO
    :class:`WireVectors<WireVector>` it maps to; this is a :class:`list` because for
    unmerged IO vectors, each old N-bit IO :class:`WireVector` maps to N new 1-bit IO
    :class:`WireVectors<WireVector>`.
    """
    reg_map: dict[Register, list[Register]]
    """
    A map from old :class:`Register` to a :class:`list` of new
    :class:`Registers<Register>`; a :class:`list` because post-synthesis, each N-bit
    :class:`Register` has been mapped to N 1-bit :class:`Registers<Register>`.
    """
    mem_map: dict[MemBlock, MemBlock]
    """
    A map from old :class:`MemBlock` to the new :class:`MemBlock`.
    """

    def __init__(self):
        super().__init__()
        self.io_map = collections.defaultdict(list)
        self.reg_map = collections.defaultdict(list)
        self.mem_map = {}


# -----------------------------------------------------------------------
#          __   __               __      __        __   __
#    |  | /  \ |__) |__/ | |\ | / _`    |__) |    /  \ /  ` |__/
#    |/\| \__/ |  \ |  \ | | \| \__>    |__) |___ \__/ \__, |  \
#

# Right now we use singleton_block to store the one global block, but in the future we
# should support multiple Blocks. The argument "singleton_block" should never be passed.
_singleton_block = Block()

# settings help tweak the behavior of pyrtl as needed, especially when there is a trade
# off between speed and debugability. These are useful for developers to adjust
# behaviors in the different modes but should not be set directly by users.
debug_mode = False
_setting_keep_wirevector_call_stack = False
_setting_slower_but_more_descriptive_tmps = False


def _get_debug_mode():
    return debug_mode


def _get_useful_callpoint_name():
    """Attempts to find the lowest user-level call into the PyRTL module.

    This function walks back the current frame stack attempting to find the first frame
    that is not part of the pyrtl module. The filename (stripped of path and .py
    extension) and line number of that call are returned. This point should be the point
    where the user-level code is making the call to some pyrtl intrisic (for example,
    calling "mux"). If the attempt to find the callpoint fails for any reason, None is
    returned.

    :return (string, int) or None: the file name and line number respectively
    """
    if not _setting_slower_but_more_descriptive_tmps:
        return None

    loc = None
    frame_stack = inspect.stack()
    try:
        for frame in frame_stack:
            modname = inspect.getmodule(frame[0]).__name__
            if not modname.startswith("pyrtl."):
                full_filename = frame[0].f_code.co_filename
                filename = full_filename.split("/")[-1].rstrip(".py")
                lineno = frame[0].f_lineno
                loc = (filename, lineno)
                break
    except Exception:
        loc = None
    finally:
        del frame_stack
    return loc


def working_block(block: Block = None) -> Block:
    """Convenience function for capturing the current working block.

    If a ``block`` is not passed, or if the ``block`` passed is ``None``, then this will
    return the "current working block". However, if a ``block`` is passed in it will
    simply return ``block`` instead. This feature is useful in allowing functions to
    "override" the current working block.
    """

    if block is None:
        return _singleton_block
    if not isinstance(block, Block):
        msg = "error, expected instance of Block as block argument"
        raise PyrtlError(msg)
    return block


def reset_working_block():
    """Reset the working block to be empty."""
    global _singleton_block
    _singleton_block = Block()


class set_working_block:
    """Set the working block to be the block passed as argument. Compatible with the
    ``with`` statement.

    Sanity checks will only be run if the new block is different from the original
    block.
    """

    @staticmethod
    def _set_working_block(block, no_sanity_check=False):
        global _singleton_block
        if not isinstance(block, Block):
            msg = "error, expected instance of Block as block argument"
            raise PyrtlError(msg)
        if block is not _singleton_block:  # don't update if the blocks are the same
            if not no_sanity_check:
                block.sanity_check()
            _singleton_block = block

    def __init__(self, block, no_sanity_check=False):
        self.old_block = working_block()  # for with statement compatibility
        self._set_working_block(working_block(block), no_sanity_check)

    def __enter__(self):
        return self.old_block

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._set_working_block(self.old_block, no_sanity_check=True)


def temp_working_block():
    """Set the working block to be new temporary block.

    If used with the ``with`` statement the block will be reset to the original value
    (at the time of call) at exit of the context.
    """
    return set_working_block(Block())


def set_debug_mode(debug: bool = True):
    """Set the global debug mode.

    Sets the debug mode to the specified ``debug`` value. Debug mode is off by default,
    to improve performance. When debug mode is enabled, all temporary
    :class:`WireVectors<WireVector>` will be assigned names based on the line of code on
    which they were created.

    Each :class:`WireVector` will also save a copy of its call stack when constructed.
    These call stacks can be inspected as :attr:`WireVector.init_call_stack`, and they
    will appear in :meth:`Block.sanity_check` error messages.

    :param debug: Optional boolean parameter to which the debug mode will be set.
    """
    global debug_mode
    global _setting_keep_wirevector_call_stack
    global _setting_slower_but_more_descriptive_tmps
    debug_mode = debug
    _setting_keep_wirevector_call_stack = debug
    _setting_slower_but_more_descriptive_tmps = debug


_py_regex = r"^[^\d\W]\w*\Z"


class _NameIndexer:
    """Provides internal names that are based on a prefix and an index."""

    def __init__(self, internal_prefix="_sani_temp"):
        self.internal_prefix = internal_prefix
        self.internal_index = 0

    def make_valid_string(self):
        """Build a valid string based on the prefix and internal index."""
        return self.internal_prefix + str(self.next_index())

    def next_index(self):
        index = self.internal_index
        self.internal_index += 1
        return index


class _NameSanitizer(_NameIndexer):
    """Sanitizes names so they can be used in contexts that don't allow arbitrary names.

    For example, ``a.b`` is a valid ``WireVector`` name, but ``a.b`` is not a valid name
    for a Python variable. If we want to generate Python code for ``a.b`` (like
    ``FastSimulation``), the name must be sanitized.

    Sanitization first attempts to replace non-word characters (anything that's not
    alphanumeric or an underscore) with an underscore. If that didn't work, we try
    appending a unique integer value. If that still doesn't work, we generate an
    entirely new name consisting of ``internal_prefix`` followed by a unique integer
    value.

    ``make_valid_string`` must be called once to generate the sanitized version of a
    name.

    .. doctest only::

        >>> import pyrtl

    After ``make_valid_string`` has been called, the sanitized name can be retrieved
    with ``__getitem__`` any number of times. For example::

        >>> sanitizer = pyrtl.core._NameSanitizer(pyrtl.core._py_regex)

        >>> sanitizer.make_valid_string("foo.bar")
        'foo_bar'
        >>> sanitizer["foo.bar"]
        'foo_bar'
        >>> sanitizer["foo.bar"]
        'foo_bar'

        >>> sanitizer.make_valid_string("foo_bar")
        'foo_bar0'
    """

    def __init__(
        self,
        identifier_regex_str,
        internal_prefix="_sani_temp",
        extra_checks=lambda _string: True,
    ):
        if identifier_regex_str[-1] != "$":
            identifier_regex_str += "$"
        self.identifier = re.compile(identifier_regex_str)
        # Map from un-sanitized name to sanitized name.
        self.val_map = {}
        # Set of all generated sanitized names.
        self.sanitized_names = set()
        self.extra_checks = extra_checks
        super().__init__(internal_prefix)

    def __getitem__(self, name: str) -> str:
        """Return the sanitized name for an un-sanitized name that was generated by
        ``make_valid_string``.
        """
        return self.val_map[name]

    def is_valid_str(self, string: str) -> bool:
        """Return ``True`` iff ``string`` matches ``identifier_regex_str`` and satisfies
        ``extra_checks``.
        """
        return self.identifier.match(string) and self.extra_checks(string)

    def make_valid_string(self, string: str = "") -> str:
        """Generate a sanitized name from an un-sanitized name."""
        if string in self.val_map:
            msg = f"Value {string} has already been given to the sanitizer"
            raise IndexError(msg)

        def is_usable(name: str) -> bool:
            """Return ``True`` iff ``name`` can be used as a sanitized name.

            A sanitized name is usable if it ``is_valid_str``, and isn't already in use.
            """
            return self.is_valid_str(name) and name not in self.sanitized_names

        internal_name = string
        if not is_usable(internal_name):
            # Try replacing non-word characters with ``_``.
            internal_name = re.sub(r"\W", "_", string)

            if not is_usable(internal_name):
                # If that didn't work, try appending the next ``internal_index``.
                internal_name = f"{internal_name}{self.next_index()}"

                if not is_usable(internal_name):
                    # If that didn't work, generate an entirely new name starting with
                    # ``internal_prefix``.
                    internal_name = super().make_valid_string()

                    if not is_usable(internal_name):
                        msg = f"Could not generate a usable sanitized name for {string}"
                        raise PyrtlError(msg)

        self.val_map[string] = internal_name
        self.sanitized_names.add(internal_name)
        return internal_name


class _PythonSanitizer(_NameSanitizer):
    """Name Sanitizer specifically built for Python identifers."""

    def __init__(self, internal_prefix="_sani_temp"):
        super().__init__(_py_regex, internal_prefix)
        self.extra_checks = lambda s: not keyword.iskeyword(s)
