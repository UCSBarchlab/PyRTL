from __future__ import absolute_import
import pyrtl


def fibonacci_lfsr(seed, bitwidth, reset, enable=pyrtl.Const(1)):
    """
    Creates a Fibonacci linear feedback shift register given the seed and bitwidth.

    :param seed: the initial value of the LFSR
    :param bitwidth: the bitwidth of LFSR
    :param reset: one bit WireVector to set the LFSR to its seed state
    :param enable: one bit WireVector to enable/disable the LFSR
    :return: register storing the random value produced by the LFSR

    The Fibonacci LFSR uses cascaded external xor gates to generate a 2^n - 1 cycles
    pseudo random number sequence without repeating. It has a longer critical path
    delay than the Galois LFSR.
    """
    assert len(reset) == len(enable) == 1
    if bitwidth not in tap_table:
        raise pyrtl.PyrtlError(
            'Bitwidth {} is either illegal or not supported'.format(bitwidth))
    seed = pyrtl.as_wires(seed, bitwidth)
    pyrtl.rtl_assert(seed != 0, pyrtl.PyrtlError(
        'LFSR must start in non-zero seed state'))
    lfsr = pyrtl.Register(bitwidth, 'lfsr')
    feedback = lfsr[bitwidth - tap_table[bitwidth][0]]
    for tap in tap_table[bitwidth][1:]:
        # tap numbering is reversed for Fibonacci LFSRs
        feedback = feedback ^ lfsr[bitwidth - tap]
    with pyrtl.conditional_assignment:
        with enable:
            with reset:
                lfsr.next |= seed
            with pyrtl.otherwise:
                lfsr.next |= pyrtl.concat(feedback, lfsr[1:])
    return lfsr


def galois_lfsr(seed, bitwidth, reset, enable=pyrtl.Const(1)):
    """
    Creates a Galois linear feedback shift register given the seed and bitwidth.

    :param seed: initial value of the LFSR
    :param bitwidth: the bitwidth of LFSR
    :param reset: one bit WireVector to set the LFSR to its seed state
    :param enable: one bit WireVector to enable/disable the LFSR
    :return: register storing the random value produced by the LFSR

    The Galois LFSR uses parallel internal xor gates to generate a 2^n - 1 cycles
    pseudo random number sequence without repeating. The Galois LFSR is faster than
    the Fibonacci LFSR. It produces the same msb stream as the Fibonacci LFSR but a
    different random number sequence.
    """
    assert len(reset) == len(enable) == 1
    if bitwidth not in tap_table:
        raise pyrtl.PyrtlError(
            'Bitwidth {} is either illegal or not supported'.format(bitwidth))
    seed = pyrtl.as_wires(seed, bitwidth)
    pyrtl.rtl_assert(seed != 0, pyrtl.PyrtlError(
        'LFSR must start in non-zero seed state'))
    lfsr = pyrtl.Register(bitwidth, 'lfsr')
    shifted_lfsr = lfsr[0]
    for i in reversed(range(1, bitwidth)):
        if i in tap_table[bitwidth]:
            shifted_lfsr = pyrtl.concat(shifted_lfsr, lfsr[0] ^ lfsr[i])
        else:
            shifted_lfsr = pyrtl.concat(shifted_lfsr, lfsr[i])
    with pyrtl.conditional_assignment:
        with enable:
            with reset:
                lfsr.next |= seed
            with pyrtl.otherwise:
                lfsr.next |= shifted_lfsr
    return lfsr


# maximal-cycle taps taken from table by Roy Ward, Tim Molteno
# http://www.physics.otago.ac.nz/reports/electronics/ETR2012-1.pdf
# taps for other numbers of bitwidth can be added in the same fashion
tap_table = {
    2: (2, 1),
    3: (3, 2),
    4: (4, 3),
    5: (5, 3),
    6: (6, 5),
    7: (7, 6),
    8: (8, 6, 5, 4),
    9: (9, 5),
    10: (10, 7),
    11: (11, 9),
    12: (12, 11, 8, 6),
    13: (13, 12, 10, 9),
    14: (14, 13, 11, 9),
    15: (15, 14),
    16: (16, 14, 13, 11),
    17: (17, 14),
    18: (18, 11),
    19: (19, 18, 17, 14),
    20: (20, 17),
    21: (21, 19),
    22: (22, 21),
    23: (23, 18),
    24: (24, 23, 21, 20),
    25: (25, 22),
    26: (26, 25, 24, 20),
    27: (27, 26, 25, 22),
    28: (28, 25),
    29: (29, 27),
    30: (30, 29, 26, 24),
    31: (31, 28),
    32: (32, 30, 26, 25),
    64: (64, 63, 61, 60),
    128: (128, 127, 126, 121),
    256: (256, 254, 251, 246),
    1024: (1024, 1015, 1002, 1001),
    2048: (2048, 2035, 2034, 2029),
    4096: (4096, 4095, 4081, 4069),
}
