# # Introduction to Hardware Design

# This code works through the hardware design process with the audience of software
# developers more in mind. We start with the simple problem of designing a Fibonacci
# sequence calculator (http://oeis.org/A000045).
import pyrtl


# ## Software Fibonacci implementation
def software_fibonacci(n: int):
    """An ordinary Python function to return the `n`th Fibonacci number."""
    a = 0
    b = 1
    for _ in range(n):
        a, b = b, a + b
    return a


# `software_fibonacci` is an iterative Fibonacci implementation. It repeatedly adds `a`
# and `b` to calculate the `n`th number in the sequence.
print("n   software_fibonacci(n)")
print("─────────────────────────")
for n in range(10):
    print(n, " ", software_fibonacci(n))


# ## Hardware Fibonacci implementation, first attempt
#
# So let's convert this into some hardware that computes the same thing. Our first go
# will be to just replace the `0` and `1` with `WireVectors` to see what happens.
def attempt1_hardware_fibonacci(n: int) -> pyrtl.WireVector:
    a = pyrtl.Const(0)
    b = pyrtl.Const(1)
    for _ in range(n):
        a, b = b, a + b
    return a


# The above looks really nice but does not really represent a hardware implementation
# of Fibonacci. Let's reason through the code, line by line, to figure out what
# it would actually build.
#
#     a = pyrtl.Const(0)      # ← This makes a `WireVector` with `bitwidth=1` that is
#                             #   driven by a zero.  Thus `a` is a `WireVector`.  Seems
#                             #   good.
#     b = pyrtl.Const(1)      # ← Just like above, `b` is a `WireVector` driven by `1`.
#        for i in range(n):   # ← Okay, here is where things start to go off the rails a
#                             #   bit. This says to perform the following code `n`
#                             #   times, but the value `n` is passed as an argument and
#                             #   is not something that is evaluated in the hardware; it
#                             #   is evaluated when you run the PyRTL program which
#                             #   generates (or more specifically elaborates) the
#                             #   hardware. Thus the hardware we are building will have
#                             #   the value of `n` built into the hardware and won't
#                             #   actually be a run-time parameter. Loops are useful for
#                             #   building large repetitive hardware structures, but
#                             #   they CAN'T be used to represent hardware that should
#                             #   do a computation iteratively. Instead we will need
#                             #   some `Registers` to build a state machine.
#            a, b = b, a + b  # ← Let's break this apart. In the first cycle, `a` is
#                             #   `Const(0) and `b` is `Const(1)`, so `(a + b)` builds
#                             #   an adder with `Const(0)` and `Const(1)` as inputs.
#                             #   So `(b, a + b)` in the first iteration evaluates to:
#                             #   `(Const(1), result_of_adding(Const(0), Const(1)))`.
#                             #   At the end of the first iteration, `a` and `b` refer
#                             #   to those two constant values. In each following
#                             #   iteration more adders are built and the Python
#                             #   variables `a` and `b` are bound to larger and larger
#                             #   trees of adders. But all the adder inputs are
#                             #   constants!
#        return a             # ← The final thing that is returned then is the last
#                             #   output from this tree of adders which all have
#                             #   `Consts` as inputs. Thus this hardware is hard-wired
#                             #   to produce only the exact the value of the `n`th
#                             #   Fibonacci number, where `n` is hard-coded into the
#                             #   design! This is most likely not what you want.
#
# ## Hardware Fibonacci implementation, second attempt
#
# So let's try a different approach. Let's specify two registers (`a` and `b`) and then
# we can update those values as we iteratively compute the `n`th Fibonacci number cycle
# by cycle.
def attempt2_hardware_fibonacci(bitwidth: int) -> pyrtl.WireVector:
    a = pyrtl.Register(bitwidth, "a")
    b = pyrtl.Register(bitwidth, "b")

    a.next <<= b
    b.next <<= a + b

    return a


# This is looking much better. Two registers, `a` and `b`, store the values from which
# we can compute the series. The line `a.next <<= b` means that the value of `a` in the
# next cycle should be simply be `b` from the current cycle. The line `b.next <<= a + b`
# says to build an adder with inputs of `a` and `b` from the current cycle and assign
# the value to `b` in the next cycle. A visual representation of the hardware built is
# as such:
#
#        ┌─────┐     ┌─────┐
#        │     │     │     │
#        ▼     │     ▼     │
#     ▕▔▔▔▔▔▏  │  ▕▔▔▔▔▔▏  │
#     ▕  a  ▏  │  ▕  b  ▏  │
#     ▕▁▁▁▁▁▏  │  ▕▁▁▁▁▁▏  │
#        │     │     │     │
#        │     └─────┤     │
#        │           │     │
#        ▼           ▼     │
#      ╲▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔╱   │
#       ╲    adder    ╱    │
#        ╲▁▁▁▁▁▁▁▁▁▁▁╱     │
#              │           │
#              └───────────┘
#
# Note that in the picture the register `a` and `b` each have a `WireVector` which is
# the current value (shown flowing out of the bottom of the register) and an "input"
# which is giving the value that should be the value of the register in the following
# cycle (shown flowing into the top of the register) which are `b` and `a + b`
# respectively. When we say `return a` what we are returning is a reference to the
# register `a` in the picture above.
#
# ## Hardware Fibonacci implementation, third attempt
#
# Of course one problem is that we don't know when we are done. How do we know we
# reached the `n`th number in the sequence? Well, we need to add a `Register` to keep
# count and see if we are done.
def attempt3_hardware_fibonacci(
    n: pyrtl.WireVector,
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    a = pyrtl.Register(bitwidth=n.bitwidth, name="a")
    b = pyrtl.Register(bitwidth=n.bitwidth, name="b")
    counter = pyrtl.Register(bitwidth=n.bitwidth, name="counter")

    counter.next <<= counter + 1
    a.next <<= b
    b.next <<= a + b

    return a, counter == n


# This is very similar to the example before, except that now we have a register
# `counter` which keeps track of the iteration that we are on:
#     counter.next <<= counter + 1
# The function now returns two values, a reference to the register `a` and a reference
# to a single bit that tells us if we are done. That bit is calculated by comparing
# `counter` to the to a WireVector `n` that is passed in to see if they are the same.
#
# ## Hardware Fibonacci implementation, fourth attempt
#
# Finally, we need a way to indicate that we want a new Fibonacci number. We'll add
# another input, `start`, which when high sets our `local_n` register and resets the
# others. Now our ending condition occurs when the current iteration `counter` is equal
# to the locally stored `local_n`.
def attempt4_hardware_fibonacci(
    n: pyrtl.WireVector, start: pyrtl.WireVector
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    a = pyrtl.Register(bitwidth=n.bitwidth, name="a")
    b = pyrtl.Register(bitwidth=n.bitwidth, name="b")
    counter = pyrtl.Register(bitwidth=n.bitwidth, name="counter")
    local_n = pyrtl.Register(bitwidth=n.bitwidth, name="local_n")
    local_done = pyrtl.WireVector(bitwidth=1, name="local_done")

    with pyrtl.conditional_assignment:
        with start:
            local_n.next |= n
            counter.next |= 0
            a.next |= 0
            b.next |= 1
        with pyrtl.otherwise:
            counter.next |= counter + 1
            a.next |= b
            b.next |= a + b
    local_done <<= counter == local_n
    return a, local_done


# ## Simulating the hardware Fibonacci implementation
#
# This is now far enough along that we can simulate the design and see what happens. We
# begin by connecting our input and output wires to the implementation, stepping once
# with the `start` signal high to signify we're starting a new Fibonacci request, and
# then continuing to `step()` until `done` is asserted. Note that although the Fibonacci
# implementation only uses the value of `n` when `start` is high, we must still provide
# a value for `n` (and all other `Inputs` tracked by the `Simulation`) for each
# `step()`.
print("\nHardware Fibonacci Simulation:")
n = pyrtl.Input(bitwidth=8, name="n")
start = pyrtl.Input(bitwidth=1, name="start")
fib_out = pyrtl.Output(bitwidth=8, name="fib")
done_out = pyrtl.Output(bitwidth=1, name="done")

fib, done = attempt4_hardware_fibonacci(n, start)
fib_out <<= fib
done_out <<= done

sim = pyrtl.Simulation()

sim.step({"n": 7, "start": 1})

sim.step({"n": 0, "start": 0})
while not sim.inspect("done"):
    sim.step({"n": 0, "start": 0})

sim.tracer.render_trace(
    trace_list=["n", "start", "counter", "fib", "done"], repr_func=int
)

assert sim.inspect("fib") == software_fibonacci(7)
