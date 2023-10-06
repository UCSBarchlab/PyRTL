Registers and Memories
======================

Registers
---------

The class :class:`.Register` is derived from :class:`.WireVector`, and so can
be used just like any other :class:`.WireVector`.  Reading a register produces
the stored value available in the current cycle. The stored value for the
following cycle can be set by assigning to property
:attr:`~pyrtl.wire.Register.next` with the
``<<=`` (:meth:`~pyrtl.wire.WireVector.__ilshift__`) operator.  Registers reset
to zero by default, and reside in the same clock domain.

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
