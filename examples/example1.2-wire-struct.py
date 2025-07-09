# # Example 1.2: `wire_struct` and `wire_matrix()`.
#
# This example demonstrates named slicing with `wire_struct` and `wire_matrix()`:
# * `wire_struct`: Named `WireVector` slices. Names are alphanumeric, like a Python
#   namedtuple.
# * `wire_matrix()`: Indexed `WireVector` slices. Indices are integers, like a Python
#   list.
import inspect

import pyrtl

# ## Motivation
#
# `wire_struct` and `wire_matrix()` are syntactic sugar. They make PyRTL code easier to
# read and write, but they do not introduce any new functionality. We start with a
# motivating example that does not use `wire_struct` or `wire_matrix()`, point out some
# common problems, then rewrite the example with `wire_struct` to address those
# problems.
#
# This example deals with 24-bit pixel data. These 24 bits are composed of three
# concatenated components:
#
#     pixel:
#      ┌───────┬───────┬───────┐
#      │  red  │ green │ blue  │
#      └┬─────┬┴┬─────┬┴┬─────┬┘
#      23    16 15    8 7     0
#
# In other words:
# * The `red` component is in `pixel[16:24]`
# * The `green` component is in `pixel[8:16]`
# * And the `blue` component is in `pixel[0:8]`
#
# Accept a 24-bit pixel as a PyRTL `Input`:
pixel_in = pyrtl.Input(name="pixel_in", bitwidth=24)

# Split the pixel data into `red`, `green`, and `blue` components. The indices are
# manually calculated and hardcoded below. These calculations are prone to off-by-one
# errors. If we wanted to change the pixel data format (for example, adding an 8-bit
# `alpha` channel), we may need to update all these indices.
red_in = pixel_in[16:24]
red_in.name = "red_in"
green_in = pixel_in[8:16]
green_in.name = "green_in"
blue_in = pixel_in[0:8]
blue_in.name = "blue_in"

# Do some calculations on the individual components:
red_out = red_in + 0x11
green_out = green_in + 0x22
blue_out = blue_in + 0x33

# `red_out`, `green_out`, and `blue_out` are 9 bits wide, so they must be truncated back
# down to 8 bits before concatenating.
assert red_out.bitwidth == 9
assert green_out.bitwidth == 9
assert blue_out.bitwidth == 9

# Now `concat()` the processed components into a new output pixel. The components must
# be specified in the correct order, and we must `truncate()` them to the correct
# bitwidth.
pixel_out = pyrtl.concat(
    red_out.truncate(8), green_out.truncate(8), blue_out.truncate(8)
)
assert pixel_out.bitwidth == 24
pixel_out.name = "pixel_out"

# Test this slicing and concatenation logic.
print("Pixel slicing and concatenation without wire_struct:")
sim = pyrtl.Simulation()
sim.step_multiple(provided_inputs={"pixel_in": [0x112233, 0xAABBCC]})
sim.tracer.render_trace(
    trace_list=["pixel_in", "red_in", "green_in", "blue_in", "pixel_out"]
)

# ## Introducing `wire_struct`
#
# Start over, and rebuild the example with `wire_struct`.
pyrtl.reset_working_block()


# This `Pixel` class is the single source of truth that specifies how the `red`,
# `green`, and `blue` components are packed into 24 bits. A `Pixel` instance can do one
# of two things:
#
# 1. Slice a 24-bit value into `red`, `green`, and `blue` components, OR
# 2. Pack `red`, `green`, and `blue` components into a 24-bit value.
#
# Because this definition is the single source of truth, we can change the pixel data
# format just by changing this class definition. For example, try making the `red`
# component the last component, instead of the first component.
@pyrtl.wire_struct
class Pixel:
    # The most significant bits are specified first, so the `red` component is the 8
    # most significant bits, indices 16..23
    red: 8
    # The `green` component is the 8 middle bits, indices 8..15
    green: 8
    # The `blue` component is the 8 least significant bits, indices 0..7
    blue: 8


# `pixel_in` is a `Pixel` constructed from a 24-bit `Input`, option (1) above. The
# 24-bit `Input` will be sliced into 8-bit components, and those components can be
# manipulated as `pixel_in.red`, `pixel_in.green`, and `pixel_in.blue` in the Python
# code below.
#
# Because this `Pixel` has a name, the 8-bit components will be assigned the names
# `"pixel_in.red"`, `"pixel_in.green"`, and `"pixel_in.blue"`. These component names are
# included in the `trace_list` below.
pixel_in = Pixel(name="pixel_in", concatenated_type=pyrtl.Input)
assert pixel_in.bitwidth == 24
assert pixel_in.red.bitwidth == 8
assert pixel_in.green.bitwidth == 8
assert pixel_in.blue.bitwidth == 8

# Repeat our calculations with the named components. Components are accessed with "dot"
# notation (`.green`), like a Python namedtuple. There are no more hardcoded indices
# like `[8:16]` in this example.
red_out = pixel_in.red + 0x11
green_out = pixel_in.green + 0x22
blue_out = pixel_in.blue + 0x33

# `pixel_out` is a `Pixel` constructed from components, option (2) above. Components
# with more than 8 bits are implicitly truncated to 8 bits.
#
# Python keyword arguments are used for `red`, `green`, and `blue` here, so the order
# does not matter. We arbitrarily provide the value of the `green` component first.
pixel_out = Pixel(name="pixel_out", green=green_out, red=red_out, blue=blue_out)
assert pixel_out.bitwidth == 24

# Test this new version of our slicing and concatenation logic.
print("\nPixel slicing and concatenation with wire_struct:")
sim = pyrtl.Simulation()
sim.step_multiple(provided_inputs={"pixel_in": [0x112233, 0xAABBCC]})
sim.tracer.render_trace(
    trace_list=[
        "pixel_in",
        "pixel_in.red",
        "pixel_in.green",
        "pixel_in.blue",
        "pixel_out",
    ]
)

# ## Introducing `wire_matrix()`
#
# `wire_matrix()` is like `wire_struct`, except the components are indexed by integers,
# like a list.
#
# Start over.
pyrtl.reset_working_block()

# `PixelPair` is a pair of two `Pixels`. This also shows how `wire_matrix()` and
# `wire_struct` work together - `PixelPair` is a `wire_struct` nested in a
# `wire_matrix()`.
PixelPair = pyrtl.wire_matrix(component_schema=Pixel, size=2)

# `wire_matrix()` returns a class!
assert inspect.isclass(PixelPair)

# Create a `PixelPair` that decomposes a 48-bit input into two 24-bit `Pixels`. Each
# 24-bit `Pixel` can be further decomposed into 8-bit `red`, `green`, and `blue`
# components. This `PixelPair` has been assigned a name, so all its components are
# named, as seen in the simulation trace below.
pixel_pair_in = PixelPair(name="pixel_pair_in", concatenated_type=pyrtl.Input)
assert pixel_pair_in.bitwidth == 48
assert pixel_pair_in[0].bitwidth == 24
assert pixel_pair_in[0].red.bitwidth == 8

# Do some calculations on the `Pixel` components. Components are accessed with
# square-bracket notation (`[1]`), like a Python list.
pixel_pair_out_values = [
    Pixel(
        red=pixel_pair_in[0].red + 0x10,
        green=pixel_pair_in[0].green,
        blue=pixel_pair_in[0].blue,
    ),
    pixel_pair_in[1] + 1,
]

# Pack the new component values into a new `PixelPair`.
pixel_pair_out = PixelPair(name="pixel_pair_out", values=pixel_pair_out_values)

# Test out `PixelPair`.
print("\nPixelPair slicing and concatenating with wire_matrix:")
sim = pyrtl.Simulation()
sim.step_multiple(provided_inputs={"pixel_pair_in": [0x112233AABBCC, 0x445566778899]})
sim.tracer.render_trace(
    trace_list=[
        "pixel_pair_in",
        "pixel_pair_in[0]",
        "pixel_pair_in[0].red",
        "pixel_pair_in[0].green",
        "pixel_pair_in[0].blue",
        "pixel_pair_in[1]",
        "pixel_pair_in[1].red",
        "pixel_pair_in[1].green",
        "pixel_pair_in[1].blue",
        "pixel_pair_out",
    ]
)

# These examples hopefully show how `wire_matrix()` and `wire_struct` result in code
# that's easier to write correctly and easier to read.
#
# `wire_struct` and `wire_matrix()` have many more features, but this example should
# demonstrate the main ideas. See the documentation for more details:
#
# https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.wire_struct
#
# https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.wire_matrix
