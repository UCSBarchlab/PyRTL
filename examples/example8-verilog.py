# # Example 8: Interfacing with Verilog.
#
# PyRTL provides utilities to import from, and export to, Verilog. Simulation traces can
# also be exported to `vcd` files.
import io
import random

import pyrtl

# ## Importing From Verilog
#
# Sometimes it is useful to pull in components written in Verilog to be used as
# subcomponents of PyRTL designs, or for analysis in PyRTL. PyRTL supports the standard
# `blif` format: https://www.ece.cmu.edu/~ee760/760docs/blif.pdf
#
# Many tools support outputting hardware designs to `blif`, including the open source
# project `yosys`. `blif` files can then be imported either as a string or directly from
# a file name by the function `input_from_blif()`. Here is a simple example of a 1-bit
# full adder imported and then simulated from `blif`:
full_adder_blif = """
.model full_adder
.inputs x y cin
.outputs sum cout
.names $false
.names $true
1
.names y $not$FA.v:12$3_Y
0 1
.names x $not$FA.v:11$1_Y
0 1
.names cin $not$FA.v:15$6_Y
0 1
.names ind3 ind4 sum
1- 1
-1 1
.names $not$FA.v:15$6_Y ind2 ind3
11 1
.names x $not$FA.v:12$3_Y ind1
11 1
.names ind2 $not$FA.v:16$8_Y
0 1
.names cin $not$FA.v:16$8_Y ind4
11 1
.names x y $and$FA.v:19$11_Y
11 1
.names ind0 ind1 ind2
1- 1
-1 1
.names cin ind2 $and$FA.v:19$12_Y
11 1
.names $and$FA.v:19$11_Y $and$FA.v:19$12_Y cout
1- 1
-1 1
.names $not$FA.v:11$1_Y y ind0
11 1
.end
"""

pyrtl.input_from_blif(full_adder_blif)
# Find the `WireVectors` corresponding to wires named in the `blif` file.
x, y, cin = [pyrtl.working_block().get_wirevector_by_name(s) for s in ["x", "y", "cin"]]

# Simulate the logic with random input values:
sim = pyrtl.Simulation()
for _cycle in range(15):
    sim.step(
        {"x": random.randrange(2), "y": random.randrange(2), "cin": random.randrange(2)}
    )
# Only display the `Input` and `Output` `WireVectors` for clarity.
input_vectors = pyrtl.working_block().wirevector_subset(pyrtl.Input)
output_vectors = pyrtl.working_block().wirevector_subset(pyrtl.Output)
sim.tracer.render_trace(trace_list=[*input_vectors, *output_vectors], symbol_len=2)

# ## Exporting to Verilog
#
# To demonstrate Verilog export, we create a simple 3-bit counter. This is like the
# counter in `example2`, except this one can be reset at any time by asserting `zero`.
pyrtl.reset_working_block()

zero = pyrtl.Input(1, "zero")
counter_output = pyrtl.Output(3, "counter_output")
counter = pyrtl.Register(3, "counter")
counter.next <<= pyrtl.select(zero, 0, counter + 1)
counter_output <<= counter

# The `select()` statement resets the `counter` to `0` in the next cycle when the `zero`
# signal goes high, otherwise the `counter`'s next value is just `counter + 1`.
#
# The constants `0` and `1` are automatically `zero_extended()` to the proper length.
# Let's export this resettable counter to a Verilog file and see what is looks like
# (here we are using `StringIO` just to print it to a string for demo purposes; most
# likely you will want to pass a normal `open` file).
print("\n--- PyRTL Representation ---")
print(pyrtl.working_block())

print("\n--- Verilog for the Counter ---")
with io.StringIO() as verilog_file:
    pyrtl.output_to_verilog(verilog_file)
    print(verilog_file.getvalue())

print("\n--- Simulation Results ---")
sim = pyrtl.Simulation(tracer=pyrtl.SimulationTrace([counter_output, zero]))
for _cycle in range(15):
    sim.step({"zero": random.choice([0, 0, 0, 1])})
sim.tracer.render_trace()

# We already did the "hard" work of generating a test input for this simulation, so we
# might want to reuse that work when we take this design through a Verilog toolchain.
# `output_verilog_testbench()` grabs the `Inputs` used in the `SimulationTrace` and sets
# them up in a standard Verilog testbench.
print("\n--- Verilog for the TestBench (first 10 lines) ---")
with io.StringIO() as testbench_file:
    pyrtl.output_verilog_testbench(
        dest_file=testbench_file, simulation_trace=sim.tracer
    )
    for i, line in enumerate(testbench_file.getvalue().split("\n")):
        if i == 10:
            break
        print(line)
    print("...")

# ## Transformations
#
# Now let's talk about transformations of the hardware block. Many times when you are
# doing some hardware-level analysis you might wish to ignore higher level things like
# multi-bit wirevectors, adds, concatenation, etc, and just think about wires and basic
# gates. PyRTL supports "lowering" of designs into this more restricted set of
# functionality though the function `synthesize()`. Once we lower a design to this form
# we can then apply basic optimizations like constant propagation and dead wire
# elimination as well. By printing it out to Verilog we can see exactly how the design
# changed.
print("\n--- Optimized Single-bit Verilog for the Counter ---")
pyrtl.synthesize()
pyrtl.optimize()

with io.StringIO() as verilog_file:
    pyrtl.output_to_verilog(verilog_file)
    print(verilog_file.getvalue())
