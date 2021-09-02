""" Example 7: Reduction and Speed Analysis

    After building a circuit, one might want to do some stuff to reduce the
    hardware into simpler nets as well as analyze various metrics of the
    hardware. This functionality is provided in the Passes part of PyRTL
    and will be demonstrated here.
"""


import pyrtl

# --- Part 1: Timing Analysis ------------------------------------------------

# Timing and area usage are key considerations of any hardware block that one
# makes. PyRTL provides functions to do these operations.

# Creating a sample hardware block
pyrtl.reset_working_block()
const_wire = pyrtl.Const(6, bitwidth=4)
in_wire2 = pyrtl.Input(bitwidth=4, name="input2")
out_wire = pyrtl.Output(bitwidth=5, name="output")
out_wire <<= const_wire + in_wire2


# Now we will do the timing analysis as well as print out the critical path

# Generating timing analysis information
print("Pre Synthesis:")
timing = pyrtl.TimingAnalysis()
timing.print_max_length()

# We are also able to print out the critical paths as well as get them
# back as an array.
critical_path_info = timing.critical_path()

# --- Part 2: Area Analysis --------------------------------------------------

# PyRTL also provides estimates for the area that would be used up if the
# circuit was printed as an ASIC.

logic_area, mem_area = pyrtl.area_estimation(tech_in_nm=65)
est_area = logic_area + mem_area
print("Estimated Area of block", est_area, "sq mm")
print()


# --- Part 3: Synthesis ------------------------------------------------------

# Synthesis is the operation of reducing the circuit into simpler components.
# The base synthesis function breaks down the more complex logic operations
# into logic gates (keeping registers and memories intact) as well as reduces
# all combinatorial logic into operations that only use 1-bitwidth wires.
#
# This synthesis allows for PyRTL to make optimizations to the net structure
# as well as prepares it for further transformations on the PyRTL toolchain.

pyrtl.synthesize()

print("Pre Optimization:")
timing = pyrtl.TimingAnalysis()
timing.print_max_length()
for net in pyrtl.working_block().logic:
    print(str(net))
print()


# --- Part 4: Optimization ----------------------------------------------------

# PyRTL has functions built-in to eliminate unnecessary logic from the
# circuit. These functions are all done with a simple call:
pyrtl.optimize()

# Now to see the difference
print("Post Optimization:")
timing = pyrtl.TimingAnalysis()
timing.print_max_length()

for net in pyrtl.working_block().logic:
    print(str(net))

# As we can see, the number of nets in the circuit was drastically reduced by
# the optimization algorithm.
