"""
Basic integer multiplication is defined in PyRTL's core library, see:

- :meth:`.WireVector.__mul__` for unsigned integer multiplication.

- :func:`.signed_mult` for signed integer multiplication.

The functions below provide more complex alternatives.
"""

import math
from typing import Callable

import pyrtl
from pyrtl.rtllib import adders


def simple_mult(
    A: pyrtl.WireVector, B: pyrtl.WireVector, start: pyrtl.WireVector
) -> tuple[pyrtl.Register, pyrtl.WireVector]:
    """Builds a slow, small multiplier using the simple shift-and-add algorithm.

    Requires very small area (it uses only a single adder), but has long delay (worst
    case is ``len(A)`` cycles).

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> b = pyrtl.Input(name="b", bitwidth=4)
        >>> start = pyrtl.Input(name="start", bitwidth=1)

        >>> output, done = pyrtl.rtllib.multipliers.simple_mult(a, b, start=start)
        >>> output.name = "output"
        >>> done.name = "done"

        >>> sim = pyrtl.Simulation()
        >>> sim.step({"a": 2, "b": 3, "start": True})
        >>> while not sim.inspect("done"):
        ...     sim.step({"a": 0, "b": 0, "start": False})
        >>> sim.inspect("output")
        6

    :param A: Input wire for the multiplication.
    :param B: Input wire for the multiplication.
    :param start: A one-bit input that indicates when the inputs are ready.

    :return: A :class:`.Register` containing the product, and a 1-bit ``done`` signal.
    """
    triv_result = _trivial_mult(A, B)
    if triv_result is not None:
        return triv_result, pyrtl.Const(1, 1)

    alen = len(A)
    blen = len(B)
    areg = pyrtl.Register(alen)
    breg = pyrtl.Register(blen + alen)
    accum = pyrtl.Register(blen + alen)
    done = pyrtl.WireVector(bitwidth=1)

    # During multiplication, shift a right every cycle, b left every cycle
    with pyrtl.conditional_assignment:
        with start:  # initialization
            areg.next |= A
            breg.next |= B
            accum.next |= 0
        with areg != 0:  # don't run when there's no work to do
            areg.next |= areg[1:]  # right shift
            breg.next |= pyrtl.concat(breg, pyrtl.Const(0, 1))  # left shift
            a_0_val = areg[0].sign_extended(len(accum))

            # adds to accum only when LSB of areg is 1
            accum.next |= accum + (a_0_val & breg)
        with pyrtl.otherwise:
            done |= True

    return accum, done


def _trivial_mult(A, B):
    """
    Turns a multiplication into an And gate if one of the wires is a bitwidth of 1.

    :param A:
    :param B:

    :return:
    """
    if len(B) == 1:
        A, B = B, A  # so that we can reuse the code below :)
    if len(A) == 1:
        a_vals = A.sign_extended(len(B))

        # keep the wirevector len consistent
        return pyrtl.concat_list([a_vals & B, pyrtl.Const(0)])
    return None


def complex_mult(
    A: pyrtl.WireVector, B: pyrtl.WireVector, shifts: int, start: pyrtl.WireVector
) -> tuple[pyrtl.Register, pyrtl.WireVector]:
    """Generate shift-and-add multiplier that can shift and add multiple bits per clock
    cycle. Uses substantially more space than :func:`simple_mult` but is much faster.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> b = pyrtl.Input(name="b", bitwidth=4)
        >>> start = pyrtl.Input(name="start", bitwidth=1)

        >>> output, done = pyrtl.rtllib.multipliers.complex_mult(
        ...     a, b, shifts=2, start=start)
        >>> output.name = "output"
        >>> done.name = "done"

        >>> sim = pyrtl.Simulation()
        >>> sim.step({"a": 2, "b": 3, "start": True})
        >>> while not sim.inspect("done"):
        ...     sim.step({"a": 0, "b": 0, "start": False})
        >>> sim.inspect("output")
        6

    :param A: Input wire for the multiplication.
    :param B: Input wire for the multiplication.
    :param shifts: Number of spaces :class:`.Register` is to be shifted per clock cycle.
        Cannot be greater than the length of ``A`` or ``B``.
    :param start: One-bit start signal.

    :return: :class:`.Register` containing the product, and a 1-bit ``done`` signal.
    """

    alen = len(A)
    blen = len(B)
    areg = pyrtl.Register(alen)
    breg = pyrtl.Register(alen + blen)
    accum = pyrtl.Register(alen + blen)
    done = pyrtl.WireVector(bitwidth=1)
    if (shifts > alen) or (shifts > blen):
        msg = (
            "shift is larger than one or both of the parameters A or B, please choose "
            "smaller shift"
        )
        raise pyrtl.PyrtlError(msg)

    # During multiplication, shift a right every cycle 'shift' times, shift b left every
    # cycle 'shift' times
    with pyrtl.conditional_assignment:
        with start:  # initialization
            areg.next |= A
            breg.next |= B
            accum.next |= 0

        with areg != 0:  # don't run when there's no work to do
            # "Multiply" shifted breg by LSB of areg by cond. adding
            areg.next |= pyrtl.shift_right_logical(areg, shifts)
            breg.next |= pyrtl.shift_left_logical(breg, shifts)
            accum.next |= accum + _one_cycle_mult(areg, breg, shifts)

        with pyrtl.otherwise:
            done |= True

    return accum, done


def _one_cycle_mult(areg, breg, rem_bits, sum_sf=0, curr_bit=0):
    """Returns a WireVector sum of ``rem_bits`` multiplies (in one clock cycle)

    ..note::

        this method requires a lot of area because of the indexing in the else statement
    """
    if rem_bits == 0:
        return sum_sf
    a_curr_val = areg[curr_bit].sign_extended(len(breg))
    if curr_bit == 0:  # if no shift
        return _one_cycle_mult(
            areg,
            breg,
            rem_bits - 1,  # areg, breg, rem_bits
            sum_sf + (a_curr_val & breg),  # sum_sf
            curr_bit + 1,
        )  # curr_bit
    return _one_cycle_mult(
        areg,
        breg,
        rem_bits - 1,  # areg, breg, rem_bits
        sum_sf + (a_curr_val & pyrtl.concat(breg, pyrtl.Const(0, curr_bit))),  # sum_sf
        curr_bit + 1,  # curr_bit
    )


def tree_multiplier(
    A: pyrtl.WireVector,
    B: pyrtl.WireVector,
    reducer: Callable = adders.wallace_reducer,
    adder_func: Callable = adders.kogge_stone,
) -> pyrtl.WireVector:
    """Build an fast unclocked multiplier using a Wallace or Dada Tree.

    Delay is `O(log(N))`, while area is `O(N^2)`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> b = pyrtl.Input(name="b", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.multipliers.tree_multiplier(a, b)

        >>> sim = pyrtl.Simulation()
        >>> sim.step({"a": 2, "b": 3})
        >>> sim.inspect("output")
        6

    :param A: Input wire for the multiplication.
    :param B: Input wire for the multiplication.
    :param reducer: Reducing the tree with a :func:`~.adders.wallace_reducer` or a
        :func:`~.adders.dada_reducer` determines whether the ``tree_multiplier`` is a
        Wallace tree multiplier or a Dada tree multiplier.
    :param adder_func: An adder function that will be used to do the last addition.

    :return: The multiplied result.
    """
    # The two tree multipliers basically works by splitting the multiplication into a
    # series of many additions, and it works by applying 'reductions'.
    triv_res = _trivial_mult(A, B)
    if triv_res is not None:
        return triv_res

    bits_length = len(A) + len(B)

    # create a list of lists, with slots for all the weights (bit-positions)
    bits = [[] for weight in range(bits_length)]

    # AND every bit of A with every bit of B (N^2 results) and store by "weight"
    # (bit-position)
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            bits[i + j].append(a & b)

    return reducer(bits, bits_length, adder_func)


def signed_tree_multiplier(
    A, B, reducer=adders.wallace_reducer, adder_func=adders.kogge_stone
):
    """Same as :func:`tree_multiplier`, but uses two's-complement signed integers.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> b = pyrtl.Input(name="b", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.multipliers.signed_tree_multiplier(a, b)

        >>> sim = pyrtl.Simulation()
        >>> sim.step({"a": -2, "b": 3})
        >>> pyrtl.val_to_signed_integer(sim.inspect("output"), bitwidth=output.bitwidth)
        -6
    """
    if len(A) == 1 or len(B) == 1:
        msg = "sign bit required, one or both wires too small"
        raise pyrtl.PyrtlError(msg)

    aneg, bneg = A[-1], B[-1]
    a = _twos_comp_conditional(A, aneg)
    b = _twos_comp_conditional(B, bneg)

    res = tree_multiplier(
        a[:-1], b[:-1], reducer=reducer, adder_func=adder_func
    ).zero_extended(len(A) + len(B))
    return _twos_comp_conditional(res, aneg ^ bneg)


def _twos_comp_conditional(
    orig_wire: pyrtl.WireVector, sign_bit: pyrtl.WireVector
) -> pyrtl.WireVector:
    """Returns two's complement of ``orig_wire`` if ``sign_bit`` == 1"""
    return pyrtl.select(sign_bit, (~orig_wire + 1).truncate(len(orig_wire)), orig_wire)


def fused_multiply_adder(
    mult_A: pyrtl.WireVector,
    mult_B: pyrtl.WireVector,
    add: pyrtl.WireVector,
    signed: bool = False,
    reducer: Callable = adders.wallace_reducer,
    adder_func: Callable = adders.kogge_stone,
) -> pyrtl.WireVector:
    """Generate efficient hardware for ``mult_A * mult_B + add``.

    Multiplies two :class:`WireVectors<.WireVector>` together and adds a third
    :class:`.WireVector` to the multiplication result, all in one step. By combining
    these operations, rather than doing them separately, one reduces both the area and
    the timing delay of the circuit.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> b = pyrtl.Input(name="b", bitwidth=4)
        >>> c = pyrtl.Input(name="c", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.multipliers.fused_multiply_adder(a, b, c)

        >>> sim = pyrtl.Simulation()
        >>> sim.step({"a": 2, "b": 3, "c": 4})
        >>> pyrtl.val_to_signed_integer(sim.inspect("output"), bitwidth=output.bitwidth)
        10
        >>> 2 * 3 + 4
        10

    :param mult_A: Input wire for the multiplication.
    :param mult_B: Input wire for the multiplication.
    :param add: Input wire for the addition.
    :param signed: Currently not supported (will be added in the future) The default
        will likely be changed to ``True``, so if you want the smallest set of wires in
        the future, specify this as ``False``.
    :param reducer: (advanced) The tree reducer to use. See
        :func:`~.adders.dada_reducer` and :func:`~.adders.wallace_reducer`.
    :param adder_func: (advanced) The adder to use to add the two results at the end.

    :return: The result :class:`.WireVector`.
    """

    # TODO: Specify the length of the result wirevector

    return generalized_fma(((mult_A, mult_B),), (add,), signed, reducer, adder_func)


def generalized_fma(
    mult_pairs: list[tuple[pyrtl.WireVector, pyrtl.WireVector]],
    add_wires: list[pyrtl.WireVector],
    signed: bool = False,  # noqa: ARG001
    reducer: Callable = adders.wallace_reducer,
    adder_func: Callable = adders.kogge_stone,
) -> pyrtl.WireVector:
    """Generated an optimized fused multiply adder.

    A generalized FMA unit that multiplies each pair of numbers in ``mult_pairs``, then
    adds up the resulting products and all the values of the ``add_wires``. This is
    faster than multiplying and adding separately because you avoid unnecessary adder
    structures for intermediate representations.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> mult_pairs = [(pyrtl.Const(2), pyrtl.Const(3)),
        ...               (pyrtl.Const(4), pyrtl.Const(5))]
        >>> add_wires = [pyrtl.Const(6), pyrtl.Const(7)]
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.multipliers.generalized_fma(mult_pairs, add_wires)

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> sim.inspect("output")
        39
        >>> 2 * 3 + 4 * 5 + 6 + 7
        39

    :param mult_pairs: Either ``None`` (if there are no pairs to multiply) or a list of
        pairs of wires to multiply together: ``[(mult1_1, mult1_2), ...]``
    :param add_wires: Either ``None`` (if there are no individual items to add other
        than the ``mult_pairs`` products), or a list of wires to add on top of the
        result of the pair multiplication.
    :param signed: Currently not supported (will be added in the future) The default
        will likely be changed to ``True``, so if you want the smallest set of wires in
        the future, specify this as ``False``.
    :param reducer: (advanced) The tree reducer to use. See
        :func:`~.adders.dada_reducer` and :func:`~.adders.wallace_reducer`.
    :param adder_func: (advanced) The adder to use to add the two results at the end.

    :return: The result :class:`.WireVector`.
    """
    # first need to figure out the max length
    if mult_pairs:  # Need to deal with the case when it is empty
        mult_max = max(len(m[0]) + len(m[1]) - 1 for m in mult_pairs)
    else:
        mult_max = 0

    if add_wires:
        add_max = max(len(x) for x in add_wires)
    else:
        add_max = 0

    longest_wire_len = max(add_max, mult_max)
    bits = [[] for i in range(longest_wire_len)]

    for mult_a, mult_b in mult_pairs:
        for i, a in enumerate(mult_a):
            for j, b in enumerate(mult_b):
                bits[i + j].append(a & b)

    for wire in add_wires:
        for bit_loc, bit in enumerate(wire):
            bits[bit_loc].append(bit)

    result_bitwidth = longest_wire_len + math.ceil(
        math.log2(len(add_wires) + len(mult_pairs))
    )
    return reducer(bits, result_bitwidth, adder_func)
