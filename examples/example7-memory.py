""" Example 7: Memories in PyRTL

    One important part of many circuits is the ability to have data in
    locations that are persistent over clock cycles. In previous examples,
    we have shown the register wirevector, which is great for storing
    a small amount of data for a single clock cycle. However, PyRTL also
    has other ways to store data, namely memories and ROMs.
"""
import sys
sys.path.append("..")  # needed only if not installed

import pyrtl
from pyrtl import *

# --- Part 1: Memories -------------------------------------------------------

# Memories is a way to store multiple sets of data for extended periods of
# time. Below we will make two instances of the same memory to test using
# that the same thing happens to two different memories using the same
# inputs

mem1 = MemBlock(bitwidth=32, addrwidth=3, name='mem')
mem2 = MemBlock(32, 3, 'mem')

# One memory will use input as write address, the other a register
waddr = Input(3, 'waddr')
count = Register(3, 'count')

# In order to make sure that the two memories take the same inputs,
# we will use same write data, write enable, and read addr values
wdata = Input(32, 'wdata')
we = Input(1, 'we')
raddr = Input(3, 'raddr')

# We will be grabbing data from each of the two memory blocks so we need
# two different output wires to see the results

rdata1 = Output(32, 'rdata1')
rdata2 = Output(32, 'rdata2')

# Ports
# The way of sending data to and from a memory block is through the
# use of a port. There are two types of ports, read ports and write ports.
# Each memory can have multiple read and write ports, but it doesn't make
# sense for one to have either 0 read ports or 0 write ports. Below, we
# will make one read port for each of the two memories

rdata1 <<= mem1[raddr]
rdata2 <<= mem2[raddr]

# Write Enable Bit
# For the write ports, we will do something different. Sometimes you don't
# want the memories to always accept the data and address on the write port.
# The write enable bit allows us to disable the write port as long as the
# value is zero, giving us complete control over whether to accept the data.

WE = MemBlock.EnabledWrite
mem1[waddr] <<= WE(wdata, we)  # Uses input wire
mem2[count] <<= WE(wdata, we)  # Uses count register

# Now we will finish up the circuit
# We will increment count register on each write

count.next <<= mux(we, falsecase=count, truecase=count + 1)

# we will also verify that the two write address are always the same

validate = Output(1, 'validate')
validate <<= waddr == count

# Now it is time to simulate the circuit. first we will set up the values
# for all of the inputs.
# Write 1 through 8 into the eight registers, then read back out
simvals = {
    we:        "00111111110000000000000000",
    waddr:     "00012345670000000000000000",
    wdata:     "00123456789990000000000000",
    raddr:     "00000000000000000123456789"
}

# for simulation purposes, we can give the spots in memory an initial value
# note that in real circuits, the values are initially undefined
# below, we are building the data with which to initialize memory
mem1_init = {addr: 9 for addr in range(8)}
mem2_init = {addr: 9 for addr in range(8)}

# The simulation only recognizes initial values of memories when they are in a
# dictionary composing of memory : mem_values pairs.
memvals = {mem1: mem1_init, mem2: mem2_init}

# now run the simulation like before. Note the adding of the memory
# value map.
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map=memvals)
for cycle in range(len(simvals[we])):
    sim.step({k: int(v[cycle]) for k, v in simvals.items()})
sim_trace.render_trace()
