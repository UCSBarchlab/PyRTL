PyRTL
=====

A collection of classes providing simple RTL specification, simulation, tracing, and testing suitable for teaching and research. 
Simplicity, usability, clarity, and extendability rather than performance or optimization is the overarching goal.

todo list:
* all user visible assert calls should be replaced with "raise PyrtlError"
* all PyrtlError calls should have useful error message
* all classes should have useful docstrings
* all public functions and methods should have useful docstrings
* all private methods and members should use "_" at the start of their names
* should have set of unit tests for main abstractions
* should be PEP8 compliant
* multiple nested blocks should be supported
* add verilog export option to block
* add debug mode, where we track call stack for each wirevector initiated
