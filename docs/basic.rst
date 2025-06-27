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
    :special-members: __init__, __add__, __sub__, __mul__, __getitem___,
                      __len__, __ilshift__, __and__, __or__, __xor__, __lt__,
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

.. automodule:: pyrtl.conditional
   :members:
