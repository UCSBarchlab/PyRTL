Wires and Logic
===============

Wires define the relationship between logic blocks in PyRTL. They are treated
like normal wires in traditional RTL systems except the :class:`.Register`
wire.  Logic is then created when wires are combined with one another using the
provided operators.  For example, if ``a`` and ``b`` are both of type
:class:`.WireVector`, then ``a + b`` will make an adder, plug ``a`` and ``b``
into the inputs of that adder, and return a new :class:`.WireVector` which is
the output of that adder.  :class:`.Block` stores the description of the
hardware as you build it.

:class:`.Input`, :class:`.Output`, :class:`.Const`, and :class:`.Register` all
derive from :class:`.WireVector`.  :class:`.Input` represents an input pin,
serving as a placeholder for an external value provided during simulation.
:class:`.Output` represents an output pin, which does not drive any wires in
the design. :class:`.Const` is useful for specifying hard-wired values and
:class:`.Register` is how sequential elements are created (they all have an
implicit clock).

.. inheritance-diagram:: pyrtl.WireVector
                         pyrtl.Input
                         pyrtl.Output
                         pyrtl.Const
                         pyrtl.Register
    :parts: 1

WireVector
----------

.. autoclass:: pyrtl.WireVector
    :members:
    :special-members: __init__, __add__, __sub__, __mul__, __getitem__,
                      __len__, __ilshift__, __invert__, __and__, __or__, __xor__, __lt__,
                      __le__, __eq__, __ne__, __gt__, __ge__, __len__

Input Pins
----------

.. autoclass:: pyrtl.Input
    :members:
    :show-inheritance:

Output Pins
-----------

.. autoclass:: pyrtl.Output
    :members:
    :show-inheritance:

Constants
---------

.. autoclass:: pyrtl.Const
    :members:
    :show-inheritance:
    :special-members: __init__

.. _conditional_assignment:

Conditional Assignment
----------------------

.. autodata:: pyrtl.conditional_assignment

:class:`WireVectors<.WireVector>`, :class:`Registers<.Register>`, and
:class:`MemBlocks<.MemBlock>` can be conditionally assigned values based on predicates.

Conditional assignments are written with `Python with statements
<https://docs.python.org/3/reference/compound_stmts.html#with>`_, using two
context managers:

#. :data:`.conditional_assignment`, which provides the framework for specifying
   conditional assignments.
#. :data:`.otherwise`, which specifies the 'fall through' case.

Conditional assignments are easiest to understand with an example::

    r1 = pyrtl.Register(bitwidth=8)
    r2 = pyrtl.Register(bitwidth=8)
    w = pyrtl.WireVector(bitwidth=8)
    mem = pyrtl.MemBlock(bitwidth=8, addrwidth=4)

    a = pyrtl.Input(bitwidth=1)
    b = pyrtl.Input(bitwidth=1)
    c = pyrtl.Input(bitwidth=1)
    d = pyrtl.Input(bitwidth=1)

    with pyrtl.conditional_assignment:
        with a:
            # Set when a is True.
            r1.next |= 1
            mem[0] |= 2
            with b:
                # Set when a and b are both True.
                r2.next |= 3
        with c:
            # Set when a is False and c is True.
            r1.next |= 4
            r2.next |= 5
        with pyrtl.otherwise:
            # Set when a and c are both False.
            r2.next |= 6

        with d:
            # Set when d is True. A `with` block after an `otherwise` starts a new
            # set of conditional assignments.
            w |= 7

This :data:`.conditional_assignment` is equivalent to::

    r1.next <<= pyrtl.select(a, 1, pyrtl.select(c, 4, r1))
    r2.next <<= pyrtl.select(a, pyrtl.select(b, 3, r2), pyrtl.select(c, 5, 6))
    w <<= pyrtl.select(d, 7, 0)
    mem[0] <<= pyrtl.MemBlock.EnabledWrite(data=2, enable=a)

Conditional assignments are generally recommended over nested :func:`.select` statements
because conditional assignments are easier to read and write.

:data:`.conditional_assignment` accepts an optional ``default`` argument that
maps from :class:`.WireVector` to its default value for the
:data:`.conditional_assignment` block. ``defaults`` are not supported for
:class:`.MemBlock`. See :ref:`conditional_assignment_defaults` for more details.

See `the state machine example
<https://github.com/UCSBarchlab/PyRTL/blob/development/examples/example3-statemachine.py>`_
for more examples of :data:`.conditional_assignment`.

.. autodata:: pyrtl.otherwise

Context manager implementing PyRTL's ``otherwise`` under :data:`.conditional_assignment`.

.. autofunction:: pyrtl.currently_under_condition

.. _conditional_assignment_defaults:

Conditional Assignment Defaults
-------------------------------

Every PyRTL wire, register, and memory must have a value in every cycle. PyRTL does not
support "don't care" or ``X`` values. To satisfy this requirement, conditional
assignment must always assign a value to every wire in a :data:`.conditional_assignment`
block, even if the :data:`.conditional_assignment` does not specify a value. This can
happen when:

#. A condition is ``True``, but no value is specified for a wire or register in that
   condition's ``with`` block. In the example above, no value is specified for ``r1`` in
   the :data:`.otherwise` block.
#. No conditions are ``True``, and there is no :data:`.otherwise` block. In the example
   above, there is no :data:`.otherwise` block to for the case when ``d`` is ``False``,
   so no value is specified for ``w`` when ``d`` is ``False``.

When this happens for a wire, ``0`` is assigned as a default value. See how a ``0``
appears in the final :func:`.select` in the equivalent example above.

When this happens for a register, the register's current value is assigned as a default
value. See how ``r1`` and ``r2`` appear within the :func:`.select` s in the first and second
lines of the example above.

When this happens for a memory, the memory's write port is disabled. See how the example
above uses a :class:`.EnabledWrite` to disable writes to ``mem[0]`` when ``a`` is
``False``.

These default values can be changed by passing a ``defaults`` dict to
:data:`.conditional_assignment`, as seen in this example::

    # Most instructions advance the program counter (`pc`) by one instruction. A few
    # instructions change `pc` in special ways.
    pc = pyrtl.Register(bitwidth=32)
    instr = pyrtl.WireVector(bitwidth=32)
    res = pyrtl.WireVector(bitwidth=32)

    op = instr[:7]
    ADD = 0b0110011
    JMP = 0b1101111

    # Use conditional_assignment's `defaults` to advance `pc` by one instruction by
    # default.
    with pyrtl.conditional_assignment(defaults={pc: pc + 1}):
        with op == ADD:
            res |= instr[15:20] + instr[20:25]
            # pc.next will be updated to pc + 1
        with op == JMP:
            pc.next |= pc + instr[7:]
            # res will be set to 0

.. WARNING::
    :data:`.conditional_assignment` ``defaults`` are not supported for
    :class:`.MemBlock`.

The Conditional Assigment Operator (``|=``)
-------------------------------------------

Conditional assignments are written with the ``|=`` operator, and not the usual ``<<=``
operator.

* The ``|=`` operator is a *conditional* assignment. Conditional assignments can only be
  written in a :data:`.conditional_assignment` block.
* The ``<<=`` operator is an *unconditional* assignment, *even if* it is written in a
  :data:`.conditional_assignment` block.

Consider this example::

    w1 = pyrtl.WireVector()
    w2 = pyrtl.WireVector()
    with pyrtl.conditional_assignment:
        with a:
            w1 |= 1
            w2 <<= 2

Which is equivalent to::

    w1 <<= pyrtl.select(a, 1, 0)
    w2 <<= 2

This behavior may seem undesirable, but consider this example::

    def make_adder(x: pyrtl.WireVector) -> pyrtl.WireVector:
        output = pyrtl.WireVector(bitwidth=a.bitwidth + 1)
        output <<= x + 2
        return output

    w = pyrtl.WireVector()
    with pyrtl.conditional_assignment:
        with a:
            w |= make_adder(b)

Which is equivalent to::

    # The assignment to `output` in `make_adder` is unconditional.
    w <<= pyrtl.select(a, make_adder(b), 0)

In this example the ``<<=`` in ``make_adder`` should be unconditional, even though
``make_adder`` is called from a :data:`.conditional_assignment`, because the top-level
assignment to ``w`` is already conditional. Making the lower-level assignment to
``output`` conditional would not make sense, especially if ``output`` is used elsewhere
in the circuit.
