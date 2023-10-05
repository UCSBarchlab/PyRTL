Wires and Logic
===============

Wires define the relationship between logic blocks in PyRTL. They are treated
like normal wires in traditional RTL systems except the :class:`.Register`
wire.  Logic is then created when wires are combined with one another using the
provided operators.  For example, if ``a`` and ``b`` are both of type
:class:`.WireVector`, the ``a + b`` will make an adder, plug ``a`` and ``b``
into the inputs of that adder, and return a new :class:`.WireVector` which is
the output of that adder.  Wires provide the basic input and output interfaces
to the generated :class:`.Block` which stores the description of the hardware
as you build it.

The classes :class:`.Input`, :class:`.Output`, :class:`.Const`, and
:class:`.Register` are all derived from :class:`.WireVector`, but extend it
with (or restrict it from) with certain functionality.  The :class:`.Input` and
:class:`.Output` classes are for those values that will be external to the
entire system once complete (e.g.  driving a signal off-chip, rather than the
interface to some particular sub-block of the design).  The :class:`.Const`
class is useful for specifying hard-wired values, while :class:`.Register` is
how sequential elements are created (the all have an implict clock).

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
