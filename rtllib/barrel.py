import sys
sys.path.append("..")
from pyrtl import *
import math


def barrel_shifter(shift_in, bit_in, direction, shift_dist, wrap_around=0):
    """
    Create a barrel shifter that operates on data based on the wire width
    :param shift_in:the input wire;
    :param bit_in: the 1-bit wire giving the value to shift in.
    :param direction: direction is a one bit wirevector representing shift direction
        0 = shift down, 1 = shift up.
    :param shift_dist: wirevector representing offset to shift
    :param wrap_around: ****currently not implemented*****
    :return: shifted wirevector
    """
    # Implement with logN stages muxing between shifted and un-shifted values

    val = shift_in
    appendval = bit_in
    log_length = int(math.log(len(shift_in)-1, 2))  # note the one offset

    if len(shift_dist) > log_length:
        print "Warning: for barrel shifter, the shift distance wirevector " \
              "has bits that are not used in the barrel shifter"

    for i in range(min(len(shift_dist), log_length)):
        shift_amt = pow(2, i)  # stages shift 1,2,4,8,...
        newval = mux(direction, truecase=val[:-shift_amt], falsecase=val[shift_amt:])
        newval = mux(direction, truecase=concat(newval, appendval),
                     falsecase=concat(appendval, newval))  # Build shifted value for this stage
        # mux shifted vs. unshifted by using i-th bit of shift amount signal
        val = mux(shift_dist[i-1], truecase=newval, falsecase=val)
        appendval = concat(appendval, appendval)

    return val
