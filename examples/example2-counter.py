# # Example 2: A Counter with Ripple Carry Adder.
#
# This next example shows how you make stateful things with registers and more complex
# hardware structures with functions. We generate a 3-bit ripple carry adder, building
# off of the 1-bit adder from Example 1, and then hook it to a register to count
# up modulo 8.
import pyrtl


# Let's just dive right in.
#
# A function in PyRTL is nothing special -- it just so happens that the statements it
# encapsulate tell PyRTL to build some hardware.
def one_bit_add(
    a: pyrtl.WireVector, b: pyrtl.WireVector, carry_in: pyrtl.WireVector
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    assert len(a) == len(b) == 1  # len returns the bitwidth
    sum = a ^ b ^ carry_in
    carry_out = a & b | a & carry_in | b & carry_in
    return sum, carry_out


# If we call `one_bit_add` above with the arguments `x`, `y`, and `z`, it will make a
# one-bit adder to add those values together, returning `WireVectors` for `sum` and
# `carry_out` as applied to `x`, `y`, and `z`. If I call it again on `i`, `j`, and `k`
# it will build a new one-bit adder for those inputs and return the resulting `sum` and
# `carry_out` for that adder.
#
# While PyRTL actually provides an `+` operator for `WireVectors` which generates
# adders, a ripple carry adder is something people can understand easily but has enough
# structure to be mildly interesting. Let's define an adder of arbitrary length
# recursively and (hopefully) Pythonically. More comments after the code.
def ripple_add(
    a: pyrtl.WireVector, b: pyrtl.WireVector, carry_in: pyrtl.WireVector = 0
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    a, b = pyrtl.match_bitwidth(a, b)
    # This function is a function that allows us to match the bitwidth of multiple
    # different wires. By default, it zero extends the shorter bits
    if len(a) == 1:
        return one_bit_add(a, b, carry_in)
    lsb, ripple_carry = one_bit_add(a[0], b[0], carry_in)
    msbits, carry_out = ripple_add(a[1:], b[1:], ripple_carry)
    return pyrtl.concat(msbits, lsb), carry_out


# ## The above code breaks down into two cases:
#
# 1. If `a` is one-bit wide, just do a `one_bit_add`.
# 2. Otherwise, do a `one_bit_add` on the least significant bits, `ripple_add` the rest,
#    and then stick the results back together into one `WireVector`.
#
# ## A couple interesting features of PyRTL can be seen here:
#
# * WireVectors can be indexed like lists, with `[0]` accessing the least significant
#   bit and `[1:]` accessing the remaining bits. Python slicing is supported, with the
#   usual `start:stop:stop` syntax.
# * While you can add two lists together in Python, a `WireVector` + `WireVector` means
#   "make an adder". To concatenate the bits of two `WireVectors` one needs to use
#   `concat()`.
# * Finally, if we look at `carry_in` it seems to have a default value of the integer
#   `0` but is a `WireVector` at other times. Python supports polymorphism throughout
#   and PyRTL will cast integers and some other types to `WireVectors` when it can.
#
# Now let's build a 3-bit counter from our N-bit ripple carry adder.
counter = pyrtl.Register(bitwidth=3, name="counter")
sum, carry_out = ripple_add(counter, pyrtl.Const("1'b1"))
counter.next <<= sum

# ## A few new things in the above code:
#
# * The two remaining types of basic `WireVectors`, `Const` and `Register`, both appear.
#   `Const`, unsurprisingly, is just for holding constants (such as the `0` in
#   `ripple_add`), but here we create one explicitly with a Verilog-like string which
#   includes both the value and the bitwidth.
# * `Registers` are just like `WireVectors`, except their updates are delayed to the
#   next clock cycle. This is made explicit in the syntax through the property `.next`
#   which should always be set for registers.
# * In this simple example, we make the counter's value on the next cycle equal to the
#   counter's value this cycle plus one.
#
# Now let's run the bugger. No need for `Inputs`, as this circuit doesn't have any.
# Finally we'll print the trace to the screen and check that it counts up correctly.
sim = pyrtl.Simulation()
for cycle in range(15):
    sim.step()
    assert sim.value[counter] == cycle % 8
sim.tracer.render_trace()
