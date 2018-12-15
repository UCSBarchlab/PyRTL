"""
Example::
    req, load = pyrtl.Input(1, 'req'), pyrtl.Input(1, 'load')
    ready = pyrtl.Output(1, 'ready')
    rand, ready_out = prngs.prng(bitwidth=8, req, load)
    ready <<= ready_out
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)

    sim.step({'load': 1, 'req': 0})
    while sim.value[ready] == 0:
        sim.step({'load': 0, 'req': 0})

    sim.step({'load': 0, 'req': 1})
    while sim.value[ready] == 0:
        sim.step({'load': 0, 'req': 0})

    print(sim.inspect(rand))
    sim_trace.render_trace(trace_list=[
        'load', 'req', 'ready', 'rand'], symbol_len=5, segment_size=10)

    # explicit seeding
    seed =  pyrtl.Input(40, 'seed')
    req, load = pyrtl.Input(1, 'req'), pyrtl.Input(1, 'load')
    ready = pyrtl.Output(1, 'ready')
    rand, ready_out = prngs.prng(bitwidth=8, req, load, seed)
    ready <<= ready_out
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)

    sim.step({'load': 1, 'req': 0, 'seed': 0x123456789a})
    while sim.value[ready] == 0:
        sim.step({'load': 0, 'req': 0, 'seed': 0x123456789a})

    # csprng can be used in the same way
"""


from __future__ import absolute_import
import pyrtl
from pyrtl.rtllib import libutils


def prng(bitwidth, req, load, seed=None):
    """
    Builds a quick PRNG using a 39 bits Galois LFSR.

    :param bitwidth: the bitwidth of the random number
    :param req: one bit signal to request the PRNG to generate a random number
    :param load: one bit signal to load the seed into the PRNG
    :param seed: 40 bits WireVector
    :return rand, ready: ready is a one bit signal showing either the random number has
      been produced or the seed has been loaded

    Discards the first 39 bits after seeding and produces one bit per cycle afterwards.
    prng is a quick PRNG with good statistical properties. Can be used as a test pattern
    generator or anything that requires random patterns. prng is not cryptographically
    strong and should not be used for crypto purposes.
    """
    from math import ceil, log
    # prng will seed itself if no seed signal is given
    try:
        seed = pyrtl.as_wires(seed, 40)
    except pyrtl.PyrtlError:
        import time
        seed = int(time.time() * 256)

    shift = pyrtl.WireVector(1)
    # 39 bits internal state
    lfsr = galois_lfsr(39, shift, load, seed)
    rand = pyrtl.Register(bitwidth, 'rand')
    counter = pyrtl.Register(
        int(ceil(log(max(bitwidth, 39), 2) + 1)), 'counter')
    init_done = counter == 39
    gen_done = counter == bitwidth
    state = pyrtl.Register(1, 'state')
    INIT, GEN = (pyrtl.Const(x, 1) for x in range(2))

    with pyrtl.conditional_assignment:
        with load:
            counter.next |= 0
            state.next |= INIT
        with req:
            counter.next |= 0
            rand.next |= 0
            state.next |= GEN
        with state == INIT:
            with ~init_done:
                counter.next |= counter + 1
        with state == GEN:
            with ~gen_done:
                counter.next |= counter + 1
                rand.next |= pyrtl.concat(rand, lfsr[-1])

    shift <<= (state == INIT) & ~init_done | (state == GEN) & ~gen_done
    ready = ~load & ~req & ((state == INIT) & init_done | (
        state == GEN) & gen_done)
    return rand, ready


def csprng(bitwidth, req, load, seed=None):
    """
    Builds a cyptographically secure PRNG using the Trivium stream cipher.

    :param bitwidth: the bitwidth of the random number
    :param req: one bit signal to request the PRNG to generate a random number
    :param load: one bit signal to load the seed into the PRNG
    :param seed: 160 bits WireVector
    :return rand, ready: ready is a one bit signal showing either the random number has
      been produced or the seed has been loaded

    Discards the first 1152 bits after seeding and produces one bit per cycle afterwards.
    csprng takes advantage of Trivium's small gate area, superior speed and statistical
    performance compared to other stream ciphers. Can be used to generate random
    encryption keys or IVs.

    Trivium specifications retrived from
    http://www.ecrypt.eu.org/stream/ciphers/trivium/trivium.pdf
    """
    from math import ceil, log
    # csprng will seed itself if no seed signal is given
    try:
        seed = pyrtl.as_wires(seed, 160)
        iv, key = libutils.partition_wire(seed, 80)
    except pyrtl.PyrtlError:
        import os
        key, iv = (int(os.urandom(10).hex(), 16) for i in range(2))

    # 288 bits internal state
    a = pyrtl.Register(93, 'a')
    b = pyrtl.Register(84, 'b')
    c = pyrtl.Register(111, 'c')
    feedforward_a = a[65] ^ a[90] & a[91] ^ a[92]
    feedback_b = feedforward_a ^ b[77]
    feedforward_b = b[68] ^ b[81] & b[82] ^ b[83]
    feedback_c = feedforward_b ^ c[86]
    feedforward_c = c[65] ^ c[108] & c[109] ^ c[110]
    feedback_a = feedforward_c ^ a[68]
    bit_out = feedforward_a ^ feedforward_b ^ feedforward_c

    rand = pyrtl.Register(bitwidth, 'rand')
    counter = pyrtl.Register(
        int(ceil(log(max(bitwidth, 1152) + 1, 2))), 'counter')
    init_done = counter == 1152
    gen_done = counter == bitwidth
    state = pyrtl.Register(1, 'state')
    INIT, GEN = (pyrtl.Const(x, 1) for x in range(2))

    with pyrtl.conditional_assignment:
        with load:
            counter.next |= 0
            a.next |= key
            b.next |= iv
            c.next |= pyrtl.concat(pyrtl.Const("3'b111"), pyrtl.Const(0, 108))
            state.next |= INIT
        with req:
            counter.next |= 0
            rand.next |= 0
            state.next |= GEN
        with state == INIT:
            with ~init_done:
                counter.next |= counter + 1
                a.next |= pyrtl.concat(a, feedback_a)
                b.next |= pyrtl.concat(b, feedback_b)
                c.next |= pyrtl.concat(c, feedback_c)
        with state == GEN:
            with ~gen_done:
                counter.next |= counter + 1
                a.next |= pyrtl.concat(a, feedback_a)
                b.next |= pyrtl.concat(b, feedback_b)
                c.next |= pyrtl.concat(c, feedback_c)
                rand.next |= pyrtl.concat(rand, bit_out)

    ready = ~load & ~req & ((state == INIT) & init_done | (
        state == GEN) & gen_done)
    return rand, ready


def fibonacci_lfsr(bitwidth, req, load, seed):
    """
    Creates a LFSR configured in fibonacci setting.

    :param bitwidth: the bitwidth of the LFSR
    :param req: one bit signal to request the LFSR to generate one bit
    :param load: one bit signal to load the seed into LFSR
    :param seed: the initial state of the LFSR
    :return: register containing the internal state of the LFSR. Entire state
      returned for flexibility. Take lsb only for maximum randomness.

    Fibonacci LFSR uses cascaded external xor gates to generate a peudorandom bit
    per cycle with a period of 2^n - 1.
    Has a longer critical path delay than a Galois LFSR.
    """
    seed = pyrtl.as_wires(seed, bitwidth)
    if bitwidth not in lfsr_tap_table:
        raise pyrtl.PyrtlError(
            'Bitwidth {} is either illegal or not supported'.format(bitwidth))
    pyrtl.rtl_assert(seed != 0, pyrtl.PyrtlError(
        'LFSR must start in non-zero seed state'))

    lfsr = pyrtl.Register(bitwidth, 'lfsr')
    feedback = lfsr[lfsr_tap_table[bitwidth][0] - 1]
    for tap in lfsr_tap_table[bitwidth][1:]:
        feedback = feedback ^ lfsr[tap - 1]

    with pyrtl.conditional_assignment:
        with load:
            lfsr.next |= seed
        with req:
            lfsr.next |= pyrtl.concat(lfsr, feedback)
    return lfsr


def galois_lfsr(bitwidth, req, load, seed):
    """
    Creates a LFSR configured in galois setting.

    :param bitwidth: the bitwidth of the LFSR
    :param req: one bit signal to request the LFSR to generate one bit
    :param load: one bit signal to load the seed into LFSR
    :param seed: the initial state of the LFSR
    :return: register containing the internal state of the LFSR. Entire state
      returned for flexibility. Take msb only for maximum randomness.

    Galois LFSR uses parallel internal xor gates to generate a peudorandom bit
    per cycle with a period of 2^n - 1. Faster than a Fibonacci LFSR.
    Outputs the same bit stream as a Fibonacci LFSR with a time offset.
    """
    seed = pyrtl.as_wires(seed, bitwidth)
    if bitwidth not in lfsr_tap_table:
        raise pyrtl.PyrtlError(
            'Bitwidth {} is either illegal or not supported'.format(bitwidth))
    pyrtl.rtl_assert(seed != 0, pyrtl.PyrtlError(
        'LFSR must start in non-zero seed state'))

    lfsr = pyrtl.Register(bitwidth, 'lfsr')
    shifted_lfsr = lfsr[-1]
    for i in reversed(range(1, bitwidth)):
        if i in lfsr_tap_table[bitwidth]:
            # tap numbering is reversed for Galois LFSRs
            shifted_lfsr = pyrtl.concat(
                lfsr[-1] ^ lfsr[bitwidth - i - 1], shifted_lfsr)
        else:
            shifted_lfsr = pyrtl.concat(lfsr[bitwidth - i - 1], shifted_lfsr)

    with pyrtl.conditional_assignment:
        with load:
            lfsr.next |= seed
        with req:
            lfsr.next |= shifted_lfsr
    return lfsr


# maximal-cycle taps taken from table by Roy Ward, Tim Molteno
# http://www.physics.otago.ac.nz/reports/electronics/ETR2012-1.pdf
# taps for other number of bitwidth can be added in the same fashion
lfsr_tap_table = {
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
    37: (37, 36, 33, 31),
    39: (39, 35),
    64: (64, 63, 61, 60),
    83: (83, 81, 79, 76),
    128: (128, 127, 126, 121),
    256: (256, 254, 251, 246),
    1024: (1024, 1015, 1002, 1001),
    2048: (2048, 2035, 2034, 2029),
    4096: (4096, 4095, 4081, 4069),
}
