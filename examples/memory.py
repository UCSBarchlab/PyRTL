import sys
import numpy as np
sys.path.append("..")
import pyrtl
from pyrtl import *

mem1 = MemBlock(32, 3, 'mem')
mem2 = MemBlock(32, 3, 'mem')
WE = MemBlock.EnabledWrite

# One memory will use input as write address, the other a register
waddr = Input(3, 'waddr')
count = Register(3, 'count')

# Use same write data, write enable, and read addr values
wdata = Input(32, 'wdata')
we = Input(1, 'we')
raddr = Input(3, 'raddr')

# Separate read-out lines
rdata1 = Output(32, 'rdata1')
rdata2 = Output(32, 'rdata2')

# Instantiate ports
rdata1 <<= mem1[raddr]
rdata2 <<= mem2[raddr]
mem1[waddr] = WE(wdata, we)  # Uses input wire
mem2[count] = WE(wdata, we)  # Uses count register

# increment count regsiter on each write
count.next <<= mux(we, falsecase=count, truecase=count + 1)

# Verify that the two write address are always the same
validate = Output(1, 'validate')
validate <<= waddr == count

# Simulate: write 1 through 8 into the eight registers, then read back out
simvals = {
    we:        "0011111111000000000000000",
    waddr:     "0001234567000000000000000",
    wdata:     "0012345678999000000000000",
    raddr:     "0000000000000000012345670"
}

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in range(len(simvals[we])):
    sim.step({k: int(v[cycle]) for k, v in simvals.items()})
sim_trace.render_trace()
