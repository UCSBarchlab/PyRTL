Block and Logic Nets
=====================

Blocks
------

.. autoclass:: pyrtl.core.Block
    :members:
    :exclude-members: sanity_check_memblock, sanity_check_memory_sync, sanity_check_net, sanity_check_wirevector


``working_block``
^^^^^^^^^^^^^^^^^

Most PyRTL operations operate on the global ``working_block`` by default. PyRTL
provides several functions to inspect and manipulate the ``working_block``:

.. autofunction:: pyrtl.core.working_block

.. autofunction:: pyrtl.core.reset_working_block

.. autofunction:: pyrtl.core.set_working_block

.. autofunction:: pyrtl.core.temp_working_block

LogicNets
---------

.. autoclass:: pyrtl.core.LogicNet
    :members:
    :undoc-members:
