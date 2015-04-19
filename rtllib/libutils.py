import pyrtl
from pyrtl import *


def match_bitwidth(*args):
    # TODO: allow for custom bit extension functions
    """
    Matches the bitwidth of all of the input arguments
    :type args: WireVector
    :return tuple of args in order with extended bits
    """
    return pyrtl.match_bitwidth(*args)
