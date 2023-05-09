.. PyRTL analysis master file

.. default-domain:: pyrtl.rtllib

.. _top-of-page-analysis:


=========================
Analysis and Optimization
=========================

Provides tools for analyzing ad optimizing aspects of PyRTL designs

Estimation
----------

.. | :ref:`estimate-ref`

.. .. _estimate-ref:

.. automodule:: pyrtl.analysis
   :members:
   :special-members:
   :undoc-members:
   :exclude-members: __dict__,__weakref__,__module__

Optimization
------------

.. autofunction:: pyrtl.passes.optimize

Synthesis
---------

.. autofunction:: pyrtl.passes.synthesize

.. autoclass:: pyrtl.core.PostSynthBlock
   :show-inheritance:

Individual Passes
-----------------

.. autofunction:: pyrtl.passes.common_subexp_elimination
.. autofunction:: pyrtl.passes.constant_propagation
.. autofunction:: pyrtl.passes.nand_synth
.. autofunction:: pyrtl.passes.and_inverter_synth
.. autofunction:: pyrtl.passes.one_bit_selects
.. autofunction:: pyrtl.passes.two_way_concat

:ref:`Back to top of page <top-of-page-analysis>`
