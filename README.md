PyRTL
=====

A collection of classes providing simple RTL specification, simulation, tracing, and testing suitable for teaching and research. 
Simplicity, usability, clarity, and extendibility rather than performance or optimization is the overarching goal.

In the package you should find the following files and Directories
* **pyrtl/**  The src directory for the module
* **tests/**    A set of unit tests for pyrtl which you can run with nosetests
* **examples/** A set of hardware design examples that show the main idea behind pyrtl
* **checkcode** A script you should run before you check any code into the master or development branches

If you are just getting started with pyrtl it is suggested that you start with the examples first,
to get and sense of the "thinking with pyrtls" required to design hardware in this way.  Then 
dive into the code for the object Block, which is the core data structure at the heart of 
pyrtl and defines its semantics at a high level.   

### Near-term todo list

* all user visible assert calls should be replaced with "raise PyrtlError"
* all PyrtlError calls should have useful error message
* all classes should have useful docstrings
* all public functions and methods should have useful docstrings
* should have set of unit tests for all main abstractions
* add verilog export option to block
* add a -Wall option which warns on truncation
* change "tmp" and "const" "'" names to be more pyrtl specific to avoid confusion
* move block checks to a single function to simplify code base and provide more complete checks

### Bigger todo projects

**Multiple-Blocks:**
Rather than one single monolythic hardware block, PyRTL should support
multiple nested blocks active at the same time (and nested recursively)

**Estimators:** 
add area, clockrate, and energy estimations
(Guiding Architectural SRAM Models ICCD 2006 for memories,
Logical Effort for logic blocks and registers)

**Debug Mode:**
add debug mode, where we track call stack for each wirevector initiated (and
where all errors thrown tell you where the wire was instantiated that is causing
the problem)

**C Code Model:**
add a pass to print out the block as a set of C code that implement the 
hardware block (useful for longer running tests -- like a processor model)

**Ability to Lower Abstraction Level:**
add a pass to tranform all complex operators (such as 'cat' and multibit
arithmetic operations) down into simple and/or/not gates.  Useful for prototyping
gate-level analysis and as a very simple path to synthesis
