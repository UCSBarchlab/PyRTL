# # Example 1.1: Working with signed integers.
#
# This example demonstrates:
# * Correct addition of signed integers with `signed_add()`.
# * Displaying signed integers in traces with `val_to_signed_integer()`.
#
# Signed integers are represented in two's complement.
# https://en.wikipedia.org/wiki/Two%27s_complement
import pyrtl

# ## Let's start with unsigned addition.
#
# Add all combinations of two unsigned 2-bit inputs.
a = pyrtl.Input(bitwidth=2, name="a")
b = pyrtl.Input(bitwidth=2, name="b")

unsigned_sum = pyrtl.Output(bitwidth=3, name="unsigned_sum")
unsigned_sum <<= a + b

# Try all combinations of {0, 1, 2, 3} + {0, 1, 2, 3}.
unsigned_inputs = {
    "a": [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3],
    "b": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3],
}

sim = pyrtl.Simulation()
sim.step_multiple(provided_inputs=unsigned_inputs)

# In this trace, `unsigned_sum` is the sum of all combinations of
# {0, 1, 2, 3} + {0, 1, 2, 3}. For example:
# * cycle  0 shows 0 + 0 = 0
# * cycle  1 shows 0 + 1 = 1
# * cycle 15 shows 3 + 3 = 6
print(
    "Unsigned addition. Each cycle adds a different combination of numbers.\n"
    "unsigned_sum == a + b"
)
sim.tracer.render_trace(repr_func=int)

# ## Re-interpreting `a`, `b`, and `unsigned_sum` as signed is **incorrect**.
#
# Use `val_to_signed_integer()` to re-interpret the previous simulation results
# as signed integers. But the results are **INCORRECT**, because `unsigned_sum`
# performed unsigned addition with `+`. For example:
#
# * cycle  2 shows 0 + -2 = 2
# * cycle 13 shows -1 + 1 = -4
#
# `unsigned_sum` is incorrect because PyRTL must extend `a` and `b` to the
# sum's bitwidth before adding, but PyRTL zero-extends by default, instead of
# sign-extending. Zero-extending is correct when `a` and `b` are unsigned, but
# sign-extending is correct when `a` and `b` are signed. Use `signed_add()` to
# sign-extend `a` and `b`, as demonstrated next.
print(
    "\nUse `val_to_signed_integer()` to re-interpret the previous simulation results as"
    "\nsigned integers. But re-interpreting the previous trace as signed integers \n"
    "produces INCORRECT RESULTS!"
)
sim.tracer.render_trace(repr_func=pyrtl.val_to_signed_integer)

# ## Use `signed_add()` to correctly add signed integers.
#
# `signed_add()` works by sign-extending its inputs to the sum's bitwidth before
# adding. There are many `signed_*` functions for signed operations, like
# `signed_sub()`, `signed_mult()`, `signed_lt()`, and so on.
pyrtl.reset_working_block()

a = pyrtl.Input(bitwidth=2, name="a")
b = pyrtl.Input(bitwidth=2, name="b")

signed_sum = pyrtl.Output(bitwidth=3, name="signed_sum")
signed_sum <<= pyrtl.signed_add(a, b)

# Try all combinations of {-2, -1, 0, 1} + {-2, -1, 0, 1}.
signed_inputs = {
    "a": [-2, -2, -2, -2, -1, -1, -1, -1, 0, 0, 0, 0, 1, 1, 1, 1],
    "b": [-2, -1, 0, 1, -2, -1, 0, 1, -2, -1, 0, 1, -2, -1, 0, 1],
}
sim = pyrtl.Simulation()
sim.step_multiple(provided_inputs=signed_inputs)

# In this trace, `signed_sum` is the sum of all combinations of
# {-2, -1, 0, 1} + {-2, -1, 0, 1}. For example:
# * cycle  0 shows -2 + -2 = -4
# * cycle  1 shows -2 + -1 = -3
# * cycle 15 shows 1 + 1 = 2
print(
    "\nReset the simulation and use `signed_add()` to correctly add signed integers.\n"
    "signed_sum == signed_add(a, b)"
)
sim.tracer.render_trace(repr_func=pyrtl.val_to_signed_integer)

# ## Manually sign-extend inputs to correctly add signed integers with `+`.
#
# Instead of using `signed_add()`, we can manually sign-extend the inputs with
# `sign_extended()` and `truncate()` the output to correctly add signed integers with
# `+`. Use this trick to implement other signed arithmetic operations.
pyrtl.reset_working_block()

a = pyrtl.Input(bitwidth=2, name="a")
b = pyrtl.Input(bitwidth=2, name="b")

# Using `+` produces the correct result for signed addition here because we
# manually extend `a` and `b` to 3 bits. The result of
#
#     a.sign_extended(3) + b.sign_extended(3)
#
# is now 4 bits, but we truncate it to 3 bits. This truncation is subtle, but important!
# The addition's full 4 bit result would not be correct.
sign_extended_sum = pyrtl.Output(bitwidth=3, name="sign_extended_sum")
extended_a = a.sign_extended(bitwidth=3)
extended_b = b.sign_extended(bitwidth=3)
sign_extended_sum <<= (extended_a + extended_b).truncate(bitwidth=3)

# Try all combinations of {-2, -1, 0, 1} + {-2, -1, 0, 1}.
signed_inputs = {
    "a": [-2, -2, -2, -2, -1, -1, -1, -1, 0, 0, 0, 0, 1, 1, 1, 1],
    "b": [-2, -1, 0, 1, -2, -1, 0, 1, -2, -1, 0, 1, -2, -1, 0, 1],
}
sim = pyrtl.Simulation()
sim.step_multiple(provided_inputs=signed_inputs)

print(
    "\nInstead of using `signed_add()`, we can also manually sign extend the inputs to"
    "\ncorrectly add signed integers with `+`.\nsign_extended_sum == "
    "(a.sign_extended(3) + b.sign_extended(3)).truncate(3)"
)
sim.tracer.render_trace(repr_func=pyrtl.val_to_signed_integer)
