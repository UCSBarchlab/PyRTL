Helper Functions
================

Cutting and Extending WireVectors
---------------------------------

The functions below provide ways of combining, slicing, and extending
:class:`WireVectors<.WireVector>` in ways that are often useful in hardware
design.  The functions below extend those member functions of the
:class:`.WireVector` class itself (which provides support for the Python
builtin ``len``, slicing e.g. ``wire[3:6]``,
:meth:`~pyrtl.wire.WireVector.zero_extended`,
:meth:`~pyrtl.wire.WireVector.sign_extended`, and many operators such as
addition and multiplication).

.. autofunction:: pyrtl.corecircuits.concat
.. autofunction:: pyrtl.corecircuits.concat_list
.. autofunction:: pyrtl.corecircuits.match_bitwidth
.. autofunction:: pyrtl.helperfuncs.truncate
.. autofunction:: pyrtl.helperfuncs.chop
.. autofunction:: pyrtl.helperfuncs.wire_struct
.. autofunction:: pyrtl.helperfuncs.wire_matrix

Coercion to WireVector
----------------------

In PyRTL there is only one function in charge of coercing values into
:class:`WireVectors<.WireVector>`, and that is :func:`.as_wires`.  This
function is called in almost all helper functions and classes to manage the
mixture of constants and WireVectors that naturally occur in hardware
development.

.. autofunction:: pyrtl.corecircuits.as_wires

Control Flow Hardware
---------------------

.. autofunction:: pyrtl.corecircuits.mux
.. autofunction:: pyrtl.corecircuits.select
.. autofunction:: pyrtl.corecircuits.enum_mux
.. autofunction:: pyrtl.corecircuits.bitfield_update
.. autofunction:: pyrtl.corecircuits.bitfield_update_set
.. autofunction:: pyrtl.helperfuncs.match_bitpattern

Creating Lists of WireVectors
-----------------------------

.. autofunction:: pyrtl.helperfuncs.input_list
.. autofunction:: pyrtl.helperfuncs.output_list
.. autofunction:: pyrtl.helperfuncs.register_list
.. autofunction:: pyrtl.helperfuncs.wirevector_list

Interpreting Vectors of Bits
----------------------------

Under the hood, every single `value` a PyRTL design operates on is a bit vector
(which is, in turn, simply an integer of bounded power-of-two size.
Interpreting these bit vectors as humans, and turning human understandable
values into their corresponding bit vectors, can both be a bit of a pain.  The
functions below do not create any hardware but rather help in the process of
reasoning about bit vector representations of human understandable values.

.. autofunction:: pyrtl.helperfuncs.val_to_signed_integer
.. autofunction:: pyrtl.helperfuncs.val_to_formatted_str
.. autofunction:: pyrtl.helperfuncs.formatted_str_to_val
.. autoclass:: pyrtl.helperfuncs.ValueBitwidthTuple
   :members: value, bitwidth
.. autofunction:: pyrtl.helperfuncs.infer_val_and_bitwidth
.. autofunction:: pyrtl.helperfuncs.log2

Debugging
---------

.. autofunction:: pyrtl.core.set_debug_mode
.. autofunction:: pyrtl.helperfuncs.probe
.. autofunction:: pyrtl.helperfuncs.rtl_assert
.. autofunction:: pyrtl.helperfuncs.check_rtl_assertions

Reductions
----------

.. autofunction:: pyrtl.corecircuits.and_all_bits
.. autofunction:: pyrtl.corecircuits.or_all_bits
.. autofunction:: pyrtl.corecircuits.xor_all_bits
.. autofunction:: pyrtl.corecircuits.parity
.. autofunction:: pyrtl.corecircuits.rtl_any
.. autofunction:: pyrtl.corecircuits.rtl_all

Extended Logic and Arithmetic
-----------------------------

The functions below provide ways of comparing and arithmetically combining
:class:`WireVectors<.WireVector>` in ways that are often useful in hardware
design. The functions below extend those member functions of the
:class:`.WireVector` class itself (which provides support for unsigned
addition, subtraction, multiplication, comparison, and many others).

.. autofunction:: pyrtl.corecircuits.signed_add
.. autofunction:: pyrtl.corecircuits.signed_sub
.. autofunction:: pyrtl.corecircuits.signed_mult
.. autofunction:: pyrtl.corecircuits.signed_lt
.. autofunction:: pyrtl.corecircuits.signed_le
.. autofunction:: pyrtl.corecircuits.signed_gt
.. autofunction:: pyrtl.corecircuits.signed_ge
.. autofunction:: pyrtl.corecircuits.shift_left_arithmetic
.. autofunction:: pyrtl.corecircuits.shift_right_arithmetic
.. autofunction:: pyrtl.corecircuits.shift_left_logical
.. autofunction:: pyrtl.corecircuits.shift_right_logical

Encoders and Decoders
---------------------

.. autofunction:: pyrtl.helperfuncs.one_hot_to_binary
.. autofunction:: pyrtl.helperfuncs.binary_to_one_hot

