""" Example 1a: More Connection vs Assignment Clarification

    If by the end of example 1, you understand the connection
    and assignment operators, feel free to skip this.
    This example declares the same block of hardware as example 1,
    however, it will be done slightly differently to accentuate the
    difference between the connection and assignment operators. The
    difference should be rather intuitive for people with software
    development backgrounds, but for people with more hardware oriented
    backgrounds, the concept of assignment might be different from
    what they expected.
"""

import pyrtl
import random

# Okay, let's build that one bit adder again.

a, b, c = pyrtl.Input(1, 'a'), pyrtl.Input(1, 'b'), pyrtl.Input(1, 'c')
add_sum, carry_out = pyrtl.Output(1, 'sum'), pyrtl.Output(name='carry_out')

# First we will assemble the carry out bit. It can all be done in one line,
# but let's try to again build it in a different way

temp1 = a & b  # we've seen this before

# note that logic operations, as well as most PyRTL functions return wirevectors
# as outputs which can be used without connecting them to another wire as we will
# show with the following line:

assert(isinstance(temp1, pyrtl.WireVector))

# We can similarly make the rest of the carry out logic
temp2 = a & c
temp2_copy = temp2  # done to facilitate the explanation below

# now here comes something more interesting
temp2 = temp2 | (b & c)

# Notice here that temp2 is treated as a variable in the software sense.
# When it is assigned to, it replaces the wire that was previously in
# it's location (software folks should be familiar with this). Therefore,
# the new temp2 and the old temp2 are two different wires.
assert(temp2 is not temp2_copy)

# we will now put together the carry out bit like we have last time:

c_out_copy = carry_out
carry_out <<= temp1 | temp2

# Note that when a wire is connected to another wire, it still is the
# original wire (unlike the assignment operator we saw earlier)
assert(carry_out is c_out_copy)

# Also, note that even though we had left out the bitwidth for carry_out
# when we declared it, PyRTL was able to infer that it is 1
assert (carry_out.bitwidth == 1)

# The connection operator is relatively simple, it just connects two existing
# wires. However, the assignment operator, being assignment in the software sense
# can be treated like any normal python object. For example, it can be assigned to
# part of an list then pulled out of it for use as we will show when building the
# sum bit:

input_wires = [a, b, c]  # make a list with a, b, c in it
assert(input_wires[0] is a)

temp_sum = pyrtl.Const(0)
for wire in input_wires:  # taking each wire from the input wire
    temp_sum = temp_sum ^ wire

add_sum <<= temp_sum

# --- Simulate Design  --------------------------------------------------------

# now we will verify the design again to prove that this is logically equivalent
# to the previous design. Feel free to skip over this.

# this simulation does exactly the sam thing as the one from example 1, but
# does it in a more compact manner, using more complex python concepts.

cycles = 15
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
input_vectors = [[random.randrange(0, 2) for i in range(3)] for j in range(cycles)]

for a_in, b_in, c_in in input_vectors:
    sim.step({a: a_in, b: b_in, c: c_in})

sim_trace.render_trace()
for cycle in range(cycles):
    add_result = sum(input_vectors[cycle])

    python_sum = add_result & 0x1
    python_cout = (add_result >> 1) & 0x1
    if (python_sum != sim_trace.trace[add_sum][cycle] or
            python_cout != sim_trace.trace[carry_out][cycle]):
        print('This Example is Broken!!!')
        exit(1)
