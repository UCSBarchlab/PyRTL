""":class:`GateGraph` is an alternative representation for PyRTL logic.

.. _gate_motivation:

Motivation
----------

.. doctest only::

    >>> import pyrtl
    >>> pyrtl.reset_working_block()

PyRTL represents logic internally with :class:`WireVectors<.WireVector>` and
:class:`LogicNets<.LogicNet>`. For example, the following code creates five
:class:`WireVectors<.WireVector>` and two :class:`LogicNets<.LogicNet>`::

    >>> a = pyrtl.Input(name="a", bitwidth=1)
    >>> b = pyrtl.Input(name="b", bitwidth=1)
    >>> c = pyrtl.Input(name="c", bitwidth=1)

    >>> x = a & b
    >>> x.name = "x"

    >>> y = x | c
    >>> y.name = "y"

    >>> print(pyrtl.working_block())
    x/1W <-- & -- a/1I, b/1I
    y/1W <-- | -- x/1W, c/1I

The :class:`WireVectors<.WireVector>` and :class:`LogicNets<.LogicNet>` are arranged
like this::

    ┌──────────────┐
    │ LogicNet "&" │
    │     op: "&"  │    ┌────────────────┐
    │     args:────┼───▶│ WireVector "a" │
    │     args:────┼─┐  └────────────────┘
    │              │ │  ┌────────────────┐
    │              │ └─▶│ WireVector "b" │
    │              │    └────────────────┘
    │              │    ┌────────────────┐
    │     dests:───┼───▶│ WireVector "x" │
    └──────────────┘ ┌─▶└────────────────┘
    ┌──────────────┐ │
    │ LogicNet "|" │ │
    │     op: "|"  │ │
    │     args:────┼─┘  ┌────────────────┐
    │     args:────┼───▶│ WireVector "c" │
    │              │    └────────────────┘
    │              │    ┌────────────────┐
    │     dests:───┼───▶│ WireVector "y" │
    └──────────────┘    └────────────────┘

This data structure is difficult to work with for two reasons:

1. The arrows do not consistently point from producer to consumer, or from consumer to
   producer. For example, there is no arrow from :class:`.WireVector` ``x`` (producer)
   to :class:`.LogicNet` ``|`` (consumer). Similarly, there is no arrow from
   :class:`.WireVector` ``x`` (consumer) to :class:`.LogicNet` ``&`` (producer). These
   missing arrows make it impossible to iteratively traverse the data structure. This
   creates a need for methods like :meth:`~.Block.net_connections`, which creates
   ``wire_src_dict`` and ``wire_sink_dict`` with the missing pointers.

2. The data structure is composed of two different classes, :class:`.LogicNet` and
   :class:`.WireVector`, and these two classes have completely different interfaces. As
   we follow pointers from one class to another, we must keep track of the current
   object's class, and interact with it appropriately.

:class:`GateGraph` is an alternative representation that addresses both of these issues.
"""

from __future__ import annotations

from pyrtl.core import Block, LogicNet, working_block
from pyrtl.pyrtlexceptions import PyrtlError
from pyrtl.wire import Const, Input, Register, WireVector


class Gate:
    """:class:`Gate` is an alternative to PyRTL's default :class:`.LogicNet` and
    :class:`.WireVector` representation.

    :class:`Gate` makes it easy to iteratively explore a circuit, while simplifying the
    circuit's representation by making everything a :class:`Gate`. A :class:`Gate` is
    equivalent to a :class:`.LogicNet` fused with its :attr:`dest<.LogicNet.dests>`
    :class:`WireVector`. So this :class:`.LogicNet` and :class:`.WireVector`::

        ┌──────────────────┐
        │ LogicNet         │    ┌───────────────────┐
        │     op: o        │    │ WireVector        │
        │     args: [x, y] │    │     name: n       │
        │     dests:───────┼───▶│     bitwidth: b   │
        └──────────────────┘    └───────────────────┘

    Are equivalent to this :class:`Gate`::

        ┌─────────────────────┐
        │ Gate                │
        │     op: o           │
        │     args: [x, y]    │
        │     name: n         │
        │     bitwidth: b     │
        │     dests: [g1, g2] │
        └─────────────────────┘

    Key differences between the two representations:

    1. The :class:`Gate`'s :attr:`~Gate.args` ``[x, y]`` are references to other
       :class:`Gates<Gate>`.

    2. The :class:`.WireVector`'s :attr:`~WireVector.name` and
       :attr:`~WireVector.bitwidth` are stored as corresponding :class:`Gate`
       attributes. If a :class:`Gate` produces no output, like a :class:`.MemBlock`
       write, the :class:`Gate`'s :attr:`~Gate.name` and :attr:`~Gate.bitwidth` will be
       ``None``. PyRTL does not have an :attr:`~.LogicNet.op` that produces multiple
       outputs.

    3. The :class:`Gate` has a new :attr:`~Gate.dests` attribute, which has no direct
       equivalent in the :class:`.LogicNet`/:class:`.WireVector` representation.
       :attr:`~Gate.dests` is a list of the :class:`Gates<Gate>` that use this
       :class:`Gate`'s output as one of their :attr:`~Gate.args`.

    :attr:`.LogicNet.dests` and :attr:`Gate.dests` represent slightly different things,
    despite having similar names:

    - :attr:`.LogicNet.dests` represents the :class:`LogicNet`'s output wire. It is a
      list of :class:`WireVectors<.WireVector>` which hold the :class:`.LogicNet`'s
      output. There can be at most one :class:`WireVector` in :attr:`.LogicNet.dests`,
      but that :class:`.WireVector` can be an :attr:`arg<.LogicNet.args>` to any number
      of :class:`LogicNets<.LogicNet>`.

    - :attr:`Gate.dests` represents the :class:`Gate`'s users. It is a list of
      :class:`Gates<Gate>` that use the :class:`Gate`'s output as one of their
      :attr:`~Gate.args`. There can be any number of :class:`Gates<Gate>` in
      :attr:`Gate.dests`.

    With a :class:`Gate` representation, it is easy to iteratively traverse the data
    structure:

    1. Forwards (from producer to consumer), by following :attr:`~Gate.dests`
       references.

    2. Backwards (from consumer to producer), by following :attr:`~Gate.args`
       references.

    With :class:`Gates<Gate>`, the example from the :ref:`gate_motivation` section looks
    like::

        ┌─────────────────┐
        │ Gate "a"        │
        │     op: "I"     │
        │     name: "a"   │
        │     bitwidth: 1 │    ┌─────────────────┐
        │     dests:──────┼───▶│ Gate "&"        │
        └─────────────────┘◀─┐ │     op: "&"     │
        ┌─────────────────┐  └─┼─────args        │
        │ Gate "b"        │◀───┼─────args        │
        │     op: "I"     │    │     name: "x"   │    ┌─────────────────┐
        │     name: "b"   │    │     bitwidth: 1 │    │ Gate "|"        │
        │     bitwidth: 1 │ ┌─▶│     dests:──────┼───▶│     op: "|"     │
        │     dests:──────┼─┘  └─────────────────┘◀───┼─────args        │
        └─────────────────┘  ┌────────────────────────┼─────args        │
        ┌─────────────────┐  │                        │     name: "y"   │
        │ Gate "c"        │◀─┘   ┌───────────────────▶│     bitwidth: 1 │
        │     op: "I"     │      │                    └─────────────────┘
        │     name: "c"   │      │
        │     bitwidth: 1 │      │
        │     dests:──────┼──────┘
        └─────────────────┘

    The :class:`Gate` representation addresses the two issues raised in the
    :ref:`gate_motivation` section:

    1. The :class:`Gate` representation is easy to explore iteratively by following
       references, which are shown as arrows in the figure above.

    2. There is only one class in the :class:`Gate` graph, so we don't need to keep
       track of the current object's type as we follow arrows in the graph, like we did
       with :class:`LogicNet` and :class:`WireVector`. Everything is a :class:`Gate`.

    For usage examples, see :class:`GateGraph` and :class:`Gate`'s documentation below.
    """

    op: str
    """Operation performed by this ``Gate``. Corresponds to :attr:`.LogicNet.op`.

    For special ``Gates`` created for :class:`.Input`, ``op`` will instead be the
    :class:`.Input`'s ``_code``, which is ``I``.

    For special ``Gates`` created for :class:`.Const`, ``op`` will instead be the
    :class:`.Const`'s ``_code``, which is ``C``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> _ = ~a

        >>> gate_graph = pyrtl.GateGraph()
        >>> gate_a = gate_graph.get_gate("a")
        >>> gate_a.op
        'I'
        >>> gate_a.dests[0].op
        '~'
    """

    op_param: tuple
    """Static parameters for the operation. Corresponds to :attr:`.LogicNet.op_param`.

    These are constant parameters, whose values are statically known. These values
    generally do not appear as actual values on wires. For example, the bits to select
    for the ``s`` bit-slice operation are stored as ``op_params``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=8)
        >>> bit_slice = a[1:3]
        >>> bit_slice.name = "bit_slice"

        >>> gate_graph = pyrtl.GateGraph()
        >>> bit_slice_gate = gate_graph.get_gate("bit_slice")
        >>> bit_slice_gate.op_param
        (1, 2)
    """

    args: list[Gate]
    """Inputs to the operation. Corresponds to :attr:`.LogicNet.args`.

    For each ``Gate`` ``arg`` in ``self.args``, ``self`` is in ``arg.dests``.

    Some special ``Gates`` represent operations without ``args``, like :class:`.Input`
    and :class:`.Const` :class:`WireVectors<.WireVector>`. Such operations will have an
    empty list of ``args``.

    .. note::

        The same ``Gate`` may appear multiple times in ``args``. A :class:`.Register`
        ``Gate`` may be its own ``arg``, creating a self-loop.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> b = pyrtl.Input(name="b", bitwidth=1)
        >>> c = pyrtl.Input(name="c", bitwidth=1)
        >>> abc = pyrtl.concat(a, b, c)
        >>> abc.name = "abc"

        >>> gate_graph = pyrtl.GateGraph()
        >>> abc_gate = gate_graph.get_gate("abc")
        >>> [gate.name for gate in abc_gate.args]
        ['a', 'b', 'c']
    """

    name: str
    """Name of the operation's output :class:`.WireVector`.

    Corresponds to :attr:`.WireVector.name`.

    Some operations do not have outputs, like :class:`.MemBlock` writes. These
    operations will have a ``name`` of ``None``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> b = pyrtl.Input(name="b", bitwidth=1)
        >>> ab = a + b
        >>> ab.name = "ab"

        >>> gate_graph = pyrtl.GateGraph()
        >>> ab_gate = gate_graph.get_gate("ab")
        >>> ab_gate.name
        'ab'
    """

    bitwidth: int
    """Bitwidth of the operation's output :class:`.WireVector`.

    Corresponds to :attr:`.WireVector.bitwidth`.

    Some operations do not have outputs, like :class:`.MemBlock` writes. These
    operations will have a ``bitwidth`` of ``None``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> b = pyrtl.Input(name="b", bitwidth=1)
        >>> ab = a + b
        >>> ab.name = "ab"

        >>> gate_graph = pyrtl.GateGraph()
        >>> ab_gate = gate_graph.get_gate("ab")
        >>> ab_gate.bitwidth
        2
    """

    dests: list[Gate]
    """:class:`list` of :class:`Gates<Gate>` that use this operation's output as one of
    their :attr:`~Gate.args`.

    For each :class:`Gate` ``dest`` in ``self.dests``, ``self`` is in ``dest.args``.

    .. note::

        The same :class:`Gate` may appear multiple times in ``dests``. A self-loop
        :class:`.Register` ``Gate`` may appear in its own ``dests``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> _ = a + 1
        >>> _ = a - 1

        >>> gate_graph = pyrtl.GateGraph()
        >>> a_gate = gate_graph.get_gate("a")
        >>> [gate.op for gate in a_gate.dests]
        ['+', '-']
    """

    is_output: bool
    """Indicates if the operation's output is an :class:`.Output` :class:`.WireVector`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> b = pyrtl.Output(name="b", bitwidth=1)
        >>> b <<= a

        >>> gate_graph = pyrtl.GateGraph()
        >>> a_gate = gate_graph.get_gate("a")
        >>> a_gate.is_output
        False
        >>> b_gate = gate_graph.get_gate("b")
        >>> b_gate.is_output
        True
    """

    def __init__(
        self,
        logic_net: LogicNet = None,
        wire_vector: WireVector = None,
        args: list[Gate] | None = None,
    ):
        """Create a ``Gate`` from a :class:`.LogicNet` or :class:`.WireVector`.

        ``Gates`` are complicated to construct because they are doubly-linked, and there
        may be cycles in the ``Gate`` graph. Most users should not call this constructor
        directly, and instead use :class:`GateGraph` to create ``Gates`` from a
        :class:`.Block`.

        :param logic_net: :class:`.LogicNet` to create this ``Gate`` from. If
            ``logic_net`` is specified, ``wire_vector`` must be ``None``.

            ``logic_net`` must not be a register, where ``logic_net.op == 'r'``.

            Register ``Gates`` are created in two phases by :class:`GateGraph`. In the
            first phase, a placeholder ``Gate`` is created from the :class:`.Register`
            :class:`.WireVector`. In this first phase, the register ``Gate``'s ``op`` is
            temporarily set to ``R``, which is the :class:`.Register`'s ``_code``. This
            placeholder is needed to resolve other ``Gate``'s references to the register
            in the second phase. In the second phase, the register ``Gate``'s remaining
            fields are populated from the register's :class:`.LogicNet`. In the second
            phase, the register ``Gate``'s ``op`` is changed to ``r``, which is the
            :class:`.LogicNet`'s :attr:`~.LogicNet.op`.

        :param wire_vector: :class:`.WireVector` to create this ``Gate`` from. If
            ``wire_vector`` is specified, ``logic_net`` must be ``None``.

            ``wire_vector`` must be a :class:`.Const`, :class:`.Input`, or
            :class:`.Register`.

        :param args: A :class:`list` of ``Gates`` that are inputs to this ``Gate``. This
            corresponds to :attr:`.LogicNet.args`, except that each of a ``Gate``'s
            ``args`` is a ``Gate``.
        """
        self.op_param = None
        if args is None:
            self.args = []
        else:
            self.args = args
        self.name = None
        self.bitwidth = None
        # ``dests`` will be set up later, by ``GateGraph``.
        self.dests = []
        self.is_output = False

        if logic_net is not None:
            # Constructing a ``Gate`` from a ``logic_net``.
            self.logic_net = logic_net

            # For ``LogicNets``, set the ``Gate``'s ``op``, ``op_param``, ``name``,
            # ``bitwidth``.
            if wire_vector is not None:
                msg = "Do not pass both logic_net and wire_vector to Gate."
                raise PyrtlError(msg)
            self.op = logic_net.op
            if self.op == "r":
                msg = "Registers should be created from a wire_vector, not a logic_net."
                raise PyrtlError(msg)
            self.op_param = logic_net.op_param

            num_dests = len(logic_net.dests)
            if num_dests:
                if num_dests > 1:
                    # The ``Gate`` representation supports at most one ``LogicNet``
                    # ``dest``. If more than one ``LogicNet`` ``dest`` is needed in the
                    # future, concat them together, then split them apart with ``s``
                    # bit-selection ``Gates``, or use multiple ``Gates`` with the same
                    # ``args``.
                    msg = "LogicNets with more than one dest are not supported"
                    raise PyrtlError(msg)
                dest = logic_net.dests[0]
                self.wire_vector = dest
                self.name = dest.name
                self.bitwidth = dest.bitwidth
                if dest._code == "O":
                    self.is_output = True

        else:
            # Constructing a ``Gate`` from a ``wire_vector``.
            #
            # For ``Inputs`` and ``Registers``, set the ``Gate``'s ``op`` and ``dest``.
            # For ``Consts``, also copy the ``val`` to ``op_param``.
            # For ``Registers``, also copy the ``reset_value`` to ``op_param``.
            if wire_vector is None:
                msg = "Gate must be constructed from a logic_net or a wire_vector."
                raise PyrtlError(msg)

            if wire_vector._code not in "CIR":
                msg = (
                    "Gate must be constructed from a Const, Input or Register "
                    "wire_vector."
                )
                raise PyrtlError(msg)

            self.wire_vector = wire_vector

            self.op = wire_vector._code
            self.name = wire_vector.name
            self.bitwidth = wire_vector.bitwidth
            if self.op == "C":
                self.op_param = (wire_vector.val,)
            elif self.op == "R":
                if not wire_vector.reset_value:
                    self.op_param = (0,)
                else:
                    self.op_param = (wire_vector.reset_value,)

    def __str__(self):
        """Return a string representation of this ``Gate``.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> a = pyrtl.Input(name="a", bitwidth=8)
            >>> bit_slice = a[2:4]
            >>> bit_slice.name = "bit_slice"

            >>> gate_graph = pyrtl.GateGraph()
            >>> bit_slice_gate = gate_graph.get_gate("bit_slice")

            >>> print(bit_slice_gate)
            bit_slice/2 = slice(a/8) [sel=(2, 3)]

        In this sample string representation:

        - :attr:`~Gate.name` is ``bit_slice``.

        - :attr:`~Gate.bitwidth` is ``2``.

        - :attr:`~Gate.op` is ``s``, spelled out as ``slice`` to improve readability.

        - :attr:`~Gate.args` is ``[<Gate for "a">]``::

            >>> bit_slice_gate.args[0] is gate_graph.get_gate("a")
            True

        - :attr:`~Gate.op_param` is ``(2, 3)``, written as ``sel``
          because a ``slice``'s :attr:`~Gate.op_param` determines the selected bits.
          This improves readability by indicating what the :attr:`~Gate.op_param` means
          for the :attr:`~Gate.op`.
        """
        if self.name is None:
            dest = ""
        else:
            dest_notes = ""
            if self.is_output:
                dest_notes = " [Output]"

            dest = f"{self.name}/{self.bitwidth}{dest_notes} "

        op_name_map = {
            "&": "and",
            "|": "or",
            "^": "xor",
            "n": "nand",
            "~": "not",
            "+": "add",
            "-": "sub",
            "*": "mul",
            "=": "eq",
            "<": "lt",
            ">": "gt",
            "w": "",
            "x": "",
            "c": "concat",
            "s": "slice",
            "r": "reg",
            "m": "read",
            "@": "write",
            "I": "Input",
            "C": "Const",
        }
        if self.name is None:
            op = op_name_map[self.op]
        else:
            op = f"= {op_name_map[self.op]}"

        if not self.args:
            args = ""
        else:
            arg_names = [f"{arg.name}/{arg.bitwidth}" for arg in self.args]
            if self.op == "w":
                args = arg_names[0]
            elif self.op == "x":
                args = f"{arg_names[0]} ? {arg_names[2]} : {arg_names[1]}"
            elif self.op == "m":
                args = f"(addr={arg_names[0]})"
            elif self.op == "@":
                args = (
                    f"(addr={arg_names[0]}, data={arg_names[1]}, enable={arg_names[2]})"
                )
            else:
                args = f"({', '.join(arg_names)})"

        if self.op_param is None:
            op_param = ""
        elif self.op == "C":
            op_param = f"({self.op_param[0]})"
        elif self.op == "s":
            op_param = f" [sel={self.op_param}]"
        elif self.op == "m" or self.op == "@":
            op_param = f" [memid={self.op_param[0]} mem={self.op_param[1].name}]"
        elif self.op == "r":
            op_param = f" [reset_value={self.op_param[0]}]"
        else:
            op_param = f" [op_param={self.op_param}]"

        return f"{dest}{op}{args}{op_param}"


class GateGraph:
    """A :class:`GateGraph` is a collection of :class:`Gates<Gate>`.
    :class:`GateGraph`'s constructor creates :class:`Gates<Gate>` from a
    :class:`.Block`.

    Users should generally construct :class:`GateGraphs<GateGraph>`, rather than
    attempting to directly construct individual :class:`Gates<Gate>`. :class:`Gate`
    construction is complex because they are doubly-linked, and the :class:`Gate` graph
    may contain cycles.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    For example, let's build a :class:`GateGraph` for the :ref:`gate_motivation`
    example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> b = pyrtl.Input(name="b", bitwidth=1)
        >>> c = pyrtl.Input(name="c", bitwidth=1)

        >>> x = a & b
        >>> x.name = "x"

        >>> y = x | c
        >>> y.name = "y"

        >>> gate_graph = pyrtl.GateGraph()
        >>> print(gate_graph)
        a/1 = Input
        b/1 = Input
        c/1 = Input
        x/1 = and(a/1, b/1)
        y/1 = or(x/1, c/1)

    We can examine the input ``a``'s :attr:`~Gate.dests` to see that ``a`` is an
    argument to a bitwise ``&`` operation::

        >>> a = gate_graph.get_gate("a")
        >>> a.dests[0].op
        '&'

    We can examine the bitwise ``&``'s other :attr:`~Gate.args`, to get a reference to
    input :class:`Gate` ``b``::

        >>> b = a.dests[0].args[1]
        >>> b.name
        'b'

    Special :class:`Gates<Gate>`
    ----------------------------

    Generally, :class:`GateGraph` converts each :class:`.LogicNet` in a :class:`.Block`
    to a corresponding :class:`Gate`, but some :class:`WireVectors<.WireVector>` and
    :class:`LogicNets<.LogicNet>` are handled differently:

    - An :class:`.Input` :class:`.WireVector` is converted to a special input
      :class:`Gate`, with op ``I``. Input :class:`Gates<Gate>` have no
      :attr:`~Gate.args`.

    - A :class:`.Const` :class:`.WireVector` is converted to a special const
      :class:`Gate`, with op ``C``. Const :class:`Gates<Gate>` have no
      :attr:`~Gate.args`. The constant's value is stored in :attr:`Gate.op_param`.

    - An :class:`.Output` :class:`.WireVector` is handled normally, and will be the
      ``dest`` of the :class:`Gate` that defines the :class:`.Output`'s value. That
      :class:`Gate` will have its :attr:`~Gate.is_output` attribute set to ``True``.

    - :class:`.Register` :class:`WireVectors<.WireVector>` and
      :class:`LogicNets<.LogicNet>` are handled normally, except that the
      :class:`.Register`'s ``reset_value`` is stored in :attr:`Gate.op_param`. Register
      :class:`Gates<Gate>` use the register :class:`.LogicNet` :attr:`~.LogicNet.op`
      ``r``, not the :class:`.Register` ``_code`` ``R``.

    .. note::

        Registers can create cycles in the :class:`Gate` graph, because the logic that
        defines the register's :attr:`~.Register.next` value (which is the register
        :class:`Gate`'s :attr:`~Gate.args`) can depend on the register's current value
        (which is the register :class:`Gate`'s :attr:`~Gate.dests`). Watch out for
        infinite loops when traversing a :class:`GateGraph` with registers. For example,
        if you keep following :attr:`~Gate.dests` references, you may end up back where
        you started.
    """

    gates: list[Gate]
    """A :class:`list` of all :class:`Gates<Gate>` in the ``GateGraph``."""

    sources: list[Gate]
    """A :class:`list` of all ``source`` :class:`Gates<Gate>` in the ``GateGraph``.

    A ``source`` :class:`Gate`'s output value is known at the beginning of each clock
    cycle. :class:`Consts<.Const>`, :class:`Inputs<.Input>`, and
    :class:`Registers<.Register>` are ``source`` :class:`Gates<Gate>`.

    .. note::

        :class:`Registers<.Register>` are both ``sources`` and ``sinks``. As a
        ``source``, it provides the :class:`.Register`'s value for the current cycle. As
        a ``sink``, it determines the :class:`.Register`'s value for the next cycle.
    """

    sinks: list[Gate]
    """A list of all ``sink`` :class:`Gates<Gate>` in the ``GateGraph``.

    A ``sink`` :class:`Gate`'s output value is known only at the end of each clock
    cycle. :class:`Registers<.Register>`, :class:`Outputs<.Output>` and any
    :class:`Gate` without users (``len(dests) == 0``) are sink :class:`Gates<Gate>`.

    .. note::

        :class:`Registers<.Register>` are both ``sources`` and ``sinks``. As a
        ``source``, it provides the :class:`.Register`'s value for the current cycle. As
        a ``sink``, it determines the :class:`.Register`'s value for the next cycle.
    """

    def __init__(self, block: Block = None):
        """Create :class:`Gates<Gate>` from a :class:`.Block`.

        Most users should use this constructor, rather than attempting to directly
        construct individual :class:`Gates<Gate>`.

        :param block: :class:`.Block` to construct the :class:`GateGraph` from. Defaults
            to the :ref:`working_block`.
        """
        self.gates = []
        self.sources = []
        self.sinks = []

        block = working_block(block)

        # The ``Gate`` graph is doubly-linked, and may contain cycles, so construction
        # is done in two phases. In the first phase, we only construct ``Gates`` for
        # ``sources``, which are ``Consts``, ``Inputs``, and ``Registers``.
        #
        # In this phase, register gates are placeholders. They do not have ``args``, and
        # their ``op`` is temporarily ``R``, which is ``Register._code`. These
        # placeholders are needed to resolve references to registers in the second
        # phase.
        #
        # ``wire_vector_map`` maps from ``WireVector`` to the corresponding gate. It is
        # initially populated with ``Gates`` constructed from ``sources``.
        wire_vector_map: dict[WireVector, Gate] = {}
        for wire_vector in block.wirevector_subset((Const, Input, Register)):
            gate = Gate(wire_vector=wire_vector)
            self.gates.append(gate)
            self.sources.append(gate)
            wire_vector_map[wire_vector] = gate

        # In the second phase, we construct all remaining ``Gates`` from ``LogicNets``.
        # ``Block``'s iterator returns ``LogicNets`` in topological order, so we can be
        # sure that each ``LogicNet``'s ``args`` are all in ``wire_vector_map``.
        for logic_net in block:
            # Find the ``Gates`` corresponding to the ``LogicNet``'s ``args``.
            gate_args = []
            for wire_arg in logic_net.args:
                gate_arg = wire_vector_map.get(wire_arg)
                if gate_arg is None:
                    msg = f"Missing Gate for wire {wire_arg}"
                    raise PyrtlError(msg)
                gate_args.append(gate_arg)
            if logic_net.op == "r":
                # Find the placeholder register ``Gate`` we created earlier, and finish
                # constructing it.
                gate = wire_vector_map[logic_net.dests[0]]
                gate.op = "r"
                gate.args = gate_args
                self.sinks.append(gate)
            else:
                gate = Gate(logic_net=logic_net, args=gate_args)
                self.gates.append(gate)

            # Add the new ``Gate`` as a ``dest`` for its ``args``.
            for gate_arg in gate_args:
                gate_arg.dests.append(gate)

            # Add the new ``Gate`` to ``wire_vector_map``, so we can resolve future
            # references to it.
            num_dests = len(logic_net.dests)
            if num_dests:
                if num_dests > 1:
                    msg = "LogicNets with more than one dest are not supported"
                    raise PyrtlError(msg)
                dest = logic_net.dests[0]
                wire_vector_map[dest] = gate

        for gate in self.gates:
            if len(gate.dests) == 0:
                self.sinks.append(gate)

    def get_gate(self, name: str) -> Gate:
        """Return the :class:`Gate` whose :attr:`~Gate.name` is ``name``, or ``None`` if
        no such :class:`Gate` exists.

        .. warning::

            :class:`.MemBlock` writes do not produce an output, so they can not be
            retrieved with ``get_gate``.

        :param name: Name of the :class:`Gate` to find.

        :return: The named :class:`Gate`, or ``None`` if no such :class:`Gate` was
                 found.
        """
        for gate in self.gates:
            if gate.name == name:
                return gate
        return None

    def __str__(self) -> str:
        """Return a string representation of the ``GateGraph``.

        This returns a string representation of each :class:`Gate` in the ``GateGraph``,
        one :class:`Gate` per line. The :class:`Gates<Gate>` will be sorted by name.
        """
        sorted_gates = sorted(self.gates, key=lambda gate: gate.name)
        return "\n".join([str(gate) for gate in sorted_gates])
