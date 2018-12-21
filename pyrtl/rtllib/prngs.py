"""

``Example``::

    # prng_trivium
    load, req = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'req')
    ready, rand = pyrtl.Output(1, 'ready'), pyrtl.Output(128, 'rand')
    ready_out, rand_out = prngs.prng_trivium(128, load, req)
    ready <<= ready_out
    rand <<= rand_out
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)

    # seed once at the beginning
    sim.step({'load': 1, 'req': 0})
    while sim.value[ready] == 0:
        sim.step({'load': 0, 'req': 0})

    sim.step({'load': 0, 'req': 1})
    while sim.value[ready] == 0:
        sim.step({'load': 0, 'req': 0})

    print(sim.inspect(rand))
    sim_trace.render_trace(symbol_len=45, segment_size=5)

    # prng_lfsr
    load, req = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'req')
    rand = pyrtl.Output(32, 'rand')
    rand <<= prngs.prng_lfsr(32, load, req)
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)

    sim.step({'load': 1, 'req': 0}) # seed once at the beginning
    sim.step({'load': 0, 'req': 1})
    sim.step({'load': 0, 'req': 0})
    print(sim.inspect(rand))
    sim_trace.render_trace(symbol_len=30, segment_size=1)

    # explicit seeding
    seed =  pyrtl.Input(89, 'seed')
    load, req = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'req')
    rand = pyrtl.Output(32, 'rand')
    rand <<= prngs.prng_lfsr(32, load, req, seed)
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)

    sim.step({'load': 1, 'req': 0, 'seed': 0x102030405060708090a0b0c})
    sim.step({'load': 0, 'req': 1, 'seed': 0x102030405060708090a0b0c})
    sim.step({'load': 0, 'req': 0, 'seed': 0x102030405060708090a0b0c})
    print(sim.inspect(rand))
    sim_trace.render_trace(symbol_len=30, segment_size=1)

"""


from __future__ import absolute_import
import pyrtl


def prng_lfsr(bitwidth, load, req, seed=None):
    """
    Builds a single-cycle PRNG using a 89 bits Fibonacci LFSR.

    :param bitwidth: the desired bitwidth of the random number
    :param load: one bit signal to load the seed into prng
    :param req: one bit signal to request a random number
    :param seed: 89 bits WireVector, defaults to None (self-seeding)
    :return: register containing the random number with the given bitwidth

    A fast PRNG that generates a random number using only one clock cycle.
    Large bitwidth may require very big area, because a regular LFSR outputs only
    one bit per cycle, unrolling the loop adds extra gates. Not cryptographically strong,
    but can be used as a test pattern generator or anything that requires random patterns.
    """
    # Note: 89 bits is chosen because 89 is a mersenne prime, which makes the period
    # of the LFSR maximized at 2**89 - 1 for any bitwidth of random numbers
    if seed is None:
        import random
        cryptogen = random.SystemRandom()
        seed = cryptogen.randrange(1, 2**89)  # seeds itself if no seed signal is given

    lfsr = pyrtl.Register(89 if bitwidth < 89 else bitwidth)
    # leap ahead by shifting the LFSR bitwidth times
    leap_ahead = lfsr
    for i in range(bitwidth):
        leap_ahead = pyrtl.concat(leap_ahead, leap_ahead[50] ^ leap_ahead[88])

    with pyrtl.conditional_assignment:
        with load:
            lfsr.next |= seed
        with req:
            lfsr.next |= leap_ahead
    return lfsr[:bitwidth]


def prng_trivium(bitwidth, load, req, seed=None, bits_per_cycle=64):
    """
    Builds a cyptographically secure PRNG using the Trivium stream cipher.

    :param bitwidth: the desired bitwidth of the random number
    :param load: one bit signal to load the seed into csprng
    :param req: one bit signal to request a random number
    :param seed: 160 bits WireVector (80 bits key + 80 bits IV), defaults to None (self-seeding)
    :param bits_per_cycle: the number of output bits to generate in parallel each cycle
      Up to 64 bits each cycle. Must be a common divisor of 1152 and the bitwidth.
    :return ready, rand: ready is a one bit signal showing either the random number has
      been produced or the seed has been initialized, rand is a register containing the
      random number

    Trivium has a seed initialization stage that discards the first weak 1152 bits after
    each loading. Generation stage can take multiple cycles as well depending on the given
    bitwidth and bits_per_cycle.
    Has small gate area and superior speed compared to AES and other stream ciphers.
    Passes all known statistical tests. Can be used to generate encryption keys or IVs.
    """
    # Trivium specifications and performace referenced from:
    # http://www.ecrypt.eu.org/stream/ciphers/trivium/trivium.pdf
    # See also the eSTREAM portfolio page for Trivium:
    # http://www.ecrypt.eu.org/stream/e2-trivium.html
    from math import ceil, log
    if bits_per_cycle > 64:
        raise pyrtl.PyrtlError('bits_per_cycle should not exceed 64')
    if bitwidth % bits_per_cycle != 0 or 1152 % bits_per_cycle != 0:
        raise pyrtl.PyrtlError('bits_per_cycle is invalid')
    if seed is None:  # seeds itself if no seed signal is given
        import random
        cryptogen = random.SystemRandom()
        key, iv = (cryptogen.randrange(2**80) for i in range(2))
    else:
        from pyrtl.rtllib import libutils
        seed = pyrtl.as_wires(seed, 160)
        iv, key = libutils.partition_wire(seed, 80)
        # To use csprng as a stream cipher, put key in MSBs and IV in LSBs

    a = pyrtl.Register(93)
    b = pyrtl.Register(84)
    c = pyrtl.Register(111)
    feedback_a, feedback_b, feedback_c, output = ([] for i in range(4))
    for i in range(bits_per_cycle):
        t1 = a[65 - i] ^ a[92 - i]
        t2 = b[68 - i] ^ b[83 - i]
        t3 = c[65 - i] ^ c[110 - i]
        feedback_a.append(t3 ^ c[108 - i] & c[109 - i] ^ a[68 - i])
        feedback_b.append(t1 ^ a[90 - i] & a[91 - i] ^ b[77 - i])
        feedback_c.append(t2 ^ b[81 - i] & b[82 - i] ^ c[86 - i])
        output.append(t1 ^ t2 ^ t3)

    rand = pyrtl.Register(bitwidth)
    state = pyrtl.Register(1)
    counter_bitwidth = int(ceil(log(max(bitwidth, 1152) // bits_per_cycle + 1, 2)))
    counter = pyrtl.Register(counter_bitwidth, 'counter')
    init_done = counter == 1152 // bits_per_cycle
    gen_done = counter == bitwidth // bits_per_cycle
    INIT, GEN = (pyrtl.Const(x) for x in range(2))
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
                a.next |= pyrtl.concat(a, *feedback_a)
                b.next |= pyrtl.concat(b, *feedback_b)
                c.next |= pyrtl.concat(c, *feedback_c)
        with state == GEN:
            with ~gen_done:
                counter.next |= counter + 1
                a.next |= pyrtl.concat(a, *feedback_a)
                b.next |= pyrtl.concat(b, *feedback_b)
                c.next |= pyrtl.concat(c, *feedback_c)
                rand.next |= pyrtl.concat(rand, *output)

    ready = ~load & ~req & (state == INIT) & init_done | (state == GEN) & gen_done
    return ready, rand


def fibonacci_lfsr(bitwidth, load, shift, seed):
    """
    Builds a generic LFSR configured in Fibonacci setting.

    :param bitwidth: the bitwidth of the LFSR
    :param load: one bit signal to load the seed into LFSR
    :param shift: one bit signal to shift the LFSR
    :param seed: bitwidth bits WireVector
    :return: register containing the internal state of the LFSR
      Entire state returned for flexibility. Take LSB only for maximum randomness.

    A LFSR where the outputs of several bits are XORed to provide the input bit to be shifted in.
    Generates a peudorandom bit (LSB) each cycle with a period of 2**bitwidth - 1.
    """
    if bitwidth not in lfsr_tap_table:
        raise pyrtl.PyrtlError('Bitwidth {} is either invalid or not supported'.format(bitwidth))

    lfsr = pyrtl.Register(bitwidth)
    feedback = lfsr[lfsr_tap_table[bitwidth][0] - 1]
    for tap in lfsr_tap_table[bitwidth][1:]:
        feedback = feedback ^ lfsr[tap - 1]

    with pyrtl.conditional_assignment:
        with load:
            lfsr.next |= seed
        with shift:
            lfsr.next |= pyrtl.concat(lfsr, feedback)
    return lfsr


def galois_lfsr(bitwidth, load, shift, seed):
    """
    Builds a generic LFSR configured in Galois setting.

    :param bitwidth: the bitwidth of the LFSR
    :param load: one bit signal to load the seed into LFSR
    :param shift: one bit signal to shift the LFSR
    :param seed: bitwidth bits WireVector or integer
    :return: register containing the internal state of the LFSR
      Entire state returned for flexibility. Take MSB only for maximum randomness.

    A LFSR where the bit shifted out is XORed to the inputs of several bits.
    Generates a peudorandom bit (MSB) each cycle with a period of 2**bitwidth - 1.
    Faster than a Fibonacci LFSR. Outputs the same bit stream as a Fibonacci LFSR
    with a time offset.
    """
    if bitwidth not in lfsr_tap_table:
        raise pyrtl.PyrtlError('Bitwidth {} is either invalid or not supported'.format(bitwidth))

    lfsr = pyrtl.Register(bitwidth)
    shifted_lfsr = lfsr[-1]
    for tap in reversed(range(1, bitwidth)):
        if tap in lfsr_tap_table[bitwidth]:
            # tap numbering is reversed for Galois LFSRs
            shifted_lfsr = pyrtl.concat(lfsr[-1] ^ lfsr[bitwidth - tap - 1], shifted_lfsr)
        else:
            shifted_lfsr = pyrtl.concat(lfsr[bitwidth - tap - 1], shifted_lfsr)

    with pyrtl.conditional_assignment:
        with load:
            lfsr.next |= seed
        with shift:
            lfsr.next |= shifted_lfsr
    return lfsr


# maximal-cycle taps taken from table by Roy Ward, Tim Molteno:
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
    64: (64, 63, 61, 60),
    89: (89, 51),
    127: (127, 126),
    128: (128, 127, 126, 121),
    256: (256, 254, 251, 246),
    521: (521, 489),
    1024: (1024, 1015, 1002, 1001),
    2048: (2048, 2035, 2034, 2029),
    4096: (4096, 4095, 4081, 4069),
}
