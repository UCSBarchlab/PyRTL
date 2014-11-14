import sys
import numpy as np
sys.path.append("../..")
import pyrtl
from pyrtl import *

# Machine Parameters
nArgs = 8
lognargs = int(np.log2(nArgs))
nLocals = 16
width = 32

def main():
    # ######################################################################
    #     Instruction Decode
    # ######################################################################


    # ######################################################################
    #     Argument Registers
    # ######################################################################

    # Two banks of registers, one bit keeping track of which is read vs write
    # One reg tracks number of args written

    # Input/Output
    write = Input(1, 'write')  # write reg number is tracked internally
    writedata = Input(width, 'writedata')
    writeaddr = Input(lognargs, 'writeaddr')
    readaddr = Input(lognargs, 'readaddr')
    readdata = Output(width, 'readdata')
    flipstate = Input(1, 'flipargstate')

    # Handle I/O based on internal state
    state = Register(1, 'argstate')

    # Register banks
    # In each state, one is read and one is written; on flip, write becomes read and
    #  read is cleared
    # state == 0: args1 is writeargs, args2 is readargs
    # state == 1: args1 is readargs, args2 is writeargs
    #help(wire)
    read1 = WireVector(width, "argsbank1")
    read2 = WireVector(width, "argsbank2")
    
    args1 = RegisterFile(width, nArgs, writeaddr, writedata, readaddr, read1, 
                         (state == 0) & write, (state == 1) & flipstate, name='args1-')
    args2 = RegisterFile(width, nArgs, writeaddr, writedata, readaddr, read2, 
                         (state == 1) & write, (state == 0) & flipstate, name='args2-')
    # mux for output
    readdata <<= mux(state, falsecase=read2, truecase=read1)
    
    # Handle state flips
    c = ConditionalUpdate()
    with c(flipstate):
        state.next <<= ~state
        
    pyrtl.working_block().sanity_check()


class RegisterFile:

    def __init__(self, width, nregs, waddr, wdata, raddr, rdata, we, reset, name=''):

        # declare regs
        regs = []
        for i in range(nregs):
            regs.append(Register(width, name+"_"+str(i)))
        c = ConditionalUpdate()
        # all have reset; if addr matches and write enable high, take value
        for i in range(nregs):
            with c(reset):
                regs[i].next <<= 0
            with c(we & (waddr == i)):
                regs[i].next <<= wdata
        
        # use tree of muxes to choose output
        rdata <<= muxtree(regs, raddr)

        self.regs = regs

def muxtree(vals, select):
    if len(select) == 1:
        if len(vals) != 2:
            raise ValueError("Mismatched values; select should have logN bits")
        out = WireVector(1)
        out <<= mux(select, falsecase = vals[0], truecase = vals[1])
        return out
    else:
        # mux each pair of values into new wires of len N/2, recursively call
        new = []
        for i in range(len(vals)/2):
            new.append(mux(select[0], falsecase=vals[2*i], truecase=vals[2*i+1]))
        return muxtree(new, select[1:])


if __name__ == "__main__":
    main()
