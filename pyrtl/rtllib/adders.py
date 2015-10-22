from __future__ import absolute_import
import pyrtl
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
    # preparing the cin (and conveniently shifting the gen bits)
    gen_bits.insert(0, pyrtl.as_wires(cin))
    return pyrtl.concat(*reversed(gen_bits)) ^ prop_orig


def one_bit_add(a, b, cin):
    return pyrtl.concat(*_one_bit_add_no_concat(a, b, cin))


def _one_bit_add_no_concat(a, b, cin):
    assert len(a) == len(b) == len(cin) == 1
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return cout, sum


def ripple_add(a, b, cin=0):
    a, b = libutils.match_bitwidth(a, b)
    cin = pyrtl.as_wires(cin)
    if len(a) == 1:
        return one_bit_add(a, b, cin)
    else:
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
    shift_carry = (a | b) & (a | c) & (b | c)
    shift_carry_1 = pyrtl.concat(shift_carry, 0)
    return ripple_add(partial_sum, shift_carry_1)


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
        for a_wire in wire_set:
            if not isinstance(a_wire, pyrtl.WireVector) or len(a_wire) != 1:
                raise pyrtl.PyrtlError(
                    "The item %s is not a valid element for the wire_array_2. "
                    "It must be a WireVector of bitwidth 1")

    while not all(len(i) <= 2 for i in wire_array_2):
        deferred = [[] for weight in range(result_bitwidth)]
        for i, w_array in enumerate(wire_array_2):  # Start with low weights and start reducing
            while len(w_array) >= 3:  # Reduce with Full Adders until < 3 wires
                cout, sum = _one_bit_add_no_concat(*(w_array.pop(0) for j in range(3)))
                deferred[i].append(sum)  # deferred bit keeps this sum
                if i + 1 < result_bitwidth:  # watch out for index bounds
                    deferred[i + 1].append(cout)  # cout goes up by one

            if len(wire_array_2[i]) == 2 and reduce_2s:
                # Reduce with a Half Adder if exactly 2 wires remain
                a, b = w_array.pop(0), w_array.pop(0)
                deferred[i].append(a ^ b)  # deferred bit keeps this sum
                if i + 1 < result_bitwidth:
                    deferred[i + 1].append(a & b)  # cout goes up one weight
            else:
                deferred[i].extend(w_array)

        wire_array_2 = deferred  # Set bits equal to the deferred values

    # At this stage in the multiplication we have only 2 wire vectors left.
    add_wires = [], []
    result = None

    for i in range(result_bitwidth):
        if len(wire_array_2[i]) == 2:  # Check if the two wire vectors overlap yet
            break
        if result is None:
            result = wire_array_2[i][0]
        else:
            result = pyrtl.concat(wire_array_2[i][0], result)

    for j in range(i, result_bitwidth):
        for i in range(2):
            if len(wire_array_2[j]) >= i + 1:
                add_wires[i].insert(0, wire_array_2[j][i])
            else:
                add_wires[i].insert(0, pyrtl.Const(0))

    adder_result = final_adder(pyrtl.concat(*add_wires[0]), pyrtl.concat(*add_wires[1]))

    # Concatenate the results, and then return them.
    # Perhaps here we should slice off the overflow bit, if it exceeds bit_length?
    # result = result[:-1]
    if result is None:
        result = adder_result
    else:
        result = pyrtl.concat(adder_result, result)
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
