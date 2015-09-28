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
* Read through `Example PyRTL Code <https://github.com/UCSBarchlab/PyRTL/tree/master/examples>'_
* See `File a Bug or Issue <https://github.com/UCSBarchlab/PyRTL/issues>'_
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

**Prerequisites**: PyRTL will work with Python 2.7 and 3.4.

PyRTL Modules:

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
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

