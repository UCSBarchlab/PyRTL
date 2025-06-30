=====
PYRTL
=====

A collection of classes providing simple `RTL
<https://en.wikipedia.org/wiki/Register-transfer_level>`_ specification,
simulation, tracing, and testing suitable for teaching and research.
Simplicity, usability, clarity, and extensibility rather than performance or
optimization is the overarching goal. With PyRTL you can use the full power of
Python to describe complex synthesizable digital designs, simulate and test
them, and export them to `Verilog <https://en.wikipedia.org/wiki/Verilog>`_.

Quick links
===========
* Get an overview from the `PyRTL Project Webpage <http://ucsbarchlab.github.io/PyRTL/>`_
* Read through `Example PyRTL Code <https://github.com/UCSBarchlab/PyRTL/tree/development/examples>`_
* File a `Bug or Issue Report <https://github.com/UCSBarchlab/PyRTL/issues>`_
* Contribute to project on `GitHub <https://github.com/UCSBarchlab/PyRTL>`_

Installation
============

**Automatic installation**::

    pip install pyrtl

PyRTL is listed in `PyPI <http://pypi.python.org/pypi/pyrtl>`_ and can be
installed with :program:`pip` or :program:`pip3`.

Design, Simulate, and Inspect in 15 lines
=========================================

.. code-block::
    :linenos:

    import pyrtl

    a = pyrtl.Input(8,'a')  # input "pins"
    b = pyrtl.Input(8,'b')
    q = pyrtl.Output(8,'q')  # output "pins"
    gt5 = pyrtl.Output(1,'gt5')

    result = a + b  # makes an 8-bit adder
    q <<= result  # assigns output of adder to out pin
    gt5 <<= result > 5  # does a comparison, assigns that to different pin

    # simulate and output the resulting waveform to the terminal
    sim = pyrtl.Simulation()
    sim.step_multiple({'a':[0,1,2,3,4], 'b':[2,2,3,3,4]})
    sim.tracer.render_trace()

After you have PyRTL installed, you should be able to cut and paste the above
into a file and run it with Python. The result you should see, drawn right into
the terminal, is the output of the simulation. While a great deal of work has
gone into making hardware design in PyRTL as friendly as possible, please don't
mistake that for a lack of depth. You can just as easily export to Verilog or
other hardware formats, view results with your favorite waveform viewer, build
hardware transformation passes, run JIT-accelerated simulations, design, test,
verify hugely complex digital systems, and much more. Most critically of all it
is easy to extend with your own approaches to digital hardware development as
you find necessary.


Overview of PyRTL
=================

If you are brand new to PyRTL we recommend that you start with the `PyRTL Code
Examples <https://github.com/UCSBarchlab/PyRTL/tree/development/examples>`_
which will show you most of the core functionality in the context of a complete
design.

``WireVectors``
---------------

Perhaps the most important class to understand is :class:`.WireVector`, which is the
basic type from which you build all hardware. If you are coming to PyRTL from Verilog, a
:class:`.WireVector` is closest to a multi-bit `wire`. Every new :class:`.WireVector`
builds a set of wires which you can then connect with other :class:`.WireVector` through
overloaded operations such as :meth:`~.WireVector.__add__` or
:meth:`~.WireVector.__or__`.

A bunch of other related classes, including :class:`.Input`, :class:`.Output`,
:class:`.Const`, and :class:`.Register` are all derived from
:class:`.WireVector`. Coupled with :class:`.MemBlock` (and :class:`.RomBlock`),
this is all a user needs to create a functional hardware design.

.. inheritance-diagram:: pyrtl.WireVector
                         pyrtl.Input
                         pyrtl.Output
                         pyrtl.Const
                         pyrtl.Register
    :parts: 1

After specifying a hardware design, there are then options to simulate your
design right in PyRTL, synthesize it down to primitive 1-bit operations,
optimize it, and export it to Verilog (along with a testbench).

Simulation
----------

PyRTL provides tools for simulation and viewing simulation traces. Simulation
is how your hardware is "executed" for the purposes of testing, and three
different classes help you do that: :class:`.Simulation`,
:class:`.FastSimulation` and :class:`.CompiledSimulation`.  All three have
`almost` the same interface and, except for a few debugging cases, can be used
interchangeably.  Typically one starts with :class:`.Simulation` and then moves
up to :class:`.FastSimulation` when performance begins to matter.

Both :class:`.Simulation` and :class:`.FastSimulation` store a list of each
wire's value in each cycle in :attr:`.Simulation.tracer`, which is an instance
of :class:`.SimulationTrace`. Traces can then be rendered to the terminal with
:meth:`.SimulationTrace.render_trace`.
:class:`SimulationTraces<.SimulationTrace>` can be handled in other ways, for
example they can be extracted as a test bench with
:func:`.output_verilog_testbench`, or exported to a VCD file with
:meth:`~.SimulationTrace.print_vcd`.

Optimization
------------

:class:`.WireVector` and :class:`.MemBlock` are just "sugar" over a core set of
primitives, and the final design is built up incrementally as a graph of these
primitives. :class:`WireVectors<.WireVector>` connects these "primitives",
which connect to other :class:`WireVectors<.WireVector>`. Each primitive is a
:class:`.LogicNet`, and a :class:`.Block` is a graph of
:class:`LogicNets<.LogicNet>`. Typically a full design is stored in a single
:class:`.Block`.  The function :func:`.working_block()` returns the block on
which we are implicitly working.  Hardware transforms may make a new
:class:`.Block` from an old one. For example, see :class:`.PostSynthBlock`.

Errors
------

Finally, when things go wrong you may hit an :class:`Exception`, neither of which is
likely recoverable automatically (which is why we limited them to only two types).
:class:`.PyrtlError` is intended to capture end user errors such as invalid constant
strings and mis-matched bitwidths. In contrast, :class:`.PyrtlInternalError` captures
internal invariants and assertions over the core logic graph which should never be
encountered when constructing designs in the normal ways. If you hit a confusing
:class:`.PyrtlError` or any :class:`.PyrtlInternalError` feel free to file an issue.

.. autoclass:: pyrtl.PyrtlError
    :members:

.. autoclass:: pyrtl.PyrtlInternalError
    :members:

Reference Guide
===============
.. toctree::
   :maxdepth: 2

   basic
   regmem
   simtest
   helpers
   blocks
   analysis
   export
   rtllib

Index
=====
* :ref:`genindex`
