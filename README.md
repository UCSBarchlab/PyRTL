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

The docs are also available, just run `./checkcode` with no parameters in the PyRTL directory and it will build
the documentation for you (under the **docs/** directory). Requires [Sphinx](http://sphinx-doc.org/).
In addition, running './checkcode' will also run all of the tests and checks.

### Contributing to PyRTL

*Coding style*

* All major functionality should have set of unit tests covering and documenting their use
* All public functions and methods should have useful docstrings
* All code needs to conform to [PEP8](https://www.python.org/dev/peps/pep-0008/) conventions
* No root-level dependencies on external libs, import locally if required for special functions

*Workflow*

* A useful reference for working with Git is this [Git tutorial](https://www.atlassian.com/git/tutorials/)
* The "master" branch should always be stable and is updated only on major revisions (with a merge from "development" by Sherwood)
* The "development" branch is the primary stable working branch (anyone can push)
* Both "master" and "development" are automatically checked for full unit-test passing and PEP8 compliance with [Travis CI](https://travis-ci.com/)
* Before pushing code to "development" make sure you pass "./checkcode" which is the same test as Travis CI will do
* Any changes to stuff in PyRTL/pyrtl/ directory should be discussed before push to development
* Bugs and minor enhancements tracked directly through the [issue tracker](https://github.com/UCSBarchlab/PyRTL/issues)
* Ideas for projects and major enhancements described on the [PyRTL-Projects Wiki Page](https://github.com/UCSBarchlab/PyRTL/wiki)
* Anyone can add to, extended, or refine ideas on the wiki (anyone can edit)
* If you start working on a project, please add an issue in the issue tracker and assign yourself to it for coordination
* When posting a bug please post a small chunk of code that captures the bug, e.g. [Issue #56](https://github.com/UCSBarchlab/PyRTL/issues/56)
* When pushing a fix to a bug or enhancement please reference issue number in commit message, e.g. [Fix to Issue #56](https://github.com/UCSBarchlab/PyRTL/commit/1d5730db168a9e4490c580cb930075715468047a)

### Related Projects

[MyHDL](http://www.myhdl.org/) is a neat Python hardware project built around generators and decorators.  The semantics of this embedded language
are close to Verilog and unlike PyRTL, MyHDL allows asynchronous logic and higher level modeling.  Also like Verilog, only a structural
"convertible subset" of the language can be automatically synthesized into real hardware.  PyRTL requires all logic to be both synchronous
and synthesizable which avoids a common trap for beginners, it elaborates the design during execution allowing the full power of python
in describing recursive or complex hardware structures, and allows for hardware synthesis, simulation, test bench creation, and optimization
all in the same framework.

[Chisel](https://chisel.eecs.berkeley.edu/) is a project with similar goals to PyRTL but is based instead in Scala.  Using the Scala
embedded language features and rich type system, Chisel is (like PyRTL) a elaborate-through-execution hardware design language.  With support
for signed types, named hierarchies of wires useful for hardware protocols, and a neat control structure call "when" that inspired our
ConditionalUpdate contexts, Chisel is a powerful tool used in some great research projects including OpenRISC.  Unlike Chisel, PyRTL has
concentrated on a complete tool chain which is useful for instructional projects, and provides a clearly defined and relatively easy to
manipulate intermediate structure in the class Block (often times call pyrtl.core) which allows rapid prototyping of hardware analysis
routines which can then be codesigned with the architecture.

[Yosys](http://www.clifford.at/yosys/) is an open source tool for Verilog RTL synthesis. It supports a huge subset of the Verilog-2005
semantics and provides a basic set of synthesis algorithms.  The goals of this this tool are quite different from PyRTL, but the two
play very nicely together in that PyRTL can output Verilog that can then be synthesized through Yosys.  Likewise Yosys can take
Verilog designs and synthesize them to a very simple library of gates and output them as a "blif" file which can then be read in by
PyRTL.

[PyMTL](https://github.com/cornell-brg/pymtl) is an alpha stage "open-source Python-based framework for multi-level hardware modeling".
One of the neat things about this project is that they are trying to allow simulation and modeling at multiple different levels of the
design from the functional level, the cycle-close level, and down to the register-transfer level (where PyRTL really is built to play).
Like MyHDL they do some neat meta-programming tricks like parsing the Python AST to allow executable software descriptions to be (under
certain restrictions -- sort of like verilog) automatically converted into implementable hardware.  PyRTL, on the other hand, is about
providing a limited and composable set of data structures to be used specify and RTL implementation avoiding the distinction between
synthesizable and non-synthesizable code (the execution is the elaboration step).
