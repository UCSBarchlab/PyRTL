import pyrtl


def match_bitwidth(*args):
    # TODO: allow for custom bit extension functions
    """
    Matches the bitwidth of all of the input arguments
    :type args: WireVector
    :return tuple of args in order with extended bits
    """
    return pyrtl.match_bitwidth(*args)


def basic_n_bit_mux(ctrl, mux_in, default=None):

    default = pyrtl.Const(0) if default is None else default
    for ctrl_i in ctrl:
        next_mux_in = []
        for j in range((len(mux_in) + 1) //2):
            second = default if 2*j + 1 >= len(mux_in) else mux_in[2*j + 1]
            next_mux_in.append(pyrtl.mux(select=ctrl_i, falsecase=mux_in[2*j], truecase=second))
        mux_in = next_mux_in
    return mux_in[0]




