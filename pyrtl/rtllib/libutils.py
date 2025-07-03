import pyrtl


def match_bitwidth(*args: pyrtl.WireVector):
    # TODO: allow for custom bit extension functions
    """Matches the bitwidth of all of the input arguments.

    .. WARNING::

        Use :func:`.match_bitwidth` instead.

    :param args: input arguments

    :return: tuple of ``args`` in order with extended bits
    """
    return pyrtl.match_bitwidth(*args)


def partition_wire(
    wire: pyrtl.WireVector, partition_size: int
) -> list[pyrtl.WireVector]:
    """Partitions a wire into a list of ``N`` wires of size ``partition_size``.

    The ``wire``'s bitwidth must be evenly divisible by ``partition_size``.

    .. WARNING::

        Use :func:`.wire_matrix` or :func:`.chop` instead.

    :param wire: Wire to partition.
    :param partition_size: Integer representing size of each partition.
    """
    if len(wire) % partition_size != 0:
        msg = (
            f"Wire {wire} cannot be evenly partitioned into items of size "
            f"{partition_size}"
        )
        raise pyrtl.PyrtlError(msg)
    return [
        wire[offset : offset + partition_size]
        for offset in range(0, len(wire), partition_size)
    ]


def str_to_int_array(string, base=16):
    """
    Converts a string to an array of integer values according to the base specified (int
    numbers must be whitespace delimited).

    Example: ``"13 a3 3c" => [0x13, 0xa3, 0x3c]``

    .. WARNING::

        Use a :class:`list` comprehension instead::

            >>> hex_string = "13 a3 3c"

            >>> int_list = [int(s, base=16) for s in hex_string.split()]

            >>> int_list
            [19, 163, 60]
            >>> [hex(i) for i in int_list]
            ['0x13', '0xa3', '0x3c']


    :return: [int]
    """
    int_strings = string.split()
    return [int(int_str, base) for int_str in int_strings]


def twos_comp_repr(val: int, bitwidth: int) -> int:
    """Converts a value to its two's-complement (positive) integer representation using
    a given bitwidth (only converts the value if it is negative).

    .. WARNING::

        Use :func:`.infer_val_and_bitwidth` instead.

    :param val: Integer literal to convert to two's complement
    :param bitwidth: Size of val in bits
    """
    correctbw = abs(val).bit_length() + 1
    if bitwidth < correctbw:
        msg = "please choose a larger target bitwidth"
        raise pyrtl.PyrtlError(msg)
    if val >= 0:
        return val
    return (~abs(val) & (2**bitwidth - 1)) + 1  # flip the bits and add one


def rev_twos_comp_repr(val: int, bitwidth: int) -> int:
    """Takes a two's-complement represented value and converts it to a signed integer
    based on the provided ``bitwidth``.

    .. WARNING::

        Use :func:`.val_to_signed_integer` instead.
    """
    valbl = val.bit_length()
    if bitwidth < val.bit_length() or val == 2 ** (bitwidth - 1):
        msg = "please choose a larger target bitwidth"
        raise pyrtl.PyrtlError(msg)
    if bitwidth == valbl:  # MSB is a 1, value is negative
        return -(
            (~val & (2**bitwidth - 1)) + 1
        )  # flip the bits, add one, and make negative
    return val


def _shifted_reg_next(reg: pyrtl.Register, direct: str, num: int = 1):
    """Creates a shifted :attr:`.Register.next` property for shifted (left or right)
    register.

    Use: ``myReg.next = shifted_reg_next(myReg, 'l', 4)``

    .. WARNING::

        Use :func:`.shift_left_logical` or :func:`.shift_right_logical` instead.

    :param direct: Direction of shift, either ``l`` or ``r``.
    :param num: Number of bit positions to shift.

    :return: Register containing reg's (shifted) next state
    """
    if direct == "l":
        if num >= len(reg):
            return 0
        return pyrtl.concat(reg, pyrtl.Const(0, num))
    if direct == "r":
        if num >= len(reg):
            return 0
        return reg[num:]
    msg = "direction must be specified with 'direct' parameter as either 'l' or 'r'"
    raise pyrtl.PyrtlError(msg)
