=====
PYRTL
=====

A collection of classes providing simple RTL specification, simulation,
tracing, and testing suitable for teaching and research. Simplicity, usability,
clarity, and extensibility rather than performance or optimization is the
overarching goal.  With PyRTL you can use the full power of Python to describe
complex synthesizable digital designs, simulate and test them, and export them
to Verilog.

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
installed with :program:`pip` or :program:`pip3`.  If the above command fails
due to insufficient permissions, you may need to do ``sudo pip install pyrtl``
(to install as superuser) or ``pip install --user pyrtl`` (to install as a
normal user).

PyRTL is tested to work with Python 3.8+.

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
into a file and run it with Python.  The result you should see, drawn right
into the terminal, is the output of the simulation.  While a great deal of work
has gone into making hardware design in PyRTL as friendly as possible, please
don't mistake that for a lack of depth.  You can just as easily export to
Verilog or other hardware formats, view results with your favorite waveform
viewer, build hardware transformation passes, run JIT-accelerated simulations,
design, test, and even verify hugely complex digital systems, and much more.
Most critically of all it is easy to extend with your own approaches to digital
hardware development as you find necessary.


Overview of PyRTL
=================

If you are brand new to PyRTL we recommend that you start with the `PyRTL Code
Examples <https://github.com/UCSBarchlab/PyRTL/tree/development/examples>`_
which will show you most of the core functionality in the context of a complete
design.

PyRTL Classes:
--------------

Perhaps the most important class to understand is :class:`.WireVector`, which
is the basic type from which you build all hardware.  If you are coming to
PyRTL from Verilog, a :class:`.WireVector` is closest to a multi-bit `wire`.
Every new :class:`.WireVector` builds a set of wires which you can then connect
with other :class:`.WireVector` through overloaded operations such as
`addition` or `bitwise or`. A bunch of other related classes, including
:class:`.Input`, :class:`.Output`, :class:`.Const`, and :class:`.Register` are
all derived from :class:`.WireVector`. Coupled with :class:`.MemBlock` (and
:class:`.RomBlock`), this is all a user needs to create a functional hardware
design.

.. inheritance-diagram:: pyrtl.wire.WireVector
                         pyrtl.wire.Input
                         pyrtl.wire.Output
                         pyrtl.wire.Const
                         pyrtl.wire.Register
    :parts: 1

After specifying a hardware design, there are then options to simulate your
design right in PyRTL, synthesize it down to primitive 1-bit operations,
optimize it, and export it to Verilog (along with a testbench).

Simulation
^^^^^^^^^^

PyRTL provides tools for simulation and viewing simulation traces. Simulation
is how your hardware is "executed" for the purposes of testing, and three
different classes help you do that: :class:`.Simulation`,
:class:`.FastSimulation` and :class:`.CompiledSimulation`.  All three have
`almost` the same interface and, except for a few debugging cases, can be used
interchangeably.  Typically one starts with :class:`.Simulation` and then moves
up to :class:`.FastSimulation` when performance begins to matter.

Both :class:`.Simulation` and :class:`.FastSimulation` take an instance of
:class:`.SimulationTrace` as an argument (or makes an empty
:class:`.SimulationTrace` by default), which stores a list of the signals as
they are simulated.  This trace can then be rendered to the terminal with
:class:`.WaveRenderer`, although unless there are some problems with the
default configurations, most end users should not need to even be aware of
:class:`.WaveRenderer`.  The examples describe other ways that the trace may be
handled, including extraction as a test bench and export to a VCD file.

Optimization
^^^^^^^^^^^^

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
^^^^^^

Finally, when things go wrong you may hit on one of two ``Exceptions``, neither
of which is likely recoverable automatically (which is why we limited them to
only two).  The intention is that ``PyrtlError`` is intended to capture end
user errors such as invalid constant strings and mis-matched bitwidths.  In
contrast, ``PyrtlInternalError`` captures internal invariants and assertions
over the core logic graph which should never be hit when constructing designs
in the normal ways.  If you hit a confusing ``PyrtlError`` or any
``PyrtlInternalError`` feel free to file an issue.


Reference Guide
===============
.. toctree::
   :maxdepth: 2

   basic
   regmem
   simtest
   blocks
   helpers
   analysis
   export
   rtllib

Index
=====
* :ref:`genindex`
