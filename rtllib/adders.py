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

    The Kogge-Stone adder is a fast tree-based adder with O(log(n))
    propagation delay, useful for performance critical designs. However,
    it has O(n log(n)) area usage, and large fan out.
    """
    A, B = libutils.match_bitwidth(A, B)

    prop_orig = A ^ B
    prop_bits = [i for i in prop_orig]
    gen_bits = [i for i in A & B]
    prop_dist = 1

    # creation of the carry calculation
    while prop_dist < len(A):
        for i in reversed(range(prop_dist, len(A))):
            prop_old = prop_bits[i]
            gen_bits[i] = gen_bits[i] | (prop_old & gen_bits[i - prop_dist])
            if i >= prop_dist*2:  # to prevent creating unnecessary nets and wires
                prop_bits[i] = prop_old & prop_bits[i - prop_dist]
        prop_dist *= 2

    # assembling the result of the addition
    gen_bits.insert(0, as_wires(cin))  # preparing the cin (and conveniently shifting the gen bits)
    return concat(*reversed(gen_bits)) ^ prop_orig


def one_bit_add(a, b, cin):
    assert len(a) == len(b) == 1  # len returns the bitwidth
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum, cout


def ripple_add(a, b, cin=0):
    a, b = libutils.match_bitwidth(a, b)

    def ripple_add_partial(a, b, cin=0):  # this actually makes less s anc c blocks
        assert len(a) == len(b)
        if len(a) == 1:
            sumbits, cout = one_bit_add(a, b, cin)
        else:
            lsbit, ripplecarry = one_bit_add(a[0], b[0], cin)
            msbits, cout = ripple_add_partial(a[1:], b[1:], ripplecarry)
            sumbits = pyrtl.concat(msbits, lsbit)
        return sumbits, cout

    sumbits, cout = ripple_add_partial(a, b, cin)
    return concat(cout, sumbits)


if __name__ == "__main__":
    main()
