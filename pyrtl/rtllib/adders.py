import sys
sys.path.append("..")
import pyrtl
from pyrtl import *
from . import libutils


def main():
    print("You should be looking at the test case folder")


def kogge_stone(a, b, cin=0):
    """
    Creates a Kogge-Stone adder given two inputs

    :param a, b: The two Wirevectors to add up (bitwidths don't need to match)
    :param cin: An optimal carry Wirevector or value
    :return: a Wirevector representing the output of the adder

    The Kogge-Stone adder is a fast tree-based adder with O(log(n))
    propagation delay, useful for performance critical designs. However,
    it has O(n log(n)) area usage, and large fan out.
    """
    a, b = libutils.match_bitwidth(a, b)

    prop_orig = a ^ b
    prop_bits = [i for i in prop_orig]
    gen_bits = [i for i in a & b]
    prop_dist = 1

    # creation of the carry calculation
    while prop_dist < len(a):
        for i in reversed(range(prop_dist, len(a))):
            prop_old = prop_bits[i]
            gen_bits[i] = gen_bits[i] | (prop_old & gen_bits[i - prop_dist])
            if i >= prop_dist * 2:  # to prevent creating unnecessary nets and wires
                prop_bits[i] = prop_old & prop_bits[i - prop_dist]
        prop_dist *= 2

    # assembling the result of the addition
    gen_bits.insert(0, as_wires(cin))  # preparing the cin (and conveniently shifting the gen bits)
    return concat(*reversed(gen_bits)) ^ prop_orig


def one_bit_add(a, b, cin):
    assert len(a) == len(b) == 1  # len returns the bitwidth
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return pyrtl.concat(cout, sum)


def ripple_add(a, b, cin=0):
    a, b = libutils.match_bitwidth(a, b)
    cin = as_wires(cin)
    if len(a) == 1:
        return one_bit_add(a, b, cin)
    else:
        lsbit, ripplecarry = one_bit_add(a[0], b[0], cin)
        ripplecarry = one_bit_add(a[0], b[0], cin)
        msbits = ripple_add(a[1:], b[1:], ripplecarry[1])
        return pyrtl.concat(msbits, ripplecarry[0])


def carrysave_adder(a, b, c):
    """
    Adds three wirevectors up in an efficient manner
    :param a, b, c: the three wirevectors to add up
    :return: a wirevector with length 2 longer than the largest input
    """
    libutils.match_bitwidth(a, b, c)
    partial_sum = a ^ b ^ c
    partial_shift = pyrtl.concat(0, partial_sum)
    shift_carry = (a | b) & (a | c) & (b | c)
    shift_carry_1 = pyrtl.concat(shift_carry, 0)
    return ripple_add(partial_shift, shift_carry_1, 0)


def wallace_reducer(wire_array_2, result_bitwidth, final_adder=kogge_stone):
    """
    The reduction and final adding part of a dada tree. Useful for adding many numbers together
    The use of single bitwidth wires is to allow for additional flexibility

    :param [[Wirevector]] wire_array_2: An array of arrays of single bitwidth
    wirevectors
    :param int result_bitwidth: The bitwidth you want for the resulting wire
    Used to eliminate unnessary wires
    :param final_adder: The adder used for the final addition
    :return: wirevector of length result_wirevector
    """
    return _general_adder_reducer(wire_array_2, result_bitwidth, True, final_adder)


def dada_reducer(wire_array_2, result_bitwidth, final_adder=kogge_stone):
    """
    The reduction and final adding part of a dada tree. Useful for adding many numbers together
    The use of single bitwidth wires is to allow for additional flexibility

    :param [[Wirevector]] wire_array_2: An array of arrays of single bitwidth
    wirevectors
    :param int result_bitwidth: The bitwidth you want for the resulting wire
    Used to eliminate unnessary wires
    :param final_adder: The adder used for the final addition
    :return: wirevector of length result_wirevector
    """
    return _general_adder_reducer(wire_array_2, result_bitwidth, False, final_adder)


def _general_adder_reducer(wire_array_2, result_bitwidth, reduce_2s, final_adder):
    """
    Does the reduction and final adding for bot dada and wallace recucers

    :param [[Wirevector]] wire_array_2: An array of arrays of single bitwidth
    wirevectors
    :param int result_bitwidth: The bitwidth you want for the resulting wire
    Used to eliminate unnessary wires
    :param Bool reduce_2s: True=Wallace Reducer, False=Dada Reducer
    :param final_adder: The adder used for the final addition
    :return: wirevector of length result_wirevector
    """
    # verification that the wires are actually wirevectors of length 1
    """

    These reductions take place in the form of full-adders (3 inputs),
    half-adders (2 inputs), or just passing a wire along (1 input).

    These reductions take place as long as there are more than 2 wire
    vectors left. When there are 2 wire vectors left, you simply run the
    2 wire vectors through a Kogge-Stone adder.
    """
    for wire_set in wire_array_2:
        for wire in wire_set:
            if not isinstance(wire, WireVector) or len(wire) != 1:
                raise PyrtlError("The item %s is not a valid element for the wire_array_2."
                                 "It must be a WireVector of bitwidth 1")

    deferred = [[] for weight in range(result_bitwidth)]
    while not all([len(i) <= 2 for i in wire_array_2]):
        # While there's more than 2 wire vectors left
        for i in range(len(wire_array_2)):  # Start with low weights and start reducing
            while len(wire_array_2[i]) >= 3:  # Reduce with Full Adders until < 3 wires
                a, b, cin = (wire_array_2[i].pop(0) for j in range(3))
                deferred[i].append(a ^ b ^ cin)  # deferred bit keeps this sum
                if i + 1 < result_bitwidth:  # watch out for index bounds
                    deferred[i + 1].append((a & b) | (b & cin) | (a & cin))  # cout goes up by one

            if len(wire_array_2[i]) == 2:
                if reduce_2s:  # Reduce with a Half Adder if exactly 2 wires
                    a, b = wire_array_2[i].pop(0), wire_array_2[i].pop(0)
                    deferred[i].append(a ^ b)  # deferred bit keeps this sum
                    if i + 1 < result_bitwidth:
                        deferred[i + 1].append(a & b)  # cout goes up one weight
                else:
                    deferred[i].extend(wire_array_2[i])

            elif len(wire_array_2[i]) == 1:  # Remaining wire is passed along the reductions
                deferred[i].append(wire_array_2[i][0])  # deferred bit keeps this value

        wire_array_2 = deferred  # Set bits equal to the deferred values
        deferred = [[] for weight in range(result_bitwidth)]  # Reset deferred to empty

    # At this stage in the multiplication we have only 2 wire vectors left.

    num1 = []
    num2 = []
    # This humorous variable tells us when we have seen the start of the overlap
    # of the two wire vectors
    weve_seen_a_two = False
    result = None

    for i in range(result_bitwidth):

        if len(wire_array_2[i]) == 2:  # Check if the two wire vectors overlap yet
            weve_seen_a_two = True

        if not weve_seen_a_two:  # If they have not overlapped, add the 1's to result
            if result is None:
                result = wire_array_2[i][0]
            else:
                result = concat(wire_array_2[i][0], result)
        else:
            # For overlapping bits, create num1 and num2
            if weve_seen_a_two and len(wire_array_2[i]) == 2:
                num1.insert(0, wire_array_2[i][0])  # because we need to prepend to the list
                num2.insert(0, wire_array_2[i][1])

            # If there's 1 left it's part of num2
            if weve_seen_a_two and len(wire_array_2[i]) == 1 and i < result_bitwidth:
                num1.insert(0, Const(0))
                num2.insert(0, wire_array_2[i][0])

    adder_result = final_adder(concat(*num1), concat(*num2))

    # Concatenate the results, and then return them.
    # Perhaps here we should slice off the overflow bit, if it exceeds bit_length?
    # result = result[:-1]
    if result is None:
        result = adder_result
    else:
        result = concat(adder_result, result)
    if len(result) > result_bitwidth:
        return result[:result_bitwidth]
    else:
        return result

"""
Some adders that utilize these tree reducers

"""


def fast_group_adder(wires_to_add, reducer=wallace_reducer, final_adder=kogge_stone):
    """
    A generalization of the carry save adder, this is designed to add many numbers
    together in a both area and time efficient manner. Uses a tree reducer
    to achieve this performance


    :param [WireVector] wires_to_add: an array of wirevectors to add
    :param reducer: the tree reducer to use
    :param final_adder: The two value adder to use at the end
    :return: a wirevector with the result of the addition
      The length of the result is:
      max(len(w) for w in wires_to_add) + ceil(len(wires_to_add))
    """

    import math
    longest_wire_len = max(len(w) for w in wires_to_add)
    result_bitwidth = longest_wire_len + int(math.ceil(len(wires_to_add)))

    bits = [[] for i in range(longest_wire_len)]

    for wire in wires_to_add:
        for bit_loc, bit in enumerate(wire):
            bits[bit_loc].append(bit)

    return reducer(bits, result_bitwidth, final_adder)


if __name__ == "__main__":
    main()
