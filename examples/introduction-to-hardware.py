# coding: utf-8
""" Introduction to Hardware Design

    This code works through the hardware design process with the
    audience of software developers more in mind.  We start with the simple
    problem of designing a Fibonacci sequence calculator (http://oeis.org/A000045).
"""

import pyrtl


def software_fibonacci(n):
    """ A normal old Python function to return the Nth Fibonacci number. """
    a, b = 0, 1
    for i in range(n):
        a, b = b, a + b
    return a

# Iterative implementation of Fibonacci, just iteratively adds a and b to
# calculate the nth number in the sequence.
# >> [software_fibonacci(x) for x in range(10)]
# [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]


# So let's convert this into some hardware that computes the same thing.
# Our first go will be to just replace the 0 and 1 with WireVectors to see
# what happens.

def attempt1_hardware_fibonacci(n, bitwidth):
    a = pyrtl.Const(0)
    b = pyrtl.Const(1)
    for i in range(n):
        a, b = b, a + b
    return a

# The above looks really nice but does not really represent a hardware implementation
# of Fibonacci. Let's reason through the code, line by line, to figure out what
# it would actually build.
# a = pyrtl.Const(0)       -- This makes a WireVector of bitwidth=1 that is driven by
#                              a zero.  Thus "a" is a WireVector.  Seems good.
# b = pyrtl.Const(1)       -- Just like above, "b" is a WireVector driven by 1
#    for i in range(n):    -- Okay, here is where things start to go off the rails a bit.
#                             This says to perform the following code 'n' times, but the
#                             value 'n' is passed as an input and is not something that is
#                             evaluated in the hardware; it is evaluated when you run the
#                             PyRTL program which generates (or more specifically elaborates)
#                             the hardware.  Thus the hardware we are building will have
#                             the value of 'n' built into the hardware and won't actually
#                             be a run-time parameter.  Loops are really useful for building
#                             large repetitive hardware structures, but they CAN'T be used
#                             to represent hardware that should do a computation iteratively.
#                             Instead we are going to need to use some registers to build a
#                             state machine.
#        a, b = b, a + b   -- Let's break this apart.  In the first cycle b is Const(1) and
#                             (a + b) builds an adder with a (Const(0)) and b (Const(1)) as
#                             inputs.  Thus (b, a + b) in the first iteration is:
#                                 ( Const(1), result_of_adding( Const(0), Const(1) )
#                             At the end of the first iteration "a" and "b" refer to those
#                             two constant values.   In each following iteration more
#                             adders are built and the names "a" and "b" are bound to larger
#                             and larger trees of adders but all the inputs are constants!
#    return a              -- The final thing that is returned then is the last output from
#                             this tree of adders which all have Consts as inputs.   Thus
#                             this hardware is hard-wired to find only and exactly the value
#                             of Fibonacci of the value N specified at design time!  Probably
#                             not what you are intending.


# So let's try a different approach.  Let's specify two registers ("a" and "b") and then we
# can update those values as we iteratively compute Fibonacci of N cycle by cycle.

def attempt2_hardware_fibonacci(n, bitwidth):
    a = pyrtl.Register(bitwidth, 'a')
    b = pyrtl.Register(bitwidth, 'b')

    a.next <<= b
    b.next <<= a + b

    return a

# This is looking much better.  Two registers, "a" and "b", store the values from which we
# can compute the series.  The line "a.next <<= b" means that the value of "a" in the next
# cycle should be simply be "b" from the current cycle.  The line "b.next <<= a + b" says
# to build an adder with inputs of "a" and "b" from the current cycle and assign the value
# to "b" in the next cycle.  A visual representation of the hardware built is as such:
#
#      ┌─────┐     ┌─────┐
#      │     │     │     │
#      ▼     │     ▼     │
#   ▕▔▔▔▔▔▏  │  ▕▔▔▔▔▔▏  │
#   ▕  a  ▏  │  ▕  b  ▏  │
#   ▕▁▁▁▁▁▏  │  ▕▁▁▁▁▁▏  │
#      │     │     │     │
#      │     └─────┤     │
#      │           │     │
#      ▼           ▼     │
#    ╲▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔╱   │
#     ╲    adder    ╱    │
#      ╲▁▁▁▁▁▁▁▁▁▁▁╱     │
#            │           │
#            └───────────┘
#
# Note that in the picture the register "a" and "b" each have a WireVector which is
# the current value (shown flowing out of the bottom of the register) and an "input"
# which is giving the value that should be the value of the register in the following
# cycle (shown flowing into the top of the register) which are "b" and "a + b" respectively.
# When we say "return a" what we are returning is a reference to the register "a" in
# the picture above.


# Of course one problem is that we don't know when we are done.  How do we know we
# reached the "Nth" number in the sequence?  Well, we need to add a register to
# count up and see if we are done.

def attempt3_hardware_fibonacci(n, bitwidth):
    a = pyrtl.Register(bitwidth, 'a')
    b = pyrtl.Register(bitwidth, 'b')
    i = pyrtl.Register(bitwidth, 'i')

    i.next <<= i + 1
    a.next <<= b
    b.next <<= a + b

    return a, i == n

# This is very similar to the example before, except that now we have a register "i"
# which keeps track of the iteration that we are on (i.next <<= i + 1).  The function
# now returns two values, a reference to the register "a" and a reference to a single
# bit that tells us if we are done.  That bit is calculated by comparing "i" to the
# to a wirevector "n" that is passed in to see if they are the same.


# Finally, we need a way to indicate that we want a new Fibonacci number.
# We'll add another input, "req", which when high sets our "local_n" register and
# resets the others. Now our ending condition occurs when the current iteration "i" is
# equal to the locally stored "local_n".

def attempt4_hardware_fibonacci(n, req, bitwidth):
    a = pyrtl.Register(bitwidth, 'a')
    b = pyrtl.Register(bitwidth, 'b')
    i = pyrtl.Register(bitwidth, 'i')
    local_n = pyrtl.Register(bitwidth, 'local_n')
    done = pyrtl.WireVector(bitwidth=1, name='done')

    with pyrtl.conditional_assignment:
        with req:
            local_n.next |= n
            i.next |= 0
            a.next |= 0
            b.next |= 1
        with pyrtl.otherwise:
            i.next |= i + 1
            a.next |= b
            b.next |= a + b
    done <<= i == local_n
    return a, done


# This is now far enough along that we can simulate the design and see what happens.
# We begin by connecting our input and output wires to the implementation,
# stepping once with the 'req' signal high to signify we're beginning a
# a new request for a value, and then continuing to step until 'done' is emitted.
# Note that although the Fibonacci implementation only uses the value of 'n'
# when 'req' is high, we must still provide a value for 'n' (and all other inputs
# tracked by the simulator) for each step.

BITWIDTH = 8

n_in = pyrtl.Input(BITWIDTH, 'n_in')
req_in = pyrtl.Input(1, 'req_in')
fib_out = pyrtl.Output(BITWIDTH, 'fib_out')
done_out = pyrtl.Output(1, 'done_out')

output = attempt4_hardware_fibonacci(n_in, req_in, len(n_in))
fib_out <<= output[0]
done_out <<= output[1]

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

sim.step({'n_in': 7, 'req_in': 1})

sim.step({'n_in': 0, 'req_in': 0})
while not sim.inspect('done_out'):
    sim.step({'n_in': 0, 'req_in': 0})

sim_trace.render_trace(
    trace_list=['n_in', 'req_in', 'i', 'fib_out', 'done_out'], repr_func=int)
