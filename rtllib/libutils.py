from pyrtl import *


def match_bitwidth(*args):
    # TODO: allow for custom bit extension functions
    """
    Matches the bitwidth of all of the input arguments
    :type args: WireVector
    :return tuple of args in order with extended bits
    """
    max_len = max(len(wv) for wv in args)
    return (wv.zero_extended(max_len) for wv in args)
