# coding=utf-8
"""
Multipliers contains various PyRTL sample multipliers for people to use

"""
from __future__ import absolute_import
import pyrtl
from . import adders, libutils


def simple_mult(A, B, start):
    """ Builds a slow, small multiplier using the simple shift-and-add algorithm.
    Requires very small area (it uses only a single adder), but has long delay
    (worst case is len(A) cycles). start is a one-bit input to indicate inputs are ready.
    done is a one-bit output signal raised when the multiplication is finished.

    :param WireVector A, B: two input wires for the multiplication
    :returns: Register containing the product; the "done" signal

    """
    triv_result = _trivial_mult(A, B)
    if triv_result is not None:
        return triv_result, pyrtl.Const(1, 1)

    alen = len(A)
    blen = len(B)
    areg = pyrtl.Register(alen)
    breg = pyrtl.Register(blen + alen)
    accum = pyrtl.Register(blen + alen)
    done = (areg == 0)  # Multiplication is finished when a becomes 0

    # During multiplication, shift a right every cycle, b left every cycle
    with pyrtl.conditional_assignment:
        with start:  # initialization
            areg.next |= A
            breg.next |= B
            accum.next |= 0
        with ~done:  # don't run when there's no work to do
            areg.next |= areg[1:]  # right shift
            breg.next |= pyrtl.concat(breg, pyrtl.Const(0, 1))  # left shift
            a_0_val = areg[0].sign_extended(len(accum))

            # adds to accum only when LSB of areg is 1
            accum.next |= accum + (a_0_val & breg)

    return accum, done


def _trivial_mult(A, B):
    """
    turns a multiplication into an And gate if one of the
    wires is a bitwidth of 1

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


def complex_mult(A, B, shifts, start):
    """ Generate shift-and-add multiplier that can shift and add multiple bits per clock cycle.
    Uses substantially more space than `simple_mult()` but is much faster.

    :param WireVector A, B: two input wires for the multiplication
    :param int shifts: number of spaces Register is to be shifted per clk cycle
        (cannot be greater than the length of `A` or `B`)
    :param bool start: start signal
    :returns: Register containing the product; the "done" signal
    """

    alen = len(A)
    blen = len(B)
    areg = pyrtl.Register(alen)
    breg = pyrtl.Register(alen + blen)
    accum = pyrtl.Register(alen + blen)
    done = (areg == 0)  # Multiplication is finished when a becomes 0
    if (shifts > alen) or (shifts > blen):
        raise pyrtl.PyrtlError("shift is larger than one or both of the parameters A or B,"
                               "please choose smaller shift")

    # During multiplication, shift a right every cycle 'shift' times,
    # shift b left every cycle 'shift' times
    with pyrtl.conditional_assignment:
        with start:  # initialization
            areg.next |= A
            breg.next |= B
            accum.next |= 0

        with ~done:  # don't run when there's no work to do
            # "Multiply" shifted breg by LSB of areg by cond. adding
            areg.next |= libutils._shifted_reg_next(areg, 'r', shifts)  # right shift
            breg.next |= libutils._shifted_reg_next(breg, 'l', shifts)  # left shift
            accum.next |= accum + _one_cycle_mult(areg, breg, shifts)

    return accum, done


def _one_cycle_mult(areg, breg, rem_bits, sum_sf=0, curr_bit=0):
    """ returns a WireVector sum of rem_bits multiplies (in one clock cycle)
    note: this method requires a lot of area because of the indexing in the else statement """
    if rem_bits == 0:
        return sum_sf
    else:
        a_curr_val = areg[curr_bit].sign_extended(len(breg))
        if curr_bit == 0:  # if no shift
            return(_one_cycle_mult(areg, breg, rem_bits - 1,  # areg, breg, rem_bits
                                   sum_sf + (a_curr_val & breg),  # sum_sf
                                   curr_bit + 1))  # curr_bit
        else:
            return _one_cycle_mult(
                areg, breg, rem_bits - 1,  # areg, breg, rem_bits
                sum_sf + (a_curr_val
                          & pyrtl.concat(breg, pyrtl.Const(0, curr_bit))),  # sum_sf
                curr_bit + 1  # curr_bit
            )


def tree_multiplier(A, B, reducer=adders.wallace_reducer, adder_func=adders.kogge_stone):
    """ Build an fast unclocked multiplier for inputs A and B using a Wallace or Dada Tree.

    :param WireVector A, B: two input wires for the multiplication
    :param function reducer: Reduce the tree using either a Dada recuder or a Wallace reducer
      determines whether it is a Wallace tree multiplier or a Dada tree multiplier
    :param function adder_func: an adder function that will be used to do the last addition
    :return WireVector: The multiplied result

    Delay is order logN, while area is order N^2.
    """

    """
    The two tree multipliers basically works by splitting the multiplication
    into a series of many additions, and it works by applying 'reductions'.
    """
    triv_res = _trivial_mult(A, B)
    if triv_res is not None:
        return triv_res

    bits_length = (len(A) + len(B))

    # create a list of lists, with slots for all the weights (bit-positions)
    bits = [[] for weight in range(bits_length)]

    # AND every bit of A with every bit of B (N^2 results) and store by "weight" (bit-position)
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            bits[i + j].append(a & b)

    return reducer(bits, bits_length, adder_func)


def signed_tree_multiplier(A, B, reducer=adders.wallace_reducer, adder_func=adders.kogge_stone):
    """Same as tree_multiplier, but uses two's-complement signed integers"""
    if len(A) == 1 or len(B) == 1:
        raise pyrtl.PyrtlError("sign bit required, one or both wires too small")

    aneg, bneg = A[-1], B[-1]
    a = _twos_comp_conditional(A, aneg)
    b = _twos_comp_conditional(B, bneg)

    res = tree_multiplier(a[:-1], b[:-1]).zero_extended(len(A) + len(B))
    return _twos_comp_conditional(res, aneg ^ bneg)


def _twos_comp_conditional(orig_wire, sign_bit, bw=None):
    """Returns two's complement of wire (using bitwidth bw) if sign_bit == 1"""
    if bw is None:
        bw = len(orig_wire)
    new_wire = pyrtl.WireVector(bw)
    with pyrtl.conditional_assignment:
        with sign_bit:
            new_wire |= ~orig_wire + 1
        with pyrtl.otherwise:
            new_wire |= orig_wire
    return new_wire


def fused_multiply_adder(mult_A, mult_B, add, signed=False, reducer=adders.wallace_reducer,
                         adder_func=adders.kogge_stone):
    """ Generate efficient hardware for a*b+c.

    Multiplies two wirevectors together and adds a third wirevector to the
    multiplication result, all in
    one step. By doing it this way (instead of separately), one reduces both
    the area and the timing delay of the circuit.


    :param Bool signed: Currently not supported (will be added in the future)
      The default will likely be changed to True, so if you want the smallest
      set of wires in the future, specify this as False
    :param reducer: (advanced) The tree reducer to use
    :param adder_func: (advanced) The adder to use to add the two results at the end
    :return WireVector: The result WireVector

    """

    # TODO: Specify the length of the result wirevector

    return generalized_fma(((mult_A, mult_B),), (add,), signed, reducer, adder_func)


def generalized_fma(mult_pairs, add_wires, signed=False, reducer=adders.wallace_reducer,
                    adder_func=adders.kogge_stone):
    """Generated an opimitized fused multiply adder.

    A generalized FMA unit that multiplies each pair of numbers in mult_pairs,
    then adds the resulting numbers and and the values of the add wires all
    together to form an answer. This is faster than separate adders and
    multipliers because you avoid unnecessary adder structures for intermediate
    representations.

    :param mult_pairs: Either None (if there are no pairs to multiply) or
      a list of pairs of wires to multiply:
      [(mult1_1, mult1_2), ...]
    :param add_wires: Either None (if there are no individual
      items to add other than the mult_pairs), or a list of wires for adding on
      top of the result of the pair multiplication.
    :param Bool signed: Currently not supported (will be added in the future)
      The default will likely be changed to True, so if you want the smallest
      set of wires in the future, specify this as False
    :param reducer: (advanced) The tree reducer to use
    :param adder_func: (advanced) The adder to use to add the two results at the end
    :return WireVector: The result WireVector

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

    import math
    result_bitwidth = (longest_wire_len
                       + int(math.ceil(math.log(len(add_wires) + len(mult_pairs), 2))))
    return reducer(bits, result_bitwidth, adder_func)
