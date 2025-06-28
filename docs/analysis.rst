.. PyRTL analysis master file

.. _analysis_and_optimization:

Analysis and Optimization
=========================

Tools for analyzing and optimizing aspects of PyRTL designs.

Estimation
----------

.. autoclass:: pyrtl.TimingAnalysis
   :members:
   :special-members: __init__

.. autofunction:: pyrtl.area_estimation
.. autofunction:: pyrtl.distance
.. autofunction:: pyrtl.fanout
.. autoclass:: pyrtl.analysis.PathsResult
   :members:
.. autofunction:: pyrtl.paths
.. autofunction:: pyrtl.yosys_area_delay

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
