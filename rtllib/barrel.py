import sys
sys.path.append("..")
from pyrtl import *


def barrel_shifter(bitwidth, logbitwidth, shiftIn, bitIn, direction, amount):
    '''Create a barrel shifter that operates on data of width bitwidth.
    logbitwidth is the number of bits specifying the shift (e.g. 5 for 32-bit.)
    shiftIn is the input wire; bitIn is the 1-bit wire giving the value to shift in.
    direction should be 1 for left-shift and 0 for right.
    amount is the number of bits to shift.

    bitwidth and logbitwidth are design-time parameters (python ints).
    The remaining inputs are pyrtl wires.'''

    # Implement with logN stages muxing between shifted and un-shifted values
    val = shiftIn
    appendval = bitIn
    for i in range(logbitwidth):
        shamt = pow(2, i)  # stages shift 1,2,4,8,...
        newval = mux(direction, truecase=val[:-shamt], falsecase=val[shamt:])
        newval = mux(direction, truecase=concat(newval, appendval),
                     falsecase=concat(appendval, newval))  # Build shifted value for this stage
        # mux shifted vs. unshifted by using i-th bit of shift amount signal
        val = mux(amount[i], truecase=newval, falsecase=val)
        appendval = concat(appendval, appendval)

    return val
