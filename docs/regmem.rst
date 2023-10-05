Registers and Memories
======================

Registers
---------

The class :class:`.Register` is derived from :class:`.WireVector`, and so can be used just like any other
:class:`.WireVector`.  A read from the register is the value that is available in the current clock
period, and the value for the follow cycle can be set by assigning to property :attr:`~pyrtl.wire.Register.next` with
the ``<<=`` operator.  Registers all, by default, reset to 0, and all reside in the same clock
domain.

.. autoclass:: pyrtl.wire.Register
    :members:
    :show-inheritance:
    :special-members: __init__


Memories
--------

.. autoclass:: pyrtl.memory.MemBlock
    :members:
    :special-members: __init__

ROMs
----

.. autoclass:: pyrtl.memory.RomBlock
    :members:
    :show-inheritance:
    :special-members: __init__
