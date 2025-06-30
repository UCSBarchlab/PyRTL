RTL Library
===========

Useful circuits, functions, and utilities.

Multiplexers
------------

.. automodule:: pyrtl.rtllib.muxes
   :members:
   :exclude-members: MultiSelector

Adders
------

.. automodule:: pyrtl.rtllib.adders
   :members:
   :undoc-members:

Multipliers
-----------

.. automodule:: pyrtl.rtllib.multipliers
   :members:

Barrel Shifter
--------------

.. automodule:: pyrtl.rtllib.barrel
   :members:
   :undoc-members:

Matrix
------

.. automodule:: pyrtl.rtllib.matrix
   :members:
   :special-members: __init__, __len__, __getitem__, __reversed__, __add__, __sub__, __mul__, __matmul__, __pow__
   :exclude-members: multiply

Pseudo-Random Numbers
---------------------

.. automodule:: pyrtl.rtllib.prngs
   :members:

AES-128
-------

.. autoclass:: pyrtl.rtllib.aes.AES
   :members:

Testing Utilities
-----------------

.. automodule:: pyrtl.rtllib.testingutils
   :members:
   :exclude-members: generate_in_wire_and_values, sim_and_ret_out, sim_and_ret_outws, sim_multicycle, multi_sim_multicycle
