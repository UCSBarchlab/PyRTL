Block and Logic Nets
=====================

:class:`.Block` and :class:`.LogicNet` are lower level PyRTL abstractions. Most
users won't need to understand them, unless they are implementing
:ref:`analysis_and_optimization` passes or modifying PyRTL itself.

Blocks
------

.. autoclass:: pyrtl.Block
    :members:
    :exclude-members: sanity_check_memblock, sanity_check_memory_sync, sanity_check_net, sanity_check_wirevector

.. _working_block:

``working_block``
^^^^^^^^^^^^^^^^^

Most PyRTL operations operate on the global ``working_block`` by default. PyRTL
provides several functions to inspect and manipulate the ``working_block``:

.. autofunction:: pyrtl.working_block

.. autofunction:: pyrtl.reset_working_block

.. autofunction:: pyrtl.set_working_block

.. autofunction:: pyrtl.temp_working_block

LogicNets
---------

.. autoclass:: pyrtl.LogicNet
    :members:
    :undoc-members:

GateGraphs
----------

.. automodule:: pyrtl.gate_graph

.. autoclass:: pyrtl.Gate
    :members:
    :special-members: __init__, __str__

.. autoclass:: pyrtl.GateGraph
    :members:
    :special-members: __init__, __str__

