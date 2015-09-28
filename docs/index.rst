.. PyRTL documentation master file, created by
   sphinx-quickstart on Mon Nov  3 09:36:08 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PyRTL
=====

A collection of classes providing simple RTL specification, simulation, tracing, and testing suitable for teaching and research. Simplicity, usability, clarity, and extendability rather than performance or optimization is the overarching goal.  With PyRTL you can use the full power of python to describe complex synthesizable digital designs, simulate and test them, and export them to verilog.  

Quick links
-----------
* Get an overview from the `Project Webpage <https://github.com/UCSBarchlab/PyRTL>`_
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

The 10,000 Foot Overview
------------------------

At a high level PyRTL builds the hardware structure that you explicitly define. If you are looking for a tool to take your random python code and turn it into hardware, you will have to look elsewhere. Instead PyRTL is designed to help you concisely and precisely describe a digitial hardware structure (that you already have worked out in detail) in python. PyRTL restricts you to a set of resonable digital designs practices -- the clock and resets are implicit, block memories are syncronous by default, there are no "undriven" states, and no weird un-registered feedbacks are allowed. Instead, of worrying about these "analog-ish" tricks that are horrible ideas in modern processes anyways, PyRTL let's you treat hardware design like a software problem -- build recursive hardware, write instrospective containers, and have fun building digital designs again!

To the user it provides a set of python classes that allow you to express their hardware designs reasonably pythonically. For example, with WireVector you get a structure that acts very much like a python list of 1-bit wires, so that `mywire[0:-1]` selects everything except the most-significant-bit. Of course you can add, subtract, and multiply these WireVectors or concat multiple bit-vectors end-to-end as well. You can then even make normal python collections of those WireVectors and do operations on them in bulk. For example, if you have a list of n different k-bit WireVectors (called "x") and you want to multiply each of them by 2 and put the sum of the result in a WireVector "y", it looks like the following: `y = sum([elem * 2 for elem in x])`. Hardware comprehensions are surprisingly useful.

* Elaboration-through-execution, meaning all of Python can be used including introspection
* Design, instantiate, and simulate all in one file and without leaving Python
* Export to, or import from, common HDLs (BLIF-in, Verilog-out currently supported)
* Examine execution with waveforms on the terminal or export to a .vcd as projects scale
* Elaboration, synthesis, and basic optimizations all included
* Small and well-defined internal core structure means writing new transforms is easier


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

