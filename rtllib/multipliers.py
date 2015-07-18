import sys
sys.path.append("..")
import io
from pyrtl import *
import adders


def main():
    # test_simple_mult()
    # test_wallace_tree()
    # test_wallace_timing()
    print "look at the test case folder"


def simple_mult(A, B, start, done):
    """Build a slow, small multiplier using the simple shift-and-add algorithm.
    Requires very small area (it uses only a single adder), but has long delay
    (worst case is len(a) cycles). a and b are arbitrary-length inputs; start
    is a one-bit input to indicate inputs are ready.done is a one-bit signal
    output raised when the multiplication is finished, at which point the
    product will be on the result line (returned by the function)."""
    alen = len(A)
    blen = len(B)
    areg = Register(alen)
    breg = Register(blen+alen)
    accum = Register(blen+alen)
    aiszero = areg == 0

    # Multiplication is finished when a becomes 0
    done <<= aiszero

    # During multiplication, shift a right every cycle, b left every cycle
    with ConditionalUpdate() as condition:
        with condition(start):  # initialization
            areg.next |= A
            breg.next |= B
            accum.next |= 0
        with condition(~aiszero):  # don't run when there's no work to do
            areg.next |= areg[1:]  # right shift
            breg.next |= concat(breg, "1'b0")  # left shift

            # "Multply" shifted breg by LSB of areg by conditionally adding
            with condition(areg[0]):
                accum.next |= accum + breg  # adds to accum only when LSB of areg is 1

    return accum


def tree_multiplier(A, B, reducer=adders.walllace_reducer, adder_func=adders.kogge_stone):
    """
    Build an fast unclocked multiplier for inputs A and B using a Wallace or Dada Tree.
    Delay is order logN, while area is order N^2.

    :param Wirevector A, B: two input wires for the multiplication
    :param function reducer: Reduce the tree using either a Dada recuder or a Wallace reducer
      determines whether it is a Wallace tree multiplier or a Dada tree multiplier
    :param function adder_func: an adder function that will be used to do the last addition
    :return: the multiplied result
    """

    """
    The two tree multipliers basically works by splitting the multiplication
    into a series of many additions, and it works by applying 'reductions'.
    """

    bits_length = (len(A) + len(B))

    # create a list of lists, with slots for all the weights (bit-positions)
    bits = [[] for weight in range(bits_length)]

    # AND every bit of A with every bit of B (N^2 results) and store by "weight" (bit-position)
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            bits[i+j].append(a & b)

    return reducer(bits, bits_length, adder_func)



def __test_wallace_timing():
    # Legacy code, just for internal use
    x = 4
    a, b = Input(x, "a"), Input(x, "b")
    product = Output(2*x, "product")

    product <<= tree_multiplier(a, b)

    timing_map = timing_analysis()

    print_max_length(timing_map)


if __name__ == "__main__":
    main()
