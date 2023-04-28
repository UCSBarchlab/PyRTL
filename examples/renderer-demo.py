import pyrtl

"""Render traces with various WaveRenderer options.

Run this demo to see which options work well in your terminal.

"""


def make_clock(n: int):
    """Make a clock signal that inverts every 'n' cycles."""
    assert n > 0
    first_state = pyrtl.Register(bitwidth=1, name=f'clock_0_{n}',
                                 reset_value=1)
    last_state = first_state
    for i in range(1, n):
        state = pyrtl.Register(bitwidth=1, name=f'clock_{i}_{n}')
        state.next <<= last_state
        last_state = state

    first_state.next <<= ~last_state
    return last_state


def make_counter(n: int):
    """Make a counter that increments every 'n' cycles."""
    assert n > 0
    first_state = pyrtl.Register(bitwidth=8, name=f'counter_0_{n}')
    last_state = first_state
    for i in range(1, n):
        state = pyrtl.Register(bitwidth=8, name=f'counter_{i}_{n}')
        state.next <<= last_state
        last_state = state

    first_state.next <<= last_state + pyrtl.Const(1)
    return last_state


make_clock(n=1)
make_clock(n=2)
make_counter(n=1)
make_counter(n=2)

# Simulate 10 cycles.
sim = pyrtl.Simulation()
sim.step_multiple(nsteps=10)

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
    print(f'export PYRTL_RENDERER={name}')
    sim.tracer.render_trace(
        renderer=pyrtl.simulation.WaveRenderer(constants),
        repr_func=int)
    print()
