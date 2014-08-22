import sys
sys.path.append("..")  # needed only if not installed
from pyrtl import *


def mips_core(bitwidth, addrwidth):
    # state elements
    imem = MemBlock(bitwidth, addrwidth, 'imem')
    dmem = MemBlock(bitwidth, addrwidth, 'dmem')
    regfile = MemBlock(bitwidth, 5, 'regfile')
    pc = Register(addrwidth, 'pc')

    # counterflow wires
    pcsrc = WireVector(1,'pcsrc')
    computed_address = WireVector(1,'computed_address')
    regwrite = WireVector(1,'regwrite')
    write_register = WireVector(5,'write_register')
    write_data = WireVector(bitwidth,'write_data')

    fetch(pcsrc, computed_address, pc, imem)
    decode(
    execute
    mem
    writeback

    # decode the current instruction
    opcode = instr[26:]
    immed = instr[10:26]
    rt = instr[10:15]
    rs = instr[5:10]
    rd = instr[0:5]

def fetch(pcsrc, computed_address, pc, imem):
    instr = imem[pc]
    pc_incr = pc + 4
    pc.next <<= mux(pcsrc, pc_incr, computed_address)

def decode(regwrite, write_register, write_data)
    

def decode(

mips_core(5, 5)

# Simulation of the core
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    sim.step({})
sim_trace.render_trace()
