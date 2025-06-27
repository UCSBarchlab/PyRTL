.. PyRTL analysis master file

=========================
Analysis and Optimization
=========================

Tools for analyzing and optimizing aspects of PyRTL designs.

Estimation
----------

.. automodule:: pyrtl.analysis
   :members:
   :special-members: __init__

Optimization
------------

.. autofunction:: pyrtl.optimize

Synthesis
---------

.. autofunction:: pyrtl.synthesize

.. autoclass:: pyrtl.PostSynthBlock
   :show-inheritance:
   :members:

Individual Passes
-----------------

.. autofunction:: pyrtl.common_subexp_elimination
.. autofunction:: pyrtl.constant_propagation
.. autofunction:: pyrtl.nand_synth
.. autofunction:: pyrtl.and_inverter_synth
.. autofunction:: pyrtl.one_bit_selects
.. autofunction:: pyrtl.two_way_concat
