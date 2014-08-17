import sys
sys.path.append("..")  # needed only if not installed
from pyrtl import *


def wickerman_core(bitwidth, addrwidth):
    imem = MemBlock(bitwidth, addrwidth, 'imem')
    dmem = MemBlock(bitwidth, addrwidth, 'dmem')
    regfile = MemBlock(bitwidth, 5, 'imem')
    pc = Register(addrwidth, 'pc')

    # decode the current instruction
    instr = imem[pc]
    opcode = instr[26:]
    immed = instr[10:26]
    rt = instr[10:15]
    rs = instr[5:10]
    rd = instr[0:5]


def alu(command, a, b):
    """ perform command on a and b, return tuple of value and status """
    sub_r = a - b
    add_r = a + b
    mul_r = a * b
    and_r = a & b
    or_r = a | b
    le_r = a < b

    #if command == add
    #elif command == op
    #elif command == le


wickerman_core(5, 5)

# Simulation of the core
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    sim.step({})
sim_trace.render_trace()
