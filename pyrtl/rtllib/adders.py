"""
Basic integer addition is defined in PyRTL's core library, see:

- :meth:`.WireVector.__add__` for unsigned integer addition.

- :func:`.signed_add` for signed integer addition.

The functions below provide more complex alternatives.
"""

import itertools
import math
from typing import Callable

import pyrtl


def kogge_stone(
    a: pyrtl.WireVector, b: pyrtl.WireVector, cin: pyrtl.wire.WireVectorLike = 0
) -> pyrtl.WireVector:
    """Creates a Kogge-Stone adder given two inputs.

    The Kogge-Stone adder is a fast tree-based adder with `O(log(n))` propagation delay,
    useful for performance critical designs. However, it has `O(n log(n))` area usage,
    and large fan out.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> b = pyrtl.Input(name="b", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.adders.kogge_stone(a, b)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"a": 2, "b": 3})
        >>> sim.inspect("output")
        5

    :param a: A :class:`.WireVector` to add up. Bitwidths don't need to match.
    :param b: A :class:`.WireVector` to add up. Bitwidths don't need to match.
    :param cin: An optional 1-bit carry-in :class:`.WireVector`. Can be any type that
        can be coerced to :class:`.WireVector` by :func:`.as_wires`.

    :return: A :class:`.WireVector` representing the output of the adder.
    """
    a, b = pyrtl.match_bitwidth(a, b)

    prop_orig = a ^ b
    prop_bits = list(prop_orig)
    gen_bits = list(a & b)
    prop_dist = 1

    # creation of the carry calculation
    while prop_dist < len(a):
        for i in reversed(range(prop_dist, len(a))):
            prop_old = prop_bits[i]
            gen_bits[i] = gen_bits[i] | (prop_old & gen_bits[i - prop_dist])
            if i >= prop_dist * 2:  # to prevent creating unnecessary nets and wires
                prop_bits[i] = prop_old & prop_bits[i - prop_dist]
        prop_dist *= 2

    # assembling the result of the addition. preparing the cin (and conveniently
    # shifting the gen bits)
    gen_bits.insert(0, pyrtl.as_wires(cin))
    return pyrtl.concat_list(gen_bits) ^ prop_orig


def one_bit_add(a, b, cin=0):
    return pyrtl.concat(*_one_bit_add_no_concat(a, b, cin))


def _one_bit_add_no_concat(a, b, cin=0):
    cin = pyrtl.as_wires(cin)  # to make sure that an int cin doesn't break things
    assert len(a) == len(b) == len(cin) == 1
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return cout, sum


def half_adder(a, b):
    assert len(a) == len(b) == 1
    sum = a ^ b
    cout = a & b
    return cout, sum


def ripple_add(a, b, cin=0):
    if len(a) < len(b):  # make sure that b is the shorter wire
        b, a = a, b
    cin = pyrtl.as_wires(cin)
    if len(a) == 1:
        return one_bit_add(a, b, cin)
    ripplecarry = one_bit_add(a[0], b[0], cin)
    if len(b) == 1:
        msbits = ripple_half_add(a[1:], ripplecarry[1])
    else:
        msbits = ripple_add(a[1:], b[1:], ripplecarry[1])
    return pyrtl.concat(msbits, ripplecarry[0])


def ripple_half_add(a, cin=0):
    cin = pyrtl.as_wires(cin)
    if len(a) == 1:
        return pyrtl.concat(*half_adder(a, cin))
    ripplecarry = half_adder(a[0], cin)
    msbits = ripple_half_add(a[1:], ripplecarry[0])
    return pyrtl.concat(msbits, ripplecarry[1])


def carrysave_adder(
    a: pyrtl.WireVector,
    b: pyrtl.WireVector,
    c: pyrtl.WireVector,
    final_adder: Callable = ripple_add,
) -> pyrtl.WireVector:
    """Adds three :class:`WireVectors<.WireVector>` up in an efficient manner.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> b = pyrtl.Input(name="b", bitwidth=4)
        >>> c = pyrtl.Input(name="c", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.adders.carrysave_adder(a, b, c)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"a": 2, "b": 3, "c": 4})
        >>> sim.inspect("output")
        9

    :param a: A :class:`.WireVector` to add up. Bitwidths don't need to match.
    :param b: A :class:`.WireVector` to add up. Bitwidths don't need to match.
    :param c: A :class:`.WireVector` to add up. Bitwidths don't need to match.
    :param final_adder: The adder to use for the final addition.

    :return: A :class:`.WireVector` with bitwidth equal to the longest input, plus 2.
    """
    a, b, c = pyrtl.match_bitwidth(a, b, c)
    partial_sum = a ^ b ^ c
    shift_carry = (a | b) & (a | c) & (b | c)
    return pyrtl.concat(final_adder(partial_sum[1:], shift_carry), partial_sum[0])


def cla_adder(
    a: pyrtl.WireVector,
    b: pyrtl.WireVector,
    cin: pyrtl.WireVector = 0,
    la_unit_len: int = 4,
) -> pyrtl.WireVector:
    """Carry Look-Ahead Adder.

    A Carry Look-Ahead Adder is an adder that is faster than :func:`ripple_add`, as it
    calculates the carry bits faster. It is not as fast as :func:`kogge_stone`, but uses
    less area.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> a = pyrtl.Input(name="a", bitwidth=4)
        >>> b = pyrtl.Input(name="b", bitwidth=4)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.adders.cla_adder(a, b)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"a": 2, "b": 3})
        >>> sim.inspect("output")
        5

    :param a: A :class:`.WireVector` to add up. Bitwidths don't need to match.
    :param b: A :class:`.WireVector` to add up. Bitwidths don't need to match.
    :param cin: A 1-bit carry-in :class:`.WireVector`.
    :param la_unit_len: The length of input that every unit processes.

    :return: A :class:`.WireVector` representing the output of the adder.
    """
    a, b = pyrtl.match_bitwidth(a, b)
    if len(a) <= la_unit_len:
        sum, cout = _cla_adder_unit(a, b, cin)
        return pyrtl.concat(cout, sum)
    sum, cout = _cla_adder_unit(a[0:la_unit_len], b[0:la_unit_len], cin)
    msbits = cla_adder(a[la_unit_len:], b[la_unit_len:], cout, la_unit_len)
    return pyrtl.concat(msbits, sum)


def _cla_adder_unit(a, b, cin):
    """
    Carry generation and propogation signals will be calculated only using the inputs;
    their values don't rely on the sum. Every unit generates a cout signal which is used
    as cin for the next unit.
    """
    gen = a & b
    prop = a ^ b
    assert len(prop) == len(gen)

    carry = [gen[0] | prop[0] & cin]
    sum_bit = prop[0] ^ cin

    cur_gen = gen[0]
    cur_prop = prop[0]
    for i in range(1, len(prop)):
        cur_gen = gen[i] | (prop[i] & cur_gen)
        cur_prop = cur_prop & prop[i]
        sum_bit = pyrtl.concat(prop[i] ^ carry[i - 1], sum_bit)
        carry.append(gen[i] | (prop[i] & carry[i - 1]))
    cout = cur_gen | (cur_prop & cin)
    return sum_bit, cout


def wallace_reducer(
    wire_array_2: list[list[pyrtl.WireVector]],
    result_bitwidth: int,
    final_adder: Callable = kogge_stone,
) -> pyrtl.WireVector:
    """The reduction and final adding part of a dada tree.

    Useful for adding many numbers together with :func:`fast_group_adder`. The use of
    single bitwidth wires allows for additional flexibility.

    :param wire_array_2: An array of arrays of single bitwidth
        :class:`WireVectors<.WireVector>`.
    :param result_bitwidth: Bitwidth of the resulting wire. Used to eliminate
        unnecessary wires.
    :param final_adder: The adder used for the final addition.

    :return: :class:`.WireVector` with :attr:`~.WireVector.bitwidth`
             ``result_bitwidth``.
    """
    # verification that the wires are actually wirevectors of length 1
    for wire_set in wire_array_2:
        for a_wire in wire_set:
            if not isinstance(a_wire, pyrtl.WireVector) or len(a_wire) != 1:
                msg = (
                    f"The item {a_wire} is not a valid element for the wire_array_2. "
                    "It must be a WireVector of bitwidth 1"
                )
                raise pyrtl.PyrtlError(msg)

    while not all(len(i) <= 2 for i in wire_array_2):
        deferred = [[] for weight in range(result_bitwidth + 1)]
        for i, w_array in enumerate(
            wire_array_2
        ):  # Start with low weights and start reducing
            while len(w_array) >= 3:
                cout, sum = _one_bit_add_no_concat(*(w_array.pop(0) for j in range(3)))
                deferred[i].append(sum)
                deferred[i + 1].append(cout)

            if len(w_array) == 2:
                cout, sum = half_adder(*w_array)
                deferred[i].append(sum)
                deferred[i + 1].append(cout)
            else:
                deferred[i].extend(w_array)
        wire_array_2 = deferred[:result_bitwidth]

    # At this stage in the multiplication we have only 2 wire vectors left.
    # now we need to add them up
    result = _sparse_adder(wire_array_2, final_adder)
    if len(result) > result_bitwidth:
        return result[:result_bitwidth]
    return result


def dada_reducer(
    wire_array_2: list[list[pyrtl.WireVector]],
    result_bitwidth: int,
    final_adder: Callable = kogge_stone,
) -> pyrtl.WireVector:
    """The reduction and final adding part of a dada tree.

    Useful for adding many numbers together with :func:`fast_group_adder`. The use of
    single bitwidth wires allows for additional flexibility.

    :param wire_array_2: An array of arrays of single bitwidth
        :class:`WireVectors<.WireVector>`.
    :param result_bitwidth: Bitwidth of the resulting wire. Used to eliminate
        unnecessary wires.
    :param final_adder: The adder used for the final addition.

    :return: :class:`.WireVector` with :attr:`~.WireVector.bitwidth`
             ``result_bitwidth``.
    """
    # verification that the wires are actually wirevectors of length 1
    for wire_set in wire_array_2:
        for a_wire in wire_set:
            if not isinstance(a_wire, pyrtl.WireVector) or len(a_wire) != 1:
                msg = (
                    f"The item {a_wire} is not a valid element for the wire_array_2. "
                    "It must be a WireVector of bitwidth 1"
                )
                raise pyrtl.PyrtlError(msg)

    max_width = max(len(i) for i in wire_array_2)
    reduction_schedule = [2]
    while reduction_schedule[-1] <= max_width:
        reduction_schedule.append(int(reduction_schedule[-1] * 3 / 2))

    for reduction_target in reversed(reduction_schedule[:-1]):
        deferred = [[] for weight in range(result_bitwidth + 1)]
        for i, w_array in enumerate(
            wire_array_2
        ):  # Start with low weights and start reducing
            while len(w_array) + len(deferred[i]) > reduction_target:
                if len(w_array) + len(deferred[i]) - reduction_target >= 2:
                    cout, sum = _one_bit_add_no_concat(
                        *(w_array.pop(0) for j in range(3))
                    )
                    deferred[i].append(sum)
                    deferred[i + 1].append(cout)
                else:
                    cout, sum = half_adder(*(w_array.pop(0) for j in range(2)))
                    deferred[i].append(sum)
                    deferred[i + 1].append(cout)
            deferred[i].extend(w_array)
            if len(deferred[i]) > reduction_target:
                msg = "Expected that the code would be able to reduce more wires"
                raise pyrtl.PyrtlError(msg)
        wire_array_2 = deferred[:result_bitwidth]

    # At this stage in the multiplication we have only 2 wire vectors left.
    # now we need to add them up
    result = _sparse_adder(wire_array_2, final_adder)
    if len(result) > result_bitwidth:
        return result[:result_bitwidth]
    return result


def _sparse_adder(wire_array_2, adder):
    result = []
    for single_w_index in range(len(wire_array_2)):
        if (
            len(wire_array_2[single_w_index]) == 2
        ):  # Check if the two wire vectors overlap yet
            break
        result.append(wire_array_2[single_w_index][0])

    wires_to_zip = wire_array_2[single_w_index:]
    add_wires = tuple(itertools.zip_longest(*wires_to_zip, fillvalue=pyrtl.Const(0)))
    adder_result = adder(
        pyrtl.concat_list(add_wires[0]), pyrtl.concat_list(add_wires[1])
    )
    return pyrtl.concat(adder_result, *reversed(result))


"""
Some adders that utilize these tree reducers
"""


def fast_group_adder(
    wires_to_add: list[pyrtl.WireVector],
    reducer: Callable = wallace_reducer,
    final_adder: Callable = kogge_stone,
):
    """A generalization of :func:`carrysave_adder`, ``fast_group_adder`` is designed to
    add many numbers together in a both area and time efficient manner. Uses a tree
    reducer to achieve this performance.

    The length of the result is::

        max(len(w) for w in wires_to_add) + ceil(len(wires_to_add))

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> wires_to_add = [pyrtl.Const(n) for n in range(10)]
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.adders.fast_group_adder(wires_to_add)

        >>> sim = pyrtl.Simulation()
        >>> sim.step()
        >>> sim.inspect("output")
        45
        >>> sum(range(10))
        45


    :param wires_to_add: A :class:`list` of :class:`WireVectors<.WireVector>` to add.
    :param reducer: The tree reducer to use. See :func:`wallace_reducer` and
        :func:`dada_reducer`.
    :param final_adder: The two value adder to use at the end.

    :return: A :class:`.WireVector` with the result of the addition.
    """
    longest_wire_len = max(len(w) for w in wires_to_add)
    result_bitwidth = longest_wire_len + math.ceil(math.log2(len(wires_to_add)))

    bits = [[] for i in range(longest_wire_len)]

    for wire in wires_to_add:
        for bit_loc, bit in enumerate(wire):
            bits[bit_loc].append(bit)

    return reducer(bits, result_bitwidth, final_adder)
