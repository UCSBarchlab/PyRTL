# # Example 6: Memories in PyRTL
#
# One important part of many circuits is the ability to have data in locations that are
# persistent over clock cycles. Previous examples have used `Register` `WireVectors`,
# which are great for storing a small amount of data for a single clock cycle. However,
# PyRTL also has other ways to store data, namely `MemBlocks` and `RomBlocks`.

import random

import pyrtl

# ## Part 1: `MemBlocks`
#
# `MemBlocks` are a way to store multiple sets of data for extended periods of time.
# Below we will make two `MemBlocks` and test that they behave identically given the
# same inputs.
mem1 = pyrtl.MemBlock(bitwidth=32, addrwidth=3, name="mem1")
mem2 = pyrtl.MemBlock(32, 3, "mem2")

# One memory will receive the write address from an `Input`, the other, a `Register`:
waddr = pyrtl.Input(3, "waddr")
count = pyrtl.Register(3, "count")

# To make sure that the two memories take the same `Inputs`, we will use same write
# data, write enable, and read addr values:
wdata = pyrtl.Input(32, "wdata")
we = pyrtl.Input(1, "we")
raddr = pyrtl.Input(3, "raddr")

# We will be grabbing data from each of the two `MemBlocks` so we need two different
# output wires to see the results:
rdata1 = pyrtl.Output(32, "rdata1")
rdata2 = pyrtl.Output(32, "rdata2")

# ### Ports
#
# Data is read from and written to `MemBlocks` via ports. There are two types of ports:
# read ports and write ports. Each memory can have multiple read and write ports, but a
# `MemBlock` must have at least one of each. Below, we will make one read port for each
# of the two memories:

rdata1 <<= mem1[raddr]
rdata2 <<= mem2[raddr]

# ### Write Enable Bit
#
# For the write ports, we will do something different. Sometimes you don't want the
# memories to always accept the data and address on the write port. The write enable bit
# allows us to disable the write port as long as the enable bit's value is zero, giving
# us complete control over whether the `MemBlock` will accept the data.
mem1[waddr] <<= pyrtl.MemBlock.EnabledWrite(wdata, we)  # Uses input wire
mem2[count] <<= pyrtl.MemBlock.EnabledWrite(wdata, we)  # Uses count register

# Now we will finish up the circuit. We will increment the `count` register on each
# write
count.next <<= pyrtl.select(we, truecase=count + 1, falsecase=count)

# We will also verify that the two write addresses are always the same
validate = pyrtl.Output(1, "validate")
validate <<= waddr == count

# Now it is time to simulate the circuit. First we will set up the values for all of the
# inputs. Write 1 through 8 into the eight addresses (`addrwidth == 3`), then read the
# data back out:
simvals = {
    "we": "00111111110000000000000000",
    "waddr": "00012345670000000000000000",
    "wdata": "00123456789990000000000000",
    "raddr": "00000000000000000123456777",
}

# For simulation purposes, we can give the spots in memory an initial value. Note that
# in the actual circuit, the values are initially undefined. Below, we are building the
# data with which to initialize memory.
mem1_init = dict.fromkeys(range(8), 9)
mem2_init = dict.fromkeys(range(8), 9)
memvals = {mem1: mem1_init, mem2: mem2_init}

# Now run the simulation like before. Note the adding of the `memory_value_map`.
print("---------MemBlocks----------")
print(pyrtl.working_block())
sim = pyrtl.Simulation(memory_value_map=memvals)
sim.step_multiple(simvals)
sim.tracer.render_trace()

# Cleanup in preparation for the `RomBlock` example
pyrtl.reset_working_block()


# ## Part 2: RomBlocks
#
# `RomBlocks` are another type of memory. Unlike `MemBlocks`, `RomBlocks` are read-only
# and therefore only have read ports. They are used to store predefined data.
#
# There are two different ways to define the data stored in a `RomBlock`, either through
# passing a function or though a list or tuple:
def rom_data_func(address: int) -> int:
    return 31 - 2 * address


rom_data_array = [rom_data_func(a) for a in range(16)]

# Now we will make the `RomBlocks`. `RomBlocks` are similar to `MemBlocks`, but because
# they are read-only, they also need to be passed a set of data to be initialized as.
rom1 = pyrtl.RomBlock(bitwidth=5, addrwidth=4, romdata=rom_data_func)
rom2 = pyrtl.RomBlock(5, 4, rom_data_array)

rom_add_1, rom_add_2 = pyrtl.Input(4, "rom_in"), pyrtl.Input(4, "rom_in_2")

rom_out_1, rom_out_2 = pyrtl.Output(5, "rom_out_1"), pyrtl.Output(5, "rom_out_2")
rom_out_3, cmp_out = pyrtl.Output(5, "rom_out_3"), pyrtl.Output(1, "cmp_out")

# Because `Output` `WireVectors` cannot be used as the source for other nets, in order
# to use the `RomBlock` outputs in two different places, we must instead assign them to
# a temporary variable.
temp1 = rom1[rom_add_1]
temp2 = rom2[rom_add_1]

rom_out_3 <<= rom2[rom_add_2]

# Now we connect the rest of the outputs together:
rom_out_1 <<= temp1
rom_out_2 <<= temp2

cmp_out <<= temp1 == temp2

# Repeatability is very useful, but we also don't want the hassle of typing out a set of
# values to test. One approach is to use a fixed `random` seed:
print("\n---------RomBlocks----------")
print(pyrtl.working_block())
random.seed(4839483)

# Now we will create a new set of simulation values. In this case, since we want to use
# simulation values that are larger than `9` we cannot use the trick used in previous
# examples to parse values, so we pass lists of integers instead.
simvals = {
    "rom_in": [1, 11, 4, 2, 7, 8, 2, 4, 5, 13, 15, 3, 4, 4, 4, 8, 12, 13, 2, 1],
    "rom_in_2": [random.randrange(16) for i in range(20)],
}

# Now run the simulation like before. Note that for `RomBlocks`, we do not supply a
# `memory_value_map` because `RomBlock` get their data when they are constructed via
# `romdata`.
sim = pyrtl.Simulation()
sim.step_multiple(simvals)
sim.tracer.render_trace()
