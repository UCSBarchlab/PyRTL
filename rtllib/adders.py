import sys
sys.path.append("..")
import pyrtl
from pyrtl import *
import libutils


def main():
    print "You should be looking at the test case folder"


def kogge_stone(A, B, cin=0):
    """
    Creates a Kogge-Stone adder given two inputs
    :param A, B: The two Wirevectors to add up (bitwidths don't need to match)
    :param cin: An optimal carry Wirevector or value
    :return: a Wirevector representing the output of the adder

    The Kogge-Stone adder is a fast tree-based addder with O(log(n))
    propagation delay, useful for performance critical designs. However,
    it has O(n log(n)) area usage, and large fan out.
    """
    A, B = libutils.match_bitwidth(A, B)

    prop_bits = [a ^ b for a, b in zip(A, B)]
    prop_orig = prop_bits[:]  # just making a copy
    gen_bits = [a & b for a, b in zip(A, B)]
    prop_dist = 1

    # creation of the carry calculation
    while prop_dist < len(A):
        for i in reversed(range(prop_dist, len(A))):
            prop_old = prop_bits[i]
            gen_bits[i] = gen_bits[i] | (prop_old & gen_bits[i - prop_dist])
            if i >= prop_dist*2:  # to prevent creating unnecessary nets and wires
                prop_bits[i] = prop_old & prop_bits[i - prop_dist]
        prop_dist *= 2

    # assembling the addition result
    gen_bits.insert(0, as_wires(cin))  # preparing the cin (and conveniently shifting the gen bits)
    result = concat(*[g ^ p for g, p in reversed(zip(gen_bits, prop_orig))])  # need MSB first
    result = concat(gen_bits[-1], result)  # have to add the Most Significant Bit from gen somehow
    return result


if __name__ == "__main__":
    main()
