from __future__ import absolute_import
import pyrtl
from . import adders


def main():
    # test_simple_mult()
    # test_wallace_tree()
    # test_wallace_timing()
    print("look at the test case folder")


def simple_mult(A, B, start):
    """ Generate simple shift-and-add multiplier.

    Builds a slow, small multiplier using the simple shift-and-add algorithm.
    Requires very small area (it uses only a single adder), but has long delay
    (worst case is len(a) cycles). a and b are arbitrary-length inputs; start
    is a one-bit input to indicate inputs are ready.done is a one-bit signal
    output raised when the multiplication is finished, at which point the
    product will be on the result line (returned by the function).
    """
    alen = len(A)
    blen = len(B)
    areg = pyrtl.Register(alen)
    breg = pyrtl.Register(blen + alen)
    accum = pyrtl.Register(blen + alen)
    done = areg == 0  # Multiplication is finished when a becomes 0

    # During multiplication, shift a right every cycle, b left every cycle
    with pyrtl.conditional_assignment:
        with start:  # initialization
            areg.next |= A
            breg.next |= B
            accum.next |= 0
        with ~done:  # don't run when there's no work to do
            areg.next |= areg[1:]  # right shift
            breg.next |= pyrtl.concat(breg, "1'b0")  # left shift

            # "Multply" shifted breg by LSB of areg by conditionally adding
            with areg[0]:
                accum.next |= accum + breg  # adds to accum only when LSB of areg is 1

    return accum, done


def tree_multiplier(A, B, reducer=adders.wallace_reducer, adder_func=adders.kogge_stone):
    """ Build an fast unclocked multiplier for inputs A and B using a Wallace or Dada Tree.

    :param Wirevector A, B: two input wires for the multiplication
    :param function reducer: Reduce the tree using either a Dada recuder or a Wallace reducer
      determines whether it is a Wallace tree multiplier or a Dada tree multiplier
    :param function adder_func: an adder function that will be used to do the last addition
    :return Wirevector: The multiplied result

    Delay is order logN, while area is order N^2.
    """

    """
    The two tree multipliers basically works by splitting the multiplication
    into a series of many additions, and it works by applying 'reductions'.
    """
    if len(B) == 1:
        A, B = B, A  # so that we can reuse the code below :)
    if len(A) == 1:
        # keep the wirevector len consistent
        return pyrtl.concat_list(list(A & b for b in B) + [pyrtl.Const(0)])

    bits_length = (len(A) + len(B))

    # create a list of lists, with slots for all the weights (bit-positions)
    bits = [[] for weight in range(bits_length)]

    # AND every bit of A with every bit of B (N^2 results) and store by "weight" (bit-position)
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            bits[i + j].append(a & b)

    return reducer(bits, bits_length, adder_func)


def fused_multiply_adder(mult_A, mult_B, add, signed=False, reducer=adders.wallace_reducer,
                         adder_func=adders.kogge_stone):
    """ Generate efficient hardware for a*b+c.

    Multiplies two wirevectors together and adds a third wirevector to the
    multiplication result, all in
    one step. By doing it this way (instead of separately), you reduce both
    the area and the timing delay of the circuit.


    :param Bool signed: Currently not supported (will be added in the future)
      The default will likely be changed to True, so if you want the smallest
      set of wires in the future, specify this as false
    :return WireVector: The result WireVector

    Advanced Parameters:
    :param reducer: The tree reducer to use
    :param adder_func: The adder to use to add the two results at the end
    """

    # TODO: Specify the length of the result wirevector

    return generalized_fma(((mult_A, mult_B),), (add,), signed, reducer, adder_func)


def generalized_fma(mult_pairs, add_wires, signed=False, reducer=adders.wallace_reducer,
                    adder_func=adders.kogge_stone):
    """Generated an opimitized fused multiply adder.

    A generalized FMA unit that multiplies each pair of numbers in mult_pairs,
    then adds the resulting numbers and and the values of the add wires all
    together to form an answer. This is faster than sepserate adders and
    multipliers because you avoid unnecessary adder structures for intermediate
    representations.

    :param mult_pairs: Either None (if there are no pairs to multiply) or
      a list of pairs of wires to multiply.
      ((mult1_1, mult1_2), ...)
    :param [WireVector] or None add_wires: Either None (if there are no individual
      items to add other than the mult_pairs, or a list of wires for adding on
      top of the result of the pair multiplication.
    :param Bool signed: Currently not supported (will be added in the future)
      The default will likely be changed to True, so if you want the smallest
      set of wires in the future, specify this as false
    :return WireVector: The result WireVector

    Advanced Parameters:
    :param reducer: The tree reducer to use
    :param adder_func: The adder to use to add the two results at the end
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
    result_bitwidth = (longest_wire_len +
                       int(math.ceil(math.log(len(add_wires) + len(mult_pairs), 2))))
    return reducer(bits, result_bitwidth, adder_func)


if __name__ == "__main__":
    main()
