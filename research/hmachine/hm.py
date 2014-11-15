import sys
import numpy as np
sys.path.append("../..")
import pyrtl
from pyrtl import *

# Machine Parameters
argspace = 3  # number of bits to specify arg number
nArgs = pow(2, argspace)  # maximum number of function arguments
localspace = 4  # number of bits to specify local var number
nLocals = pow(2, localspace)  # maximum number of local vars in a function
freevarspace = 8  # number of bits to specify free variable number
nfreevars = pow(2, freevarspace)  # maximum number of free variables
width = 32  # machine width

# Memory sizes
namespace = 10  # number of bits used in IDs
ntablesize = pow(2, namespace)  # possible number of IDs (currently just 1 memory block)
evalstackspace = 15  # number of bits in eval stack addresses
evalstacksize = pow(2, evalstackspace)
heapspace = 16  # number of bits in heap addresses
heapsize = pow(2, heapspace)  # number of words in heap
textspace = 15  # number of bits in text memory addresses (a.k.a. immortal heap)
textsize = pow(2, textspace)  # number of words of immortal heap memory

def main():

    # Registers
    PC = register(textspace, "ExecutionPointer")  # addr of next instr
    envclo = register(namespace, "CurrentClosure")  # name of closure we're in now
    nlocalsreg = register(localspace, "NumberLocals")  # number of locals bound so far
    nargsreg = register(argspace, "NumberArgs")  # number of args bound so far
    nfreevarreg = register(freevarspace, "NumberFreeVars")  # number of freevars bound so far
    hp = register(heapspace, "HeapPointer")  # heap pointer (next free addr)
    sp = register(svalstackspace "EvalStackPointer")  # evaluation stack pointer
    rr = register(width, "ReturnRegister")  # return register

    # Argument Registers
    argR = WireVector(width, "argsReadData")
    argW = WireVector(width, "argsWriteData")
    argwe = WireVector(1, "argsWriteEnable")
    argRaddr = WireVector(argspace, "argsReadAddr")
    argWaddr = WireVector(argspace, "argsWriteAddr")
    argWaddr <<= nargsreg  # write to next free arg reg
    argSwitch = WireVector(1, "argsSwitch")
    arg1 = WireVector(width, "argreg1")
    arg2 = WireVector(width, "argreg2")
    argregs(argwe, argsWaddr, argW, argRaddr, argR, argSwitch, arg1, arg2)

# ######################################################################
#     Instruction Decode
# ######################################################################


# ######################################################################
#     Argument Registers
# ######################################################################
def argregs(we, waddr, wdata, raddr, rdata, flipstate, reg1, reg2):
    # Two banks of registers, one bit keeping track of which is read vs write

    # Handle I/O based on internal state
    state = Register(1, 'argstate')
    # In each state, one is read and one is written; on flip, write becomes read and
    #  read is cleared
    # state == 0: args1 is writeargs, args2 is readargs
    # state == 1: args1 is readargs, args2 is writeargs

    args1 = MemBlock(width, argspace, name="args1")
    args2 = MemBlock(width, argspace, name="args2")

    # Output
    #read1 = WireVector(width, "args1read")
    #read2 = WireVector(width, "args2read")
    read1 = args1[raddr]
    read2 = args2[raddr]
    rdata <<= mux(state, falsecase=read2, truecase=read1)  # mux for output
    # Additional ports to output arg0 and arg1; need for primitive (ALU) ops
    reg1 <<= mux(state, falsecase=args2[0], truecase=args1[0])
    reg2 <<= mux(state, falsecase=args2[1], truecase=args1[1])

    # Input
    c = ConditionalUpdate()
    with c(we & (state == 0)):
        args1[waddr] = wdata
    with c(we & (state == 1)):
        args2[waddr] = wdata
    
    # Handle state flips
    with c(flipstate):
        state.next <<= ~state
        
    pyrtl.working_block().sanity_check()

# ######################################################################
#     Primitive Ops Unit (a.k.a. ALU)
# ######################################################################












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
