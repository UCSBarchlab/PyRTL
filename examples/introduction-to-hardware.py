""" Introduction to Hardware Design

    This code works through the hardware design process with the the
    audience of software developers more in mind.  We start with the simple
    problem of designing a fibonacci sequence calculator (http://oeis.org/A000045).
"""
import sys
sys.path.append("..")
import pyrtl


def software_fibonacci(n):
    """ a normal old python function to return the Nth fibonacci number. """
    a, b = 0, 1
    for i in range(n):
        a, b = b, a + b
    return a

# Interative implementation of fibonacci, just iteratively adds a and b to
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

# The above looks really nice does not really represent a hardware implementation
# of fibonacci. Let's reason through the code, line by line, to figure out what
# it would actually build.
# a = pyrtl.Const(0)       -- This makes a wirevector of bitwidth=1 that is driven by
#                              a zero.  Thus "a" is a wirevector.  Seems good.
# b = pyrtl.Const(1)       -- Just like above, "b" is a wirevector driven by 1
#    for i in range(n):    -- Okay, here is where things start to go off the rails a bit.
#                             This says to perform the following code 'n' times, but the
#                             value 'n' is passed as an input and is not something that is
#                             evaluated in the hardware, it is evaluated when you run the
#                             PyRTL program which generates (or more specifically elaborates)
#                             the hardware.  Thus the hardware we are building will have
#                             The value of 'n' built into the hardware and won't actually
#                             be a run-time parameter.  Loops are really useful for building
#                             large repetitive hardware structures, but they CAN'T be used
#                             to represent hardware that should do a computation iteratively.
#                             Instead we are going to need to use some registers to build a
#                             state machine.
#        a, b = b, a + b   -- Let's break this apart.  In the first cycle b is Const(1) and
#                             (a + b) builds an adder with a (Const(0)) and b (Const(1) as
#                             inputs.  Thus (b, a + b) in the first iteration is:
#                                 ( Const(1), result_of_adding( Const(0), Const(1) )
#                             At the end of the first iternation "a" and "b" refer to those
#                             two constant values.   In each following iteration more
#                             adders are built and the names "a" and "b" are bound to larger
#                             and larger trees of adders but all the inputs are constants!
#    return a              -- The final thing that is returned then is the last output from
#                             this tree of adders which all have Consts as inputs.   Thus
#                             this hardware is hard-wired to find only and exactly the value
#                             of fibonacci of the value N specified at design time!  Probably
#                             not what you are intending.


# So let's try a different approach.  Let's specify two registers ("a" and "b") and then we
# can update those values as we iteratively compute fibonacci of N cycle by cycle.

def attempt2_hardware_fibonacci(n, bitwidth):
    a = pyrtl.Register(bitwidth, 'a')
    b = pyrtl.Register(bitwidth, 'b')

    a.next <<= b
    b.next <<= a + b

    return a

# This is looking much better.  Two registers, "a" and "b" store the values from which we
# can compute the series.  The line "a.next <<= b" means that the value of a in the next
# cycle should be simply be "b" from the current cycle.  The line "b.next <<= a + b" says
# to build an adder, with inputs of "a" and "b" from the current cycle and assign the value
# to "b" in the next cycle.  A visual representation of the hardware built is as such:
#
#       +-----+      +---------+
#       |     |      |         |
#   +===V==+  |  +===V==+      |
#   |      |  |  |      |      |
#   |   a  |  |  |   b  |      |
#   |      |  |  |      |      |
#   +===V==+  |  +==V===+      |
#       |     |     |          |
#       |     +-----+          |
#       |           |          |
#   +===V===========V==+       |
#    \      adder     /        |
#     +==============+         |
#              |               |
#              +---------------+
#
# Note that in the picture the register "a" and "b" each have a wirevector which is
# the current value (shown flowing out of the bottom of the register) and an "input"
# which is giving the value that should be the value of the register in the following
# cycle (shown flowing into the top of the register) which are "a" and "a.next" respectively.
# When we say "return a" what we are returning is a reference to the register "a" in
# the picture above.


# Of course one problem is that we don't know when we are done?  How do we know we
# reached the "nth" number in the sequence?  Well, we need to add a register to
# count up and see if we are done.

def attempt3_hardware_fibonacci(n, bitwidth):
    a = pyrtl.Register(bitwidth, 'a')
    b = pyrtl.Register(bitwidth, 'b')
    i = pyrtl.Register(bitwidth, 'i')

    i.next <<= i + 1
    a.next <<= b
    b.next <<= a + b

    return a, i == n

# This is very similliar to the example before, except that now we have a register "i"
# which keeps track of the iteration that we are on (i.next <<= i + 1).  The function
# now returns two values, a reference to the register "a" and a reference to a single
# bit that tells us if we are done.  That bit is calculated by comparing "i" to the
# to a wirevector "n" that is passed in to see if they are the same.   This is now far
# enough along that we can simulate the design and see what happens...


def attempt4_hardware_fibonacci(n, req, bitwidth):
    a = pyrtl.Register(bitwidth, 'a')
    b = pyrtl.Register(bitwidth, 'b')
    i = pyrtl.Register(bitwidth, 'i')
    local_n = pyrtl.Register(bitwidth, 'local_n')
    done = pyrtl.WireVector(bitwidth=1, name='done')

    with pyrtl.ConditionalUpdate() as condition:
        with condition(req):
            local_n.next |= n
            i.next |= 0
            a.next |= 0
            b.next |= 1
        with condition.fallthrough:
            i.next |= i + 1
            a.next |= b
            b.next |= a + b
    done <<= i == local_n
    return a, done
