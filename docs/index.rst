.. PyRTL documentation master file, created by
   sphinx-quickstart on Mon Nov  3 09:36:08 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PyRTL
=====

A collection of classes providing simple RTL specification, simulation, tracing, and testing suitable for teaching and research. Simplicity, usability, clarity, and extendibility rather than performance or optimization is the overarching goal.  With PyRTL you can use the full power of python to describe complex synthesizable digital designs, simulate and test them, and export them to verilog.  

Quick links
-----------
* Get an overview from the `PyRTL Project Webpage <http://ucsbarchlab.github.io/PyRTL/>`_
* Read through `Example PyRTL Code <https://github.com/UCSBarchlab/PyRTL/tree/master/examples>`_
* See `File a Bug or Issue <https://github.com/UCSBarchlab/PyRTL/issues>`_
* Contribute to project on `GitHub <https://github.com/UCSBarchlab/PyRTL>`_

Installation
------------

**Automatic installation**::

    pip install pyrtl

PyRTL is listed in `PyPI <http://pypi.python.org/pypi/pyrtl>`_ and
can be installed with ``pip`` or ``easy_install``.  If the above
command fails due to insufficient permissions, you may need to do 
``sudo pip install pyrtl`` (to install as superuser) or ``pip install --user pyrtl``
(to install as a normal user). 

**Prerequisites**:

PyRTL will work with Python 2.7 and 3.4.


PyRTL Classes:
--------------

Perhaps the most important class to understand the interface of is ``WireVector``.  A bunch
of other related classes, including ``Input``, ``Output``, ``Const``, and ``Register`` are all 
minor extensions to ``WireVector``.  Coupled with ``MemBlock`` (and ``RomBlock``), this is 
all a user needs to create a functional hardware design.

* ``WireVector()``
    * ``Input(WireVector)``
    * ``Output(WireVector)``
    * ``Const(WireVector)``
    * ``Register(WireVector)``

* ``MemBlock()``
* ``RomBlock()``

To simulate your hardware design one needs to do a simulation, and to view the output we need
to capture a "trace".  Simulation is how your hardware is "executed" for the purposes of testing,
and two different classes help you do that: ``Simulation`` and ``FastSimulation``.  Both ``Simulation``
and ``FastSimulation`` have the same interface and except for a few debugging cases can be used
interchangeably.  Typically one starts with ``Simulation`` and then moves to ``FastSimulation`` when
performance begins to matter.

Both ``Simulation`` and ``FastSimulation`` take an instance of ``SimulationTrace`` as an argument,
which stores a list of the signals as they are simulated.  This trace can then be rendered to the 
terminal using one of the Renderer classes, although unless there are some problems with the default 
configurations, most end users should not need to even be aware of these Renderer classes.  The examples
describe other ways that the trace may be handled, including extraction as a test bench and export
to a VCD file.

* ``Simulation()``
* ``FastSimulation()``
* ``SimulationTrace()``
* ``Utf8WaveRenderer()``
* ``AsciiWaveRenderer()``

When you are building hardware with the ``WireVector`` and ``MemBlock`` classes, what is really happening
under the hood is that those classes are just "sugar" over a core set of primitives and a data structure
keeps incrementally updating a graph of those primitives which, when complete, represent the final design.
``WireVectors`` connect to "primitives" which connect to other ``WireVectors`` and the class that stores
a primitive is ``LogicNet``.  The class ``Block`` is then a wrapper for a set of these ``LogicNet``s.  Typically
a full and complete design is stored in a single ``Block``.  The function ``working_block()`` will return
back the block on which we are implicitly working.  When we write hardware transforms we may wish to make a new 
``Block`` from an old one and augment the information kept with my hardware block and ``PostSynthBlock`` is
one example of this pattern in action.

* Block()
    * PostSynthBlock(Block):
* LogicNet()

Finally, when things go wrong you may hit on one of two Exceptions, neither of which is likely recoverable
automatically (which is why we limited them to only two).  The intention is that PyrtlError is intended
to capture end user errors such as invalid constant strings and mis-matched bitwidths.  In contrast, 
PyrtlInternalError captures internal invariants and assertions over the core logic graph which should never
be hit when constructing designs in the normal ways.  If you hit a confusing ``PyrtlError`` or any
``PyrtlInternalError`` feel free to file an issue.

* Exception
    * PyrtlError(Exception):
    * PyrtlInternalError(Exception):


.. inheritance-diagram::

PyRTL Modules:
--------------
.. toctree::
   :maxdepth: 2

   core
   wire
   memory
   passes
   simulation
   inputoutput
   helperfuncs

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

