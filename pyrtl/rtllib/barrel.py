from __future__ import absolute_import
import pyrtl
import math


def barrel_shifter(shift_in, bit_in, direction, shift_dist, wrap_around=0):
    """
    Create a barrel shifter that operates on data based on the wire width

    :param shift_in: the input wire
    :param bit_in: the 1-bit wire giving the value to shift in
    :param direction: a one bit WireVector representing shift direction
        0 = shift down, 1 = shift up.
    :param shift_dist: WireVector representing offset to shift
    :param wrap_around: ****currently not implemented*****
    :return: shifted WireVector
    """
    # Implement with logN stages pyrtl.muxing between shifted and un-shifted values

    val = shift_in
    append_val = bit_in
    log_length = int(math.log(len(shift_in)-1, 2))  # note the one offset

    if len(shift_dist) > log_length:
        print('Warning: for barrel shifter, the shift distance wirevector '
              'has bits that are not used in the barrel shifter')

    for i in range(min(len(shift_dist), log_length)):
        shift_amt = pow(2, i)  # stages shift 1,2,4,8,...
        newval = pyrtl.select(direction, truecase=val[:-shift_amt], falsecase=val[shift_amt:])
        newval = pyrtl.select(direction, truecase=pyrtl.concat(newval, append_val),
                              falsecase=pyrtl.concat(append_val, newval))  # Build shifted value
        # pyrtl.mux shifted vs. unshifted by using i-th bit of shift amount signal
        val = pyrtl.select(shift_dist[i - 1], truecase=newval, falsecase=val)
        append_val = pyrtl.concat(append_val, append_val)

    return val
