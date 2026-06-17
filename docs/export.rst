Exporting and Importing Designs
===============================

Exporting Hardware Designs
--------------------------

.. autofunction:: pyrtl.output_to_verilog
.. autofunction:: pyrtl.output_to_firrtl

Exporting Testbenches
---------------------

.. autofunction:: pyrtl.output_verilog_testbench

Importing Verilog
-----------------

.. autofunction:: pyrtl.input_from_blif
.. autofunction:: pyrtl.input_from_verilog

Visualizing Blocks
------------------

:class:`.Block` and :class:`.GateGraph` provides basic ``__str__`` methods for
visualizing blocks::

    >>> a = pyrtl.Input(name="a", bitwidth=3)
    >>> b = pyrtl.Input(name="b", bitwidth=3)
    >>> sum = a + b
    >>> sum.name = "sum"

    >>> print(pyrtl.working_block())
    sum/4W <-- + -- a/3I, b/3I

    >>> print(pyrtl.GateGraph())
    a/3 = Input
    b/3 = Input
    sum/4 = add(a/3, b/3)

This section covers more advanced visualization methods.

.. autofunction:: pyrtl.block_to_svg
.. autofunction:: pyrtl.block_to_graphviz_string
.. autofunction:: pyrtl.graphviz_detailed_namer
.. autofunction:: pyrtl.output_to_trivialgraph

Visualizing Simulation Traces
-----------------------------

:class:`.SimulationTrace` has :meth:`~.SimulationTrace.render_trace` and
:meth:`~.SimulationTrace.print_vcd` methods which cover most common use cases.
This section covers an additional visualization method.

.. autofunction:: pyrtl.trace_to_json
