PyRTL
=====

A collection of classes providing simple RTL specification, simulation, tracing, and testing suitable for teaching and research. 
Simplicity, usability, clarity, and extendability rather than performance or optimization is the overarching goal.

near-term todo list:
* all user visible assert calls should be replaced with "raise PyrtlError"
* all PyrtlError calls should have useful error message
* all classes should have useful docstrings
* all public functions and methods should have useful docstrings
* should have set of unit tests for main abstractions
* should be PEP8 compliant
* multiple nested blocks should be supported
* add verilog export option to block
* add multiply operation as a primitive

bigger todo projects:
* add area, clockrate, and energy estimations
(Guiding Architectural SRAM Models ICCD 2006 for memories,
Logical Effort for logic blocks and registers)
* add debug mode, where we track call stack for each wirevector initiated (and
where all errors thrown tell you where the wire was instantiated that is causing
the problem)
* add a pass to print out the block as a set of C code that implement the 
hardware block (useful for longer runing tests -- like a processor model)
