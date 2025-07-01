<!-- This README is also published on PyPI. GitHub relative links, like
[link](docs/README.md) do not work on PyPI, so don't use them here. -->

PyRTL
=====

[![PyPI version](https://badge.fury.io/py/pyrtl.svg)](http://badge.fury.io/py/pyrtl)
[![Build Status](https://github.com/UCSBarchlab/PyRTL/actions/workflows/python-test.yml/badge.svg)](https://github.com/UCSBarchlab/PyRTL/actions/workflows/python-test.yml)
[![Code Coverage](https://codecov.io/github/UCSBarchlab/PyRTL/coverage.svg?branch=development)](https://codecov.io/github/UCSBarchlab/PyRTL?branch=development)
[![Documentation Status](https://readthedocs.org/projects/pyrtl/badge/?version=latest)](http://pyrtl.readthedocs.org/en/latest/?badge=latest)
[![Binder](https://mybinder.org/badge.svg)](https://mybinder.org/v2/gh/UCSBarchlab/PyRTL/development?filepath=%2Fipynb-examples%2F)

PyRTL provides a collection of classes for Pythonic [register-transfer
level](https://en.wikipedia.org/wiki/Register-transfer_level) design,
simulation, tracing, and testing suitable for teaching and research.
Simplicity, usability, clarity, and extensibility rather than performance or
optimization is the overarching goal. Features include:

* Elaboration-through-execution, meaning all of Python can be used including
  introspection
* Design, instantiate, and simulate all in one file and without leaving Python
* Export to, or import from, common HDLs (BLIF-in, Verilog-out currently
  supported)
* Examine execution with waveforms on the terminal or export to `.vcd` as
  projects scale
* Elaboration, synthesis, and basic optimizations all included
* Small and well-defined internal core structure means writing new transforms
  is easier
* Batteries included means many useful components are already available and
  more are coming every week

What README would be complete without a screenshot? Below you can see the
waveform rendered right on the terminal for a small state machine written in
PyRTL.

![Command-line waveform for PyRTL state machine](https://github.com/UCSBarchlab/PyRTL/blob/development/docs/screenshots/pyrtl-statemachine.png?raw=true "PyRTL State Machine Screenshot")

### Tutorials and Documentation

* For users, more info and demo code is available on the [PyRTL project web
  page](http://ucsbarchlab.github.io/PyRTL/).
* Try the examples in the
  [`examples`](https://github.com/UCSBarchlab/PyRTL/tree/development/examples)
  directory. You can also [try the examples on
  MyBinder](https://mybinder.org/v2/gh/UCSBarchlab/PyRTL/development?filepath=%2Fipynb-examples%2F).
* Full reference documentation is available at https://pyrtl.readthedocs.io/

### Package Contents

If you are just getting started with PyRTL it is suggested that you start with
the
[`examples`](https://github.com/UCSBarchlab/PyRTL/tree/development/examples)
first to get a sense of the "thinking with PyRTLs" required to design hardware
in this way. If you are looking for a deeper understanding, dive into the code
for the object `Block`. It is the core data structure at the heart of PyRTL and
defines its semantics at a high level -- everything is converted to or from the
small, simple set of primitives defined there.

The package contains the following files and directories:
* [`pyrtl`](https://github.com/UCSBarchlab/PyRTL/tree/development/pyrtl)
  The src directory for the module.
* [`pyrtl/rtllib/`](https://github.com/UCSBarchlab/PyRTL/tree/development/pyrtl/rtllib)
  Finished PyRTL libraries which are hopefully both useful and documented.
* [`examples`](https://github.com/UCSBarchlab/PyRTL/tree/development/examples)
  A set of hardware design examples that show the main idea behind PyRTL.
* [`tests`](https://github.com/UCSBarchlab/PyRTL/tree/development/tests)
  A set of unit tests for PyRTL which you can run with `pytest`.
* [`docs`](https://github.com/UCSBarchlab/PyRTL/tree/development/docs)
  Location of the Sphinx documentation.

Testing requires the Python packages `tox` and `pytest`, which are installed by
`requirements.txt`. Once installed, a complete test of the system can be run with:

```shell
$ tox
```

PyRTL's code is automatically formatted with `ruff`, also installed by
`requirements.txt`. Reformat any changed code with:

```shell
$ ruff format
```

### Contributing to PyRTL

*Picking a first project*

* One of the earliest things you should submit is a unit test that hits some
  [uncovered lines of code in
  PyRTL](https://codecov.io/github/UCSBarchlab/PyRTL?branch=development). For
  example, pick a `PyrtlError` that is not covered and add a unit test in
  [`tests`](https://github.com/UCSBarchlab/PyRTL/tree/development/tests)
  that will hit it.
* After you have that down check in the [PyRTL
  Issues](https://github.com/UCSBarchlab/PyRTL/issues) list for a feature that
  is marked as "beginner friendly".
* Once you have that down, ask for access to the PyRTL-research repo where we
  keep a list of more advanced features and designs that could use more help!

*Coding style*

* All major functionality should have unit tests covering and documenting their
  use
* All public functions and methods should have useful docstrings
* All code needs to conform to
  [PEP8](https://www.python.org/dev/peps/pep-0008/) conventions
* No new root-level dependencies on external libs, import locally if required
  for special functions

*Workflow*

* A useful reference for working with Git is this [Git
  tutorial](https://www.atlassian.com/git/tutorials/)
* A useful Git Fork workflow for working on this repo is [found
  here](http://blog.scottlowe.org/2015/01/27/using-fork-branch-git-workflow/)
* The `development` branch is the primary stable working branch (everyone is
  invited to submit pull requests)
* Bugs and minor enhancements tracked directly through the [issue
  tracker](https://github.com/UCSBarchlab/PyRTL/issues)
* When posting a bug please post a small chunk of code that captures the bug,
  e.g. [Issue #56](https://github.com/UCSBarchlab/PyRTL/issues/56)
* When pushing a fix to a bug or enhancement please reference issue number in
  commit message, e.g. [Fix to Issue
  #56](https://github.com/UCSBarchlab/PyRTL/commit/1d5730db168a9e4490c580cb930075715468047a)

*Documentation*

* All important functionality should have an executable example in
  [`examples`](https://github.com/UCSBarchlab/PyRTL/tree/development/examples)
* All classes should have a block comment with high level description of the
  class
* All functions should follow the following (Sphinx parsable) docstring format:
  ```python
  """One Line Summary (< 80 chars) of the function, followed by period.

  A long description of what this function does. Talk about what the user
  should expect from this function and also what the users needs to do to use
  the function (this part is optional).

  :param param_name : Description of this parameter.
  :param param_name : Longer parameter descriptions take up a newline with four
      leading spaces like this.
  :return: Description of function's return value.
  """
  # Developer Notes (Optional):
  #
  # These would be anything that the user does not need to know in order to use
  # the functions.
  # These notes can include internal workings of the function, the logic behind
  # it, or how to extend it.
  ```
* Sphinx parses [Python type
  annotations](https://docs.python.org/3/library/typing.html), so put type
  information into annotations instead of docstrings.
* The Sphinx-generated documentation is published to
  https://pyrtl.readthedocs.io/
* PyRTL's Sphinx build process is documented in
  [`docs/README.md`](https://github.com/UCSBarchlab/PyRTL/blob/development/docs/README.md).
* PyRTL's release process is documented in
  [`docs/release/README.md`](https://github.com/UCSBarchlab/PyRTL/blob/development/docs/release/README.md).

### Using PyRTL

We love to hear from users about their projects, and if there are issues we
will try our best to push fixes quickly. You can read more about how we have
been using it in our research at UCSB both in simulation and on FPGAs in [our
PyRTL paper at FPL](http://www.cs.ucsb.edu/~sherwood/pubs/FPL-17-pyrtl.pdf).

### Related Projects

It is always important to point out that PyRTL builds on the ideas of several
other related projects as we all share the common goal of trying to make
hardware design a better experience! You can read more about those
relationships on our [PyRTL project web
page](http://ucsbarchlab.github.io/PyRTL/).
