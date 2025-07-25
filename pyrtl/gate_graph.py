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

This data structure is difficult to work with for three reasons:

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

3. :class:`.WireVector` is part of PyRTL's user interface, but also a key part of
   PyRTL's internal representation. This makes :class:`.WireVector` complex and
   difficult to modify, because it must implement user-facing features like inferring
   bitwidth from assignment, while also maintaining a consistent internal representation
   for simulation, analysis, and optimization.

:class:`GateGraph` is an alternative representation that addresses these issues. A
:class:`GateGraph` is just a collection of :class:`Gates<Gate>`, so we'll cover
:class:`Gate` first.
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
       :attr:`~WireVector.bitwidth` are stored as :attr:`Gate.name` and
       :attr:`Gate.bitwidth`. If the :class:`.LogicNet` produces no output, like a
       :class:`.MemBlock` write, the :class:`Gate`'s :attr:`~Gate.name` and
       :attr:`~Gate.bitwidth` will be ``None``. PyRTL does not have an
       :attr:`~.LogicNet.op` with multiple :attr:`.LogicNet.dests`.

    3. The :class:`Gate` has a new :attr:`Gate.dests` attribute, which has no direct
       equivalent in the :class:`.LogicNet`/:class:`.WireVector` representation.
       :attr:`Gate.dests` is a list of the :class:`Gates<Gate>` that use this
       :class:`Gate`'s output as one of their :attr:`~Gate.args`.

    :attr:`.LogicNet.dests` and :attr:`Gate.dests` represent slightly different things,
    despite having similar names:

    - :attr:`.LogicNet.dests` represents the :class:`LogicNet`'s output wire. It is a
      list of :class:`WireVectors<.WireVector>` which hold the :class:`.LogicNet`'s
      output. There can only be zero or one :class:`WireVectors<.WireVector>` in
      :attr:`.LogicNet.dests`, but that :class:`.WireVector` can be an
      :attr:`arg<.LogicNet.args>` to any number of :class:`LogicNets<.LogicNet>`.

    - :attr:`Gate.dests` represents the :class:`Gate`'s users. It is a list of
      :class:`Gates<Gate>` that use the :class:`Gate`'s output as one of their
      :attr:`~Gate.args`. There can be any number of :class:`Gates<Gate>` in
      :attr:`Gate.dests`.

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

    With a :class:`Gate` representation, it is easy to iteratively traverse the data
    structure:

    1. Forwards, from producer to consumer, by following :attr:`~Gate.dests` references.

    2. Backwards, from consumer to producer, by following :attr:`~Gate.args` references.

    The :class:`Gate` representation addresses the issues raised in the
    :ref:`gate_motivation` section:

    1. The :class:`Gate` representation is easy to iteratively explore by following
       :attr:`~Gate.args` and :attr:`~Gate.dests` references, which are shown as arrows
       in the figure above.

    2. There is only one class in the :class:`Gate` graph, so we don't need to keep
       track of the current object's type as we follow arrows in the graph, like we did
       with :class:`LogicNet` and :class:`WireVector`. Everything is a :class:`Gate`.

    3. By decoupling the :class:`Gate` representation from :class:`.WireVector` and
       :class:`.LogicNet`, :class:`Gate` specializes in supporting analysis use cases,
       without the burden of supporting all of :class:`.WireVector`'s other features.
       This significantly simplifies :class:`Gate`'s design and implementation.

    For usage examples, see :class:`GateGraph` and :class:`Gate`'s documentation below.
    """

    op: str
    """Operation performed by this ``Gate``. Corresponds to :attr:`.LogicNet.op`.

    For special ``Gates`` created for :class:`Inputs<.Input>`, ``op`` will instead be
    the :class:`.Input`'s ``_code``, which is ``I``.

    For special ``Gates`` created for :class:`Consts<.Const>`, ``op`` will instead be
    the :class:`.Const`'s ``_code``, which is ``C``.

    See :class:`.LogicNet`'s documentation for a description of all other ``ops``.

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
    and :class:`.Const`. Such operations will have an empty list of ``args``.

    .. note::

        The same ``Gate`` may appear multiple times in ``args``. A self-loop
        :class:`.Register` ``Gate`` may be its own ``arg``.

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

    name: str | None
    """Name of the operation's output. Corresponds to :attr:`.WireVector.name`.

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

    bitwidth: int | None
    """Bitwidth of the operation's output. Corresponds to :attr:`.WireVector.bitwidth`.

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
    """Indicates if the operation's output is an :class:`.Output`.

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
            first phase, a placeholder ``Gate`` is created from the :class:`.Register`.
            In this first phase, the register ``Gate``'s ``op`` is temporarily set to
            ``R``, which is the :class:`.Register`'s ``_code``. This placeholder is
            needed to resolve other ``Gate``'s references to the register in the second
            phase. In the second phase, the register ``Gate``'s remaining fields are
            populated from the register's :class:`.LogicNet`. In the second phase, the
            register ``Gate``'s ``op`` is changed to ``r``, which is the
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
            #
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

    def __str__(self) -> str:
        """:return: A string representation of this ``Gate``.

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
            "~": "invert",
            "+": "add",
            "-": "sub",
            "*": "mul",
            "=": "eq",
            "<": "lt",
            ">": "gt",
            "w": "",
            "x": "",  # Multiplexers are printed as ternary operators.
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

    See :ref:`gate_motivation` for more background.

    Users should generally construct :class:`GateGraphs<GateGraph>`, rather than
    attempting to directly construct individual :class:`Gates<Gate>`. :class:`Gate`
    construction is complex because they are doubly-linked, and the :class:`Gate` graph
    may contain cycles.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example
    -------

    Let's build a :class:`GateGraph` for the :ref:`gate_motivation` example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> b = pyrtl.Input(name="b", bitwidth=1)
        >>> c = pyrtl.Input(name="c", bitwidth=1)

        >>> x = a & b
        >>> x.name = "x"

        >>> y = x | c
        >>> y.name = "y"

        >>> gate_graph = pyrtl.GateGraph()

    The :class:`GateGraph` can be printed, revealing five :class:`Gates<Gate>`::

        >>> print(gate_graph)
        a/1 = Input
        b/1 = Input
        c/1 = Input
        x/1 = and(a/1, b/1)
        y/1 = or(x/1, c/1)

    We can retrieve the :attr:`Gate` for input ``a``::

        >>> a = gate_graph.get_gate("a")
        >>> print(a)
        a/1 = Input
        >>> a.name
        'a'
        >>> a.op
        'I'

    We can check ``a``'s :attr:`~Gate.dests` to see that it is an argument to a bitwise
    ``&`` operation, with output named ``x``::

        >>> len(a.dests)
        1
        >>> x = a.dests[0]
        >>> print(x)
        x/1 = and(a/1, b/1)
        >>> x.op
        '&'
        >>> x.name
        'x'

    We can examine the bitwise ``&``'s :attr:`~Gate.args`, to get references to input
    :class:`Gates<Gate>` ``a`` and ``b``::

        >>> x.args[0] is a
        True

        >>> b = x.args[1]
        >>> print(b)
        b/1 = Input
        >>> b.name
        'b'
        >>> b.op
        'I'

    Special :class:`Gates<Gate>`
    ----------------------------

    Generally, :class:`GateGraph` converts each :class:`.LogicNet` in a :class:`.Block`
    to a corresponding :class:`Gate`, but some :class:`WireVectors<.WireVector>` and
    :class:`LogicNets<.LogicNet>` are handled differently:

    - An :class:`.Input` :class:`.WireVector` is converted to a special input
      :class:`Gate`, with op ``I``. Input :class:`Gates<Gate>` have no
      :attr:`~Gate.args`, and do not correspond to a :class:`.LogicNet`.

    - A :class:`.Const` :class:`.WireVector` is converted to a special const
      :class:`Gate`, with op ``C``. Const :class:`Gates<Gate>` have no
      :attr:`~Gate.args`, and do not correspond to a :class:`.LogicNet`. The constant's
      value is stored in :attr:`Gate.op_param`.

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

    gates: set[Gate]
    """A :class:`set` of all :class:`Gates<Gate>` in the ``GateGraph``.

    Similar to :attr:`~GateGraph.__iter__`, except that ``gates`` is a :class:`set`
    rather than an :class:`~collections.abc.Iterable`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> b = pyrtl.Input(name="b", bitwidth=1)
        >>> c = pyrtl.Input(name="c", bitwidth=1)
        >>> x = a & b
        >>> x.name = "x"
        >>> y = x | c
        >>> y.name = "y"

        >>> gate_graph = pyrtl.GateGraph()

        >>> sorted(gate.name for gate in gate_graph.gates)
        ['a', 'b', 'c', 'x', 'y']
    """

    consts: set[Gate]
    """A :class:`set` of :class:`.Const` :class:`Gates<Gate>` in the ``GateGraph``.

    These :class:`Gates<Gate>` provide constant values, with :attr:`~Gate.op` ``C``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> c = pyrtl.Const(name="c", val=0)
        >>> d = pyrtl.Const(name="d", val=1)
        >>> _ = c + d

        >>> gate_graph = pyrtl.GateGraph()

        >>> sorted(gate.name for gate in gate_graph.consts)
        ['c', 'd']
    """

    inputs: set[Gate]
    """A :class:`set` of :class:`.Input` :class:`Gates<Gate>` in the ``GateGraph``.

    These :class:`Gates<Gate>` provide :class:`.Input` values, with :attr:`~Gate.op`
    ``I``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> b = pyrtl.Input(name="b", bitwidth=1)
        >>> _ = a & b

        >>> gate_graph = pyrtl.GateGraph()

        >>> sorted(gate.name for gate in gate_graph.inputs)
        ['a', 'b']
    """

    outputs: set[Gate]
    """A :class:`set` of :class:`.Output` :class:`Gates<Gate>` in the ``GateGraph``.

    These :class:`Gates<Gate>` set :class:`.Output` values, with :attr:`~Gate.is_output`
    ``True``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> x = pyrtl.Output(name="x")
        >>> y = pyrtl.Output(name="y")
        >>> x <<= 42
        >>> y <<= 255

        >>> gate_graph = pyrtl.GateGraph()

        >>> sorted(gate.name for gate in gate_graph.outputs)
        ['x', 'y']
    """

    registers: set[Gate]
    """A :class:`set` of :class:`.Register` update :class:`Gates<Gate>` in the
    ``GateGraph``.

    These :class:`Gates<Gate>` set a :class:`.Register`'s value for the next cycle, with
    :attr:`~Gate.op` ``r``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> r = pyrtl.Register(name="r", bitwidth=1)
        >>> s = pyrtl.Register(name="s", bitwidth=1)
        >>> r.next <<= r + 1
        >>> s.next <<= s + 2

        >>> gate_graph = pyrtl.GateGraph()

        >>> sorted(gate.name for gate in gate_graph.registers)
        ['r', 's']
    """

    mem_reads: set[Gate]
    """A :class:`set` of :class:`.MemBlock` read :class:`Gates<Gate>` in the
    ``GateGraph``.

    These :class:`Gates<Gate>` read :class:`MemBlocks<.MemBlock>`, with
    :attr:`~Gate.op` ``m``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> mem = pyrtl.MemBlock(name="mem", bitwidth=4, addrwidth=2)
        >>> addr = pyrtl.Input(name="addr", bitwidth=2)
        >>> mem_read_1 = mem[addr]
        >>> mem_read_1.name = "mem_read_1"
        >>> mem_read_2 = mem[addr]
        >>> mem_read_2.name = "mem_read_2"

        >>> gate_graph = pyrtl.GateGraph()

        >>> sorted(gate.name for gate in gate_graph.reads)
        ['mem_read_1', 'mem_read_2']
    """

    mem_writes: set[Gate]
    """A :class:`set` of :class:`.MemBlock` write :class:`Gates<Gate>` in the
    ``GateGraph``.

    These :class:`Gates<Gate>` write :class:`MemBlocks<.MemBlock>`, with
    :attr:`~Gate.op` ``@``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> mem = pyrtl.MemBlock(name="mem", bitwidth=4, addrwidth=2)
        >>> addr = pyrtl.Input(name="addr", bitwidth=2)
        >>> mem[addr] <<= 7

        >>> gate_graph = pyrtl.GateGraph()

        >>> # MemBlock writes have no name.
        >>> [gate.name for gate in gate_graph.mem_writes]
        [None]

        >>> [gate.op for gate in gate_graph.mem_writes]
        ['@']
    """

    sources: set[Gate]
    """A :class:`set` of ``source`` :class:`Gates<Gate>` in the ``GateGraph``.

    A ``source`` :class:`Gate`'s output value is known at the beginning of each clock
    cycle. :class:`Consts<.Const>`, :class:`Inputs<.Input>`, and
    :class:`Registers<.Register>` are ``source`` :class:`Gates<Gate>`.

    .. note::

        :class:`Registers<.Register>` are both ``sources`` and :attr:`~GateGraph.sinks`.
        As a ``source``, it provides the :class:`.Register`'s value for the current
        cycle. As a :attr:`sink<GateGraph.sinks>`, it determines the
        :class:`.Register`'s value for the next cycle.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> c = pyrtl.Const(name="c", bitwidth=1, val=0)
        >>> r = pyrtl.Register(name="r", bitwidth=1)
        >>> r.next <<= a + c

        >>> gate_graph = pyrtl.GateGraph()

        >>> sorted(gate.name for gate in gate_graph.sources)
        ['a', 'c', 'r']
    """

    sinks: set[Gate]
    """A :class:`set` of ``sink`` :class:`Gates<Gate>` in the ``GateGraph``.

    A ``sink`` :class:`Gate`'s output value is known only at the end of each clock
    cycle. :class:`Registers<.Register>`, :class:`Outputs<.Output>`, :class:`MemBlock`
    writes, and any :class:`Gate` without users (``len(dests) == 0``) are sink
    :class:`Gates<Gate>`.

    .. note::

        :class:`Registers<.Register>` are both :attr:`~GateGraph.sources` and ``sinks``.
        As a :attr:`source<GateGraph.sources>`, it provides the :class:`.Register`'s
        value for the current cycle. As a ``sink``, it determines the
        :class:`.Register`'s value for the next cycle.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=1)
        >>> r = pyrtl.Register(name="r", bitwidth=1)
        >>> o = pyrtl.Output(name="o", bitwidth=1)
        >>> r.next <<= a + 1
        >>> o <<= 1
        >>> sum = a + r
        >>> sum.name = "sum"

        >>> gate_graph = pyrtl.GateGraph()

        >>> sorted(gate.name for gate in gate_graph.sinks)
        ['o', 'r', 'sum']
    """

    def __init__(self, block: Block = None):
        """Create :class:`Gates<Gate>` from a :class:`.Block`.

        Most users should call this constructor, rather than attempting to directly
        construct individual :class:`Gates<Gate>`.

        :param block: :class:`.Block` to construct the :class:`GateGraph` from. Defaults
            to the :ref:`working_block`.
        """
        self.gates = set()
        self.consts = set()
        self.inputs = set()
        self.outputs = set()
        self.registers = set()
        self.mem_reads = set()
        self.mem_writes = set()
        self.sources = set()
        self.sinks = set()

        block = working_block(block)
        block.sanity_check()

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
            self.gates.add(gate)
            self.sources.add(gate)
            wire_vector_map[wire_vector] = gate

            if gate.op == "C":
                self.consts.add(gate)
            elif gate.op == "I":
                self.inputs.add(gate)
            elif gate.op == "R":
                self.registers.add(gate)

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
                self.sinks.add(gate)
            else:
                gate = Gate(logic_net=logic_net, args=gate_args)
                self.gates.add(gate)

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

            if gate.is_output:
                self.outputs.add(gate)
            if gate.op == "m":
                self.mem_reads.add(gate)
            elif gate.op == "@":
                self.mem_writes.add(gate)

        for gate in self.gates:
            if len(gate.dests) == 0:
                self.sinks.add(gate)

    def get_gate(self, name: str) -> Gate | None:
        """Return the :class:`Gate` whose :attr:`~Gate.name` is ``name``, or ``None`` if
        no such :class:`Gate` exists.

        .. warning::

            :class:`.MemBlock` writes do not produce an output, so they can not be
            retrieved with ``get_gate``.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> a = pyrtl.Input(name="a", bitwidth=1)
            >>> na = ~a
            >>> na.name = "na"

            >>> gate_graph = pyrtl.GateGraph()

            >>> a_gate = gate_graph.get_gate("a")
            >>> na_gate = gate_graph.get_gate("na")
            >>> na_gate.op
            '~'
            >>> na_gate.args[0] is a_gate
            True

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

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> a = pyrtl.Input(name="a", bitwidth=2)
            >>> b = pyrtl.Input(name="b", bitwidth=2)
            >>> sum = a + b
            >>> sum.name = "sum"

            >>> gate_graph = pyrtl.GateGraph()

            >>> print(gate_graph)
            a/2 = Input
            b/2 = Input
            sum/3 = add(a/2, b/2)

        :return: A string representation of each :class:`Gate` in the ``GateGraph``, one
                 :class:`Gate` per line. The :class:`Gates<Gate>` will be sorted by
                 name.
        """
        sorted_gates = sorted(
            self.gates, key=lambda gate: gate.name if gate.name else "~~~"
        )
        return "\n".join([str(gate) for gate in sorted_gates])

    def __iter__(self):
        """Iterate over each gate in the :class:`GateGraph`.

        Similar to :attr:`~GateGraph.gates`, except that ``__iter__`` returns an
        :class:`~collections.abc.Iterable` rather than a :class:`set`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> a = pyrtl.Input(name="a", bitwidth=2)
            >>> b = pyrtl.Input(name="b", bitwidth=2)
            >>> sum = a + b
            >>> sum.name = "sum"

            >>> gate_graph = pyrtl.GateGraph()

            >>> sorted(gate.name for gate in gate_graph)
            ['a', 'b', 'sum']
        """
        return iter(self.gates)
