import sys
sys.path.append("..")
import pyrtl
from pyrtl import *
import libutils


def main():
    print "You should be looking at the test case folder"


def kogge_stone(A, B):
    A, B = libutils.match_bitwidth(A, B)

    prop_bit = [a ^ b for a, b in zip(A, B)]
    prop_orig = prop_bit[:]  # just making a copy
    gen_bit = [a & b for a, b in zip(A, B)]
    prop_dist = 1

    # creation of the carry calculation
    while prop_dist < len(A):
        for i in range(len(A) - 1, prop_dist - 1, -1):
            prop_old = prop_bit[i]
            gen_old = gen_bit[i]
            gen_bit[i] = gen_old | (prop_old & gen_bit[i - prop_dist])
            if i >= prop_dist*2:  # to prevent creating unnecessary nets and wires
                prop_bit[i] = prop_old & prop_bit[i - prop_dist]
        prop_dist *= 2

    # assembling the addition result
    result = prop_orig[0]
    for i in range(1, len(A)):
        result = concat(gen_bit[i-1] ^ prop_orig[i], result)  # prepending the middle bits
    result = concat(gen_bit[len(A)-1], result)
    return result


if __name__ == "__main__":
    main()
