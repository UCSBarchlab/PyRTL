""" Example 4: Debugging

Debugging is half the coding process in software, and in PyRTL, it's no
different. PyRTL provides some additional challenges when it comes to
debugging as a problem may surface long after the error was made. Fortunately,
PyRTL comes with various features to help you find mistakes.
"""

import random
import io
from pyrtl.rtllib import adders
import pyrtl

random.seed(93729473)  # used to make random calls deterministic for this example


# This example covers debugging strategies for PyRTL.  For general python debugging
# we recommend healthy use of the "assert" statement, and use of "pdb" for
# tracking down bugs.  However, PyRTL introduces some new complexities because
# the place where  functionality is defdined (when you construct and operate
# on PyRTL classes) is seperate in time from where that functionalty is executed
# (i.e. during siumation).  Thus, sometimes it hard to track down where a wire
# might have come from, or what exactly it is doing.

# In this example specifically, we will be building a circuit that adds up three values.
# However, instead of building an add function ourselves or using the
# built-in "+" function in PyRTL, we will instead use the Kogge-Stone adders
# in RtlLib, the standard library for PyRTL.

# building three inputs
in1, in2, in3 = (pyrtl.Input(8, "in" + str(x)) for x in range(1, 4))
out = pyrtl.Output(10, "out")

add1_out = adders.kogge_stone(in1, in2)
add2_out = adders.kogge_stone(add1_out, in2)
out <<= add2_out

# Now, before we go onto setting up some debugging, lets look at how PyRTL
# handles things under the hood. In PyRTL, there's an block object that
# stores everything in the circuit. You can access the working (aka current)
# block through pyrtl.working_block(), and for most things one block is all
# you will need. Let's look at it now. The format is a bit weird, but roughly
# translates to a list of gates (the 'w' gates are just wires, aka the
# connections made using <<= earlier).  The ins and outs of the gates are
# printed 'name'/'bitwidth''WireVectorType'

block = pyrtl.working_block()
print(block)

# The most basic way of debugging PyRTL is to connect a value to an output wire
# and use the simulation to trace the output. A simple "print" statement doesn't work
# because the values in the wires are not populated during *creation* time

# If we want to check the result of the first addition, we can connect an output wire
# to the result wire of the first adder

debug_out = pyrtl.Output(9, "debug_out")
debug_out <<= add1_out

# now simulate the circuit.  Let's create some random inputs to feed our adder.

vals1 = [int(2**random.uniform(1, 8) - 2) for _ in range(20)]
vals2 = [int(2**random.uniform(1, 8) - 2) for _ in range(20)]
vals3 = [int(2**random.uniform(1, 8) - 2) for _ in range(20)]

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in range(len(vals1)):
    sim.step({
        in1: vals1[cycle],
        in2: vals2[cycle],
        in3: vals3[cycle]})

# in order to get the result data, you do not need to print a waveform of the trace
# You always have the option to just pull the data out of the tracer directly

print("in1:       ", str(sim_trace.trace[in1]))
print("in2:       ", str(sim_trace.trace[in2]))
print("debug_out: ", str(sim_trace.trace[debug_out]))

# Below, I am using the ability to directly retrieve the trace data to
# verify the correctness of the first adder

for i in range(len(vals1)):
    assert(sim_trace.trace[debug_out][i] == sim_trace.trace[in1][i] + sim_trace.trace[in2][i])


# --- Probe ----

# now that we have built some stuff, let's clear it so we can try again in a
# different way.  We can start by clearing all of the hardware from the current working
# block.  The working block is a global structure that keeps track of all the
# hardware you have built thus far.  A "reset" will clear it so we can start fresh.
# pyrtl.reset_working_block()

# ...

# Finally, to clean up for the next section, we will replace the current working block
pyrtl.reset_working_block()

# This sets the current working block to a new one with no wires or logic in it
# All new logic and wires will be added to this new block.

# ----Wirevector Stack Trace ----

# Another case that might arise is that a certain wire is causing an error to occur
# in your program. Wirevector Stack Traces allow you to find out more about where a particular
# wirevector was made in your code. With this enabled the wirevector will
# store exactly were it was created, which should help with issues where
# there is a problem with an indentified wire.

# To enable this, just add the following line before the relevant wirevector
# might be made or at the beginning of the program.

pyrtl.set_debug_mode()

# Because we have changed the working block, using wires from the old
# block will cause issues. Therefore, we need to create new input wirevectors

new_in0, new_in1 = (pyrtl.Input(8, "in" + str(x)) for x in range(2))

# Now we will build a test wire to demonstrate retrieving the call stack
test_out = pyrtl.Output(9, "test_out")
test_out <<= adders.kogge_stone(new_in0, new_in1)

# Now to retrieve the call stack
wire_trace = test_out.init_call_stack

# This data is generated using the traceback.format_stack() call from the Python
# standard library's Traceback module (look at the Python standard library docs for
# details on the function). Therefore, the stack traces are stored as a list with the
# outermost call first.

assert(isinstance(wire_trace, list))

print("--- Printing Call stack ---")

for frame in wire_trace:
    print(frame)

# Storage of Additional Debug Data

# ------------------------------------
# WARNING: the debug information generated by the following two processes are
# not guarenteed to be preserved when functions (eg. pyrtl.synthesize() ) are
# done over the block.
# ------------------------------------

# However, if the stack trace does not give you enough information about the
# wirevector, you can also enbed additional information into the wire itself
# Two ways of doing so is either through manipulating the name of the
# wirevector, or by adding your own custom metadata to the wirevector.


# So far, each input and output wirevector have been given their own names, but
# normal wirevectors can also be given names by supplying the name argument to
# the constructor

dummy_wv = pyrtl.WireVector(1, name="blah")

# Also, because of the flexible nature of Python, you can also add custom
# properties to the wirevector.

dummy_wv.my_custom_property_name = "John Clow is great"
dummy_wv.custom_value_028493 = 13

# removing the wirevector from the block to prevent problems with the rest of
# this example
pyrtl.working_block().remove_wirevector(dummy_wv)

# ---- Trivial Graph Format

# Finally, there is a handy way to view your hardware creations as a graph.  The function
# output_to_trivialgraph will render your hardware a formal that you can then open with the
# free software "yEd" (http://en.wikipedia.org/wiki/YEd).  There are options under the
# "heirachical" rendering to draw something looks quite like a circuit.


import io
print("--- Trivial Graph Format  ---")
with io.StringIO() as tgf:
    pyrtl.output_to_trivialgraph(tgf)
    print(tgf.getvalue())
