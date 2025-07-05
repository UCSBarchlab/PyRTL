"""
Basic shifting is defined in PyRTL's core library, see:

- :func:`.shift_left_logical`

- :func:`.shift_right_logical`

- :func:`.shift_right_arithmetic`

:func:`barrel_shifter` should only be used when more complex shifting behavior is
required.
"""

from enum import IntEnum

from pyrtl.wire import WireVector, WireVectorLike


class Direction(IntEnum):
    """Assigns names to each shift direction, to improve code readability."""

    RIGHT = 0
    LEFT = 1


def barrel_shifter(
    bits_to_shift: WireVector,
    bit_in: WireVectorLike,
    direction: WireVectorLike,
    shift_dist: WireVector,
    wrap_around=0,
) -> WireVector:
    """Create a barrel shifter.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> bits_to_shift = pyrtl.Input(name="input", bitwidth=8)
        >>> shift_dist = pyrtl.Input(name="shift_dist", bitwidth=3)
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.barrel.barrel_shifter(
        ...     bits_to_shift,
        ...     bit_in=1,
        ...     direction=pyrtl.rtllib.barrel.Direction.RIGHT,
        ...     shift_dist=shift_dist)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"input": 0x55, "shift_dist": 4})
        >>> hex(sim.inspect("output"))
        '0xf5'

    :param bits_to_shift: :class:`.WireVector` with the value to shift.
    :param bit_in: A 1-bit :class:`.WireVector` representing the value to shift in.
    :param direction: A one bit :class:`.WireVector` representing the shift direction
        (``0`` = shift right, ``1`` = shift left). If ``direction`` is constant, use
        :class:`Direction` to improve code readability (``direction=Direction.RIGHT``
        instead of ``direction=0``).
    :param shift_dist: :class:`.WireVector` representing the amount to shift.
    :param wrap_around: ****currently not implemented****

    :return: The shifted :class:`.WireVector`.
    """
    from pyrtl import concat, select  # just for readability

    if wrap_around != 0:
        raise NotImplementedError

    # Implement with logN stages pyrtl.muxing between shifted and un-shifted values
    final_width = len(bits_to_shift)
    val = bits_to_shift
    append_val = bit_in

    for i in range(len(shift_dist)):
        shift_amt = pow(2, i)  # stages shift 1,2,4,8,...
        if shift_amt < final_width:
            newval = select(
                direction,
                concat(val[:-shift_amt], append_val),  # shift left
                concat(append_val, val[shift_amt:]),
            )  # shift right
            val = select(
                shift_dist[i],
                truecase=newval,  # if bit of shift is 1, do the shift
                falsecase=val,
            )  # otherwise, don't
            # the value to append grows exponentially, but is capped at full width
            append_val = concat(append_val, append_val)[:final_width]
        else:
            # if we are shifting this much, all the data is gone
            val = select(
                shift_dist[i],
                truecase=append_val,  # if bit of shift is 1, do the shift
                falsecase=val,
            )  # otherwise, don't

    return val
