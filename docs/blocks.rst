Block and Logic Nets
=====================

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
