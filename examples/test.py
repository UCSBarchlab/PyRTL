import random

import pyrtl
from pyrtl import *
import toFirrtl

def rom_data_func(address):
    return 31 - 2 * address

rom_data_array = [rom_data_func(a) for a in range(16)]

# Now we will make the ROM blocks. ROM blocks are similar to memory blocks
# but because they are read only, they also need to be passed in a set of
# data to be initialized as

# FIXME: rework how memassigns work to account for more read ports
rom1 = RomBlock(bitwidth=5, addrwidth=4, romdata=rom_data_func, max_read_ports=10)
rom2 = RomBlock(5, 4, rom_data_array, max_read_ports=10)

rom_add_1, rom_add_2 = Input(4, "rom_in"), Input(4, "rom_in_2")

rom_out_1, rom_out_2 = Output(5, "rom_out_1"), Output(5, "rom_out_2")
rom_out_3, cmp_out = Output(5, "rom_out_3"), Output(1, "cmp_out")

# Because output wirevectors cannot be used as the source for other nets,
# in order to use the rom outputs in two different places, we must instead
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
for cycle in range(len(simvals['rom_in'])):
    sim.step({k: v[cycle] for k, v in simvals.items()})
sim_trace.render_trace()


roms = [rom1, rom2]

#need to fix out file path
#toFirrtl.main_translate(pyrtl.working_block().__str__(), roms)

