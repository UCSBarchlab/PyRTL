Helper Functions
================

Cutting and Extending WireVectors
---------------------------------

The functions below provide ways of combining, slicing, and extending
:class:`WireVectors<.WireVector>` in ways that are often useful in hardware
design. The functions below extend those member functions of the
:class:`.WireVector` class itself (which provides support for the Python
builtin :func:`len`, slicing e.g. ``wire[3:6]``,
:meth:`~.WireVector.zero_extended`, :meth:`~.WireVector.sign_extended`, and
many operators such as addition and multiplication).

.. autofunction:: pyrtl.concat
.. autofunction:: pyrtl.concat_list
.. autofunction:: pyrtl.match_bitwidth
.. autofunction:: pyrtl.truncate
.. autofunction:: pyrtl.chop
.. autofunction:: pyrtl.wire_struct
.. autofunction:: pyrtl.wire_matrix

Coercion to WireVector
----------------------

In PyRTL there is only one function in charge of coercing values into
:class:`WireVectors<.WireVector>`, and that is :func:`.as_wires`. This function
is called in almost all helper functions and classes to manage the mixture of
constants and :class:`WireVectors<.WireVector>` that naturally occur in
hardware development.

See :ref:`wirevector_coercion` for examples and more details.

.. autofunction:: pyrtl.as_wires

Control Flow Hardware
---------------------

.. autofunction:: pyrtl.mux
.. autofunction:: pyrtl.select
.. autofunction:: pyrtl.enum_mux
.. autoclass:: pyrtl.helperfuncs.MatchedFields
    :members:
    :undoc-members:
.. autofunction:: pyrtl.match_bitpattern
.. autofunction:: pyrtl.bitfield_update
.. autofunction:: pyrtl.bitfield_update_set

Interpreting Vectors of Bits
----------------------------

Under the hood, every single `value` a PyRTL design operates on is a bit vector
(which is, in turn, simply an integer of bounded power-of-two size.
Interpreting these bit vectors as humans, and turning human understandable
values into their corresponding bit vectors, can both be a bit of a pain.  The
functions below do not create any hardware but rather help in the process of
reasoning about bit vector representations of human understandable values.

.. autofunction:: pyrtl.val_to_signed_integer
.. autoclass:: pyrtl.helperfuncs.ValueBitwidthTuple
   :members: value, bitwidth
.. autofunction:: pyrtl.infer_val_and_bitwidth
.. autofunction:: pyrtl.val_to_formatted_str
.. autofunction:: pyrtl.formatted_str_to_val
.. autofunction:: pyrtl.log2

Debugging
---------

.. autofunction:: pyrtl.set_debug_mode
.. autofunction:: pyrtl.probe
.. autofunction:: pyrtl.rtl_assert

Reductions
----------

.. autofunction:: pyrtl.and_all_bits
.. autofunction:: pyrtl.or_all_bits
.. autofunction:: pyrtl.xor_all_bits
.. autofunction:: pyrtl.parity
.. autofunction:: pyrtl.rtl_any
.. autofunction:: pyrtl.rtl_all

.. _extended_logic_and_arithmetic:

Extended Logic and Arithmetic
-----------------------------

The functions below provide ways of comparing and arithmetically combining
:class:`WireVectors<.WireVector>` in ways that are often useful in hardware
design. The functions below extend those member functions of the
:class:`.WireVector` class itself (which provides support for unsigned
addition, subtraction, multiplication, comparison, and many others).

.. autofunction:: pyrtl.signed_add
.. autofunction:: pyrtl.signed_sub
.. autofunction:: pyrtl.signed_mult
.. autofunction:: pyrtl.signed_lt
.. autofunction:: pyrtl.signed_le
.. autofunction:: pyrtl.signed_gt
.. autofunction:: pyrtl.signed_ge
.. autofunction:: pyrtl.shift_left_logical
.. autofunction:: pyrtl.shift_left_arithmetic
.. autofunction:: pyrtl.shift_right_logical
.. autofunction:: pyrtl.shift_right_arithmetic

Encoders and Decoders
---------------------

.. autofunction:: pyrtl.one_hot_to_binary
.. autofunction:: pyrtl.binary_to_one_hot
