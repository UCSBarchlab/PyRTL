"""Some useful hardware generators (e.g. muxes, signed multipliers, etc.)"""

from __future__ import annotations

import itertools

from pyrtl.conditional import otherwise
from pyrtl.core import Block, LogicNet, working_block
from pyrtl.pyrtlexceptions import PyrtlError, PyrtlInternalError
from pyrtl.rtllib import barrel, muxes
from pyrtl.wire import Const, WireVector, WireVectorLike, WrappedWireVector


def mux(
    index: WireVectorLike, *mux_ins: WireVectorLike, default: WireVectorLike = None
) -> WireVector:
    """Multiplexer returning a wire from ``mux_ins`` according to ``index``.

    ``index`` ``0`` corresponds to the first ``mux_in`` argument.

    .. note::

        If ``index`` is a 1-bit predicate (something that is ``True`` or ``False``
        rather than an integer), it is clearer to use :func:`select`, whose argument
        order is consistent with the ternary operators in C-style languages
        (``condition ? truecase : falsecase``).

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example of multiplexing between four values::

        >>> index = pyrtl.Input(name="index", bitwidth=2)
        >>> selected = pyrtl.WireVector(name="selected")

        >>> selected <<= pyrtl.mux(index, 4, 5, 6, 7)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"index": 0})
        >>> sim.inspect("selected")
        4

        >>> sim.step(provided_inputs={"index": 3})
        >>> sim.inspect("selected")
        7

    .. doctest only::

        >>> pyrtl.reset_working_block()

    Example with ``default``::

        >>> index = pyrtl.Input(name="index", bitwidth=2)
        >>> selected = pyrtl.WireVector(name="selected")
        >>> selected <<= pyrtl.mux(index, 4, 5, default=9)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"index": 1})
        >>> sim.inspect("selected")
        5

        >>> sim.step(provided_inputs={"index": 2})
        >>> sim.inspect("selected")
        9

    :param index: Multiplexer's selection input. Can be a :class:`WireVector`, or any
        type that can be coerced to :class:`WireVector` by :func:`as_wires`.
    :param mux_ins: :class:`WireVector` arguments to select from. Can be a
        :class:`WireVector`, or any type that can be coerced to :class:`WireVector` by
        :func:`as_wires`.
    :param default: If you are selecting between fewer items than ``index`` can address,
        ``default`` will be used for all remaining items. For example, if you have a
        3-bit index but are selecting between 6 ``mux_ins``, you need to specify a value
        for those other 2 possible values of ``index`` (``0b110`` and ``0b111``).

    :raises PyrtlError: If there are not enough ``mux_ins`` to select from. If
        ``default=None``, the number of ``mux_ins`` must be exactly ``2 **
        index.bitwidth``.

    :return: :class:`WireVector` with :attr:`~WireVector.bitwidth` matching the length
             of the longest input (not including ``index``).
    """
    # find the diff between the addressable range and number of inputs given
    index = as_wires(index)
    short_by = 2 ** len(index) - len(mux_ins)
    if short_by > 0 and default is not None:  # extend the list to appropriate size
        mux_ins = list(mux_ins)
        mux_ins.extend([default] * short_by)

    if 2 ** len(index) != len(mux_ins):
        msg = (
            f"Mux select line is {len(index)} bits, but selecting from {len(mux_ins)} "
            "inputs."
        )
        raise PyrtlError(msg)

    if len(index) == 1:
        return select(index, falsecase=mux_ins[0], truecase=mux_ins[1])
    half = len(mux_ins) // 2
    return select(
        index[-1],
        falsecase=mux(index[0:-1], *mux_ins[:half]),
        truecase=mux(index[0:-1], *mux_ins[half:]),
    )


def select(
    sel: WireVectorLike, truecase: WireVectorLike, falsecase: WireVectorLike
) -> WireVector:
    """Multiplexer returning ``truecase`` when ``sel == 1``, otherwise ``falsecase``.

    ``select`` is equivalent to :func:`mux` with a 1-bit ``index``, except that
    ``select``'s ``truecase`` is its first argument, rather than its second.
    ``select``'s argument order is consistent with the ternary operator in C-style
    languages, which improves readability, so prefer ``select`` over :func:`mux` when
    selecting between exactly two options.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example that computes ``min(a, 5)``::

        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> min = pyrtl.WireVector(name="min")

        >>> min <<= pyrtl.select(a < 5, 5, a)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"a": 4})
        >>> sim.inspect("min")
        5

        >>> sim.step(provided_inputs={"a": 6})
        >>> sim.inspect("min")
        6

    :param sel: Multiplexer's selection input. Can be a :class:`WireVector`, or any type
        that can be coerced to :class:`WireVector` by :func:`as_wires`.
    :param truecase: The WireVector selected if ``sel == 1``. Can be a
        :class:`WireVector`, or any type that can be coerced to :class:`WireVector` by
        :func:`as_wires`.
    :param falsecase: The WireVector selected if ``sel == 0``. Can be a
        :class:`WireVector`, or any type that can be coerced to :class:`WireVector` by
        :func:`as_wires`.

    :return: :class:`WireVector` with :attr:`~WireVector.bitwidth` matching the longer
             of ``truecase`` and ``falsecase``.
    """
    sel, f, t = (as_wires(w) for w in (sel, falsecase, truecase))
    f, t = match_bitwidth(f, t)
    outwire = WireVector(bitwidth=len(f))

    net = LogicNet(op="x", op_param=None, args=(sel, f, t), dests=(outwire,))
    working_block().add_net(net)  # this includes sanity check on the mux
    return outwire


def concat(*args: WireVectorLike) -> WireVector:
    """Concatenates multiple :class:`WireVectors<WireVector>` into a single
    :class:`WireVector`.

    Concatenates any number of arguments. The right-most argument is the least
    significant bits of the result.

    .. note::

        If you have a :class:`list` of arguments to ``concat`` together, you probably
        want index 0 to be the least significant bit. If so, and you unpack the
        :class:`list` into ``concat``'s ``args``, the result will be backwards. The
        function :func:`concat_list` is provided specifically for that case.

    .. note::

        Consider using :func:`wire_struct` or :func:`wire_matrix` instead, which helps
        with consistently disassembling, naming, and reassembling fields.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example that concatenates two bytes into a 16-bit ``output``::

        >>> msb = pyrtl.Input(name="msb", bitwidth=8)
        >>> lsb = pyrtl.Input(name="lsb", bitwidth=8)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.concat(msb, lsb)
        >>> output.bitwidth
        16

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"msb": 0xab, "lsb": 0xcd})
        >>> hex(sim.inspect("output"))
        '0xabcd'

    :param args: Inputs to concatenate, with the most significant bits first. Each input
        can be a :class:`WireVector`, or any type that can be coerced to
        :class:`WireVector` by :func:`as_wires`.

    :return: :class:`WireVector` with :attr:`~WireVector.bitwidth` equal to the sum of
             all ``args``' :attr:`bitwidths<~WireVector.bitwidth>`.
    """
    if len(args) <= 0:
        msg = "error, concat requires at least 1 argument"
        raise PyrtlError(msg)
    if len(args) == 1:
        return as_wires(args[0])

    arg_wirevectors = tuple(as_wires(arg) for arg in args)
    final_width = sum(len(arg) for arg in arg_wirevectors)
    outwire = WireVector(bitwidth=final_width)
    net = LogicNet(op="c", op_param=None, args=arg_wirevectors, dests=(outwire,))
    working_block().add_net(net)
    return outwire


def concat_list(wire_list: list[WireVectorLike]) -> WireVector:
    """Concatenates a list of :class:`WireVectors<WireVector>` into a single
    :class:`WireVector`.

    This take a :class:`list` of :class:`WireVectors<WireVector>` and concats them all
    into a single :class:`WireVector`, with the element at index 0 serving as the least
    significant bits. This is useful when you have a variable number of
    :class:`WireVectors<WireVector>` to concatenate, otherwise :func:`concat` is
    prefered.

    .. note::

        Consider using :func:`wire_struct` or :func:`wire_matrix` instead, which helps
        with consistently disassembling, naming, and reassembling fields.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example that concatenates two bytes into a 16-bit ``output``::

        >>> msb = pyrtl.Input(name="msb", bitwidth=8)
        >>> lsb = pyrtl.Input(name="lsb", bitwidth=8)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.concat_list([lsb, msb])
        >>> output.bitwidth
        16

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"msb": 0xab, "lsb": 0xcd})
        >>> hex(sim.inspect("output"))
        '0xabcd'

    :param wire_list: List of inputs to concatenate. Each input can be a
        :class:`WireVector`, or any type that can be coerced to :class:`WireVector` by
        :func:`as_wires`.

    :return: :class:`WireVector` with :attr:`~WireVector.bitwidth` equal to the sum of
             all ``wire_list`` :attr:`bitwidths<~WireVector.bitwidth>`.
    """
    return concat(*reversed(wire_list))


def _signed_input_to_wirevector(x):
    """Convert int input to a signed Const, otherwise call `as_wires`."""
    if isinstance(x, int):
        return Const(x, signed=True)
    return as_wires(x)


def signed_add(a: WireVectorLike, b: WireVectorLike) -> WireVector:
    """Return a :class:`WireVector` for the result of signed addition.

    The inputs are :meth:`~WireVector.sign_extended` to the result's bitwidth before
    adding.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> neg_three = pyrtl.Const(val=-3, signed=True, bitwidth=3)
        >>> neg_five = pyrtl.Const(val=-5, signed=True, bitwidth=5)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.signed_add(neg_three, neg_five)
        >>> output.bitwidth
        6

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> pyrtl.val_to_signed_integer(sim.inspect("output"), bitwidth=output.bitwidth)
        -8

    :param a: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.
    :param b: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.

    :return: A :class:`WireVector` representing the sum of ``a`` and ``b``, with
             :attr:`~WireVector.bitwidth` ``max(a.bitwidth, b.bitwidth) + 1``.
    """
    a = _signed_input_to_wirevector(a)
    b = _signed_input_to_wirevector(b)
    result_bitwidth = max(a.bitwidth, b.bitwidth) + 1
    a = a.sign_extended(result_bitwidth)
    b = b.sign_extended(result_bitwidth)
    return (a + b).truncate(result_bitwidth)


def signed_sub(a: WireVectorLike, b: WireVectorLike) -> WireVector:
    """Return a :class:`WireVector` for the result of signed subtraction.

    The inputs are :meth:`~WireVector.sign_extended` to the result's bitwidth before
    subtracting.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> neg_three = pyrtl.Const(val=-3, signed=True, bitwidth=3)
        >>> neg_five = pyrtl.Const(val=-5, signed=True, bitwidth=5)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.signed_sub(neg_three, neg_five)
        >>> output.bitwidth
        6

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> pyrtl.val_to_signed_integer(sim.inspect("output"), bitwidth=output.bitwidth)
        2

    :param a: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.
    :param b: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.

    :return: A :class:`WireVector` representing the difference between ``a`` and ``b``,
             with :attr:`~WireVector.bitwidth` ``max(a.bitwidth, b.bitwidth) + 1``.
    """
    a = _signed_input_to_wirevector(a)
    b = _signed_input_to_wirevector(b)
    result_bitwidth = max(a.bitwidth, b.bitwidth) + 1
    a = a.sign_extended(result_bitwidth)
    b = b.sign_extended(result_bitwidth)
    return (a - b).truncate(result_bitwidth)


def mult_signed(a, b):
    """mult_signed is now deprecated, use ``signed_mult`` instead"""
    return signed_mult(a, b)


def signed_mult(a: WireVectorLike, b: WireVectorLike) -> WireVector:
    """Return a :class:`WireVector` for the result of signed multiplication.

    The inputs are :meth:`~WireVector.sign_extended` to the result's bitwidth before
    multiplying.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> neg_three = pyrtl.Const(val=-3, signed=True, bitwidth=3)
        >>> neg_five = pyrtl.Const(val=-5, signed=True, bitwidth=5)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.signed_mult(neg_three, neg_five)
        >>> output.bitwidth
        8

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> pyrtl.val_to_signed_integer(sim.inspect("output"), bitwidth=output.bitwidth)
        15

    :param a: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.
    :param b: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.

    :return: A :class:`WireVector` representing the product of ``a`` and ``b``, with
             :attr:`~WireVector.bitwidth` ``a.bitwidth + b.bitwidth``.
    """
    a = _signed_input_to_wirevector(a)
    b = _signed_input_to_wirevector(b)
    result_bitwidth = a.bitwidth + b.bitwidth
    a = a.sign_extended(result_bitwidth)
    b = b.sign_extended(result_bitwidth)
    return (a * b).truncate(result_bitwidth)


def signed_lt(a: WireVectorLike, b: WireVectorLike) -> WireVector:
    """Return a 1-bit :class:`WireVector` for the result of a signed ``<`` comparison.

    The inputs are :meth:`~WireVector.sign_extended` to matching bitwidths before
    comparing.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> neg_three = pyrtl.Const(val=-3, signed=True, bitwidth=3)
        >>> neg_five = pyrtl.Const(val=-5, signed=True, bitwidth=5)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.signed_lt(neg_three, neg_five)
        >>> output.bitwidth
        1

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> sim.inspect("output")
        0

    :param a: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.
    :param b: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.

    :return: A 1-bit :class:`WireVector` indicating if ``a`` is less than ``b``.
    """
    a, b = match_bitwidth(as_wires(a), as_wires(b), signed=True)
    r = a - b
    return r[-1] ^ (~a[-1]) ^ (~b[-1])


def signed_le(a: WireVectorLike, b: WireVectorLike) -> WireVector:
    """Return a 1-bit :class:`WireVector` for the result of a signed ``<=`` comparison.

    The inputs are :meth:`~WireVector.sign_extended` to matching bitwidths before
    comparing.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> neg_three = pyrtl.Const(val=-3, signed=True, bitwidth=3)
        >>> neg_five = pyrtl.Const(val=-5, signed=True, bitwidth=5)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.signed_le(neg_three, neg_five)
        >>> output.bitwidth
        1

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> sim.inspect("output")
        0

    :param a: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.
    :param b: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.

    :return: A 1-bit :class:`WireVector` indicating if ``a`` is less than or equal to
             ``b``.
    """
    a, b = match_bitwidth(as_wires(a), as_wires(b), signed=True)
    r = a - b
    return (r[-1] ^ (~a[-1]) ^ (~b[-1])) | (a == b)


def signed_gt(a: WireVectorLike, b: WireVectorLike) -> WireVector:
    """Return a 1-bit :class:`WireVector` for the result of a signed ``>`` comparison.

    The inputs are :meth:`~WireVector.sign_extended` to matching bitwidths before
    comparing.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> neg_three = pyrtl.Const(val=-3, signed=True, bitwidth=3)
        >>> neg_five = pyrtl.Const(val=-5, signed=True, bitwidth=5)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.signed_gt(neg_three, neg_five)
        >>> output.bitwidth
        1

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> sim.inspect("output")
        1

    :param a: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.
    :param b: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.

    :return: A 1-bit :class:`WireVector` indicating if ``a`` is greater than ``b``.
    """
    a, b = match_bitwidth(as_wires(a), as_wires(b), signed=True)
    r = b - a
    return r[-1] ^ (~a[-1]) ^ (~b[-1])


def signed_ge(a: WireVectorLike, b: WireVectorLike) -> WireVector:
    """Return a 1-bit :class:`WireVector` for the result of a signed ``>=`` comparison.

    The inputs are :meth:`~WireVector.sign_extended` to matching bitwidths before
    comparing.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> neg_three = pyrtl.Const(val=-3, signed=True, bitwidth=3)
        >>> neg_five = pyrtl.Const(val=-5, signed=True, bitwidth=5)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.signed_ge(neg_three, neg_five)
        >>> output.bitwidth
        1

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> sim.inspect("output")
        1

    :param a: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.
    :param b: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`.

    :return: A 1-bit :class:`WireVector` indicating if ``a`` is greater than or equal to
             ``b``.
    """
    a, b = match_bitwidth(as_wires(a), as_wires(b), signed=True)
    r = b - a
    return (r[-1] ^ (~a[-1]) ^ (~b[-1])) | (a == b)


def shift_right_arithmetic(
    bits_to_shift: WireVector, shift_amount: WireVector | int
) -> WireVector:
    """Arithmetic right shift operation.

    Arithemetic shifting treats the ``bits_to_shift`` as a signed number, so copies of
    ``bits_to_shift``'s sign bit will be added on the left.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> neg_forty = pyrtl.Const(val=-40, signed=True, bitwidth=7)
        >>> shift_amount = pyrtl.Input(name="shift_amount", bitwidth=3)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.shift_right_arithmetic(neg_forty, shift_amount)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"shift_amount": 3})
        >>> pyrtl.val_to_signed_integer(sim.inspect("output"), bitwidth=output.bitwidth)
        -5
        >>> int(-40 / 2 ** 3)
        -5

    Right shifting by ``N`` bits is equivalent to dividing by ``2^N``.

    :param bits_to_shift: Value to shift right arithmetically.
    :param shift_amount: Number of bit positions to shift, as an unsigned integer.

    :return: A new :class:`WireVector` with the same bitwidth as ``bits_to_shift``.
    """
    if isinstance(shift_amount, int):
        if shift_amount >= bits_to_shift.bitwidth:
            return bits_to_shift[-1].sign_extended(len(bits_to_shift))

        return bits_to_shift[shift_amount:].sign_extended(len(bits_to_shift))

    bit_in = bits_to_shift[-1]  # shift in sign_bit
    dir = barrel.Direction.RIGHT
    return barrel.barrel_shifter(bits_to_shift, bit_in, dir, shift_amount)


def shift_left_logical(
    bits_to_shift: WireVector, shift_amount: WireVector | int
) -> WireVector:
    """Logical left shift operation.

    Logical shifting treats the ``bits_to_shift`` as an unsigned number. Zeroes will be
    added on the right and the result will be truncated to ``bits_to_shift.bitwidth``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> three = pyrtl.Const(val=3, bitwidth=6)
        >>> shift_amount = pyrtl.Input(name="shift_amount", bitwidth=3)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.shift_left_logical(three, shift_amount)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"shift_amount": 3})
        >>> sim.inspect("output")
        24
        >>> 3 * 2 ** 3
        24

    Left shifting by ``N`` bits is equivalent to multiplying by ``2^N``.

    :param bits_to_shift: Value to shift left logically.
    :param shift_amount: Number of bit positions to shift, as an unsigned integer.

    :return: A new :class:`WireVector` with the same bitwidth as ``bits_to_shift``.
    """
    if isinstance(shift_amount, int):
        if shift_amount >= bits_to_shift.bitwidth:
            return Const(val=0, bitwidth=bits_to_shift.bitwidth)

        return concat(bits_to_shift[:-shift_amount], Const(0, shift_amount))

    bit_in = 0  # shift in a 0
    dir = barrel.Direction.LEFT
    return barrel.barrel_shifter(bits_to_shift, bit_in, dir, shift_amount)


shift_left_arithmetic = shift_left_logical
"""Alias for :func:`shift_left_logical`"""


def shift_right_logical(
    bits_to_shift: WireVector, shift_amount: WireVector | int
) -> WireVector:
    """Logical right shift operation.

    Logical shifting treats the ``bits_to_shift`` as an unsigned number, so zeroes will
    be added on the left.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> forty = pyrtl.Const(val=40, bitwidth=6)
        >>> shift_amount = pyrtl.Input(name="shift_amount", bitwidth=3)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.shift_right_logical(forty, shift_amount)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"shift_amount": 3})
        >>> sim.inspect("output")
        5
        >>> int(40 / 2 ** 3)
        5

    Right shifting by ``N`` bits is equivalent to dividing by ``2^N``.

    :param bits_to_shift: Value to shift right logically.
    :param shift_amount: Number of bit positions to shift, as an unsigned integer.

    :return: A new :class:`WireVector` with the same bitwidth as ``bits_to_shift``.
    """
    if isinstance(shift_amount, int):
        if shift_amount >= bits_to_shift.bitwidth:
            return Const(val=0, bitwidth=bits_to_shift.bitwidth)
        return bits_to_shift[shift_amount:].zero_extended(len(bits_to_shift))

    bit_in = 0  # shift in a 0
    dir = barrel.Direction.RIGHT
    return barrel.barrel_shifter(bits_to_shift, bit_in, dir, shift_amount)


def match_bitwidth(*args: WireVector, signed: bool = False) -> tuple[WireVector]:
    """Matches multiple :class:`WireVector` :attr:`bitwidths<~WireVector.bitwidth>` via
    zero- or sign-extension.

    :class:`WireVectors<WireVector>` with shorter
    :attr:`bitwidths<~WireVector.bitwidth>` will be to match the longest
    :attr:`~WireVector.bitwidth` in ``args``. :class:`WireVectors<WireVector>` will be
    :meth:`~WireVector.sign_extended` or :meth:`~WireVector.zero_extended`, depending on
    ``signed``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example with sign-extension::

        >>> a = pyrtl.Const(-1, name="a_short", signed=True, bitwidth=2)
        >>> b = pyrtl.Const(-3, name="b", signed=True, bitwidth=4)

        >>> a, b = match_bitwidth(a, b, signed=True)
        >>> a.name = "a_long"
        >>> a.bitwidth, b.bitwidth
        (4, 4)

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> bin(sim.inspect("b"))
        '0b1101'
        >>> bin(sim.inspect("a_short"))
        '0b11'
        >>> bin(sim.inspect("a_long"))
        '0b1111'

    :param args: :class:`WireVectors<WireVector>` of which to match
        :attr:`~WireVector.bitwidth`
    :param signed: If ``True``, extend shorter :class:`WireVectors<WireVector>` with
        :meth:`~WireVector.sign_extended`. Otherwise, extend with
        :meth:`~WireVector.zero_extended`.

    :return: :class:`tuple` of :class:`WireVectors<WireVector>`, in the same order they
             appeared in ``args``, all with :attr:`~WireVector.bitwidth` equal to the
             longest :attr:`~WireVector.bitwidth` in ``args``.
    """
    max_len = max(len(wv) for wv in args)
    if signed:
        return (wv.sign_extended(max_len) for wv in args)
    return (wv.zero_extended(max_len) for wv in args)


def as_wires(
    val: WireVectorLike,
    bitwidth: int | None = None,
    truncating: bool = True,
    block: Block = None,
) -> WireVector:
    """Convert ``val`` to a :class:`WireVector`.

    ``val`` may be a :class:`WireVector`, :class:`int` (including
    :class:`~enum.IntEnum`), :class:`str`, or :class:`bool`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    ``as_wires`` is mainly used to coerce values into :class:`WireVectors<WireVector>`
    (for example, operations such as ``x + 1`` where ``1`` needs to be converted to a
    :class:`Const` :class:`WireVector`). See :ref:`wirevector_coercion`. An example::

        >>> def make_my_hardware(a, b):
        ...     a = as_wires(a)
        ...     b = as_wires(b)
        ...     return (a + b) & 0xf

        >>> input = pyrtl.Input(name="input", bitwidth=8)
        >>> output = pyrtl.Output(name="output", bitwidth=4)

        >>> output <<= make_my_hardware(input, 7)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input": 20})
        >>> sim.inspect("output")
        11
        >>> (20 + 7) % 16
        11

    In the example above, ``as_wires`` will convert the ``7`` to ``Const(7)`` but keep
    ``input`` unchanged.

    :param val: A :class:`WireVector`, or a constant value that can be converted into a
        :class:`Const`.
    :param bitwidth: The :attr:`~WireVector.bitwidth` of the resulting
        :class:`WireVector`.
    :param truncating: Determines whether bits will be dropped to achieve the desired
        :attr:`~WireVector.bitwidth` if ``val`` is too long (if ``True``, the
        most-significant bits will be dropped).
    :param block: ``Block`` to use for the returned :class:`WireVector`. Defaults to the
        :ref:`working_block`.
    """
    from pyrtl.memory import _MemIndexed

    block = working_block(block)

    if isinstance(val, (int, str)):
        # note that this case captures bool as well (as bools are instances of ints)
        return Const(val, bitwidth=bitwidth, block=block)
    if isinstance(val, _MemIndexed):
        # convert to a memory read when the value is actually used
        if val.wire is None:
            val.wire = as_wires(
                val.mem._readaccess(val.index), bitwidth, truncating, block
            )
        return val.wire
    if isinstance(val, WrappedWireVector):
        return val.wire
    if not isinstance(val, WireVector):
        msg = (
            "error, expecting a wirevector, int, or Verilog-style const string got "
            f"{val} instead"
        )
        raise PyrtlError(msg)
    if bitwidth == "0":
        msg = "error, bitwidth must be >= 1"
        raise PyrtlError(msg)
    if val.bitwidth is None:
        msg = "error, attempting to use wirevector with no defined bitwidth"
        raise PyrtlError(msg)
    if bitwidth and bitwidth > val.bitwidth:
        return val.zero_extended(bitwidth)
    if bitwidth and truncating and bitwidth < val.bitwidth:
        return val[:bitwidth]  # truncate the upper bits
    return val


def bitfield_update(
    w: WireVectorLike,
    range_start: int,
    range_end: int,
    newvalue: int,
    truncating: bool = False,
) -> WireVector:
    """Update a :class:`WireVector` by replacing some of its bits with ``newvalue``.

    Given a :class:`WireVector` ``w``, this function returns a new :class:`WireVector`
    that is identical to ``w`` except in the range of bits specified by ``[range_start,
    range_end)``. In that range, the value ``newvalue`` is swapped in. For example::

        bitfield_update(w, range_start=20, range_end=23, newvalue=0b111)

    will return a :class:`WireVector` of the same length as ``w``, and with the same
    values as ``w``, but with bits 20, 21, and 22 all set to ``1``.

    Note that ``range_start`` and ``range_end`` will be inputs to a slice and so
    standard Python slicing rules apply (e.g. negative values for end-relative indexing
    and support for ``None``)::

        # Sets bits 20, 21, 22 to 1.
        w = bitfield_update(w, 20, 23, 0b111)

        # Sets bit 20 to 0, bits 21 and 22 to 1.
        w = bitfield_update(w, 20, 23, 0b110)

        # Assuming w is 32 bits, sets bits 31..20 = 0x7.
        w = bitfield_update(w, 20, None, 0x7)

        # Set the MSB (bit) to 1.
        w = bitfield_update(w, -1, None, 0x1)

        # Set the bits before the MSB (bit) to 9.
        w = bitfield_update(w, None, -1, 0x9)

        # Set the LSB (bit) to 1.
        w = bitfield_update(w, None, 1, 0x1)

        # Set the bits after the LSB (bit) to 9.
        w = bitfield_update(w, 1, None, 0x9)

    .. note::

        Consider using :func:`wire_struct` or :func:`wire_matrix` instead, which helps
        with consistently disassembling, naming, and reassembling fields.

    :param w: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`, to use as the starting point for
              the update
    :param range_start: The start of the range of bits to be updated.
    :param range_end: The end of the range of bits to be updated.
    :param newvalue: The value to be written in to the ``range_start:range_end`` range.
    :param truncating: If ``True``, clip ``newvalue`` to the proper bitwidth if
        ``newvalue`` is too large.

    :raise PyrtlError: If ``newvalue`` is too large to fit in the selected range of bits
        and ``truncating`` is ``False``.

    :return: ``w`` with some of the bits overwritten by ``newvalue``.
    """
    w = as_wires(w)
    idxs = list(
        range(len(w))
    )  # we make a list of integers and slice those up to use as indexes
    idxs_middle = idxs[range_start:range_end]
    if len(idxs_middle) == 0:
        msg = "Cannot update bitfield of size 0 (i.e. there are no bits to update)"
        raise PyrtlError(msg)
    idxs_lower = idxs[: idxs_middle[0]]
    idxs_upper = idxs[idxs_middle[-1] + 1 :]

    newvalue = as_wires(newvalue, bitwidth=len(idxs_middle), truncating=truncating)
    if len(idxs_middle) != len(newvalue):
        msg = (
            f"Cannot update bitfield of length {len(idxs_middle)} with value of length "
            f"{len(newvalue)} unless truncating=True is specified"
        )
        raise PyrtlError(msg)

    result_list = []
    if idxs_lower:
        result_list.append(w[idxs_lower[0] : idxs_lower[-1] + 1])
    result_list.append(newvalue)
    if idxs_upper:
        result_list.append(w[idxs_upper[0] : idxs_upper[-1] + 1])
    result = concat_list(result_list)

    if len(result) != len(w):
        msg = f"len(result)={len(result)}, len(original)={len(w)}"
        raise PyrtlInternalError(msg)
    return result


def bitfield_update_set(
    w: WireVectorLike,
    update_set: dict[tuple[int, int], WireVectorLike],
    truncating: bool = False,
) -> WireVector:
    """Update a :class:`WireVector` by replacing the bits specified in ``update_set``.

    Given a WireVector ``w``, return a new :class:`WireVector` that is identical to `w`
    except in the ranges of bits specified by ``update_set``. When multiple
    non-overlapping fields need to be updated in a single cycle, this provides a clearer
    way to describe that behavior than iterative calls to :func:`bitfield_update`::

        w = bitfield_update_set(w, update_set={
                (20, 23):    0x6,      # sets bit 20 to 0, bits 21 and 22 to 1
                (26, None):  0x7,      # assuming w is 32 bits, sets bits 31..26 to 0x7
                (None, 1):   0x0,      # set the LSB (bit) to 0
            })

    .. note::

        Consider using :func:`wire_struct` or :func:`wire_matrix` instead, which helps
        with consistently disassembling, naming, and reassembling fields.

    :param w: A :class:`WireVector`, or any type that can be coerced to
              :class:`WireVector` by :func:`as_wires`, to use as the starting point for
              the update
    :param update_set: A map from tuples of ``(range_start, range_end)`` integers to a
        new value for the range of bits.
    :param truncating: If ``True``, clip new values to the proper bitwidth if a new
        value is too large.

    :raise PyrtlError: If ``update_set`` contains overlapping fields.

    :return: ``w`` with some of its bits updated.
    """
    w = as_wires(w)
    # keep a list of bits that are updated to find overlaps
    setlist = [False] * len(w)
    # call bitfield for each one
    for (range_start, range_end), new_value in update_set.items():
        # check for overlaps
        setbits = setlist[range_start:range_end]
        if any(setbits):
            msg = "Bitfields for update are overlapping"
            raise PyrtlError(msg)
        setlist[range_start:range_end] = [True] * len(setbits)
        # do the actual update
        w = bitfield_update(w, range_start, range_end, new_value, truncating)
    return w


def enum_mux(
    cntrl: WireVector,
    table: dict[int, WireVector],
    default: WireVector = None,
    strict: bool = True,
) -> WireVector:
    """Build a mux for the control signals specified by an :class:`enum.IntEnum`.

    .. note::

        Consider using :ref:`conditional_assignment` instead.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> from enum import IntEnum
        >>> class Command(IntEnum):
        ...     ADD = 0
        ...     SUB = 1

        >>> command = pyrtl.Input(name="command", bitwidth=1)
        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> b = pyrtl.Input(name="b", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.enum_mux(cntrl=command, table={
        ...     Command.ADD: a + b,
        ...     Command.SUB: a - b,
        ... })

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"command": Command.ADD, "a": 1, "b": 2})
        >>> sim.inspect("output")
        3

        >>> sim.step(provided_inputs={"command": Command.SUB, "a": 5, "b": 3})
        >>> sim.inspect("output")
        2

    :param cntrl: Control for the mux.
    :param table: Maps :class:`enum.IntEnum` values to :class:`WireVector`.
    :param default: A :class:`WireVector` to use when the key is not present. In
        addition it is possible to use the key :data:`otherwise` to specify a default
        value, but it is an error if both are supplied.
    :param strict: When ``True``, check that the dictionary has an entry for every
        possible value in the :class:`enum.IntEnum`. Note that if a ``default`` is set,
        then this check is not performed as the ``default`` will provide valid values
        for any underspecified keys.

    :return: Result of the mux.
    """
    # check dictionary keys are of the right type
    keytypeset = {type(x) for x in table if x is not otherwise}
    if len(keytypeset) != 1:
        msg = f"table mixes multiple types {keytypeset} as keys"
        raise PyrtlError(msg)
    keytype = next(iter(keytypeset))
    # check that dictionary is complete for the enum
    try:
        enumkeys = list(keytype.__members__.values())
    except AttributeError as exc:
        msg = f"type {keytype} not an Enum and does not support the same interface"
        raise PyrtlError(msg) from exc
    missingkeys = [e for e in enumkeys if e not in table]

    # check for "otherwise" in table and move it to a default
    if otherwise in table:
        if default is not None:
            msg = 'both "otherwise" and default provided to enum_mux'
            raise PyrtlError(msg)
        default = table[otherwise]

    if strict and default is None and missingkeys:
        msg = f"table provided is incomplete, missing: {missingkeys}"
        raise PyrtlError(msg)

    # generate the actual mux
    vals = {k.value: d for k, d in table.items() if k is not otherwise}
    if default is not None:
        vals["default"] = default
    return muxes.sparse_mux(cntrl, vals)


def and_all_bits(vector: WireVector) -> WireVector:
    """Returns the result of bitwise ANDing all the bits in ``vector``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> input = pyrtl.Input(name="input", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.and_all_bits(input)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input": 0b0101})
        >>> sim.inspect("output")
        0
        >>> sim.step(provided_inputs={"input": 0b1111})
        >>> sim.inspect("output")
        1

    :param vector: Takes a single arbitrary length :class:`WireVector`.

    :return: Returns a 1-bit result, the bitwise ``&`` of all of the bits in ``vector``.
    """
    return tree_reduce(lambda a, b: a & b, vector)


def or_all_bits(vector: WireVector) -> WireVector:
    """Returns the result of bitwise ORing all the bits in ``vector``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> input = pyrtl.Input(name="input", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.or_all_bits(input)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input": 0b0000})
        >>> sim.inspect("output")
        0
        >>> sim.step(provided_inputs={"input": 0b0100})
        >>> sim.inspect("output")
        1

    :param vector: Takes a single arbitrary length :class:`WireVector`.

    :return: Returns a 1-bit result, the bitwise ``|`` of all of the bits in ``vector``.
    """
    return tree_reduce(lambda a, b: a | b, vector)


def xor_all_bits(vector: WireVector) -> WireVector:
    """Returns the result of bitwise XORing all the bits in ``vector``.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> input = pyrtl.Input(name="input", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.xor_all_bits(input)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input": 0b0100})
        >>> sim.inspect("output")
        1
        >>> sim.step(provided_inputs={"input": 0b0101})
        >>> sim.inspect("output")
        0

    :param vector: Takes a single arbitrary length :class:`WireVector`.

    :return: Returns a 1-bit result, the bitwise ``^`` of all of the bits in ``vector``.
    """
    return tree_reduce(lambda a, b: a ^ b, vector)


parity = xor_all_bits  # shadowing the xor_all_bits function
"""Alias for :func:`xor_all_bits`."""


def tree_reduce(op, vector: WireVector) -> WireVector:
    if len(vector) < 1:
        msg = "Cannot reduce empty vectors"
        raise PyrtlError(msg)
    if len(vector) == 1:
        return vector[0]
    left = tree_reduce(op, vector[: len(vector) // 2])
    right = tree_reduce(op, vector[len(vector) // 2 :])
    return op(left, right)


def _apply_op_over_all_bits(op, vector):
    if len(vector) < 1:
        msg = "Cannot reduce empty vectors"
        raise PyrtlError(msg)
    if len(vector) == 1:
        return vector[0]
    rest = _apply_op_over_all_bits(op, vector[1:])
    return op(vector[0], rest)


def rtl_any(*vectorlist: WireVectorLike) -> WireVector:
    """Hardware equivalent of Python's :func:`any`.

    Given any number of :class:`WireVectors<WireVector>`, return a 1-bit
    :class:`WireVector` which will hold a ``1`` if any of the inputs are ``1``. In other
    words, this generates a large OR gate. If no inputs are provided, it will return a
    :class:`Const` ``0`` (since there are no ``1s`` present) similar to Python's
    :func:`any` called with an empty list.

    .. note::

        ``rtl_any`` is most useful when working with a variable number of
        :class:`WireVectors<WireVector>`. For a fixed number of
        :class:`WireVectors<WireVector>`, it is clearer to use ``|``::

            any_ones = a | b | c

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> inputs = [pyrtl.Input(name="input0", bitwidth=1),
        ...           pyrtl.Input(name="input1", bitwidth=1)]
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtl_any(*inputs)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input0": 0, "input1": 0})
        >>> sim.inspect("output")
        0
        >>> sim.step(provided_inputs={"input0": 0, "input1": 1})
        >>> sim.inspect("output")
        1

    :param vectorlist: All arguments are length 1 :class:`WireVector`, or any type that
        can be coerced to :class:`WireVector` by :func:`as_wires`, with length 1.

    :raise PyrtlError: If any argument's :attr:`~WireVector.bitwidth` is not 1.

    :return: Length 1 :class:`WireVector` indicating if any bits in ``vectorlist`` are
             ``1``.
    """
    if len(vectorlist) == 0:
        return as_wires(False)
    converted_vectorlist = [as_wires(v) for v in vectorlist]
    if any(len(v) != 1 for v in converted_vectorlist):
        msg = "only length 1 WireVectors can be inputs to rtl_any"
        raise PyrtlError(msg)
    return or_all_bits(concat_list(converted_vectorlist))


def rtl_all(*vectorlist: WireVectorLike) -> WireVector:
    """Hardware equivalent of Python's :func:`all`.

    Given any number of :class:`WireVectors<WireVector>`, return a 1-bit
    :class:`WireVector` which will hold a ``1`` only if all of the inputs are ``1``. In
    other words, this generates a large AND gate. If no inputs are provided, it will
    return a :class:`Const` ``1`` (since there are no ``0s`` present) similar to
    Python's :func:`all` called with an empty list.

    .. note::

        ``rtl_all`` is most useful when working with a variable number of
        :class:`WireVectors<WireVector>`. For a fixed number of
        :class:`WireVectors<WireVector>`, it is clearer to use ``&``::

            all_ones = a & b & c

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> inputs = [pyrtl.Input(name="input0", bitwidth=1),
        ...           pyrtl.Input(name="input1", bitwidth=1)]
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtl_all(*inputs)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input0": 0, "input1": 1})
        >>> sim.inspect("output")
        0
        >>> sim.step(provided_inputs={"input0": 1, "input1": 1})
        >>> sim.inspect("output")
        1

    :param vectorlist: All arguments are length 1 :class:`WireVector`, or any type that
        can be coerced to :class:`WireVector` by :func:`as_wires`, with length 1.

    :raise PyrtlError: If any argument's :attr:`~WireVector.bitwidth` is not 1.

    :return: Length 1 :class:`WireVector` indicating if all bits in ``vectorlist`` are
             ``1``.
    """
    if len(vectorlist) == 0:
        return as_wires(True)
    converted_vectorlist = [as_wires(v) for v in vectorlist]
    if any(len(v) != 1 for v in converted_vectorlist):
        msg = "only length 1 WireVectors can be inputs to rtl_all"
        raise PyrtlError(msg)
    return and_all_bits(concat_list(converted_vectorlist))


def _basic_mult(A, B):
    """A stripped-down copy of the Wallace multiplier in rtllib"""
    if len(B) == 1:
        A, B = B, A  # so that we can reuse the code below :)
    if len(A) == 1:
        return concat_list(
            [A & b for b in B] + [Const(0)]
        )  # keep WireVector len consistent

    result_bitwidth = len(A) + len(B)
    bits = [[] for weight in range(result_bitwidth)]
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            bits[i + j].append(a & b)

    while not all(len(i) <= 2 for i in bits):
        deferred = [[] for weight in range(result_bitwidth + 1)]
        for i, w_array in enumerate(bits):  # Start with low weights and start reducing
            while len(w_array) >= 3:  # build a new full adder
                a, b, cin = (w_array.pop(0) for j in range(3))
                deferred[i].append(a ^ b ^ cin)
                deferred[i + 1].append(a & b | a & cin | b & cin)
            if len(w_array) == 2:
                a, b = w_array
                deferred[i].append(a ^ b)
                deferred[i + 1].append(a & b)
            else:
                deferred[i].extend(w_array)
        bits = deferred[:result_bitwidth]

    add_wires = tuple(itertools.zip_longest(*bits, fillvalue=Const(0)))
    adder_result = concat_list(add_wires[0]) + concat_list(add_wires[1])
    return adder_result[:result_bitwidth]


def _one_bit_add(a, b, carry_in):
    assert len(a) == len(b) == 1
    sumbit = a ^ b ^ carry_in
    carry_out = a & b | a & carry_in | b & carry_in
    return sumbit, carry_out


def _add_helper(a, b, carry_in):
    a, b = match_bitwidth(a, b)
    if len(a) == 1:
        sumbits, carry_out = _one_bit_add(a, b, carry_in)
    else:
        lsbit, ripplecarry = _one_bit_add(a[0], b[0], carry_in)
        msbits, carry_out = _add_helper(a[1:], b[1:], ripplecarry)
        sumbits = concat(msbits, lsbit)
    return sumbits, carry_out


def _basic_add(a, b):
    sumbits, carry_out = _add_helper(a, b, 0)
    return concat(carry_out, sumbits)


def _basic_sub(a, b):
    sumbits, carry_out = _add_helper(a, ~b, 1)
    return concat(carry_out, sumbits)


def _basic_eq(a, b):
    return ~or_all_bits(a ^ b)


def _basic_lt(a, b):
    assert len(a) == len(b)
    a_msb = a[-1]
    b_msb = b[-1]
    if len(a) == 1:
        return b_msb & ~a_msb
    small = _basic_lt(a[:-1], b[:-1])
    return (b_msb & ~a_msb) | (small & ~(a_msb ^ b_msb))


def _basic_gt(a, b):
    return _basic_lt(b, a)


def _basic_select(s, a, b):
    assert len(a) == len(b)
    assert len(s) == 1
    sa = concat(*[~s] * len(a))
    sb = concat(*[s] * len(b))
    return (a & sa) | (b & sb)
