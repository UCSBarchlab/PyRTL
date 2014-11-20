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
datawidth = 32
width = datawidth + 1   # machine width
primtag_bits = 0
data_bits = slice(1, datawidth)

# Memory sizes
namespace = 10  # number of bits used in IDs
ntablesize = pow(2, namespace)  # possible number of IDs (currently just 1 memory block)
evalstackspace = 15  # number of bits in eval stack addresses
evalstacksize = pow(2, evalstackspace)
heapspace = 16  # number of bits in heap addresses
heapsize = pow(2, heapspace)  # number of words in heap
textspace = 15  # number of bits in text memory addresses (a.k.a. immortal heap)
textsize = pow(2, textspace)  # number of words of immortal heap memory
itablespace = 10  # number of bits in info table memory address

# Info Table structure
itable_entrycode_bits = slice(0,15)
itable_nvars_bits = slice(15,22)
itable_nptrs_bits = slice(22,29)
itable_arity_bits = slice(29,32)

# Instruction structure
instr_opcode_bits = slice(27,32)
instr_dsrc_bits = slice(24,27)
instr_name_bits = slice(0,localspace)
if namespace > 24:
    raise ValueError("Size of names cannot fit in instruction.")
instr_argindex_bits = slice(0, argspace)
instr_freevarindex_bits = slice(0, freevarspace)
instr_litpattern_bits = slice(8,24)
instr_conitable_bits = slice(8,8+itablespace)
if itablespace > 16:
    raise ValueError("Size of instruction table address space cannot fit in instruction.")
instr_itable_bits = slice(0, itablespace)
instr_nInstrs_bits = slice(0,8)
instr_imm_bits = slice(0,24)

# Instruction opcodes/varietals
OPCODES = {
    "arg"         : Const(0 , bitwidth=5),
    "freevar"     : Const(1 , bitwidth=5),
    "alias"       : Const(2 , bitwidth=5),
    "let_closure" : Const(3 , bitwidth=5),
    "case"        : Const(4 , bitwidth=5),
    "lit_pattern" : Const(5 , bitwidth=5),
    "con_pattern" : Const(6 , bitwidth=5),
    "else_pattern": Const(7 , bitwidth=5),
    "call"        : Const(8 , bitwidth=5),
    "enter"       : Const(9 , bitwidth=5),
    "ret"         : Const(10 , bitwidth=5)
}

# Continuation structure
cont_nLocals_bits = slice(0,localspace)
cont_envclo_bits = slice(localspace,localspace+namespace)
cont_exptr_bits = slice(localspace+namespace,textspace)
'''
# Mux control constants
PC_INC = Const("2'b00")
PC_NINSTRS = Const("2'b01")
PC_ITABLE = Const("2'b10")
PC_CONTINUATION = Const("2'b11")
SRC_LOCALS = Const("3'b000")
SRC_ARGS = Const("3'b001")
SRC_HEAP = Const("3'b010")
SRC_IMM = Const("3'b011")
SRC_RR = Const("3'b100")
SRC_ELEM = Const("3'b101")
SRC_NAME = Const("3'b110")
SRC_STACK = Const("3'b111")
'''
def main():

    #test_argregs()
    #test_args_alu_rr()
    #test_evalstack()
    #test_localsregs()
    test_table_heap()
    #buildAll()
    

def buildAll():

    # Build source mux
    # On src_elem (use component of matched constructor), we use contents of RR as address in
    #  name table, address a free variable of the objet in the heap, and send that through the srcMux
    localsOut = WireVector(width, "localsOut")
    argsOut =  WireVector(width, "argsOut")
    heapOut =  WireVector(width, "heapOut")
    immediate =  WireVector(width, "instrImmediate")
    retRegOut = WireVector(width, "returnRegisterOut")
    newName = WireVector(namespace, "NewName")
    evalStackOut = WireVector(width, "evalStackOut")
    dSources = {
        SRC_LOCALS : localsOut,
        SRC_ARGS : argsOut,
        SRC_HEAP : heapOut,
        SRC_IMM : immediate,
        SRC_RR : retRegOut,
        SRC_ELEM : heapOut,
        SRC_NAME : newName,
        SRC_STACK : evalStackOut,
        None : 0
    }    
    dataSrcSelect = WireVector(3, "dataSourceSelect")
    srcMux = switch(dataSrcSelect, dSources)

    # other needed wires
    iheapOut = WireVector(width, "InstrHeapOut")
    itableOut = WireVector(32, "InstrTableOut")
    nLocalsOut = WireVector(localspace, "nLocals")
    exptr = WireVector(textspace, "exptr")
    envcloOut = WireVector(namespace, "CurEnvClosureRegOut")
    continuation = concat(exptr, envcloOut, nLocalsOut)
    cont_nLocals = evalStackOut[0:localspace]
    cont_envclo = evalStackOut[localspace:localspace+namespace]
    cont_exptr = evalStackOut[localspace+namespace:textspace]
    closureTable = heapOut[0:itablespace]

    # Name each component of info table
    itable_arity = itableOut[itable_arity_bits]
    itable_nptrs = itableOut[itable_nptrs_bits]
    itable_nvars = itableOut[itable_nvars_bits]
    itable_entryCode = itableOut[itable_entrycode_bits]

    # Name each possible section of instruction
    instr_opcode = iheapOut[instr_opcode_bits]
    instr_dsrc = iheapOut[instr_dsrc_bits]
    instr_name = iheapOut[instr_name_bits]
    instr_argindex = iheapOut[instr_argindex_bits]
    instr_freevarindex = iheapOut[instr_freevarindex_bits]
    instr_litpattern = iheapOut[instr_litpattern_bits]
    instr_conitable = iheapOut[instr_conitable_bits]
    instr_itable = iheapOut[instr_itable_bits]
    instr_nInstrs = iheapOut[instr_nInstrs_bits]
    instr_imm = iheapOut[instr_imm_bits]

    # Declare control signals
    ctrl_argwe = WireVector(1, "ctrl_argsWriteEnable")  # write value into args reg
    ctrl_argSwitch = WireVector(1, "ctrl_argsSwitch")  # switch read & write regs
    ctrl_ALUop = WireVector(8, "ctrl_ALUcontrol")  # alu operation code
    ctrl_alu2rr = WireVector(1, "ctrl_ALU-to-returnReg")  # if 1 ? RR <<= ALU : RR <<= srcMux
    ctrl_loadrr = WireVector(1, "ctrl_loadRR")  # load muxed value into return register
    ctrl_exptrsrc = WireVector(2, "ctrl_exptrSource")  # choose source of exptr (see mux constants)
    ctrl_exptrload = WireVector(1, "ctrl_exptrLoad")  # load muxed value into exptr
    ctrl_spDecr = WireVector(1, "ctrl_evalStackDecrement")  # decrement the eval stack pointer
    ctrl_clearLocals = WireVector(1, "ctrl_clearLocals")  # sp <<= sp - nLocals; nLocals <<= 0
    ctrl_stackWrite = WireVector(1, "ctrl_stackWrite")  # write value onto top of eval stack
    ctrl_writeContinuation = WireVector(1, "ctrl_writeContinuation")  # write cont onto stack
    ctrl_inclocals = WireVector(1, "ctrl_incrementLocals")  # nLocals <<= nLocals + 1
    ctrl_declocals = WireVector(1, "ctrl_decrementLocals")  # nLocals <<= nLocals - 1
    ctrl_loadcont = WireVector(1, "ctrl_loadContinuation")  # load cont. into nLocals and envclo
    ctrl_writelocal = WireVector(1, "ctrl_writeLocalReg")  # locals[nLocals] <<= value
    ctrl_enter = WireVector(1, "ctrl_enterNamedClosure")  # envclo <<= locals[index]; nTable addr=loc
    ctrl_inspectElement = WireVector(1, "ctrl_inspectConsElement")  # nameTable addr = return reg
    ctrl_writeFreevar = WireVector(1, "ctrl_writeFreevar")  # heap[hp] <<= evalstackOut; hp++
    ctrl_allocWriteName = WireVector(1, "ctrl_allocWriteName")  # nTable[next]<<=hp;heap[hp]<<=itable
    ctrl_aliasName = WireVector(1, "ctrl_aliasName")  # nTable[next] <<= nTable[value]
    ctrl_aliasPrim = WireVector(1, "ctrl_aliasPrim")  # nTable[next] <<= value
    ctrl_addrFreevar = WireVector(1, "ctrl_addressFreevar") # heapAddr = nTable + index + 1

    args_alu_rr(srcMux, instr_argindex, ctrl_argwe, ctrl_argSwitch, ctrl_ALUop, ctrl_alu2rr,
            ctrl_loadrr, argsOut, retRegOut)
    itable_exptr_iheap(closureTable, ctrl_exptrsrc, ctrl_exptrload, instr_nInstrs, srcMux, 
            itableOut, iheapOut, exptr)
    evalstack(ctrl_spDecr, ctrl_clearLocals, nLocalsOut, ctrl_stackWrite, 
            ctrl_writeContinuation, continuation, srcMux, evalStackOut)
    localsregs(ctrl_inclocals, ctrl_declocals, ctrl_clearLocals, ctrl_loadcont, srcMux,
               instr_name, localsOut, ctrl_writelocal, ctrl_enter, envcloOut, nLocalsOut)
    table_heap(envcloOut, retRegOut, localsOut, ctrl_enter, ctrl_inspectElement, srcMux, newName,
            ctrl_writeFreevar, ctrl_allocWriteName, instr_freevarindex, heapOut, instr_itable, evalStackOut,
               ctrl_aliasName, ctrl_aliasPrim, ctrl_addrFreevar)

    pyrtl.working_block().sanity_check()

# ######################################################################
#     Instruction Decode
# ######################################################################
def instrdecode():
    '''
    ALL INSTRUCTIONS:
    arg_*
    freevar_*
    alias_*
    let_closure
    case
    lit_pattern
    con_pattern
    else_pattern
    call
    enter
    ret

    ALL CONTROL SIGNALS:
    ctrl_argSwitch # switch read & write regs
    ctrl_loadrr # load muxed value into return register
    ctrl_stackWrite # write value onto top of eval stack
    ctrl_writelocal # locals[nLocals] <<= value
    ctrl_inclocals # nLocals <<= nLocals + 1

    # NEEDED: separate clearLocals into two signals; when entering case expression, need to clear nLocals reg without affecting locals on stack
    # Add nlocalsIsZero output to locals module for state machine termination condition
    # store nvars from itable in local register on alloc machine entrance
    # work out allocation and restoration state machines
    # Refactor remaining signals to use by-signal style instead of by-instruction (can't mix the two)
    # Add isConstructor tag to itable
    # Add block somewhere that produces isEvaluated on RR
    # For each instruction, check definition in simulator, then walk through all control signals to verify operation
    ctrl_declocals # nLocals <<= nLocals - 1
    ctrl_clearLocals # sp <<= sp - nLocals; nLocals <<= 0

    ctrl_alias # nTable[next] <<= nTable[value] or value
    intrl_enterAlloc  # enter the allocation state machine
    ctrl_allocWriteName # nTable[next]<<=hp;heap[hp]<<=itable
    ctrl_inspectElement # nameTable addr = return reg
    ctrl_enter # envclo <<= locals[index]; nTable addr=loc
    intrl_returnCheck  # load continuation or enter RR closure
    ctrl_exptrload # load muxed value into exptr
    ctrl_alu2rr # if 1 ? RR <<= ALU : RR <<= srcMux
    ctrl_argwe # write value into args reg
    ctrl_writeContinuation # write cont onto stack
    ctrl_loadcont # load cont. into nLocals and envclo
    ctrl_addrFreevar # heapAddr = nTable + index + 1
    ctrl_ALUop # alu operation code
    ctrl_exptrsrc # choose source of exptr (see mux constants)
    '''
    intrl_enterAlloc = WireVector(1, "EnterAllocState")  # enter allocation state machine
    intrl_enterRestore = WireVector(1, "EnterRestoreState")  # enter restore continuation state machine
    intrl_returnCheck = WireVector(1, "returnCheck")

    decodeDict = {
        "arg"         : "00000",
        "freevar"     : "00100",
        "alias"       : "00011",
        "let_closure" : "00111",
        "case"        : "00000",
        "lit_pattern" : "00000",
        "con_pattern" : "00000",
        "else_pattern": "00000",
        "call"        : "11000",
        "enter"       : "10000",
        "ret"         : "11000"
    }

    beginalloc = op == OPCODES["let_closure"]
    state_alloc = state == ALLOC
    state_restore = state == CONT_RESTORE

    ctrl_exptrload <<= op ~beginalloc
    ctrl_writeContinuation <<= op == OPCODES["case"]
    ctrl_argwe <<= op == OPCODES["arg"]
    ctrl_alu2rr <<= op == OPCODES["call"]
    intrl_returnCheck <<= op == OPCODES["ret"]
    ctrl_enter <<= op == OPCODES["enter"]
    ctrl_inspectElement <<= dsrc == SRC_ELEM
    ctrl_addrFreevar <<= (dsrc == SRC_ELEM) | (state_alloc)
    ctrl_allocWriteName <<= beginalloc
    intrl_enterAlloc <<= (beginalloc | state_alloc) & (itablenvars != 0)
    ctrl_writeFreevar <<= state_alloc
    ctrl_spDecr <<= state_alloc
    ctrl_alias <<= op == OPCODES["alias"]
    intrl_enterRestore <<=

    ctrl_ALUop <<= instr_itable_bits[:aluopbits]
    
# ######################################################################
#     Evaluation Stack
# ######################################################################
def evalstack(ctrl_spDecr, ctrl_spclearLocals, nLocals, ctrl_writeValue, 
              ctrl_writeContinuation, continuation, srcMux, evalStackOut):
    sp = Register(evalstackspace, "EvalStackPointer")
    spinc = ctrl_writeValue | ctrl_writeContinuation  # auto-increment on writes
    stacknext = switch(concat(spinc, ctrl_spDecr, ctrl_spclearLocals), {
        "3'b100" : sp + 1,
        "3'b010" : sp - 1,
        "3'b001" : sp - nLocals,
        None : 0
    })
    cond = ConditionalUpdate()
    with cond(ctrl_spDecr | ctrl_spclearLocals | spinc):
        sp.next <<= stacknext

    # Instantiate stack memory
    evalStack = MemBlock(width, evalstackspace, "EvaluationStack")

    # Stack ports
    evalStackOut <<= evalStack[sp]  # always read top of stack
    # can write data from srcMux (includes newly allocated names) or continuations
    evalStackWData = mux(ctrl_writeValue, falsecase=continuation, truecase=srcMux)
    EW = MemBlock.EnabledWrite
    nextspace = sp + 1
    evalStack[nextspace[0:evalstackspace]] = EW(evalStackWData, enable=spinc)

def test_evalstack():

    ctrl_spDecr = Input(1, "ctrl_spDecr")
    ctrl_spclearLocals = Input(1, "ctrl_spclearLocals")
    nLocals = Input(localspace, "nLocals")
    ctrl_writeValue = Input(1, "ctrl_writeValue")
    ctrl_writeContinuation = Input(1, "ctrl_writeContinuation")
    continuation = Input(textspace + namespace + localspace, "continuation")
    srcMux = Input(width, "srcMux")
    evalStackOut = Output(width, "evalStackOut")

    evalstack(ctrl_spDecr, ctrl_spclearLocals, nLocals, ctrl_writeValue, 
              ctrl_writeContinuation, continuation, srcMux, evalStackOut)

    simvals = {
        ctrl_spDecr            : "000000000111000",
        ctrl_spclearLocals     : "000000000000010",
        nLocals                : "000000000000040",
        ctrl_writeValue        : "011111000000000",
        ctrl_writeContinuation : "000000111000000",
        continuation           : "000000987000000",
        srcMux                 : "012345000000000",
    }

    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)
    for cycle in range(len(simvals[srcMux])):
        sim.step({k:int(v[cycle]) for k,v in simvals.items()})
    sim_trace.render_trace()


# ######################################################################
#     Locals
# ######################################################################
def localsregs(ctrl_inclocals, ctrl_declocals, ctrl_clearlocals, ctrl_loadcont, srcMux,
               localsindex, localsOut, ctrl_writelocal, ctrl_enter, envcloOut, nLocalsOut):

    # Register storing number of local variables so far in this scope
    nlocals = Register(localspace, "nLocalsReg")
    nLocalsOut <<= nlocals
    nlocalsnext = switch(concat(ctrl_inclocals, ctrl_declocals, ctrl_clearlocals, ctrl_loadcont), {
        "4'b1000" : nlocals + 1,  # increment register
        "4'b0100" : nlocals - 1,  # decrement register
        "4'b0010" : Const(0, bitwidth=localspace),  # clear register
        "4'b0001" : srcMux[cont_nLocals_bits],  # load saved number of locals section of continuation
        None : nlocals
    })
    cond = ConditionalUpdate()
    with cond(ctrl_inclocals | ctrl_declocals | ctrl_clearlocals | ctrl_loadcont):
        nlocals.next <<= nlocalsnext

    # Locals registers
    localsRegs = MemBlock(namespace, localspace, name="LocalsRegisters")
    # read port; read local specified in instr
    localsOut <<= concat(localsRegs[localsindex], Const(0, bitwidt=primtag_bits))  # add primtag
    # Values written on allocation and all aliases
    localsRegs[nlocals] = MemBlock.EnabledWrite(srcMux, enable=ctrl_writelocal)

    # Current environment closure register
    envclo = Register(namespace, "CurrentEnvClosure")
    envcloOut <<= envclo
    # Can load closure off of stack or name in local reg on enter instruction
    envclonext = switch(concat(ctrl_loadcont, ctrl_enter), {
        "2'b10" : srcMux[cont_envclo_bits],
        "2'b01" : localsOut,
        None : envclo
    })
    cond = ConditionalUpdate()
    with cond(ctrl_loadcont | ctrl_enter):
        envclo.next <<= envclonext
    #envclo.next <<= envclonext

    c1 = WireVector(1, "TEST_ctrl_loadcont")
    c1 <<= ctrl_loadcont
    c2 = WireVector(namespace, "TEST_contClo")
    c2 <<= srcMux[cont_envclo_bits]

def test_localsregs():

    ctrl_inclocals = Input(1, "ctrl_inclocals")
    ctrl_declocals = Input(1, "ctrl_declocals")
    ctrl_clearlocals = Input(1, "ctrl_clearlocals")
    ctrl_loadcont = Input(1, "ctrl_loadcont")
    srcMux = Input(width, "srcMux")
    localsindex = Input(localspace, "localsindex")
    localsWire = WireVector(namespace, "localsWire")
    localsOut = Output(namespace, "localsOut")
    localsOut <<= localsWire
    ctrl_writelocal = Input(1, "ctrl_writelocal")
    ctrl_enter = Input(1, "ctrl_enter")
    envcloOut = Output(namespace, "envcloOut")
    nLocalsOut = Output(localspace, "nLocalsOut")
    contenvout = Output(namespace, "ContEnv")
    contenvout <<= srcMux[cont_envclo_bits]

    localsregs(ctrl_inclocals, ctrl_declocals, ctrl_clearlocals, ctrl_loadcont, srcMux,
            localsindex, localsWire, ctrl_writelocal, ctrl_enter, envcloOut, nLocalsOut)

#    cont_envclo_bits = slice(localspace,localspace+namespace)

    simvals = {
        ctrl_inclocals   : "011110000000000000",
        ctrl_declocals   : "000001000000000000",
        ctrl_clearlocals : "000000000000100000",
        ctrl_loadcont    : "000000000000010000",
        srcMux           : [b for b in "0123450000000"] + [0xFFFFFFF,0,0xF,0,0],
        localsindex      : "000000123453000020",
        ctrl_writelocal  : "011111000000000100",
        ctrl_enter       : "000000000001000010"
    }

    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)
    for cycle in range(len(simvals[srcMux])):
        sim.step({k:int(v[cycle]) for k,v in simvals.items()})
    sim_trace.render_trace()
    

    
# ######################################################################
#     Name Table and Heap
# ######################################################################
def table_heap(envclo, returnReg, localsOut, ctrl_enter, ctrl_inspectElement, srcMux, newNameOut,
               ctrl_writeFreevar, ctrl_allocWriteName, freevarIndex, heapOut, infoTable, evalStackOut,
               ctrl_alias, ctrl_addrFreevar, srcMuxFiltered):

    freePtr = Register(heapspace, "HeapFreePointer")

    # Name Table
    nameTable = MemBlock(heapspace, namespace, "NameTable")
    nameTableAddr = switch(concat(ctrl_enter, ctrl_inspectElement), {
        "2'b10" : localsOut,
        "2'b01" : returnReg,
        None : envclo
    })
    nameTableOut = WireVector(heapspace, "NameTableOut")
    # Read name for heap addressing
    nameTableOut <<= nameTable[nameTableAddr[primtag_bits:namespace+primtag_bits]]
    nameTableAliasPort = WireVector(heapspace, "NameTableAliasPort")
    # Read entry for re-aliasing
    nameTableAliasPort <<= nameTable[srcMux[primtag_bits:namespace+primtag_bits]] 
    # Two read ports are required to make alias_freevar single-cycle; it requires dereferencing 
    # a name, reading the freevar from the heap, and then dereferencing the resulting name

    # Allocation of names
    nextName = Register(namespace, "nextNameReg")
    newNameOut <<= nextName  # needed for locals regs and eval stack saving
    cond = ConditionalUpdate()
    with cond(ctrl_allocWriteName | ctrl_alias):
        nextName.next <<= nextName + 1
    tableValFiltered = mux(srcMux[primtag_bits], falsecase=nameTableAliasPort, truecase=srcMux)
    tableWriteData = mux(ctrl_alias, falsecase=freePtr, truecase=tableValFiltered)
    '''
    tableWriteData = switch(concat(ctrl_allocWriteName, ctrl_alias & srcMux[primtag_bits], ctrl_alias & ~), {
        "3'b100" : freePtr,
        "3'b010" : srcMux,
        "3'b001" : nameTableOut,
        None : nameTableOut
        #"3'b001" : 0,
        #None : 0
    })
    '''
    # Can write newly allocated name or alias (from srcMux)
    nameTable[nextName] = MemBlock.EnabledWrite(tableWriteData[0:heapspace], 
                                    enable=(ctrl_allocWriteName | ctrl_alias))
    
    # Filter srcMux 
    # if value is a primitive or a name that refers to an object, pass it through; if it is a name
    #  that referes to a primitive, pass the primitive through instead
    srcMuxFiltered <<= mux((~srcMux[primtag_bits]) & nameTableAliasPort[primtag_bits],
                           falsecase=srcMux, truecase=nameTableAliasPort)

    # Heap
    heap = MemBlock(width, heapspace, "Heap")
    heapaddr = mux(ctrl_addrFreevar, falsecase=nameTableOut, truecase=(nameTableOut + freevarIndex + 1))
    heapMemOut = heap[heapaddr[0:heapspace]]
    heapWriteData = mux(ctrl_writeFreevar, falsecase=infoTable, truecase=evalStackOut)
    heap[freePtr] = MemBlock.EnabledWrite(heapWriteData, enable=(ctrl_writeFreevar | ctrl_allocWriteName))
    # If name table entry is a primitive, output that; otherwise, output desired heap entry
    #heapOut <<= mux(nameTableOut[primtag_bits], falsecase=heapMemOut, truecase=nameTableOut)
    heapOut <<= heapMemOut

    # Update free pointer
    cond = ConditionalUpdate()
    with cond(ctrl_writeFreevar | ctrl_allocWriteName):
        freePtr.next <<= freePtr + 1

        

def test_table_heap():

    envclo = Input(namespace, "envclo")
    returnReg = Input(width, "returnReg")
    localsOut = Input(namespace, "localsOut")
    ctrl_enter = Input(1, "ctrl_enter")
    ctrl_inspectElement = Input(1, "ctrl_inspectElement")
    srcMux = Input(width, "srcMux")
    newNameOut = Output(namespace, "newNameOut")
    ctrl_writeFreevar = Input(1, "ctrl_writeFreevar")
    ctrl_allocWriteName = Input(1, "ctrl_allocWriteName")
    freevarIndex = Input(freevarspace, "freevarIndex")
    heapOut = Output(width, "heapOut")
    infoTable = Input(itablespace, "infoTable")
    evalStackOut = Input(width, "evalStackOut")
    ctrl_alias = Input(1, "ctrl_alias")
    ctrl_addrFreevar = Input(1, "ctrl_addrFreevar")
    srcMuxFiltered = Output(width, "srcMuxFiltered")

    table_heap(envclo, returnReg, localsOut, ctrl_enter, ctrl_inspectElement, srcMux, newNameOut,
               ctrl_writeFreevar, ctrl_allocWriteName, freevarIndex, heapOut, infoTable, evalStackOut,
               ctrl_alias, ctrl_addrFreevar, srcMuxFiltered)

    #pyrtl.working_block().sanity_check()
    #print find_cycle(pyrtl.working_block())
    #return

    #print pyrtl.working_block()

    simvals = {
        envclo              : "00000000000000000",
        returnReg           : "00000000000000000",
        localsOut           : "00000000000000123",
        ctrl_enter          : "00000000000001111",
        ctrl_inspectElement : "00000000000000000",
        srcMux              : "00000000000342000",
        ctrl_writeFreevar   : "00111100000000000",
        ctrl_allocWriteName : "01000000000000000",
        freevarIndex        : "00000001230000000",
        infoTable           : "07000000000000000",
        ctrl_alias          : "00000000001110000",
        ctrl_addrFreevar    : "00000011110000000",
        evalStackOut        : "00123400000000000"
    }

    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)
    for cycle in range(len(simvals[srcMux])):
        sim.step({k:int(v[cycle]) for k,v in simvals.items()})
    sim_trace.render_trace()




# ######################################################################
#     Info Tables, Execution Pointer, and Immortal Heap
# ######################################################################
def itable_exptr_iheap(targetTable, ctrl_exptr, ctrl_loadexptr, nInstrs, srcMux, 
                       itableOut, instrOut, exptrOut):
    infoTable = MemBlock(32, itablespace, "infoTable")
    itableOut <<= infoTable[targetTable]
    
    # Execution Pointer (PC)
    exptr = Register(textspace, "ExecutionPointer")
    exptrOut <<= exptr
    itable_entryCode = itableOut[itable_entrycode_bits]
    nextexptr = switch(ctrl_exptr, {
        PC_INC : exptr + 1,
        PC_NINSTRS : nInstrs,
        PC_ITABLE : itable_entryCode,
        PC_CONTINUATION : srcMux[cont_exptr_bits],
        None : exptr
    })
    cond = ConditionalUpdate()
    with cond(ctrl_loadexptr):
        exptr.next <<= nextexptr

    # Immortal Heap
    immortalHeap = MemBlock(width, textspace, "ImmortalHeap")
    instrOut <<= immortalHeap[exptr]

# ######################################################################
#     Arg Regs, ALU, and Return Register
# ######################################################################
def args_alu_rr(srcMux, argIndex, ctrl_argwe, ctrl_argSwitch, ctrl_ALUop, ctrl_alu2rr,
                ctrl_loadrr, argsOut, rrOut):

    # Regisers used in this section
    rr = Register(width, "ReturnRegister")  # return register
    nargsreg = Register(argspace, "NumberArgs")  # number of args bound so far

    # Connections from args -> ALU
    arg1 = WireVector(width, "argreg1")
    arg2 = WireVector(width, "argreg2")

    # Instantiate argument regsiter module
    argregs(ctrl_argwe, nargsreg, srcMux, argIndex, argsOut, ctrl_argSwitch, arg1, arg2)

    # Update number of arguments register
    cond = ConditionalUpdate()
    with cond(ctrl_argSwitch):  # Reset to zero when leaving function
        nargsreg.next <<= 0
    with cond(ctrl_argwe):  # When writing arg, increment arg count
        nargsreg.next <<= nargsreg + 1

    # Instantiate ALU; connect to first two args
    ALUout = WireVector(width, "ALUout")
    makeALU(ctrl_ALUop, arg1, arg2, ALUout)

    # Return Register update
    with cond(ctrl_loadrr):  # signal to modify return reg
        with cond(ctrl_alu2rr):  # load rr with ALU output
            rr.next <<= ALUout
        with cond():  # if not loading ALU, load from srcMux
            rr.next <<= srcMux
    rrOut <<= rr  # send result to srcMux


def test_args_alu_rr():

    srcMux = Input(width, "srcMuxVal")
    argIndex = Input(argspace, "argReadIndex")
    ctrl_argwe = Input(1, "writeArg")
    ctrl_argSwitch = Input(1, "switchArgs")
    ctrl_ALUop = Input(8, "ALUop")
    ctrl_alu2rr = Input(1, "alu2rr")
    ctrl_loadrr = Input(1, "loadrr")
    argsOut = Output(width, "argsOut")
    rrOut = Output(width, "rrOut")

    args_alu_rr(srcMux, argIndex, ctrl_argwe, ctrl_argSwitch, ctrl_ALUop, ctrl_alu2rr,
                ctrl_loadrr, argsOut, rrOut)
 

    simvals = {
        srcMux          : "0123450000000000090",
        argIndex        : "0000000012345670000",
        ctrl_argwe     : "0111110000000000000", 
        ctrl_argSwitch : "0000001000000000000",
        ctrl_ALUop      : "0222222222222222220",
        ctrl_alu2rr     : "0111111111111110000",
        ctrl_loadrr     : "0111111111111110010" 
    }

    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)
    for cycle in range(len(simvals[srcMux])):
        sim.step({k:int(v[cycle]) for k,v in simvals.items()})
    sim_trace.render_trace()





# ######################################################################
#     Argument Registers
# ######################################################################
def argregs(we, waddr, wdata, raddr, rdata, flipstate, reg1, reg2):
    # Two banks of registers, one for reading one for writing;
    # Internal one-bit state tracks which is which

    # Handle I/O based on internal state
    state = Register(1, 'argstate')
    # In each state, one is read and one is written; on flip, write becomes read and
    #  read is cleared
    # state == 0: args1 is writeargs, args2 is readargs
    # state == 1: args1 is readargs, args2 is writeargs

    args1 = MemBlock(width, argspace, name="args1")
    args2 = MemBlock(width, argspace, name="args2")

    # Output
    read1 = args1[raddr]
    read2 = args2[raddr]
    rdata <<= mux(state, falsecase=read2, truecase=read1)  # mux for output

    # Additional ports to output arg0 and arg1; need both for primitive (ALU) ops
    reg1 <<= mux(state, falsecase=args2[Const("3'b0")], truecase=args1[Const("3'b0")])
    reg2 <<= mux(state, falsecase=args2[Const("3'b1")], truecase=args1[Const("3'b1")])

    # Input
    EW = MemBlock.EnabledWrite
    args1[waddr] = EW(wdata, enable=(we & (state == 0)))
    args2[waddr] = EW(wdata, enable=(we & (state == 1)))

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
    nargsreg = Register(argspace, 'nargs')

    # Update number of arguments
    
    cond = ConditionalUpdate()
    with cond(argswitch):  # Clear reg on scope change
        nargsreg.next <<= 0
    with cond(we):  # increment on control signal
        nargsreg.next <<= nargsreg + 1
    

    # connect
    argregs(we, nargsreg, wdata, raddr, rdata, argswitch, arg1, arg2)

    pyrtl.working_block().sanity_check()

    # simulate
    # Write data 1-5, switch, then read out all regs
    # Switch again, read out all data
    # Write new dta, switch while writes ongoing, read out all regs
    # switch, read out all regs
    '''simvals = {
        we:        "0011111111000000000000000",
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

    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)
    for cycle in range(len(simvals[we])):
        sim.step({k:int(v[cycle]) for k,v in simvals.items()})
    sim_trace.render_trace()


# ######################################################################
#     Primitive Ops Unit (a.k.a. ALU)
# ######################################################################
def makeALU(control, op1, op2, out):
    '''
        %and    - 8'b0000_0000
        %or     - 8'b0000_0001
        %not    - 8'b0000_0010
        %xor    - 8'b0000_0011
        %iadd   - 8'b0000_0100
        %isub   - 8'b0000_0101
        %eq     - 8'b0000_0110
        %ne     - 8'b0000_0111
        %lt     - 8'b0000_1000
        %le     - 8'b0000_1001
        %gt     - 8'b0000_1010
        %ge     - 8'b0000_1011

        %imul   - 8'b0001_0000
        %idiv   - 8'b0001_0001
        %imod   - 8'b0001_0010

        %lsl    - 8'b0010_0000
        %rsl    - 8'b0010_0001
        %rsa    - 8'b0010_0010
        %lr     - 8'b0010_0011
        %rr     - 8'b0010_0100

        %fadd   - 8'b1000_0000
        %fsub   - 8'b1000_0001
        %fmul   - 8'b1000_0010
        %fdiv   - 8'b1000_0011
    '''

    '''
    Unimplemented for now
    "8'b0001_0000": op1 * op2,
    "8'b0001_0001": op1 / op2,
    "8'b0001_0010": op1 % op2,

    "8'b0010_0000": lsl,
    "8'b0010_0001": rsl,
    "8'b0010_0010": rsa,
    "8'b0010_0011": lr,
    "8'b0010_0100": rr,

    "8'b1000_0000": fadd,
    "8'b1000_0001": fsub,
    "8'b1000_0010": fmul,
    "8'b1000_0011": fdiv,
    '''
    out <<= switch(control, {
        "8'b0000_0000": op1 & op2,
        "8'b0000_0001": op1 | op2,
        "8'b0000_0010": ~op1,
        "8'b0000_0011": op1 ^ op2,
        "8'b0000_0100": op1 + op2,
        "8'b0000_0101": op1 - op2,
        "8'b0000_0110": op1 == op2,
        "8'b0000_0111": op1 != op2,
        "8'b0000_1000": op1 < op2,
        "8'b0000_1001": op1 <= op2,
        "8'b0000_1010": op1 > op2,
        "8'b0000_1011": op1 >= op2,
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
        return mux(select, falsecase = vals[0], truecase = vals[1])
    else:
        # mux each pair of values into new N/2 new wires, recursively call
        new = []
        for i in range(len(vals)/2):
            new.append(mux(select[0], falsecase=vals[2*i], truecase=vals[2*i+1]))
        return muxtree(new, select[1:])


def find_cycle(block):
    for wire in block.wirevector_subset(Input):
        val = __cycle_dfs(block, wire, [], [])
        if val is not None:
            return val
    return False
            
def __cycle_dfs(block, wire, visited, history):
    #print "Visiting {}".format(wire)
    if wire in visited:
        return
    visited.append(wire)
    history.append(wire)
    #print len(block.logic)
    for x in block.logic.copy():
        #print len(block.logic)
        #print x
        if not(any([wire is z for z in x.args])):
        #print wire in x.args
        #if wire in x.args:
            continue
        #print "Check"
        for w in x.dests:
            #print x.dests
            #if w in history:
            if any([w is z for z in history]):
                #print len(block.logic)
                s = "Cycle detected.\n"
                s += "{} feeds into {} but is descended from it.\n".format(wire, x)
                s += "Set of recursive stack:\n"
                s += str([str(x) for x in history])
                return s
                #return wire,x,w, [str(x) for x in history]
            #if w not in visited:
            if not(any([w is z for z in visited])):
                #print len(block.logic)
                val = __cycle_dfs(block, w, visited, history)
                #print val
                if val is not None:
                    return val
    history.remove(wire)



if __name__ == "__main__":
    main()
