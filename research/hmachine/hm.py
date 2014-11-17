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

    test_argregs()

def buildAll():
    # Build list of possible data sources
    localsOut = WireVector(width, "localsOut")
    argsOut =  WireVector(width, "argsOut")
    heapOut =  WireVector(width, "heapOut")
    immediate =  WireVector(width, "instrImmediate")
    retRegOut = WireVector(width, "returnRegisterOut")
    srcList = [localsOut, argsOut, heapOut, immediate, retRegOut] + [Const(0)] * 3
    dataSrcSelect = WireVector(3, "dataSourceSelect")
    srcMux = muxtree(srcList, dataSrcSelect)

    # Registers
#    PC = Register(textspace, "ExecutionPointer")  # addr of next instr
#    envclo = Register(namespace, "CurrentClosure")  # name of closure we're in now
#    nlocalsreg = Register(localspace, "NumberLocals")  # number of locals bound so far
    nargsreg = Register(argspace, "NumberArgs")  # number of args bound so far
#    nfreevarreg = Register(freevarspace, "NumberFreeVars")  # number of freevars bound so far
#    hp = Register(heapspace, "HeapPointer")  # heap pointer (next free addr)
#    sp = Register(evalstackspace, "EvalStackPointer")  # evaluation stack pointer
    rr = Register(width, "ReturnRegister")  # return register

    # Argument Registers
    argR = WireVector(width, "argsReadData")
    argW = WireVector(width, "argsWriteData")
    argW <<= srcMux
    ctrl_argwe = WireVector(1, "ctrl_argsWriteEnable")
    argRaddr = WireVector(argspace, "argsReadAddr")
    argWaddr = WireVector(argspace, "argsWriteAddr")
    argWaddr <<= nargsreg  # write to next free arg reg
    ctrl_argSwitch = WireVector(1, "ctrl_argsSwitch")
    arg1 = WireVector(width, "argreg1")
    arg2 = WireVector(width, "argreg2")
    argregs(ctrl_argwe, argWaddr, argW, argRaddr, argR, ctrl_argSwitch, arg1, arg2)
    argsOut <<= argR  # send output to srcMux

    # Update number of arguments
    cond = ConditionalUpdate()
    with cond(ctrl_argSwitch):  # Clear reg on scope change
        nargsreg.next <<= 0
    with cond(ctrl_argwe):  # increment on control signal
        nargsreg.next <<= nargsreg + 1

    # Instantiate ALU; connect to first two args
    ctrl_ALUop = WireVector(4, "ctrl_ALUcontrol")
    ALUout = WireVector(width, "ALUout")
    makeALU(ctrl_ALUop, arg1, arg2, ALUout)

    # Return Register update
    ctrl_alu2rr = WireVector(1, "ctrl_ALU-to-returnReg")
    ctrl_loadrr = WireVector(1, "ctrl_loadRR")
    with cond(ctrl_loadrr):  # signal to modify return reg
        with cond(ctrl_alu2rr):  # load rr with ALU output
            rr.next <<= ALUout
        with cond():  # if not loading ALU, load from srcMux
            rr.next <<= srcMux
    retRegOut <<= rr  # send result to srcMux

    test_args_alu_rr()


    pyrtl.working_block().sanity_check()


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

    #    help(MemBlock.EnabledWrite)
    #    help(MemBlock)

    #block[i] = MemBlock.EnabledWrite(data, en)

    args1 = MemBlock(width, argspace, name="args1")
    args2 = MemBlock(width, argspace, name="args2")

    # Output
    #read1 = WireVector(width, "args1read")
    #read2 = WireVector(width, "args2read")
    read1 = args1[raddr]
    read2 = args2[raddr]
    rdata <<= mux(state, falsecase=read2, truecase=read1)  # mux for output
    # Additional ports to output arg0 and arg1; need for primitive (ALU) ops
    reg1 <<= mux(state, falsecase=args2[Const("3'b0")], truecase=args1[Const("3'b0")])
    reg2 <<= mux(state, falsecase=args2[Const("3'b1")], truecase=args1[Const("3'b1")])

    # Input
    EW = MemBlock.EnabledWrite
    #args1[waddr] = EW(wdata, enable=(we & (state == 0)))
    #args2[waddr] = EW(wdata, enable=(we & (state == 1)))
    args1[waddr] = EW(wdata, enable=we)
    args2[waddr] = EW(wdata, enable=we)

    # Handle state flips
    state.next <<= mux(flipstate, falsecase=state, truecase=~state)

def test_argregs():

    we = Input(1, 'we')
    wdata = Input(width, 'wdata')
    raddr = Input(argspace, 'raddr')
    rdata = Output(width, 'rdata')
    argswitch = Input(1, 'argSwitch')
    arg1 = Output(width, 'arg1')
    arg2 = Output(width, 'arg2')
    #nargsreg = Register(argspace, 'nargs')
    nargsreg = Input(argspace, 'nargs')

    # Update number of arguments
    '''
    cond = ConditionalUpdate()
    with cond(argswitch):  # Clear reg on scope change
        nargsreg.next <<= 0
    with cond(we):  # increment on control signal
        nargsreg.next <<= nargsreg + 1
    '''

    # connect
    argregs(we, nargsreg, wdata, raddr, rdata, argswitch, arg1, arg2)

    pyrtl.working_block().sanity_check()

    # simulate
    # Write data 1-5, switch, then read out all regs
    # Switch again, read out all data
    # Write new dta, switch while writes ongoing, read out all regs
    # switch, read out all regs
    simvals = {
        we:        "0011111111000000000000000",
        nargsreg:  "0001234567000000000000000",
        wdata:     "0012345678999000000000000",
        raddr:     "0000000000000000012345670",
        argswitch: "0000000000000010000000000"
    }

    '''
    simvals = {
        we:        "0111110000000000000000011111111000000000000000000",
        wdata:     "0123450000000000000000098765432000000000000000000",
        raddr:     "0000000123456700123456755555555012345670012345670",
        argswitch: "0000010000000010000000000000100000000001000000000"
    }
    '''
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)
    for cycle in range(len(simvals[we])):
        sim.step({k:int(v[cycle]) for k,v in simvals.items()})
    sim_trace.render_trace()


# ######################################################################
#     Primitive Ops Unit (a.k.a. ALU)
# ######################################################################
def makeALU(control, op1, op2, out):

    out <<= switch(control, {
        "3'b000": op1 & op2,
        "3'b001": op1 | op2,
        "3'b010": op1 + op2,
        "3'b110": op1 - op2,
        "3'b111": op1 < op2,
        None: 0
    })    


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


def switch(ctrl, logic_dict):
    """ switch finds the matching key in logic_dict and returns the value.                                                            
    The case "None" specifies the default value to return when there is no
    match.  The logic will be a simple linear mux tree of comparisons between
    the key and the ctrl, selecting the appropriate value
    """

    working_result = logic_dict[None]
    for case_value in logic_dict:
        if case_value is None:
            continue
        working_result = mux(
            ctrl == case_value,
            falsecase=working_result,
            truecase=logic_dict[case_value])
    return working_result

def muxtree(vals, select):
    """Recursively build a tree of muxes. Takes a list of wires and a select wire; the list
    should be ordered such that the value of select is the index of the wire passed through."""
    if len(select) == 1:
        if len(vals) != 2:
            raise ValueError("Mismatched values; select should have logN bits")
        out = WireVector(max([len(x) for x in vals]))
        out <<= mux(select, falsecase = vals[0], truecase = vals[1])
        return out
    else:
        # mux each pair of values into new wires of len N/2, recursively call
        new = []
        for i in range(len(vals)/2):
            new.append(mux(select[0], falsecase=vals[2*i], truecase=vals[2*i+1]))
        return muxtree(new, select[1:])



def test_args_alu_rr():

    block = pyrtl.working_block()
    for name in ['heapOut', 'localsOut']:
        temp = block.get_wirevector_by_name(name)
        temp <<= 0

    ctrl_ALUcontrol = block.get_wirevector_by_name("ctrl_ALUcontrol")
    ctrl_ALUcontrol <<= 2
    dsrc = block.get_wirevector_by_name("dataSourceSelect")
    dsrc <<= 3  # choose immediate as sources

    # get all signals to control
    dctrl_argsSwitch = block.get_wirevector_by_name("ctrl_argsSwitch")
    dargsReadAddr = block.get_wirevector_by_name("argsReadAddr")
    dctrl_argswe = block.get_wirevector_by_name("ctrl_argsWriteEnable")
    dctrl_ALU2rr = block.get_wirevector_by_name("ctrl_ALU-to-returnReg")
    dctrl_loadRR = block.get_wirevector_by_name("ctrl_loadRR")
    dimm = block.get_wirevector_by_name("instrImmediate")

    # declare inputs, connect to signals
    ctrl_argsSwitch = Input(len(dctrl_argsSwitch))
    dctrl_argsSwitch <<= ctrl_argsSwitch
    argsReadAddr = Input(len(dargsReadAddr))
    dargsReadAddr <<= argsReadAddr
    ctrl_argswe = Input(len(dctrl_argswe))
    dctrl_argswe <<= ctrl_argswe
    ctrl_ALU2rr = Input(len(dctrl_ALU2rr))
    dctrl_ALU2rr <<= ctrl_ALU2rr
    ctrl_loadRR = Input(len(dctrl_loadRR))
    dctrl_loadRR <<= ctrl_loadRR
    imm = Input(len(dimm))
    dimm <<= imm

    valstring = {
        ctrl_ALU2rr     : [0,0,0,0,0], 
        argsReadAddr    : [0,0,0,0,0], 
        ctrl_loadRR     : [0,0,0,0,0], 
        ctrl_argswe     : [1,1,1,1,1], 
        ctrl_argsSwitch : [0,0,0,0,0],
        imm             : [1,2,3,4,5]
    }

    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)
    for cycle in range(len(valstring[imm])):
        sim.step({k:v[cycle] for k,v in valstring.items()})
    sim_trace.render_trace()


if __name__ == "__main__":
    main()
