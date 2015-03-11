import sys
sys.path.append("..")
from pyrtl import *


def barrel_shifter(bitwidth, logbitwidth, shiftIn, bitIn, direction, amount):
    '''Create a barrel shifter that operates on data of width bitwidth.
    logbitwidth is the number of bits specifying the shift (e.g. 5 for 32-bit.)
    shiftIn is the input wire; bitIn is the 1-bit wire giving the value to shift in.
    direction should be 1 for left-shift and 0 for right.
    amount is the number of bits to shift.'''

    val = shiftIn
    appendval = bitIn
    print len(val)
    print len(appendval)
    for i in range(logbitwidth):
        shamt = pow(2, i)
        newval = mux(direction, truecase=val[:-shamt], falsecase=val[shamt:])
        print len(newval)
        newval = mux(direction, truecase=concat(newval, appendval), 
                     falsecase=concat(appendval, newval))
        val = mux(amount[i], truecase=newval, falsecase=val)
        appendval = concat(appendval, appendval)
        print len(val)
        print len(appendval)

    return val
