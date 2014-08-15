import sys
sys.path.append("..") # needed only if not installed
from pyrtl import *

def wickerman_core( bitwidth, addrwidth ):
    imem = MemBlock(bitwidth, addrwidth, 'imem')
    dmem = MemBlock(bitwidth, addrwidth, 'dmem')
    regfile = MemBlock(bitwidth, 5, 'imem')
    pc = Register(addrwidth,'pc')
                
                
wickerman_core(5,5)
                
# Simulation of the core
sim_trace = SimulationTrace()
sim = Simulation( tracer=sim_trace )
for i in xrange(15):
    sim.step( {} )
sim_trace.render_trace()
