# # A simple combinational logic example.
#
# Create an 8-bit adder that adds `a` and `b`. Check if the sum is greater than `5`.
import pyrtl

# Define `Inputs` and `Outputs`.
a = pyrtl.Input(bitwidth=8, name="a")
b = pyrtl.Input(bitwidth=8, name="b")

q = pyrtl.Output(bitwidth=8, name="q")
gt5 = pyrtl.Output(bitwidth=1, name="gt5")

# Define the logic that connects the `Inputs` to the `Outputs`.
sum = a + b  # Makes an 8-bit adder.
q <<= sum  # Connects the adder's output to the `q` output pin.
gt5 <<= sum > 5  # Does a comparison and connects the result to the `gt5` output pin.

# Simulate various values for `a` and `b` over 5 cycles.
sim = pyrtl.Simulation()
sim.step_multiple({"a": [0, 1, 2, 3, 4], "b": [2, 2, 3, 3, 4]})

# Display simulation traces as waveforms.
sim.tracer.render_trace()
