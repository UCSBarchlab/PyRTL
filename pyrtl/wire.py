"""
wire has the basic extended types useful for creating logic.

Types defined in this file include:

- `WireVector` -- the base class for ordered collections of wires

- `Input` -- a wire vector that receives an input for a block

- `Output` -- a wire vector that defines an output for a block

- `Const` -- a wire vector fed by a constant

- `Register` -- a wire vector that is latched each cycle
"""

from __future__ import annotations

import enum
import numbers
import re
import traceback

from pyrtl import core  # needed for _setting_keep_wirevector_call_stack
from pyrtl.core import Block, LogicNet, _NameIndexer, working_block
from pyrtl.pyrtlexceptions import PyrtlError, PyrtlInternalError

# ----------------------------------------------------------------
#        ___  __  ___  __   __
#  \  / |__  /  `  |  /  \ |__)
#   \/  |___ \__,  |  \__/ |  \
#
_wvIndexer = _NameIndexer("tmp")
_constIndexer = _NameIndexer("const_")


def _reset_wire_indexers():
    global _wvIndexer, _constIndexer
    _wvIndexer = _NameIndexer("tmp")
    _constIndexer = _NameIndexer("const_")


def next_tempvar_name(name=""):
    if name == "":  # sadly regex checks are sometimes too slow
        wire_name = _wvIndexer.make_valid_string()
        callpoint = core._get_useful_callpoint_name()
        if callpoint:  # returns none if debug mode is false
            filename, lineno = callpoint
            safename = re.sub(
                r"[\W]+", "", filename
            )  # strip out non alphanumeric characters
            wire_name += f"_{safename}_line{lineno}"
        return wire_name
    if name.lower() in ["clk", "clock"]:
        msg = "Clock signals should never be explicit"
        raise PyrtlError(msg)
    return name


class WireVector:
    """The main class for describing the connections between operators.

    :class:`WireVectors<WireVector>` act much like a list of wires, except that there is
    no "contained" type, each slice of a :class:`WireVector` is itself a
    :class:`WireVector` (even if it just contains a single "bit" of information). The
    least significant bit of the wire is at index ``0`` and normal list slicing syntax
    applies (i.e. ``myvector[0:5]`` makes a new vector from the bottom ``5`` bits of
    ``myvector``, ``myvector[-1]`` takes the most significant bit, and ``myvector[-4:]``
    takes the ``4`` most significant bits).

    ==============  ===========  ================================================================  ===================
    Operation       Syntax       Function                                                          Documentation
    ==============  ===========  ================================================================  ===================
    Addition        ``a + b``    Creates an *unsigned* adder, returns :class:`WireVector`          :meth:`__add__`
    Subtraction     ``a - b``    Creates an *unsigned* subtracter, returns :class:`WireVector`     :meth:`__sub__`
    Multiplication  ``a * b``    Creates an *unsigned* multiplier, returns :class:`WireVector`     :meth:`__mul__`
    Xor             ``a ^ b``    Bitwise XOR, returns :class:`WireVector`                          :meth:`__xor__`
    Or              ``a | b``    Bitwise OR, returns :class:`WireVector`                           :meth:`__or__`
    And             ``a & b``    Bitwise AND, returns :class:`WireVector`                          :meth:`__and__`
    Invert          ``~a``       Bitwise invert, returns :class:`WireVector`                       :meth:`__invert__`
    Less Than       ``a < b``    Unsigned less than, return 1-bit :class:`WireVector`              :meth:`__lt__`
    Less or Eq.     ``a <= b``   Unsigned less than or equal to, return 1-bit :class:`WireVector`  :meth:`__le__`
    Greater Than    ``a > b``    Unsigned greater than, return 1-bit :class:`WireVector`           :meth:`__gt__`
    Greater or Eq.  ``a >= b``   Unsigned greater or equal to, return 1-bit :class:`WireVector`    :meth:`__ge__`
    Equality        ``a == b``   Hardware to check equality, return 1-bit :class:`WireVector`      :meth:`__eq__`
    Not Equal       ``a != b``   Inverted equality check, return 1-bit :class:`WireVector`         :meth:`__ne__`
    Bitwidth        ``len(a)``   Return bitwidth of the :class:`WireVector`                        :meth:`__len__`
    Assignment      ``a <<= b``  Connect from b to a (see Note below)                              :meth:`__ilshift__`
    Bit Slice       ``a[3:6]``   Selects bits from :class:`WireVector`, in this case bits 3,4,5    :meth:`__getitem__`
    ==============  ===========  ================================================================  ===================

    .. note::
        ``<<=`` (:meth:`__ilshift__`) is how you "drive" an already created wire with an
        existing wire. If you were to do ``a = b`` it would lose the old value of ``a``
        and simply overwrite it with a new value, in this case with a reference to
        :class:`WireVector` ``b``. In contrast ``a <<= b`` does not overwrite ``a``, but
        simply wires the two together.

    .. _wirevector_coercion:

    :class:`WireVector` Coercion
    ----------------------------

    Most PyRTL functions that accept :class:`WireVectors<WireVector>` as arguments will
    also accept any type that :func:`as_wires` can coerce to :class:`WireVector`.
    Examples include :class:`int`, :class:`bool`, and :class:`str`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    :class:`int` will be coerced to an *unsigned* :class:`Const` :class:`WireVector`
    with the minimum bitwidth required for the integer. In the following example, a
    2-bit :class:`Const` is implicitly created for ``2``::

        >>> input = pyrtl.Input(name="input", bitwidth=8)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= input + 2

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input": 3})
        >>> sim.inspect("output")
        5

    .. doctest only::

        >>> pyrtl.reset_working_block()

    :class:`bool` will be coerced to a :class:`Const` with :attr:`bitwidth` ``1``. In
    the following example, a 1-bit :class:`Const` is implicitly created for ``True``::

        >>> input = pyrtl.Input(name="input", bitwidth=1)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= input ^ True

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input": False})
        >>> sim.inspect("output")
        1

    .. doctest only::

        >>> pyrtl.reset_working_block()

    :class:`str` will be interpreted as a `Verilog-style string constant
    <https://en.wikipedia.org/wiki/Verilog#Definition_of_constants>`_. In the following
    example, a 4-bit :class:`Const` is implicitly created for ``"4'hf"``::

        >>> input = pyrtl.Input(name="input", bitwidth=8)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= input & "4'hf"

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input": 0xab})
        >>> hex(sim.inspect("output"))
        '0xb'

    .. _wirevector_equality:

    :class:`WireVector` Equality
    ----------------------------

    :meth:`WireVector.__eq__` generates logic that dynamically reports if two wires
    carry the same values. :meth:`WireVector.__eq__` returns a 1-bit
    :class:`WireVector`, not a :class:`bool`, and attempting to convert a
    :class:`WireVector` to a :class:`bool` raises a :class:`PyrtlError`. This behavior
    is incompatible with `Python's data model
    <https://docs.python.org/3/reference/expressions.html#value-comparisons>`_, which
    can cause problems.

    For example, you *can not* statically check if two :class:`WireVectors<WireVector>`
    are equal with :meth:`==<__eq__>`. Statically checking for :class:`WireVector`
    equality can be useful while constructing or analyzing circuits::

        >>> w1 = pyrtl.WireVector(name="w1", bitwidth=1)
        >>> w2 = pyrtl.WireVector(name="w2", bitwidth=2)
        >>> if w1 == w2:
        ...     print('same')
        ...
        Traceback (most recent call last):
        ...
        pyrtl.pyrtlexceptions.PyrtlError: cannot convert WireVector to compile-time boolean...

    The error about converting :class:`WireVector` to :class:`bool` results from Python
    attempting to convert the 1-bit :class:`WireVector` returned by :meth:`__eq__` to
    ``True`` or ``False`` while evaluating the ``if`` statement's condition.

    Instead, you *can* statically check if two :class:`WireVectors<WireVector>` refer to
    the same object with ``is``::

        >>> w1 is not w2
        True
        >>> temp = w1
        >>> temp is w1
        True
        >>> temp is w2
        False

    Be careful when using Python features that depend on :meth:`==<__eq__>` with
    :class:`WireVectors<WireVector>`. This often comes up when checking if a
    :class:`WireVector` is in a :class:`list` with ``in``, which does not work because
    ``in`` falls back on checking each item in the :class:`list` for equality with
    :meth:`==<__eq__>`::

        >>> l = [w1]
        >>> w2 in l
        Traceback (most recent call last):
        ...
        pyrtl.pyrtlexceptions.PyrtlError: cannot convert WireVector to compile-time
        boolean...

    Most other :class:`list` operations work, so you can store
    :class:`WireVectors<WireVector>` in a :class:`list` if you avoid using the ``in``
    operator::

        >>> len(l)
        1
        >>> l[0] is w1
        True
        >>> [(w.name, w.bitwidth) for w in l]
        [('w1', 1)]

    :class:`WireVectors<WireVector>` define a standard :meth:`__hash__` method, so if
    you need to check if a :class:`WireVector` is in a container, use a :class:`set` or
    :class:`dict`. This works because these containers use :meth:`__hash__` to skip
    unnecessary equality checks::

        >>> s = {w1}
        >>> w1 in s
        True
        >>> w2 in s
        False

        >>> d = {w1: 'hello'}
        >>> w1 in d
        True
        >>> w2 in d
        False
        >>> d[w1]
        'hello'
    """  # noqa: E501

    bitwidth: int
    """The wire's bitwidth.

    :class:`WireVectors<WireVector>` can be constructed without specifying a
    :attr:`bitwidth`. These :class:`WireVectors<WireVector>` will have a
    :attr:`bitwidth` of ``None`` until they infer a :attr:`bitwidth` from an ``<<=``
    (:meth:`__ilshift__`) assignment.

    :attr:`bitwidth` is equivalent to :meth:`__len__`, except that :meth:`__len__`
    raises an exception when :attr:`bitwidth` is ``None``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> w = pyrtl.WireVector()
        >>> w.bitwidth
        None
        >>> w <<= pyrtl.Const(val=42, bitwidth=6)
        >>> w.bitwidth
        6
    """

    block: Block
    """The ``Block`` that this :class:`WireVector` belongs to."""

    # "code" is a static variable used when output as string.
    # Each class inheriting from WireVector should overload accordingly
    _code = "W"

    def __init__(
        self, bitwidth: int | None = None, name: str = "", block: Block = None
    ):
        """Construct a generic :class:`WireVector`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Examples::

            >>> # Visible in Simulation traces as "data".
            >>> data = pyrtl.WireVector(bitwidth=8, name="data")
            >>> data.name
            'data'

            >>> # `ctrl` is assigned a temporary name, and will not be visible in
            >>> # Simulation traces by default.
            >>> ctrl = pyrtl.WireVector(bitwidth=1)
            >>> ctrl.name.startswith("tmp")
            True

            >>> # `temp` is a temporary with bitwidth specified later.
            >>> temp = pyrtl.WireVector()
            >>> temp.bitwidth is None
            True
            >>> # `temp` infers a bitwidth of 8 from `data`.
            >>> temp <<= data
            >>> temp.bitwidth
            8

        :param bitwidth: If no ``bitwidth`` is provided, it will be set to the minimum
            number of bits needed to represent this wire.
        :param block: The :class:`Block` under which the wire should be placed.
            Defaults to the :ref:`working_block`.
        :param name: The name of the wire. Must be unique. If empty, a name will be
            autogenerated. If non-empty, the wire's value can be inspected with
            :meth:`Simulation.inspect`, and this wire will appear in traces generated
            by :meth:`SimulationTrace.render_trace`.
        """
        self._name = None

        # used only to verify the one to one relationship of wires and blocks
        self._block = working_block(block)
        self.name = next_tempvar_name(name)
        self._validate_bitwidth(bitwidth)

        if core._setting_keep_wirevector_call_stack:
            self.init_call_stack = traceback.format_stack()

    @property
    def name(self) -> str:
        """A property holding the name of the :class:`WireVector`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        The name can be read or written. Examples::

            >>> a = WireVector(name="foo", bitwidth=1)
            >>> a.name
            'foo'
            >>> a.name = "mywire"
            >>> a.name
            'mywire'
        """
        return self._name

    @name.setter
    def name(self, value: str):
        if not isinstance(value, str):
            msg = "WireVector names must be strings"
            raise PyrtlError(msg)
        self._block.wirevector_by_name.pop(self._name, None)
        self._name = value
        self._block.add_wirevector(self)

    def __hash__(self):
        return id(self)

    def __str__(self):
        """A string representation of the wire in 'name/bitwidth code' form."""
        return f"{self.name}/{self.bitwidth}{self._code}"

    def __repr__(self):
        return str(self)

    def _validate_bitwidth(self, bitwidth):
        if bitwidth is not None:
            if not isinstance(bitwidth, numbers.Integral):
                msg = (
                    "bitwidth must be from type int or unspecified, instead "
                    f'"{bitwidth}" was passed of type {type(bitwidth)}'
                )
                raise PyrtlError(msg)
            if bitwidth == 0:
                msg = "bitwidth must be greater than or equal to 1"
                raise PyrtlError(msg)
            if bitwidth < 0:
                msg = "you are trying a negative bitwidth? awesome but wrong"
                raise PyrtlError(msg)
        self.bitwidth = bitwidth

    def _build(self, other: WireVectorLike):
        # Actually create and add WireVector to logic block This might be called
        # immediately from ilshift, or delayed from conditional assignment
        net = LogicNet(op="w", op_param=None, args=(other,), dests=(self,))
        working_block().add_net(net)

    def _prepare_for_assignment(self, rhs):
        # Convert right-hand-side to wires and propagate bitwidth if necessary
        from pyrtl.corecircuits import as_wires

        rhs = as_wires(rhs, bitwidth=self.bitwidth)
        if self.bitwidth is None:
            self.bitwidth = rhs.bitwidth
        return rhs

    def __ilshift__(self, other: WireVectorLike):
        """Wire assignment operator ``<<=``, connects ``other`` to ``self``.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> input = pyrtl.Input(bitwidth=8, name="input")
            >>> output = pyrtl.WireVector(name="output")

            >>> output <<= input

            >>> sim = pyrtl.Simulation()
            >>> sim.step(provided_inputs={"input": 42})
            >>> sim.inspect("output")
            42
        """
        other = self._prepare_for_assignment(other)
        self._build(other)
        return self

    def __ior__(self, other: WireVectorLike):
        """Conditional assignment operator ``|=``, only usable under
        :data:`.conditional_assignment`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> select = pyrtl.Input(bitwidth=1, name="select")
            >>> output = pyrtl.WireVector(name="output", bitwidth=2)

            >>> with pyrtl.conditional_assignment:
            ...     with select:
            ...         output |= 2
            ...     with pyrtl.otherwise:
            ...         output |= 3

            >>> sim = pyrtl.Simulation()
            >>> sim.step(provided_inputs={"select": 0})
            >>> sim.inspect("output")
            3

            >>> sim.step(provided_inputs={"select": 1})
            >>> sim.inspect("output")
            2
        """
        from pyrtl.conditional import _build, currently_under_condition

        if not self.bitwidth:
            msg = (
                "Conditional assignment only defined on WireVectors with pre-defined "
                "bitwidths"
            )
            raise PyrtlError(msg)
        other = self._prepare_for_assignment(other)
        if currently_under_condition():
            _build(self, other)
        else:
            self._build(other)
        return self

    def _two_var_op(self, other, op):
        from pyrtl.corecircuits import as_wires, match_bitwidth

        # convert constants if necessary
        a, b = self, as_wires(other)
        a, b = match_bitwidth(a, b)
        resultlen = len(a)  # both are the same length now

        # some operations actually create more or less bits
        if op in "+-":
            resultlen += 1  # extra bit required for carry
        elif op == "*":
            resultlen = resultlen * 2  # more bits needed for mult
        elif op in "<>=":
            resultlen = 1

        s = WireVector(bitwidth=resultlen)
        net = LogicNet(op=op, op_param=None, args=(a, b), dests=(s,))
        working_block().add_net(net)
        return s

    def __bool__(self):
        """Use of a WireVector in a statement like "a or b" is forbidden."""
        # python provides no way to overload these logical operations, and thus they
        # are very much not likely to be doing the thing that the programmer would be
        # expecting.
        msg = (
            "cannot convert WireVector to compile-time boolean.  This error often "
            'happens when you attempt to use WireVectors with "==" or something that '
            'calls "__eq__", such as when you test if a WireVector is "in" something'
        )
        raise PyrtlError(msg)

    def __and__(self, other: WireVectorLike) -> WireVector:
        """Returns the result of bitwise ANDing ``self`` and ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=0b11, bitwidth=2)
            >>> five = pyrtl.Const(val=0b101, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three & five
            >>> output.bitwidth
            4

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            1

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A :class:`WireVector` containing the result of bitwise ANDing ``self``
                 and ``other``. The returned :class:`WireVector` has the same
                 :attr:`bitwidth` as the longer of the two input
                 :class:`WireVectors<WireVector>`.
        """
        return self._two_var_op(other, "&")

    def __rand__(self, other: WireVectorLike):
        return self._two_var_op(other, "&")

    def __iand__(self, other: WireVectorLike):
        msg = "error, operation not allowed on WireVectors"
        raise PyrtlError(msg)

    def __or__(self, other: WireVectorLike) -> WireVector:
        """Returns the result of bitwise ORing ``self`` and ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=0b11, bitwidth=2)
            >>> five = pyrtl.Const(val=0b101, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three | five
            >>> output.bitwidth
            4

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> bin(sim.inspect("output"))
            '0b111'

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A :class:`WireVector` containing the result of bitwise ORing ``self``
                 and ``other``. The returned :class:`WireVector` has the same
                 :attr:`bitwidth` as the longer of the two input
                 :class:`WireVectors<WireVector>`.
        """
        return self._two_var_op(other, "|")

    def __ror__(self, other: WireVectorLike):
        return self._two_var_op(other, "|")

    # __ior__ used for conditional assignment above

    def __xor__(self, other: WireVectorLike) -> WireVector:
        """Returns the result of bitwise XORing ``self`` and ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=0b11, bitwidth=2)
            >>> five = pyrtl.Const(val=0b101, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three ^ five
            >>> output.bitwidth
            4

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> bin(sim.inspect("output"))
            '0b110'

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A :class:`WireVector` containing the result of bitwise XORing ``self``
                 and ``other``. The returned :class:`WireVector` has the same
                 :attr:`bitwidth` as the longer of the two input
                 :class:`WireVectors<WireVector>`.
        """
        return self._two_var_op(other, "^")

    def __rxor__(self, other: WireVectorLike):
        return self._two_var_op(other, "^")

    def __ixor__(self, other: WireVectorLike):
        msg = "error, operation not allowed on WireVectors"
        raise PyrtlError(msg)

    def __add__(self, other: WireVectorLike) -> WireVector:
        """Returns the result of adding ``self`` and ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. WARNING::

            This addition operation is *unsigned*. Use :func:`signed_add` for signed
            addition.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=3, bitwidth=2)
            >>> five = pyrtl.Const(val=5, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three + five
            >>> output.bitwidth
            5

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            8

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A :class:`WireVector` containing the result of adding ``self`` and
                 ``other``. The returned :class:`WireVector` has a :attr:`bitwidth`
                 equal to the longer of the two input :class:`WireVectors<WireVector>`,
                 plus one.
        """
        return self._two_var_op(other, "+")

    def __radd__(self, other: WireVectorLike):
        return self._two_var_op(other, "+")

    def __iadd__(self, other: WireVectorLike):
        msg = "error, operation not allowed on WireVectors"
        raise PyrtlError(msg)

    def __sub__(self, other: WireVectorLike) -> WireVector:
        """Returns the result of subtracting ``self`` and ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. WARNING::

            This subtraction operation is *unsigned*. Use :func:`signed_sub` for signed
            subtraction.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=3, bitwidth=2)
            >>> five = pyrtl.Const(val=5, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= five - three
            >>> output.bitwidth
            5

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            2

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A :class:`WireVector` containing the result of subtracting ``self`` and
                 ``other``. The returned :class:`WireVector` has a :attr:`bitwidth`
                 equal to the longer of the two input :class:`WireVectors<WireVector>`,
                 plus one.
        """
        return self._two_var_op(other, "-")

    def __rsub__(self, other: WireVectorLike):
        from pyrtl.corecircuits import as_wires

        other = as_wires(other)  # '-' op is not symmetric
        return other._two_var_op(self, "-")

    def __isub__(self, other: WireVectorLike):
        msg = "error, operation not allowed on WireVectors"
        raise PyrtlError(msg)

    def __mul__(self, other: WireVectorLike) -> WireVector:
        """Returns the result of multiplying ``self`` and ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. WARNING::

            This multiplication operation is *unsigned*. Use :func:`signed_mult` for
            signed multiplication.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=3, bitwidth=2)
            >>> five = pyrtl.Const(val=5, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three * five
            >>> output.bitwidth
            8

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            15

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A :class:`WireVector` containing the result of multiplying ``self`` and
                 ``other``. The returned :class:`WireVector` has a :attr:`bitwidth`
                 equal to twice the length of the longer input.
        """
        return self._two_var_op(other, "*")

    def __rmul__(self, other: WireVectorLike):
        return self._two_var_op(other, "*")

    def __imul__(self, other: WireVectorLike):
        msg = "error, operation not allowed on WireVectors"
        raise PyrtlError(msg)

    def __lt__(self, other: WireVectorLike) -> WireVector:
        """Checks if ``self`` is less than ``other``. Returns a one-bit
        :class:`WireVector`.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. WARNING::

            This comparison is *unsigned*. Use :func:`signed_lt` for signed comparison.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=3, bitwidth=2)
            >>> five = pyrtl.Const(val=5, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three < five
            >>> output.bitwidth
            1

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            1

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A one-bit :class:`WireVector` indicating if ``self`` is less than
                 ``other``.
        """
        return self._two_var_op(other, "<")

    def __le__(self, other: WireVectorLike) -> WireVector:
        """Checks if ``self`` is less than or equal to ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. WARNING::

            This comparison is *unsigned*. Use :func:`signed_le` for signed comparison.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=3, bitwidth=2)
            >>> five = pyrtl.Const(val=5, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three <= five
            >>> output.bitwidth
            1

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            1

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A one-bit :class:`WireVector` indicating if ``self`` is less than or
                 equal to ``other``.
        """
        return ~self._two_var_op(other, ">")

    def __eq__(self, other: WireVectorLike) -> WireVector:
        """Checks if ``self`` is equal to ``other``. Returns a one-bit
        :class:`WireVector`.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. WARNING::

            This definition of :meth:`__eq__` returns :class:`WireVector`, not
            :class:`bool`, which is not compatible with Python's data model, which can
            cause problems. See :ref:`wirevector_equality`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=3, bitwidth=2)
            >>> five = pyrtl.Const(val=5, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three == five
            >>> output.bitwidth
            1

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            0

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A one-bit :class:`WireVector` indicating if ``self`` is equal to
                 ``other``.
        """
        return self._two_var_op(other, "=")

    def __ne__(self, other: WireVectorLike) -> WireVector:
        """Checks if ``self`` is not equal to ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=3, bitwidth=2)
            >>> five = pyrtl.Const(val=5, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three != five
            >>> output.bitwidth
            1

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            1

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A one-bit :class:`WireVector` indicating if ``self`` is not equal to
                 ``other``.
        """
        return ~self._two_var_op(other, "=")

    def __gt__(self, other: WireVectorLike) -> WireVector:
        """Checks if ``self`` is greater than ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. WARNING::

            This comparison is *unsigned*. Use :func:`signed_gt` for signed comparison.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=3, bitwidth=2)
            >>> five = pyrtl.Const(val=5, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three > five
            >>> output.bitwidth
            1

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            0

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A one-bit :class:`WireVector` indicating if ``self`` is greater than
                 ``other``.
        """
        return self._two_var_op(other, ">")

    def __ge__(self, other: WireVectorLike) -> WireVector:
        """Checks if ``self`` is greater than or equal to ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. WARNING::

            This comparison is *unsigned*. Use :func:`signed_ge` for signed comparison.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=3, bitwidth=2)
            >>> five = pyrtl.Const(val=5, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three >= five
            >>> output.bitwidth
            1

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("output")
            0

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A one-bit :class:`WireVector` indicating if ``self`` is greater than or
                 equal to ``other``.
        """
        return ~self._two_var_op(other, "<")

    def __invert__(self) -> WireVector:
        """Returns a :class:`WireVector` containing the bitwise inversion of ``self``.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> five = pyrtl.Const(val=0b101, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= ~five
            >>> output.bitwidth
            4

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> bin(sim.inspect("output"))
            '0b1010'

        :return: A :class:`WireVector` containing the result of bitwise inverting
                 ``self``. The returned :class:`WireVector` has the same
                 :attr:`bitwidth` as ``self``.
        """
        outwire = WireVector(bitwidth=len(self))
        net = LogicNet(op="~", op_param=None, args=(self,), dests=(outwire,))
        working_block().add_net(net)
        return outwire

    def __getitem__(self, item: int | slice) -> WireVector:
        """Returns a :class:`WireVector` containing a subset of the wires in ``self``.

        There are two ways to retrieve :class:`WireVector` subsets:

        1. By :class:`int` index, for example ``wire[2]``. This returns a
           :class:`WireVector` with :attr:`bitwidth` ``1``.

        2. By :class:`slice`, for example ``wire[3:5]``. Slicing uses the usual
           ``[start:stop:step]`` notation.

           1. If ``start`` is omitted, it defaults to index ``0``, the least significant
              bit.
           2. If ``stop`` is omitted, it defaults to ``bitwidth - 1``, the most
              significant bit.
           3. If ``step`` is omitted, it defaults to ``1``.

        :attr:`bitwidth` is added to negative ``start`` and ``stop`` indices, so
        negative indices count backwards from just beyond the most significant bit.
        Index ``bitwidth - 1`` and index ``-1`` both refer to the most significant bit.

        If ``step`` is negative, the wires will be returned in reverse order.

        Suppose we have a :class:`WireVector` ``input``, with :attr:`bitwidth` 8::

            input = WireVector(name="input", bitwidth=8)

        We can access individual wires of ``input`` with integer indices::

            input[0]                   # Least significant bit.
            input[input.bitwidth - 1]  # Most significant bit
            input[-1]                  # Another name for the most significant bit.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> input = pyrtl.Input(name="input", bitwidth=8)
            >>> msb = pyrtl.Output(name="msb")

            >>> msb <<= input[-1]
            >>> msb.bitwidth
            1

            >>> sim = pyrtl.Simulation()
            >>> sim.step(provided_inputs={"input": 0b1000_0000})
            >>> sim.inspect("msb")
            1

        We can access contiguous subsets of ``input``'s wires with slices::

            input[2:6]  # Middle 4 bits.
            input[:4]   # Least significant 4 bits.
            input[-4:]  # Most significant 4 bits.

        .. doctest only::

            >>> pyrtl.reset_working_block()

        Example::

            >>> input = pyrtl.Input(name="input", bitwidth=8)
            >>> middle_bits = pyrtl.Output(name="middle_bits")

            >>> middle_bits <<= input[2:6]
            >>> middle_bits.bitwidth
            4

            >>> sim = pyrtl.Simulation()
            >>> sim.step(provided_inputs={"input": 0b0011_1100})
            >>> bin(sim.inspect("middle_bits"))
            '0b1111'

        We can skip some of ``input``'s wires with slices::

            input[::2]   # Even numbered wires: 0, 2, 4, 6.
            input[1::2]  # Odd numbered wires: 1, 3, 5, 7.

        .. doctest only::

            >>> pyrtl.reset_working_block()

        Example::

            >>> input = pyrtl.Input(name="input", bitwidth=8)
            >>> odd_bits = pyrtl.Output(name="odd_bits")

            >>> odd_bits <<= input[1::2]
            >>> odd_bits.bitwidth
            4

            >>> sim = pyrtl.Simulation()
            >>> sim.step(provided_inputs={"input": 0b1010_1010})
            >>> bin(sim.inspect("odd_bits"))
            '0b1111'

        We can reverse ``input``'s wires with slices::

            input[::-1]    # Reversed wires: 7, 6, 5, 4, 3, 2, 1, 0.
            input[-1::-2]  # Reversed odd wires: 7, 5, 3, 1.

        .. doctest only::

            >>> pyrtl.reset_working_block()

        Example::

            >>> input = pyrtl.Input(name="input", bitwidth=8)
            >>> reversed_bits = pyrtl.Output(name="reversed_bits")

            >>> reversed_bits <<= input[::-1]
            >>> reversed_bits.bitwidth
            8

            >>> sim = pyrtl.Simulation()
            >>> sim.step(provided_inputs={"input": 0b0000_1111})
            >>> bin(sim.inspect("reversed_bits"))
            '0b11110000'

            >>> sim.step(provided_inputs={"input": 0b1010_1010})
            >>> # `bin` omits the leading 0.
            >>> bin(sim.inspect("reversed_bits"))
            '0b1010101'

        :param item: If an :class:`int`, specifies the index of a single-bit wire to
            return. If a :class:`slice`, specifies a subset of wires to return, as
            ``start:stop:step``.

        :return: A :class:`WireVector` containing the wires selected by ``item`` from
                 ``self``.
        """
        if self.bitwidth is None:
            msg = "You cannot get a subset of a wire with no bitwidth"
            raise PyrtlError(msg)
        allindex = range(self.bitwidth)
        if isinstance(item, int):
            selectednums = (
                allindex[item],
            )  # this method handles negative numbers correctly
        else:  # slice
            selectednums = tuple(allindex[item])
        if not selectednums:
            msg = f"selection {item} must have at least one selected wire"
            raise PyrtlError(msg)
        outwire = WireVector(bitwidth=len(selectednums))
        net = LogicNet(op="s", op_param=selectednums, args=(self,), dests=(outwire,))
        working_block().add_net(net)
        return outwire

    def __lshift__(self, other: WireVectorLike):
        msg = (
            "Shifting using the << operator is not supported in PyRTL. If you are "
            "trying to select bits in a wire, use the indexing operator "
            "(wire[indexes]) instead.\n\nFor example: wire[2:9] selects the wires from "
            "index 2 to index 8 to make a new length 7 wire. \n\nIf you are really "
            'trying to *execution time* left shift you can use "shift_left_logical"'
        )
        raise PyrtlError(msg)

    def __rshift__(self, other: WireVectorLike):
        msg = (
            "Shifting using the >> operator is not supported in PyRTL. If you are "
            "trying to select bits in a wire, use the indexing operator "
            "(wire[indexes]) instead.\n\nFor example: wire[2:9] selects the wires from "
            "index 2 to index 8 to make a new length 7 wire. \n\nIf you are really "
            'trying to *execution time* right shift you can use "shift_right_logical" '
            'or "shift_right_arithmetic"'
        )
        raise PyrtlError(msg)

    def __mod__(self, other: WireVectorLike):
        msg = (
            "Masking with the % operator is not supported in PyRTL. Instead if you are "
            "trying to select bits in a wire, use the indexing operator "
            "(wire[indexes]) instead.\n\nFor example: wire[2:9] selects the wires from "
            "index 2 to index 8 to make a new length 7 wire."
        )
        raise PyrtlError(msg)

    def __len__(self) -> int:
        """Return the :class:`WireVector`'s :attr:`bitwidth`.

        :class:`WireVectors<WireVector>` can be constructed without specifying a
        :attr:`bitwidth`. These :class:`WireVectors<WireVector>` will have a
        :attr:`bitwidth` of ``None`` until they infer a :attr:`bitwidth` from an ``<<=``
        (:meth:`__ilshift__`) assignment.

        :meth:`__len__` is equivalent to :attr:`bitwidth`, except that :meth:`__len__`
        raises an exception when :attr:`bitwidth` is ``None``.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> w = pyrtl.WireVector()
            >>> len(w)
            Traceback (most recent call last):
            ...
            pyrtl.pyrtlexceptions.PyrtlError: length of WireVector not yet defined

            >>> w <<= pyrtl.Const(val=42, bitwidth=6)
            >>> len(w)
            6

        :return: Returns the length (:attr:`bitwidth`) of the :class:`WireVector`, in
                 bits.

        :raises PyrtlError: If the :attr:`bitwidth` is not yet defined.
        """
        if self.bitwidth is None:
            msg = "length of WireVector not yet defined"
            raise PyrtlError(msg)
        return self.bitwidth

    def __enter__(self):
        """Use wires as contexts for conditional assignments."""
        from pyrtl.conditional import _push_condition

        _push_condition(self)

    def __exit__(self, *execinfo):
        from pyrtl.conditional import _pop_condition

        _pop_condition()

    # more functions for wires
    def nand(self, other: WireVectorLike) -> WireVector:
        """Returns the result of bitwise NANDing ``self`` and ``other``.

        If the inputs do not have the same :attr:`bitwidth`, the shorter input will be
        :meth:`zero_extended` to the longer input's :attr:`bitwidth`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> three = pyrtl.Const(val=0b11, bitwidth=2)
            >>> five = pyrtl.Const(val=0b101, bitwidth=4)
            >>> output = pyrtl.Output(name="output")

            >>> output <<= three.nand(five)
            >>> output.bitwidth
            4

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> bin(sim.inspect("output"))
            '0b1110'

        :param other: A :class:`WireVector`, or any type that can be coerced to
            :class:`WireVector` by :func:`as_wires`.

        :return: A :class:`WireVector` containing the result of bitwise NANDing ``self``
                 and ``other``. The returned :class:`WireVector` has the same
                 :attr:`bitwidth` as the longer of the two input
                 :class:`WireVectors<WireVector>`.
        """
        return self._two_var_op(other, "n")

    @property
    def bitmask(self) -> int:
        """A property holding a bitmask of the same length as this :class:`WireVector`.

        :attr:`bitmask` is an :class:`int` with a number of bits set to 1 equal to the
        :attr:`bitwidth` of the :class:`WireVector`.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        It is often useful to "mask" an integer such that it fits in the number of bits
        of a :class:`WireVector`, so the :attr:`bitmask` property is provided as a
        convenience. Example::

            >>> w = pyrtl.WireVector(bitwidth=4)
            >>> bin(w.bitmask)
            '0b1111'
            >>> w.bitmask
            15
            >>> hex(0xabcd & w.bitmask)
            '0xd'
        """
        if "_bitmask" not in self.__dict__:
            self._bitmask = (1 << len(self)) - 1
        return self._bitmask

    def truncate(self, bitwidth: int) -> WireVector:
        """Return a copy of ``self`` with its most significant bits removed.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Truncation reduces :attr:`bitwidth` by removing the most significant bits from
        ``self``. Example::

            >>> input = pyrtl.Input(name="input", bitwidth=8)
            >>> output = pyrtl.Output(name="output", bitwidth=4)

            >>> output <<= input.truncate(bitwidth=output.bitwidth)

            >>> sim = pyrtl.Simulation()
            >>> sim.step(provided_inputs={"input": 0b0000_1111})
            >>> bin(sim.inspect("output"))
            '0b1111'

            >>> sim.step(provided_inputs={"input": 0b1100_1011})
            >>> bin(sim.inspect("output"))
            '0b1011'

        :param bitwidth: Number of bits to truncate to. This is the number of bits to
            keep.

        :return: A new :class:`WireVector` equal to the original :class:`WireVector` but
                 truncated to the specified ``bitwidth``.

        :raises PyrtlError: If the ``bitwidth`` specified is larger than
            :attr:`bitwidth`.
        """
        if not isinstance(bitwidth, int):
            msg = "Can only truncate to an integer number of bits"
            raise PyrtlError(msg)
        if bitwidth > self.bitwidth:
            msg = "Cannot truncate a WireVector to have more bits than it started with"
            raise PyrtlError(msg)
        return self[:bitwidth]

    def sign_extended(self, bitwidth) -> WireVector:
        """Return a sign-extended copy of ``self``.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Sign-extension increases :attr:`bitwidth` by adding copies of the most
        significant bit of ``self``. Example::

            >>> input = pyrtl.Input(name="input", bitwidth=1)
            >>> output = pyrtl.Output(name="output", bitwidth=4)

            >>> output <<= input.sign_extended(bitwidth=output.bitwidth)

            >>> sim = pyrtl.Simulation()
            >>> sim.step(provided_inputs={"input": 0})
            >>> bin(sim.inspect("output"))
            '0b0'

            >>> sim.step(provided_inputs={"input": 1})
            >>> bin(sim.inspect("output"))
            '0b1111'

        :return: A new :class:`WireVector` equal to the original :class:`WireVector` but
                 sign-extended to the specified ``bitwidth``.

        :raises PyrtlError: If the ``bitwidth`` specified is smaller than
            :attr:`bitwidth`.
        """
        return self._extend_with_bit(bitwidth, self[-1])

    def zero_extended(self, bitwidth) -> WireVector:
        """Return a zero-extended copy of ``self``.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Zero-extension increases :attr:`bitwidth` by adding zero-valued high bits to
        ``self``. Example::

            >>> input = pyrtl.Input(name="input", bitwidth=1)
            >>> output = pyrtl.Output(name="output", bitwidth=4)

            >>> output <<= input.zero_extended(bitwidth=output.bitwidth)

            >>> sim = pyrtl.Simulation()
            >>> sim.step(provided_inputs={"input": 0})
            >>> bin(sim.inspect("output"))
            '0b0'

            >>> sim.step(provided_inputs={"input": 1})
            >>> bin(sim.inspect("output"))
            '0b1'

        :return: A new :class:`WireVector` equal to the original :class:`WireVector` but
                 zero-extended to the specified ``bitwidth``.

        :raises PyrtlError: If the ``bitwidth`` specified is smaller than
            :attr:`bitwidth`.
        """
        return self._extend_with_bit(bitwidth, 0)

    def _extend_with_bit(self, bitwidth, extbit):
        numext = bitwidth - self.bitwidth
        if numext == 0:
            return self
        if numext < 0:
            msg = (
                "Neither zero_extended nor sign_extended can reduce the number of bits"
            )
            raise PyrtlError(msg)
        from pyrtl.corecircuits import concat

        if isinstance(extbit, int):
            extbit = Const(extbit, bitwidth=1)
        extvector = WireVector(bitwidth=numext)
        net = LogicNet(
            op="s", op_param=(0,) * numext, args=(extbit,), dests=(extvector,)
        )
        working_block().add_net(net)
        return concat(extvector, self)


WireVectorLike = WireVector | int | str | bool
"""Alias for types that can be coerced to :class:`WireVector` by :func:`as_wires`."""


# -----------------------------------------------------------------------
#  ___     ___  ___       __   ___  __           ___  __  ___  __   __   __
# |__  \_/  |  |__  |\ | |  \ |__  |  \    \  / |__  /  `  |  /  \ |__) /__`
# |___ / \  |  |___ | \| |__/ |___ |__/     \/  |___ \__,  |  \__/ |  \ .__/
#
class Input(WireVector):
    """A :class:`WireVector` placeholder for inputs to a :class:`Block`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    :class:`Input` :class:`WireVectors<WireVector>` are placeholders for values provided
    during :class:`.Simulation`. See :meth:`.Simulation.step`'s ``provided_inputs``
    argument. For example::

        >>> input = pyrtl.Input(name="input", bitwidth=8)
        >>> output = pyrtl.Output(name="output")
        >>> output <<= input + 2

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input": 1})
        >>> sim.inspect("output")
        3

    .. doctest only::

        >>> pyrtl.reset_working_block()

    Attempting to assign an :class:`Input` :class:`WireVector` with the ``<<=``
    (:meth:`~WireVector.__ilshift__`) or ``|=`` (:meth:`~WireVector.__ior__`) operators
    will raise :class:`PyrtlError`::

        >>> input = pyrtl.Input(name="input", bitwidth=1)
        >>> input <<= True
        Traceback (most recent call last):
        ...
        pyrtl.pyrtlexceptions.PyrtlError: Connection ... attempted on Input
    """

    _code = "I"

    def __init__(
        self, bitwidth: int | None = None, name: str = "", block: Block = None
    ):
        super().__init__(bitwidth=bitwidth, name=name, block=block)

    def __ilshift__(self, _):
        """This is an illegal op for Inputs. They cannot be assigned to in this way"""
        msg = (
            "Connection using <<= operator attempted on Input. Inputs, such as "
            f'"{self.name}", cannot have values generated internally. aka they can\'t '
            "have other wires driving it"
        )
        raise PyrtlError(msg)

    def __ior__(self, _):
        """This is an illegal op for Inputs. They cannot be assigned to in this way"""
        msg = (
            "Connection using |= operator attempted on Input. Inputs, such as "
            f'"{self.name}", cannot have values generated internally. aka they can\'t '
            "have other wires driving it"
        )
        raise PyrtlError(msg)


class Output(WireVector):
    """A :class:`WireVector` type denoting outputs of a :class:`Block`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Attempting to use an :class:`Output` :class:`WireVector` as the input to any
    operation, such as :meth:`~WireVector.__or__`, which implements bitwise or, will
    raise :class:`PyrtlInternalError`::

        >>> output = pyrtl.Output(name="output", bitwidth=1)
        >>> foo = output | 2
        Traceback (most recent call last):
        ...
        pyrtl.pyrtlexceptions.PyrtlInternalError: error, Outputs cannot be arguments for
        a net
    """

    _code = "O"

    def __init__(
        self, bitwidth: int | None = None, name: str = "", block: Block = None
    ):
        super().__init__(bitwidth, name, block)


class Const(WireVector):
    """A :class:`WireVector` representation of a constant value.

    Converts from :class:`bool`, :class:`int`, or Verilog-style :class:`str` to a
    constant of the specified ``bitwidth``.
    """

    _code = "C"

    val: int
    """The constant's value.

    This is the constant's raw bit value, which will not match the ``val`` passed to
    :class:`Const`'s constructor for negative values.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> pos = pyrtl.Const(val=3)
        >>> pos.val
        3

        >>> neg = pyrtl.Const(val=-3, signed=True)
        >>> neg.val
        5
        >>> bin(neg.val)
        '0b101'
    """

    def __init__(
        self,
        val: int | bool | str,
        bitwidth: int | None = None,
        name: str = "",
        signed: bool = False,
        block: Block = None,
    ):
        """Construct a constant :class:`WireVector`.

        .. WARNING::

            A constant generated with ``signed=True`` is still just a raw bitvector. All
            arithmetic on it is *unsigned* by default. The ``signed=True`` argument is
            only used for proper inference of :class:`WireVector` size and certain
            bitwidth sanity checks, assuming a two's complement representation of the
            constants. For signed arithmetic, use the ``signed_*`` functions in the
            :ref:`extended_logic_and_arithmetic` section.

        :param val: The constant value. For details of how constants are coerced from
            int, bool, and strings (for Verilog constants), see documentation for
            :func:`infer_val_and_bitwidth`.
        :param bitwidth: The desired bitwidth of the resulting :class:`Const`. If
            ``None``, the bitwidth will be inferred from ``val``.
        :param name: The name of the wire. Must be unique. If none is provided, one will
            be autogenerated.
        :param signed: Specifies if bits should be used for two's complement.
        :param block: The block under which the wire should be placed. Defaults to the
            :ref:`working_block`.

        :raise PyrtlInternalError: If the :attr:`bitwidth` is too short to represent the
            specified constant.
        """
        self._validate_bitwidth(bitwidth)
        from pyrtl.helperfuncs import infer_val_and_bitwidth

        num, bitwidth = infer_val_and_bitwidth(val, bitwidth, signed)

        if num < 0:
            msg = "Const somehow evaluating to negative integer after checks"
            raise PyrtlInternalError(msg)
        if (num >> bitwidth) != 0:
            msg = (
                f"constant {num} returned by infer_val_and_bitwidth somehow not "
                f"fitting in {bitwidth} bits"
            )
            raise PyrtlInternalError(msg)

        name = name or _constIndexer.make_valid_string() + "_" + str(val)

        super().__init__(bitwidth=bitwidth, name=name, block=block)
        # add the member "val" to track the value of the constant
        self.val = num

    def __ilshift__(self, other: WireVectorLike):
        """
        This is an illegal op for Consts. Their value is set in the __init__ function
        """
        msg = (
            f'ConstWires, such as "{self.name}", should never be assigned to with "<<="'
        )
        raise PyrtlError(msg)

    def __ior__(self, _):
        """This is an illegal op for Consts. They cannot be assigned to in this way"""
        msg = (
            "Connection using |= operator attempted on Const. ConstWires, such as "
            f'"{self.name}", cannot have values generated internally. aka they cannot '
            "have other wires driving it"
        )
        raise PyrtlError(msg)


class Register(WireVector):
    """A :class:`WireVector` with an embedded register state element.

    ``Registers`` only update their outputs on the rising edges of an implicit clock
    signal. The "value" in the current cycle can be accessed by referencing the
    ``Register`` itself. To set the value for the next cycle (after the next rising
    clock edge), set the :attr:`Register.next` property with the ``<<=``
    (:meth:`~WireVector.__ilshift__`) operator.

    ``Registers`` reset to zero by default, and reside in the same clock domain.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> counter = pyrtl.Register(name="counter", bitwidth=2)
        >>> counter.next <<= counter + 1

        >>> sim = pyrtl.Simulation()
        >>> sim.step_multiple(nsteps=6)
        >>> sim.tracer.trace["counter"]
        [0, 1, 2, 3, 0, 1]

    This builds a zero-initialized 2-bit counter. The second line sets the counter's
    value in the next cycle (``counter.next``) to the counter's value in the current
    cycle (``counter``), plus one.
    """

    _code = "R"

    reset_value: int
    """The :class:`Register`'s reset value.

    This is the reset value's raw bit value, which will not match the ``reset_value``
    passed to :class:`Register`'s constructor for negative values.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> pos = pyrtl.Register(bitwidth=2, reset_value=3)
        >>> pos.reset_value
        3

        >>> neg = pyrtl.Register(bitwidth=3, reset_value=-3)
        >>> neg.reset_value
        5
        >>> bin(neg.reset_value)
        '0b101'
    """

    # When a register's next value is assigned, the following occurs:
    #
    # 1. The register's `.next` property is retrieved. Register.next returns an instance
    #    of Register._Next.
    # 2. __ilshift__ is invoked on the returned instance of Register._Next.
    #
    # So `reg.next <<= foo` effectively does the following:
    #
    #     reg.next = Register._Next(reg)
    #     reg.next.__ilshift__(reg, foo)
    #
    # The following behavior is expected:
    #
    #     reg.next <<= 5  # good
    #     a <<= reg       # good
    #     reg <<= 5       # error
    #     a <<= reg.next  # error
    #     reg.next = 5    # error
    class _Next:
        """Type returned by the ``Register.next`` property.

        This class allows unconditional assignments (``<<=``, :meth:`__ilshift__`) and
        conditional assignments (``|=``, :meth:`__ior__`) on ``Register.next``.
        Registers themselves do not support assignments, so ``Register.__ilshift__`` and
        ``Register.__ior__`` throw errors.

        ``__ilshift__`` and ``__ior__`` must both return ``self`` because::

            x <<= y

        is equivalent to::

            x = x.__ilshift__(y)

        Note how ``__ilshift__``'s return value is assigned to ``x``, see
        https://docs.python.org/3/library/operator.html#in-place-operators

        ``__ilshift__`` and ``__ior__`` both return ``self`` and Register's @next.setter
        checks that Register.next is assigned to an instance of _Next.
        """

        def __init__(self, reg):
            self.reg = reg

        def __ilshift__(self, other: WireVectorLike):
            from pyrtl.corecircuits import as_wires

            other = as_wires(other, bitwidth=self.reg.bitwidth)
            if self.reg.bitwidth is None:
                self.reg.bitwidth = other.bitwidth

            if self.reg.reg_in is not None:
                msg = "error, .next value should be set once and only once"
                raise PyrtlError(msg)
            self.reg._build(other)

            return self

        def __ior__(self, other: WireVectorLike):
            from pyrtl.conditional import _build
            from pyrtl.corecircuits import as_wires

            other = as_wires(other, bitwidth=self.reg.bitwidth)
            if not self.reg.bitwidth:
                msg = (
                    "Conditional assignment only defined on Registers with pre-defined "
                    "bitwidths"
                )
                raise PyrtlError(msg)

            if self.reg.reg_in is not None:
                msg = "error, .next value should be set once and only once"
                raise PyrtlError(msg)
            _build(self.reg, other)

            return self

        def __bool__(self):
            """Use of a _next in a statement like "a or b" is forbidden."""
            msg = (
                "cannot convert Register.next to compile-time boolean.  This error "
                'often happens when you attempt to use a Register.next with "==" or '
                'something that calls "__eq__", such as when you test if a '
                'Register.next is "in" something'
            )
            raise PyrtlError(msg)

    def __init__(
        self,
        bitwidth: int | None = None,
        name: str = "",
        reset_value: int | None = None,
        block: Block | None = None,
        State: type[enum.IntEnum] | None = None,
    ):
        """Construct a ``Register``.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example with ``State``::

            >>> import enum
            >>> class MyState(enum.IntEnum):
            ...     ZERO = 0
            ...     ONE = 1
            ...     TWO = 2
            ...     THREE = 3

            >>> state = pyrtl.Register(
            ...     name="state", State=MyState, reset_value=MyState.ONE
            ... )
            >>> state.bitwidth
            2

            >>> state.next <<= state + 1

            >>> sim = pyrtl.Simulation()
            >>> sim.step_multiple(nsteps=4)
            >>> sim.tracer.render_trace()

        Which prints::

                 │0    │1    │2    │3
            state ONE  │TWO  │THREE│ZERO

        :param bitwidth: Number of bits to represent this ``Register``.
        :param name: The name of the ``Register``'s current value (``reg``, not
            ``reg.next``). Must be unique. If none is provided, one will be
            autogenerated.
        :param reset_value: Value to initialize this ``Register`` to during simulation
            and in any code (e.g. Verilog) that is exported. Defaults to 0. Can be
            overridden at simulation time.
        :param block: The :class:`Block` under which the wire should be placed. Defaults
            to the :ref:`working_block`.
        :param State: An :class:`~enum.IntEnum` defining all possible states for the
            ``Register``. This should be an :class:`~enum.IntEnum` class, like
            ``MyState`` in the example above. If ``bitwidth`` is ``None``, the largest
            value in the :class:`~enum.IntEnum` determines the ``Register``'s
            ``bitwidth``. When ``State`` is not ``None``,
            :meth:`~.SimulationTrace.render_trace` defaults to displaying enumeration
            names rather than hex values.

        :raises PyrtlError: If the ``reset_value`` or ``State`` cannot fit into the
            specified ``bitwidth`` for this register.
        """
        from pyrtl.helperfuncs import infer_val_and_bitwidth

        self.State = State
        if State is not None:
            largest_state = max(State)
            inferred_bitwidth = infer_val_and_bitwidth(largest_state).bitwidth
            if bitwidth is None:
                bitwidth = inferred_bitwidth

            if bitwidth < inferred_bitwidth:
                msg = (
                    f"The largest State {largest_state.name} ({largest_state}) cannot "
                    f"fit in the specified {bitwidth} bits for this register"
                )
                raise PyrtlError(msg)

        super().__init__(bitwidth=bitwidth, name=name, block=block)
        self.reg_in = None  # wire vector setting self.next
        if reset_value is not None:
            reset_value, rst_bitwidth = infer_val_and_bitwidth(
                reset_value,
                bitwidth=bitwidth,
            )
            if rst_bitwidth > bitwidth:
                msg = (
                    f'reset_value "{reset_value}" cannot fit in the specified '
                    f"{bitwidth} bits for this register"
                )
                raise PyrtlError(msg)
        self.reset_value = reset_value

    @property
    def next(self):
        """Sets the Register's value for the next cycle (it is before the D-Latch)."""
        return Register._Next(self)

    def __ilshift__(self, other: WireVectorLike):
        msg = "error, you cannot set registers directly, net .next instead"
        raise PyrtlError(msg)

    def __ior__(self, other: WireVectorLike):
        msg = "error, you cannot set registers directly, net .next instead"
        raise PyrtlError(msg)

    @next.setter
    def next(self, other: WireVectorLike):
        if not isinstance(other, Register._Next):
            msg = 'error, .next should be set with "<<=" or "|=" operators'
            raise PyrtlError(msg)

    def _build(self, next):
        # Actually build the register. This happens immediately when setting the `next`
        # property. Under conditional assignment, register build is delayed until the
        # conditional assignment is _finalized.
        self.reg_in = next
        net = LogicNet("r", None, args=(self.reg_in,), dests=(self,))
        working_block().add_net(net)


class WrappedWireVector:
    """Wraps a ``WireVector``. Forwards all method calls and attribute accesses.

    ``WrappedWireVector`` is useful for dynamically choosing a ``WireVector`` base class
    at runtime. If the base class is statically known, do not use ``WrappedWireVector``,
    and just inherit from the base class normally.

    :func:`.wire_struct` and :func:`.wire_matrix` use ``WrappedWireVector`` to implement
    the ``concatenated_type`` option, so an instance can dynamically choose its desired
    base class during construction.
    """

    wire = None

    def __init__(self, wire: WireVector):
        self.__dict__["wire"] = wire

    def __getattr__(self, name: str):
        """Forward all attribute accesses to the wrapped WireVector.

        This does not work for special methods like ``__hash__``. Special methods are
        handled separately below.
        """
        return getattr(self.wire, name)

    def __setattr__(self, name, value):
        """Forward all attribute assignments to the wrapped WireVector.

        This is needed to make ``reg.next <<= foo`` work, because that expands to::

            reg.next = reg.next.__ilshift__(foo)

        See https://docs.python.org/3/library/operator.html#in-place-operators

        This attribute assignment must be forwarded to the underlying Register.
        """
        self.wire.__setattr__(name, value)

    def __hash__(self):
        return hash(self.wire)

    def __str__(self):
        return str(self.wire)

    def __repr__(self):
        return repr(self.wire)

    def __ilshift__(self, other):
        self.wire <<= other
        return self

    def __ior__(self, other):
        self.wire |= other
        return self

    def __bool__(self):
        return bool(self.wire)

    def __and__(self, other):
        return self.wire & other

    def __rand__(self, other):
        return other & self.wire

    def __iand__(self, other):
        self.wire &= other
        return self

    def __or__(self, other):
        return self.wire | other

    def __ror__(self, other):
        return other | self.wire

    def __xor__(self, other):
        return self.wire ^ other

    def __rxor__(self, other):
        return other ^ self.wire

    def __ixor__(self, other):
        self.wire ^= other
        return self

    def __add__(self, other):
        return self.wire + other

    def __radd__(self, other):
        return other + self.wire

    def __iadd__(self, other):
        self.wire += other
        return self

    def __sub__(self, other):
        return self.wire - other

    def __rsub__(self, other):
        return other - self.wire

    def __isub__(self, other):
        self.wire -= other
        return self

    def __mul__(self, other):
        return self.wire * other

    def __rmul__(self, other):
        return other * self.wire

    def __imul__(self, other):
        self.wire *= other
        return self

    def __lt__(self, other):
        return self.wire < other

    def __le__(self, other):
        return self.wire <= other

    def __eq__(self, other):
        return self.wire == other

    def __ne__(self, other):
        return self.wire != other

    def __gt__(self, other):
        return self.wire > other

    def __ge__(self, other):
        return self.wire >= other

    def __invert__(self):
        return ~self.wire

    def __getitem__(self, item):
        return self.wire[item]

    def __lshift__(self, other):
        return self.wire << other

    def __rshift__(self, other):
        return self.wire >> other

    def __mod__(self, other):
        return self.wire % other

    def __len__(self):
        return len(self.wire)

    def __enter__(self):
        self.wire.__enter__()

    def __exit__(self, *execinfo):
        self.wire.__exit__(*execinfo)
