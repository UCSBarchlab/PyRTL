""" Example 6: Memories in PyRTL

    One important part of many circuits is the ability to have data in
    locations that are persistent over clock cycles. In previous examples,
    we have shown the Register WireVector, which is great for storing
    a small amount of data for a single clock cycle. However, PyRTL also
    has other ways to store data, namely memories and ROMs.
"""

import random

import pyrtl
from pyrtl import *

# --- Part 1: Memories -------------------------------------------------------

# Memories are a way to store multiple sets of data for extended periods of
# time. Below we will make two instances of the same memory to test
# that the same thing happens to two different memories using the same
# inputs

mem1 = MemBlock(bitwidth=32, addrwidth=3, name='mem')
mem2 = MemBlock(32, 3, 'mem')

# One memory will receive the write address from an input, the other, a register
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
# use of a port. There are two types of ports: read ports and write ports.
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

count.next <<= select(we, truecase=count + 1, falsecase=count)

# We will also verify that the two write addresses are always the same

validate = Output(1, 'validate')
validate <<= waddr == count

# Now it is time to simulate the circuit. First we will set up the values
# for all of the inputs.
# Write 1 through 8 into the eight registers, then read back out
simvals = {
    'we': "00111111110000000000000000",
    'waddr': "00012345670000000000000000",
    'wdata': "00123456789990000000000000",
    'raddr': "00000000000000000123456777"
}

# For simulation purposes, we can give the spots in memory an initial value.
# Note that in the actual circuit, the values are initially undefined.
# Below, we are building the data with which to initialize memory.
mem1_init = {addr: 9 for addr in range(8)}
mem2_init = {addr: 9 for addr in range(8)}

# The simulation only recognizes initial values of memories when they are in a
# dictionary composed of memory : mem_values pairs.
memvals = {mem1: mem1_init, mem2: mem2_init}

# Now run the simulation like before. Note the adding of the memory
# value map.
print("---------memories----------")
print(pyrtl.working_block())
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map=memvals)
sim.step_multiple(simvals)
sim_trace.render_trace()

# Cleanup in preparation for the ROM example
pyrtl.reset_working_block()

# --- Part 2: ROMs -----------------------------------------------------------

# ROMs are another type of memory. Unlike normal memories, ROMs are read-only
# and therefore only have read ports. They are used to store predefined data.

# There are two different ways to define the data stored in the ROMs,
# either through passing a function or though a list or tuple.


def rom_data_func(address):
    return 31 - 2 * address


rom_data_array = [rom_data_func(a) for a in range(16)]

# Now we will make the ROM blocks. ROM blocks are similar to memory blocks,
# but because they are read-only, they also need to be passed a set of
# data to be initialized as.

# FIXME: rework how memassigns work to account for more read ports
rom1 = RomBlock(bitwidth=5, addrwidth=4, romdata=rom_data_func, max_read_ports=10)
rom2 = RomBlock(5, 4, rom_data_array, max_read_ports=10)

rom_add_1, rom_add_2 = Input(4, "rom_in"), Input(4, "rom_in_2")

rom_out_1, rom_out_2 = Output(5, "rom_out_1"), Output(5, "rom_out_2")
rom_out_3, cmp_out = Output(5, "rom_out_3"), Output(1, "cmp_out")

# Because Output WireVectors cannot be used as the source for other nets,
# in order to use the ROM outputs in two different places, we must instead
# assign them to a temporary variable.

temp1 = rom1[rom_add_1]
temp2 = rom2[rom_add_1]

rom_out_3 <<= rom2[rom_add_2]

# now we will connect the rest of the outputs together

rom_out_1 <<= temp1
rom_out_2 <<= temp2

cmp_out <<= temp1 == temp2

# One of the things that is useful to have is repeatability, However, we
# also don't want the hassle of typing out a set of values to test. One
# solution in this case is to seed random and then pulling out 'random'
# numbers from it.
print("---------roms----------")
print(pyrtl.working_block())
random.seed(4839483)

# Now we will create a new set of simulation values. In this case, since we
# want to use simulation values that are larger than 9 we cannot use the
# trick used in previous examples to parse values. The two ways we are doing
# it below are both valid ways of making larger values

simvals = {
    'rom_in': [1, 11, 4, 2, 7, 8, 2, 4, 5, 13, 15, 3, 4, 4, 4, 8, 12, 13, 2, 1],
    'rom_in_2': [random.randrange(0, 16) for i in range(20)]
}

# Now run the simulation like before. Note that for ROMs, we do not
# supply a memory value map because ROMs are defined with the values
# predefined.

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
sim.step_multiple(simvals)
sim_trace.render_trace()
