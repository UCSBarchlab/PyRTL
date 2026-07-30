# # Render traces with various `WaveRenderer` options.

# Run this demo to see which options work well in your terminal.
import sys

import pyrtl


# Make some clock dividers and counters.
def make_clock(period: int):
    """Make a clock signal that inverts every `period` cycles."""
    assert period > 0

    # Build a chain of registers.
    first_reg = pyrtl.Register(bitwidth=1, name=f"clock_0_{period}", reset_value=1)
    last_reg = first_reg
    for offset in range(1, period):
        reg = pyrtl.Register(bitwidth=1, name=f"clock_{offset}_{period}")
        reg.next <<= last_reg
        last_reg = reg

    # The first register's input is the inverse of the last register's output.
    first_reg.next <<= ~last_reg
    return last_reg


def make_counter(period: int, bitwidth: int = 2):
    """Make a counter that increments every `period` cycles."""
    assert period > 0

    # Build a chain of registers.
    first_reg = pyrtl.Register(bitwidth=bitwidth, name=f"counter_0_{period}")
    last_reg = first_reg
    for offset in range(1, period):
        reg = pyrtl.Register(bitwidth=bitwidth, name=f"counter_{offset}_{period}")
        reg.next <<= last_reg
        last_reg = reg

    # The first register's input is the last register's output plus 1.
    first_reg.next <<= last_reg + pyrtl.Const(1)
    return last_reg


make_clock(period=1)
make_clock(period=2)
make_counter(period=1)
make_counter(period=2)

# Simulate 20 cycles.
sim = pyrtl.Simulation()
sim.step_multiple(nsteps=20)

# Render the trace with a variety of rendering options.
renderers = {
    "ascii": (
        pyrtl.simulation.AsciiRendererConstants(),
        "Basic 7-bit ASCII renderer",
    ),
}
unicode_renderers = {
    "utf-8": (
        pyrtl.simulation.Utf8RendererConstants(),
        "Unicode (default)",
    ),
    "utf-8-alt": (
        pyrtl.simulation.Utf8AltRendererConstants(),
        "Unicode, alternate display option",
    ),
    "utf-8-basic": (
        pyrtl.simulation.Utf8BasicRendererConstants(),
        "Unicode, basic display option",
    ),
    "powerline": (
        pyrtl.simulation.PowerlineRendererConstants(),
        "Requires a font with powerline glyphs",
    ),
}

if sys.stdout.encoding == "utf-8":
    renderers = renderers | unicode_renderers
else:
    print(
        "Terminal does not support UTF-8! Detected encoding: "
        f"{sys.stdout.encoding}. Disabling UTF-8 renderers."
    )

for name, (constants, notes) in renderers.items():
    print(f"# {notes}\n")
    print(f"$ export PYRTL_RENDERER={name}\n")
    sim.tracer.render_trace(
        renderer=pyrtl.simulation.WaveRenderer(constants), repr_func=int
    )
    print()
