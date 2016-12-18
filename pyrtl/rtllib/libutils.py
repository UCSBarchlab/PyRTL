from __future__ import absolute_import
from operator import add

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


def twos_comp_repr(val, bitwidth):
    """
    Converts a value to it's two's-complement (positive) integer representation using a
    given bitwidth (only converts the value if it is negative).
    For use with Simulation.step() etc. in passing negative numbers, which it does not accept
    """
    correctbw = abs(val).bit_length() + 1
    if bitwidth < correctbw:
        raise pyrtl.PyrtlError("please choose a larger target bitwidth")
    if val >= 0:
        return val
    else:
        return (~abs(val) & (2**bitwidth-1)) + 1  # flip the bits and add one


def rev_twos_comp_repr(val, bitwidth):
    """
    Takes a two's-complement represented value and
    converts it to a signed integer based on the provided bitwidth.
    For use with Simulation.inspect() etc. when expecting negative numbers,
    which it does not recognize
    """
    valbl = val.bit_length()
    if bitwidth < val.bit_length() or val == 2**(bitwidth-1):
        raise pyrtl.PyrtlError("please choose a larger target bitwidth")
    if bitwidth == valbl:  # MSB is a 1, value is negative
        return -((~val & (2**bitwidth-1)) + 1)  # flip the bits, add one, and make negative
    else:
        return val


def _shifted_reg_next(reg, direct, num=1):
    """
    Creates a shifted 'next' property for shifted (left or right) register.\n
    Use: `myReg.next = shifted_reg_next(myReg, 'l', 4)`

    :param string direct: direction of shift, either 'l' or 'r'
    :param int num: number of shifts
    :return: Register containing reg's (shifted) next state
    """
    if direct == 'l':
        if num >= len(reg):
            return 0
        else:
            return pyrtl.concat(reg, pyrtl.Const(0, num))
    elif direct == 'r':
        if num >= len(reg):
            return 0
        else:
            return reg[num:]
    else:
        raise pyrtl.PyrtlError("direction must be specified with 'direct'"
                               "parameter as either 'l' or 'r'")


def detect_add_overflow(in1, in2, add_func=add, signed=True):
    res = add_func(in1, in2)
    ov_bit = res[-2 if signed else -1]
    neg_overflow = in1[-1] & in2[-1] & ~ov_bit if signed else pyrtl.Const(0, 1)
    pos_overflow = ~in1[-1] & ~in2[-1] & ov_bit
    overflow = neg_overflow | pos_overflow
    return res, overflow
