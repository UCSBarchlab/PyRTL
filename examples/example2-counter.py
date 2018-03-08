""" Example 2:  A Counter with Ripple Carry Adder.

    This next example shows how you make stateful things with registers
    and more complex hardware structures with functions.  We generate
    a 3-bit ripple carry adder building off of the 1-bit adder from
    the prior example, and then hook it to a register to count up modulo 8.
"""

import pyrtl


# Let's just dive right in.

def one_bit_add(a, b, carry_in):
    assert len(a) == len(b) == 1  # len returns the bitwidth
    sum = a ^ b ^ carry_in
    carry_out = a & b | a & carry_in | b & carry_in
    return sum, carry_out

# A function in PyRTL is nothing special -- it just so happens that the statements
# it encapsulate tell PyRTL to build some hardware.  If I we to call "one_bit_add"
# above with the arguments "x", "y", and "z" it will make a one-bit adder to add
# those values together and return the wires for sum and carry_out as applied to "x",
# "y", and "z".  If I call it again on "i", "j", and "k" it will build a new one-bit
# adder for those inputs and return the resulting sum and carry_out for that adder.


# While PyRTL actually provides an "+" operator for wirevectors which generates
# adders, a ripple carry adder is something people can understand easily but has
# enough structure to be mildly interesting.  Let's define an adder of arbitrary
# length recursively and (hopefully) pythonically.  More comments after the code.

def ripple_add(a, b, carry_in=0):
    a, b = pyrtl.match_bitwidth(a, b)
    # this function is a function that allows us to match the bitwidth of multiple
    # different wires. By default, it zero extends the shorter bits
    if len(a) == 1:
        sumbits, carry_out = one_bit_add(a, b, carry_in)
    else:
        lsbit, ripplecarry = one_bit_add(a[0], b[0], carry_in)
        msbits, carry_out = ripple_add(a[1:], b[1:], ripplecarry)
        sumbits = pyrtl.concat(msbits, lsbit)
    return sumbits, carry_out

# The above code breaks down into two cases. 1) If the size of the inputs
# is one-bit just do one_bit_add.  2) if they are more than one bit, do
# a one-bit add on the least significant bits, a ripple carry on the rest,
# and then stick the results back together into one WireVector.  A couple
# interesting features of PyRTL can be seen here:  WireVectors can be indexed
# like lists, with [0] accessing the least significant bit and [1:] being an
# example of the use of Python slicing syntax.  While you can add two lists
# together in python a WireVector + Wirevector means "make an adder" so to
# concatenate the bits of two vectors one need to use "concat".  Finally,
# if we look at "cin" it seems to have a default value of the integer "0" but
# is a WireVector at other times.  Python supports polymorphism throughout
# and PyRTL will cast integers and some other types to WireVectors when it can.

# Now let's build a 3-bit counter from our N-bit ripple carry adder.

counter = pyrtl.Register(bitwidth=3, name='counter')
sum, carry_out = ripple_add(counter, pyrtl.Const("1'b1"))
counter.next <<= sum

# A couple new things in the above code.  The two remaining types of basic
# WireVectors, Const and Register, both  appear.  Const, unsurprisingly, is just for
# holding constants (such as the 0 in ripple_add), but here we create one directly
# from a Verilog-like string which includes both the value and the bitwidth.
# Registers are just like wires, except their updates are delayed to the next
# clock cycle.  This is made explicit in the syntax through the property '.next'
# which should always be set for registers.  In this simple example, we take
# counter next cycle equal to counter this cycle plus one.

# Now let's run the bugger.  No need for inputs, as it doesn't have any.
# Finally we'll print the trace to the screen and check that it counts up correctly.

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in range(15):
    sim.step({})
    assert sim.value[counter] == cycle % 8
sim_trace.render_trace()

# all done.

exit(0)
