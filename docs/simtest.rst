Simulation and Testing
======================

Simulation
----------

.. autoclass:: pyrtl.Simulation
    :members:
    :special-members: __init__

Fast (JIT to Python) Simulation
-------------------------------

.. autoclass:: pyrtl.FastSimulation
    :members:
    :special-members: __init__

Compiled (JIT to C) Simulation
------------------------------

.. autoclass:: pyrtl.CompiledSimulation
    :members:
    :exclude-members: run

Simulation Trace
----------------

.. autoclass:: pyrtl.SimulationTrace
    :members:
    :special-members: __init__
    :exclude-members: add_fast_step, add_step

.. autofunction:: pyrtl.enum_name

Wave Renderer
-------------

.. autoclass:: pyrtl.simulation.WaveRenderer
    :members:
    :special-members: __init__
    :exclude-members: render_ruler_segment, render_val, val_to_str
.. autoclass:: pyrtl.simulation.RendererConstants
.. autoclass:: pyrtl.simulation.PowerlineRendererConstants
    :show-inheritance:
.. autoclass:: pyrtl.simulation.Utf8RendererConstants
    :show-inheritance:
.. autoclass:: pyrtl.simulation.Utf8AltRendererConstants
    :show-inheritance:
.. autoclass:: pyrtl.simulation.Cp437RendererConstants
    :show-inheritance:
.. autoclass:: pyrtl.simulation.AsciiRendererConstants
    :show-inheritance:
