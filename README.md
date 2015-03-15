PyRTL
=====

[![Build Status](https://magnum.travis-ci.com/UCSBarchlab/PyRTL.svg?token=XAZcwAigXaYVLzkPHGNx)](https://magnum.travis-ci.com/UCSBarchlab/PyRTL)

A collection of classes providing simple RTL specification, simulation, tracing, and testing suitable for teaching and research. 
Simplicity, usability, clarity, and extendibility rather than performance or optimization is the overarching goal.

In the package you should find the following files and Directories
* **pyrtl/**  The src directory for the module
* **tests/**    A set of unit tests for pyrtl which you can run with nosetests
* **examples/** A set of hardware design examples that show the main idea behind pyrtl
* **rtllib/** A place for finished PyRTL designs which are hopefully both useful and documented
* **research/** A place for experiments and other changes not ready for primetime
* **docs/** The location of the auto-generated documentation (built when you run checkcode)
* **checkcode** A script you should run before you check any code into the master or development branches

If you are just getting started with pyrtl it is suggested that you start with the examples first,
to get and sense of the "thinking with pyrtls" required to design hardware in this way.  Then 
dive into the code for the object Block, which is the core data structure at the heart of 
pyrtl and defines its semantics at a high level.

The docs are also available, just run `./checkcode` once and it will build the documentation for you (under the **docs/** directory). Requires [Sphinx](http://sphinx-doc.org/).

### Contributing to PyRTL

*Coding style*

* All major functionality should have set of unit tests covering and documenting their use
* All public functions and methods should have useful docstrings
* All code needs to conform to PEP8(https://www.python.org/dev/peps/pep-0008/) conventions

*Workflow*

* A useful reference for working with Git is this [Git tutorial](https://www.atlassian.com/git/tutorials/)
* The "master" branch should always be stable and is updated only on major revisions (with merge from "development" by Sherwood)
* The "development" branch is the primary stable working branch (anyone can push)
* Both "master" and "development" are automatically checked for full unit-test passing and PEP8 compliance with [Travis CI](https://travis-ci.com/)
* Before pushing code to "development" make sure you pass "./checkcode" which is the same test as Travis CI will do
* Any changes to stuff in PyRTL/pyrtl/ directory should be discussed before push to development
* Bugs and minor enhancements tracked directly through the (issue tracker)[https://github.com/UCSBarchlab/PyRTL/issues]
* Ideas for projects and major enhancements described on the (PyRTL-Projects Wiki Page)[https://github.com/UCSBarchlab/PyRTL/wiki]
* Anyone can add to, extended, or refine ideas on the wiki (anyone can edit)
* If you start working on a project, please add an issue in the issue tracker and assign yourself to it for coordination
* When posting a bug please post a small chunk of code that captures the bug, e.g. [Issue #56](https://github.com/UCSBarchlab/PyRTL/issues/56)
* When pushing a fix to a bug or enhancement please reference issue number in commit message, e.g. [Fix to Issue #56](https://github.com/UCSBarchlab/PyRTL/commit/1d5730db168a9e4490c580cb930075715468047a)
