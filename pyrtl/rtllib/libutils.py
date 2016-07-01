from __future__ import absolute_import

import pyrtl


def match_bitwidth(*args):
    # TODO: allow for custom bit extension functions
    """ Matches the bitwidth of all of the input arguments.

    :param WireVector args: input arguments
    :return: tuple of `args` in order with extended bits
    """
    return pyrtl.match_bitwidth(*args)


def partition_wire(wire, partition_size):
    if len(wire) % partition_size != 0:
        raise pyrtl.PyrtlError("Wire {} cannot be evenly partitioned into items of size {}"
                               .format(wire, partition_size))
    return [wire[offset:offset + partition_size] for offset in range(0, len(wire), partition_size)]


def str_to_int_array(string, base=16):
    """
    Converts a string to an array of integer values according to the
    base specified (int numbers must be whitespace delimited).\n
    Example: "13 a3 3c" => [0x13, 0xa3, 0x3c]

    :return: [int]
    """

    int_strings = string.split()
    return [int(int_str, base) for int_str in int_strings]
