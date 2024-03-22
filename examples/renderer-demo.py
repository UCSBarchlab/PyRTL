import pyrtl

"""Render traces with various WaveRenderer options.

Run this demo to see which options work well in your terminal.

"""


def make_clock(period: int):
    """Make a clock signal that inverts every `period` cycles."""
    assert period > 0

    # Build a chain of registers.
    first_reg = pyrtl.Register(bitwidth=1, name=f'clock_0_{period}',
                               reset_value=1)
    last_reg = first_reg
    for offset in range(1, period):
        reg = pyrtl.Register(bitwidth=1, name=f'clock_{offset}_{period}')
        reg.next <<= last_reg
        last_reg = reg

    # The first register's input is the inverse of the last register's output.
    first_reg.next <<= ~last_reg
    return last_reg


def make_counter(period: int, bitwidth=2):
    """Make a counter that increments every `period` cycles."""
    assert period > 0

    # Build a chain of registers.
    first_reg = pyrtl.Register(bitwidth=bitwidth, name=f'counter_0_{period}')
    last_reg = first_reg
    for offset in range(1, period):
        reg = pyrtl.Register(bitwidth=bitwidth,
                             name=f'counter_{offset}_{period}')
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
    'powerline': (pyrtl.simulation.PowerlineRendererConstants(),
                  'Requires a font with powerline glyphs'),
    'utf-8': (pyrtl.simulation.Utf8RendererConstants(),
              'Unicode, default non-Windows renderer'),
    'utf-8-alt': (pyrtl.simulation.Utf8AltRendererConstants(),
                  'Unicode, alternate display option'),
    'cp437': (pyrtl.simulation.Cp437RendererConstants(),
              'Code page 437 (8-bit ASCII), default Windows renderer'),
    'ascii': (pyrtl.simulation.AsciiRendererConstants(),
              'Basic 7-bit ASCII renderer'),
}

for i, name in enumerate(renderers):
    constants, notes = renderers[name]
    print(f'# {notes}')
    print(f'export PYRTL_RENDERER={name}\n')
    sim.tracer.render_trace(
        renderer=pyrtl.simulation.WaveRenderer(constants),
        repr_func=int)
    print()
