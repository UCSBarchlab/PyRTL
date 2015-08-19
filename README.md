PyRTL
=====

[![Build Status](https://magnum.travis-ci.com/UCSBarchlab/PyRTL.svg?token=XAZcwAigXaYVLzkPHGNx)](https://magnum.travis-ci.com/UCSBarchlab/PyRTL)

PyRTL provides a collection of classes for pythonic RTL specification, simulation, tracing, and testing 
suitable for teaching and research. Simplicity, usability, clarity, and extendibility rather than 
performance or optimization is the overarching goal.

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
pyrtl and defines the semantics at a high level -- everything is converted to or from the small simple set of
primitives defined there.  The features of PyRTL include:

* Elaborate-through-execution means all of python can be used, including introspection
* Design, instantiate, and simulate all in one file without leaving python
* Export to, or import from, common HDLs (BLIF-in, Verilog-out currently supported)
* Examine execution with waveforms on the terminal or export to a .vcd as projects scale
* Elaboration, synthesis, and basic optimizations all included
* Small and well-defined internal core structure means writing new transforms is easier
* Batteries included means many useful components are already available and more are coming every week


### The 10,000 Foot Overview

At a high level PyRTL builds the hardware structure that you *explicitly define*.  If you are looking for a 
tool to take your random python code and turn it into hardware, you will have to look elsewhere.  Instead 
PyRTL is designed to help you concisely and precisely describe a hardware structure that you already have 
worked out in detail.  To the user it provides a set of python classes that allow you to express those 
hardware designs reasonably pythonically.  For example, with WireVector you get a structure that acts very 
much like a python list of 1-bit wires, so that ```mywire[0:-1]``` selects everything except the 
most-significant-bit.  Of course you can add, subtract, and multiple these WireVectors or concat multiple 
bit-vectors end-to-end as well.  You can then even make normal python collections of those WireVectors and 
do operations on them in bulk. For example, if you have a list of n k-bit WireVectors (called "x") and you 
want to multiply each of them by 2 and put the sum of the result in a WireVector "y", it looks like
the following:  ```y = sum([elem * 2 for elem in x])```. 
Hardware comprehensions are surprisingly useful!

The docs are also available, just run `./checkcode` with no parameters in the PyRTL directory and it will 
build the documentation for you (under the **docs/** directory). Requires [Sphinx](http://sphinx-doc.org/). 
In addition, running './checkcode' will also run all of the tests and checks.


### Hello N-bit Ripple-Carry Adder

While adders are a builtin primitive for PyRTL, most people doing RTL are familiar with the idea of a 
(Ripple-Carry Adder)[https://en.wikipedia.org/wiki/Adder_(electronics)] and so it is useful to see how you 
might express one in PyRTL if you had to.  Rather than the typical (Verilog introduction to fixed 4-bit 
adders)[https://www.youtube.com/watch?v=bL3ihMA8_Gs], let's go ahead and build an arbitrary bitwidth 
adder!.

```python
def one_bit_add(a, b, cin):
    assert len(a) == len(b) == 1  # len returns the bitwidth
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum, cout

def ripple_add(a, b, cin=0):
    a, b = pyrtl.match_bitwidth(a, b)
    if len(a) == 1:
        sumbits, cout = one_bit_add(a, b, cin)
    else:
        lsbit, ripplecarry = one_bit_add(a[0], b[0], cin)
        msbits, cout = ripple_add(a[1:], b[1:], ripplecarry)
        sumbits = pyrtl.concat(msbits, lsbit)
    return sumbits, cout

# instantiate an adder into a 3-bit counter
counter = pyrtl.Register(bitwidth=3, name='counter')
sum, cout = ripple_add(counter, pyrtl.Const("1'b1"))
counter.next <<= sum

# simulate the instantiated design for 15 cycles
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in range(15):
    sim.step({})
sim_trace.render_trace()
```

The code above includes an adder generator with python-style slices on wires (ripple_add), an instantiation 
of a register (used as a counter with the generated adder), and all the code needed to simulate the design, 
generate a waveform, and render it to the terminal. The way this particular code works is described more in 
the examples directory.  When you run it, it should look like this:

![Command-line waveform for PyRTL counter](docs/screenshots/pyrtl-counter.png?raw=true "PyRTL Counter Screenshot")

You can see the counter going from 0 to 7 and repeating.  A slightly more interesting state machine might look like this:

![Command-line waveform for PyRTL state machine]( docs/screenshots/pyrtl-statemachine.png?raw=true "PyRTL State Machine Screenshot")



### A Few Gotchas

While python is an amazing language, DSLs in python always forced to make a few compromises which can sometime catch
users in some unexpected ways.  Watch out for these couple of "somewhat surprising features"

* PyRTL never uses any of the "in-place arithmetic assignments" such as ```+=``` or ```&=``` in the traditional ways.
  Instead only ```<<=``` and ```|=``` are defined and they are used for wire-assignment and conditional-wire-assignment
  respectively (more on both of these in the examples).   If you declare a ```x = WireVector(bitwidth=3)``` and 
  ```y = WireVector(bitwidth=5)```, how do you assign ```x``` the value of ```y + 1```?  If you do ```x = y + 1``` 
  that will replace the old definition of ```x``` entirely?  Instead you need to write ```x <<= y + 1``` which you 
  can read as "x gets its value from y + 1".

* The example above also shows off another aspect of PyRTL.  The bitwidth of ```y``` is 5.  The bitwidth of ```y + 1```
  is actually 6 (PyRTL infers this automatically).  But then when you assign ```x <<= y + 1``` you are taking
  a 6-bit value and assigning it to 3-bit value.  This is completely legal and only the least significant bits 
  will be assigned.  Mind your bitwidths.

* PyRTL provides some handy functions on WireVectors, including ```==``` and ```<``` which evaluate to a new WireVector
  a single bit long to hold the result of the comparison.  The bitwise operators ```&```, ```|```, ```!``` and ```^``` 
  are also defined (however logic operations such as "and" and "not" are not).  A really tricky gotcha happens
  when you start combining the two together.  Consider: ```doit = ready & state==3```.  In python, the bitwise
  ```&``` operator has *higher precedence* than ```==```, thus python parses this as ```doit = (ready & state)==3```
  instead of what you might have guessed at first!  Make sure to use parenthesis when using comparisons with
  logic operations to be clear: ```doit = ready & (state==3)```.

* PyRTL right now assumes that all WireVectors are two's complement unsigned integers.  When you do comparisons
  such as "<" it will do unsigned comparison.  If you pass a WireVector to a function that requires more bits 
  that you have provided, it will do zero extention by default.  You can always explicitly do sign extention
  with .sign_extend() but it is not the default behavior for WireVector.  This is right now for clarity and
  consistancy, althought it does make writting signed arithmetic operations more text heavy.

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
are close to Verilog and unlike PyRTL, MyHDL allows asynchronous logic and higher level modeling.  Much like Verilog, only a structural
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
providing a limited and composable set of data structures to be used to specify an RTL implementation, thus avoiding the distinction between
synthesizable and non-synthesizable code (the execution is the elaboration step).
