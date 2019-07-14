"""

``Example``::

    ``csprng_trivium``
    load, req = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'req')
    ready, rand = pyrtl.Output(1, 'ready'), pyrtl.Output(128, 'rand')
    ready_out, rand_out = prngs.csprng_trivium(128, load, req)
    ready <<= ready_out
    rand <<= rand_out
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)

    # seed once at the beginning
    sim.step({'load': 1, 'req': 0})
    while sim.value[ready] == 0:  # or loop 19 cycles
        sim.step({'load': 0, 'req': 0})

    sim.step({'load': 0, 'req': 1})
    while sim.value[ready] == 0:  # or loop 2 cycles
        sim.step({'load': 0, 'req': 0})

    print(sim.inspect(rand))
    sim_trace.render_trace(symbol_len=45, segment_size=5)

    ``prng_xoroshiro128``
    load, req = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'req')
    ready, rand = pyrtl.Output(1, 'ready'), pyrtl.Output(128, 'rand')
    ready_out, rand_out = prngs.prng_xoroshiro128(128, load, req)
    ready <<= ready_out
    rand <<= rand_out
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)

    sim.step({'load': 1, 'req': 0})  # seed once at the beginning
    sim.step({'load': 0, 'req': 1})
    while sim.value[ready] == 0:  # or loop 2 cycles
        sim.step({'load': 0, 'req': 0})

    print(sim.inspect(rand))
    sim_trace.render_trace(symbol_len=40, segment_size=1)

    ``prng_lfsr``
    load, req = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'req')
    rand = pyrtl.Output(64, 'rand')
    rand <<= prngs.prng_lfsr(64, load, req)
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)

    sim.step({'load': 1, 'req': 0}) # seed once at the beginning
    sim.step({'load': 0, 'req': 1})
    sim.step({'load': 0, 'req': 0})
    print(sim.inspect(rand))
    sim_trace.render_trace(symbol_len=40, segment_size=1)

    ``explicit seeding``
    seed =  pyrtl.Input(127, 'seed')
    load, req = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'req')
    rand = pyrtl.Output(32, 'rand')
    rand <<= prngs.prng_lfsr(32, load, req, seed)
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)

    sim.step({'load': 1, 'req': 0, 'seed': 0x102030405060708090a0b0c0d0e0f010})
    sim.step({'load': 0, 'req': 1, 'seed': 0x102030405060708090a0b0c0d0e0f010})
    sim.step({'load': 0, 'req': 0, 'seed': 0x102030405060708090a0b0c0d0e0f010})
    print(sim.inspect(rand))
    sim_trace.render_trace(symbol_len=40, segment_size=1)

"""


from __future__ import absolute_import
import pyrtl


def prng_lfsr(bitwidth, load, req, seed=None):
    """ Builds a single-cycle PRNG using a 127 bits Fibonacci LFSR.

    :param bitwidth: the desired bitwidth of the random number
    :param load: one bit signal to load the seed into the prng
    :param req: one bit signal to request a random number
    :param seed: 127 bits WireVector, defaults to None (self-seeding),
      refrain from self-seeding if reseeding at run time is required
    :return: register containing the random number with the given bitwidth

    A very fast and compact PRNG that generates a random number using only one clock cycle.
    Has a period of 2**127 - 1. Its linearity makes it a bit statistically weak, but should be
    good enough for any noncryptographic purpose like test pattern generation.
    """
    # 127 bits is chosen because 127 is a mersenne prime, which makes the period of the
    # LFSR maximized at 2**127 - 1 for any requested bitwidth
    if seed is None:
        import random
        cryptogen = random.SystemRandom()
        seed = cryptogen.randrange(1, 2**127)  # seed itself if no seed signal is given

    lfsr = pyrtl.Register(127 if bitwidth < 127 else bitwidth)
    # leap ahead by shifting the LFSR bitwidth times
    leap_ahead = lfsr
    for i in range(bitwidth):
        leap_ahead = pyrtl.concat(leap_ahead, leap_ahead[125] ^ leap_ahead[126])

    with pyrtl.conditional_assignment:
        with load:
            lfsr.next |= seed
        with req:
            lfsr.next |= leap_ahead
    return lfsr[:bitwidth]


def prng_xoroshiro128(bitwidth, load, req, seed=None):
    """ Builds a PRNG using the Xoroshiro128+ algorithm in hardware.

    :param bitwidth: the desired bitwidth of the random number
    :param load: one bit signal to load the seed into the prng
    :param req: one bit signal to request a random number
    :param seed: 128 bits WireVector, defaults to None (self-seeding),
      refrain from self-seeding if reseeding at run time is required
    :return ready, rand: ready is a one bit signal showing the random number has been
      produced, rand is a register containing the random number with the given bitwidth

    An efficient noncryptographic PRNG, has much smaller area than Trivium.
    But it does require a 64-bit adder to compute the output, so it is a bit slower.
    Has a period of 2**128 - 1. Passes most statistical tests. Outputs a 64-bit random
    word each cycle, takes multiple cycles if more than 64 bits are requested, and MSBs
    of the random words are returned if the bitwidth is not a multiple of 64.

    See also http://xoroshiro.di.unimi.it/
    """
    from math import ceil, log
    from pyrtl.rtllib import adders
    from pyrtl.rtllib.libutils import _shifted_reg_next as shift  # for readability
    if seed is None:
        import random
        cryptogen = random.SystemRandom()
        seed = cryptogen.randrange(1, 2**128)  # seed itself if no seed signal is given
    seed = pyrtl.as_wires(seed, 128)

    s0, s1 = (pyrtl.Register(64) for i in range(2))
    output = pyrtl.WireVector(64)
    # update internal states by xoring, rotating, and shifting
    _s1 = s0 ^ s1
    s0_next = (shift(s0, 'l', 55) | shift(s0, 'r', 9)) ^ shift(_s1, 'l', 14) ^ _s1
    s1_next = shift(_s1, 'l', 36) | shift(_s1, 'r', 28)
    output <<= adders.kogge_stone(s0, s1)

    gen_cycles = int(ceil(bitwidth / 64))
    counter_bitwidth = int(ceil(log(gen_cycles, 2))) if gen_cycles > 1 else 1
    rand = pyrtl.Register(gen_cycles * 64)
    counter = pyrtl.Register(counter_bitwidth, 'counter')
    gen_done = counter == gen_cycles - 1
    state = pyrtl.Register(1)
    WAIT, GEN = (pyrtl.Const(x) for x in range(2))
    with pyrtl.conditional_assignment:
        with load:
            s0.next |= seed[:64]
            s1.next |= seed[64:]
            state.next |= WAIT
        with req:
            counter.next |= 0
            s0.next |= s0_next
            s1.next |= s1_next
            rand.next |= pyrtl.concat(rand, output)
            state.next |= GEN
        with state == GEN:
            with ~gen_done:
                counter.next |= counter + 1
                s0.next |= s0_next
                s1.next |= s1_next
                rand.next |= pyrtl.concat(rand, output)

    ready = ~load & ~req & (state == GEN) & gen_done
    return ready, rand[-bitwidth:]  # return MSBs because LSBs are less random


def csprng_trivium(bitwidth, load, req, seed=None, bits_per_cycle=64):
    """ Builds a cyptographically secure PRNG using the Trivium stream cipher.

    :param bitwidth: the desired bitwidth of the random number
    :param load: one bit signal to load the seed into the prng
    :param req: one bit signal to request a random number
    :param seed: 160 bits WireVector (80 bits key + 80 bits IV), defaults to None (self-seeding),
      refrain from self-seeding if reseeding at run time is needed
    :param bits_per_cycle: the number of output bits to generate in parallel each cycle,
      up to 64 bits, must be a power of two: either 1, 2, 4, 8, 16, 32, or 64
    :return ready, rand: ready is a one bit signal showing either the random number has
      been produced or the seed has been initialized, rand is a register containing the
      random number with the given bitwidth

    This prng uses Trivium's key stream as its random bits output.
    Both seed and key stream are MSB first (the earliest bit is stored at the MSB).
    Trivium has a seed initialization stage that discards the first weak 1152 output bits
    after each loading. Generation stage can take multiple cycles as well depending on the
    given bitwidth and bits_per_cycle.
    Has smaller gate area and faster speed than AES-CTR and any other stream cipher.
    Passes all known statistical tests. Can be used to generate encryption keys or IVs.
    Designed to securely generate up to 2**64 bits. If more than 2**64 bits is needed,
    must reseed after each generation of 2**64 bits.

    Trivium specifications:
    http://www.ecrypt.eu.org/stream/ciphers/trivium/trivium.pdf
    See also the eSTREAM portfolio page:
    http://www.ecrypt.eu.org/stream/e2-trivium.html
    """
    from math import ceil, log
    if (64 // bits_per_cycle) * bits_per_cycle != 64:
        raise pyrtl.PyrtlError('bits_per_cycle is invalid')
    if seed is None:
        import random
        cryptogen = random.SystemRandom()
        seed = cryptogen.randrange(2**160)  # seed itself if no seed signal is given
    seed = pyrtl.as_wires(seed, 160)
    key = seed[80:]
    iv = seed[:80]

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
    # update internal states by shifting bits_per_cycle times
    a_next = pyrtl.concat(a, *feedback_a)
    b_next = pyrtl.concat(b, *feedback_b)
    c_next = pyrtl.concat(c, *feedback_c)

    init_cycles = 1152 // bits_per_cycle
    gen_cycles = int(ceil(bitwidth / bits_per_cycle))
    counter_bitwidth = int(ceil(log(max(init_cycles + 1, gen_cycles), 2)))
    rand = pyrtl.Register(bitwidth)
    counter = pyrtl.Register(counter_bitwidth, 'counter')
    init_done = counter == init_cycles
    gen_done = counter == gen_cycles - 1
    state = pyrtl.Register(2)
    WAIT, INIT, GEN = (pyrtl.Const(x) for x in range(3))
    with pyrtl.conditional_assignment:
        with load:
            counter.next |= 0
            a.next |= key
            b.next |= iv
            c.next |= pyrtl.concat(pyrtl.Const("3'b111"), pyrtl.Const(0, 108))
            state.next |= INIT
        with req:
            counter.next |= 0
            a.next |= a_next
            b.next |= b_next
            c.next |= c_next
            rand.next |= pyrtl.concat(rand, *output)
            state.next |= GEN
        with state == INIT:
            with ~init_done:
                counter.next |= counter + 1
                a.next |= a_next
                b.next |= b_next
                c.next |= c_next
        with state == GEN:
            with ~gen_done:
                counter.next |= counter + 1
                a.next |= a_next
                b.next |= b_next
                c.next |= c_next
                rand.next |= pyrtl.concat(rand, *output)

    ready = ~load & ~req & ((state == INIT) & init_done | (state == GEN) & gen_done)
    return ready, rand
