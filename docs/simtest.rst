Simulation and Testing
======================

Simulation
----------

.. autoclass:: pyrtl.simulation.Simulation
    :members:
    :special-members: __init__

Fast (JIT to Python) Simulation
-------------------------------

.. autoclass:: pyrtl.simulation.FastSimulation
    :members:
    :special-members: __init__

Compiled (JIT to C) Simulation
------------------------------

.. autoclass:: pyrtl.compilesim.CompiledSimulation
    :members:
    :special-members: __init__

Simulation Trace
----------------

.. autoclass:: pyrtl.simulation.SimulationTrace
    :members:
    :special-members: __init__

Wave Renderer
-------------

.. autoclass:: pyrtl.simulation.WaveRenderer
    :members:
    :special-members: __init__
    :exclude-members: render_ruler_segment, render_val, val_to_str
.. autofunction:: pyrtl.simulation.enum_name
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
