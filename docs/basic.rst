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

.. inheritance-diagram:: pyrtl.wire.WireVector
                         pyrtl.wire.Input
                         pyrtl.wire.Output
                         pyrtl.wire.Const
                         pyrtl.wire.Register
    :parts: 1

WireVector
----------

.. autoclass:: pyrtl.wire.WireVector
    :members:
    :special-members: __init__, __add__, __sub__, __mul__, __getitem___,
                      __len__, __ilshift__

Input Pins
----------

.. autoclass:: pyrtl.wire.Input
    :members:
    :show-inheritance:
    :special-members: __init__

Output Pins
-----------

.. autoclass:: pyrtl.wire.Output
    :members:
    :show-inheritance:
    :special-members: __init__

Constants
---------

.. autoclass:: pyrtl.wire.Const
    :members:
    :show-inheritance:
    :special-members: __init__

Conditionals
------------

.. automodule:: pyrtl.conditional
   :members:
   :show-inheritance:
   :special-members:
   :undoc-members:
   :exclude-members: __dict__,__weakref__,__module__

.. autodata:: pyrtl.otherwise

.. autodata:: pyrtl.conditional_assignment
