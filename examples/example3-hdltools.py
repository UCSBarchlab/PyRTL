""" Example 3:  Interfacing with Other HDL Tools.

    While there is much more about PyRTL design to discuss, at some point somebody
    might ask you to do something with your code other than have it print
    pretty things out to the terminal.  We provide export to Verilog of designs,
    export of waveforms to VCD, and a set of transforms that make doing netlist-level
    transforms and analyis directly in pyrtl easy.  Below we describe them with
    a 3-bit counter example, but this time we extend it to be syncronously reseting.
"""

import sys
sys.path.append("..")  # needed only if not installed

import io
import random
import pyrtl

zero = pyrtl.Input(1, 'zero')
output = pyrtl.Output(3, 'output')
counter = pyrtl.Register(3, 'counter')
counter.next <<= pyrtl.mux(zero, counter + 1, 0)
output <<= counter

# The counter gets 0 in the next cycle if the "zero" signal goes high, otherwise just
# counter + 1.  Note that both "0" and "1" are bit extended to the proper length and
# here we are making use of that native add operation.  Let's dump this bad boy out
# to a verilog file and see what is looks like (here we are using StringIO just to
# print it to a string for demo purposes, most likely you will want to pass a normal
# open file).

print "--- PyRTL Representation ---"
print pyrtl.working_block()
print

print "--- Verilog for the Counter ---"
with io.BytesIO() as vfile:
    pyrtl.output_to_verilog(vfile)
    print vfile.getvalue()

print "--- Simulation Results ---"
sim_trace = pyrtl.SimulationTrace([output, zero])
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in xrange(15):
    sim.step({zero: random.choice([0, 0, 0, 1])})
sim_trace.render_trace()

# We already did the "hard" work of generating a test input for this simulation so
# we might want to reuse that work when we take this design through a verilog toolchain.
# The function output_verilog_testbench grabs the inputs used in the simulation trace
# and sets them up in a standar verilog testbench.

print "--- Verilog for the TestBench ---"
with io.BytesIO() as tbfile:
    pyrtl.output_verilog_testbench(tbfile, sim_trace)
    print tbfile.getvalue()


# Not let's talk about transformations of the hardware block.  Many times when you are
# doing some hardware-level analysis you might wish to ignore higher level things like
# multi-bit wirevectors, adds, concatination, etc. and just thing about wires and basic
# gates.  PyRTL supports "lowering" of designs into this more restricted set of functionality
# though the function "synthesize".  Once we lower a design to this form we can then apply
# basic optimizations like constant propgation and dead wire elimination as well.  By
# printing it out to verilog we can see exactly how the design changed.

print "--- Optimized Single-bit Verilog for the Counter ---"
pyrtl.synthesize()
pyrtl.optimize()

with io.BytesIO() as vfile:
    pyrtl.output_to_verilog(vfile)
    print vfile.getvalue()


# Finally, there is a handy way to view your hardware creations as a graph.  The function
# output_to_trivialgraph will ender your hardware a formal that you can then open with the
# free software "yEd" (http://en.wikipedia.org/wiki/YEd).  There are options under the
# "heirachical" rendering to draw something looks quite like a circuit.

print "--- Trivial Graph Format  ---"
with io.BytesIO() as tgf:
    pyrtl.output_to_trivialgraph(tgf)
    print tgf.getvalue()
