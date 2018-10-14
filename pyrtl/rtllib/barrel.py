from __future__ import absolute_import
import pyrtl
import math


def barrel_shifter(bits_to_shift, bit_in, direction, shift_dist, wrap_around=0):
    """ Create a barrel shifter that operates on data based on the wire width.

    :param bits_to_shift: the input wire
    :param bit_in: the 1-bit wire giving the value to shift in
    :param direction: a one bit WireVector representing shift direction
        (0 = shift down, 1 = shift up)
    :param shift_dist: WireVector representing offset to shift
    :param wrap_around: ****currently not implemented****
    :return: shifted WireVector
    """
    from pyrtl import concat, select  # just for readability

    if wrap_around != 0:
        raise NotImplementedError

    # Implement with logN stages pyrtl.muxing between shifted and un-shifted values
    final_width = len(bits_to_shift)
    val = bits_to_shift
    append_val = bit_in

    for i in range(len(shift_dist)):
        shift_amt = pow(2, i)  # stages shift 1,2,4,8,...
        if shift_amt < final_width:
            newval = select(direction,
                            concat(val[:-shift_amt], append_val),  # shift up
                            concat(append_val, val[shift_amt:]))  # shift down
            val = select(shift_dist[i],
                         truecase=newval,  # if bit of shift is 1, do the shift
                         falsecase=val)  # otherwise, don't
            # the value to append grows exponentially, but is capped at full width
            append_val = concat(append_val, append_val)[:final_width]
        else:
            # if we are shifting this much, all the data is gone
            val = select(shift_dist[i],
                         truecase=append_val,  # if bit of shift is 1, do the shift
                         falsecase=val)  # otherwise, don't

    return val
