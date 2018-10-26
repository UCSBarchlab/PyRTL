PyRTL
=====

[![PyPI version](https://badge.fury.io/py/pyrtl.svg)](http://badge.fury.io/py/pyrtl)
[![Build Status](https://travis-ci.org/UCSBarchlab/PyRTL.svg)](https://travis-ci.org/UCSBarchlab/PyRTL)
[![Code Coverage](https://codecov.io/github/UCSBarchlab/PyRTL/coverage.svg?branch=development)](https://codecov.io/github/UCSBarchlab/PyRTL?branch=development)
[![Documentation Status](https://readthedocs.org/projects/pyrtl/badge/?version=latest)](http://pyrtl.readthedocs.org/en/latest/?badge=latest)
[![Binder](https://mybinder.org/badge.svg)](https://mybinder.org/v2/gh/UCSBarchlab/PyRTL/development?filepath=%2Fipynb-examples%2F)

PyRTL provides a collection of classes for pythonic [register-transfer level](https://en.wikipedia.org/wiki/Register-transfer_level) design, simulation, tracing, and testing 
suitable for teaching and research. Simplicity, usability, clarity, and extensibility rather than
performance or optimization is the overarching goal.  Features include:

* Elaboration-through-execution, meaning all of Python can be used including introspection
* Design, instantiate, and simulate all in one file and without leaving Python
* Export to, or import from, common HDLs (BLIF-in, Verilog-out currently supported)
* Examine execution with waveforms on the terminal or export to a .vcd as projects scale
* Elaboration, synthesis, and basic optimizations all included
* Small and well-defined internal core structure means writing new transforms is easier
* Batteries included means many useful components are already available and more are coming every week

What README would be complete without a screenshot?  Below you can see the waveform rendered right on the terminal for a small state machine written in PyRTL.

![Command-line waveform for PyRTL state machine]( docs/screenshots/pyrtl-statemachine.png?raw=true "PyRTL State Machine Screenshot")

For users, more info and demo code is available on the [PyRTL project web page](http://ucsbarchlab.github.io/PyRTL/).

### Package Contents

If you are just getting started with PyRTL it is suggested that you start with the examples first
to get a sense of the "thinking with pyrtls" required to design hardware in this way.  If you are looking
for a deeper understanding, dive into the code for the object `Block`. It is the core data structure at the heart of
PyRTL and defines its semantics at a high level -- everything is converted to or from the small, simple set of
primitives defined there.

In the package you should find the following files and Directories
* **pyrtl/**  The src directory for the module
* **pyrtl/rtllib/** Finished PyRTL libraries which are hopefully both useful and documented
* **examples/** A set of hardware design examples that show the main idea behind pyrtl
* **tests/**    A set of unit tests for PyRTL which you can run with nosetests
* **docs/** Location of the sphinx documentation

Testing requires the packages `tox` and `nose`.  Once installed a complete test of the system should be possible with the simple command `tox` and nothing more.

### Contributing to PyRTL

*Picking a first project*

* One of the earliest things you should submit is a unit test that hits some [uncovered lines of code in PyRTL](https://codecov.io/github/UCSBarchlab/PyRTL?branch=development).  For example, pick a PyrtlError that is not covered and add a unit test in /tests that will hit it.
* After you have that down check in the [PyRTL Issues](https://github.com/UCSBarchlab/PyRTL/issues) list for a feature that is marked as "beginner friendly".
* Once you have that down, ask for access to the PyRTL-research repo where we keep a list of more advanced features and designs that could use more help!

*Coding style*

* All major functionality should have set of unit tests covering and documenting their use
* All public functions and methods should have useful docstrings
* All code needs to conform to [PEP8](https://www.python.org/dev/peps/pep-0008/) conventions
* No new root-level dependencies on external libs, import locally if required for special functions

*Workflow*

* A useful reference for working with Git is this [Git tutorial](https://www.atlassian.com/git/tutorials/)
* A useful Git Fork workflow for working on this repo is [found here](http://blog.scottlowe.org/2015/01/27/using-fork-branch-git-workflow/)
* The "master" branch should always be stable and is updated only on major revisions (with a merge from "development" by the core development team)
* The "development" branch is the primary stable working branch (everyone is invited to submit pull requests)
* Bugs and minor enhancements tracked directly through the [issue tracker](https://github.com/UCSBarchlab/PyRTL/issues)
* When posting a bug please post a small chunk of code that captures the bug, e.g. [Issue #56](https://github.com/UCSBarchlab/PyRTL/issues/56)
* When pushing a fix to a bug or enhancement please reference issue number in commit message, e.g. [Fix to Issue #56](https://github.com/UCSBarchlab/PyRTL/commit/1d5730db168a9e4490c580cb930075715468047a)

*Documentation*
* All important functionality, for both /pyrtl and /rtlib, should have an executable example in /examples
* All classes should have a block comment with high level description of the class
* All functions in /pyrtl or /rtllib should follow the following (sphynx parsable) docstring format: 
```python
""" One Line Summary (< 80 chars) on what the function does, followed by period.

:param [optional param type] param_name : parameter description 
:param [optional param type] param_name : Longer parameter descriptions take up a newline
  with two leading spaces like this
:return [optional return type]: return description

A long description of what this function does. Talk about what the user should expect from this function
and also what the users needs to do to use the function (this part is optional)
"""

# Developer Notes (Optional):
# These would be anything that the user does not need to know in order to use the functions.
# Such things include internal workings of the function, the logic behind it, how to extend
# it (unless the function was mainly intended to be extended). 
```

### Using PyRTL 
We love to hear from users about their projects, and if there are issues we will try our best to push fixes quickly.  You can read more about how we have been using it in our research at UCSB both in simulation and on FPGAs in [our PyRTL paper at FPL](http://www.cs.ucsb.edu/~sherwood/pubs/FPL-17-pyrtl.pdf).

### Related Projects
It is always important to point out that PyRTL builds on the ideas of several other related projects as we all share the common goal of  trying to make hardware design a better experience!  You can read more about those relationships on our [PyRTL project web page](http://ucsbarchlab.github.io/PyRTL/).
