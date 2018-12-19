import random
import unittest
from itertools import islice

import pyrtl
from pyrtl.rtllib import prngs


class TestPrngs(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    @staticmethod
    def sw_fibonacci_lfsr(bitwidth, seed):
        fib_lfsr = seed
        while True:
            feedback = 0
            for tap in prngs.lfsr_tap_table[bitwidth]:
                feedback ^= fib_lfsr >> tap - 1
            feedback = feedback & 1
            fib_lfsr = fib_lfsr << 1 | feedback
            yield feedback

    @staticmethod
    def sw_galois_lfsr(bitwidth, seed):
        gal_lfsr = seed
        while True:
            msb = gal_lfsr >> bitwidth - 1 & 1
            gal_lfsr = gal_lfsr << 1
            if msb:
                for tap in prngs.lfsr_tap_table[bitwidth]:
                    gal_lfsr ^= 1 << bitwidth - tap
            yield msb

    def test_prng(self):
        seed = pyrtl.Input(89, 'seed')
        load, req = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'req')
        rand = pyrtl.Output(128, 'rand')
        rand <<= prngs.prng(128, load, req, seed)
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        seed_vals = [random.randrange(1, 2**89) for i in range(5)]

        for trial in range(5):
            sw_lfsr = TestPrngs.sw_fibonacci_lfsr(89, seed_vals[trial])
            true_val = 0
            for bit in islice(sw_lfsr, 128):
                true_val = true_val << 1 | bit
            sim.step({'load': 1, 'req': 0, 'seed': seed_vals[trial]})
            sim.step({'load': 0, 'req': 1, 'seed': 0x0})
            sim.step({'load': 0, 'req': 0, 'seed': 0x0})
            circuit_out = sim.inspect(rand)
            self.assertEqual(circuit_out, true_val,
                             "\nAssertion failed on trial: {} Expected value: {} Gotten value: {}"
                             .format(trial, hex(true_val), hex(circuit_out)))

    def test_csprng(self):
        """
        Trivium test vectors retrived from:
        https://www.sheffield.ac.uk/polopoly_fs/1.12164!/file/eSCARGOt_full_datasheet_v1.3.pdf
        """
        in_vector = pyrtl.Input(160, 'in_vector')
        load, req = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'req')
        ready = pyrtl.Output(1, 'ready')
        out_vector = pyrtl.Output(128, 'rand')
        ready_out, rand_out = prngs.csprng(128, load, req, in_vector)
        ready <<= ready_out
        out_vector <<= rand_out
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)

        test_vectors = [0x0100000000000000000000000000000000000000,
                        0x0a09080706050403020100000000000000000000,
                        0xfffefdfcfbfaf9f8f7f600000000000000000000,
                        0xfaa75401ae5b08b5620fc760f9922bc45df68f28,
                        0xf5a24ffca95603b05d0abe57f08922bb54ed861f, ]

        true_vals = [0x1cd761ffceb05e39f5b18f5c22042ab0,
                     0x372e6b86524afa71b5fee86d5cebb07d,
                     0xc100baca274287277ff49b9fb512af1c,
                     0xcb5996fcff373a953fc169e899e02f46,
                     0xf142d1df4b36c7652cba2e4a22ee51a0, ]

        for trial in range(5):
            sim.step({'load': 1, 'req': 0, 'in_vector': test_vectors[trial]})
            for cycle in range(1, 20):
                sim.step({'load': 0, 'req': 0, 'in_vector': 0x0})
            sim.step({'load': 0, 'req': 1, 'in_vector': 0x0})
            for cycle in range(21, 24):
                sim.step({'load': 0, 'req': 0, 'in_vector': 0x0})
            circuit_out = sim.inspect(out_vector)
            self.assertEqual(circuit_out, true_vals[trial],
                             "\nAssertion failed on trial: {} Expected value: {} Gotten value: {}"
                             .format(trial, hex(true_vals[trial]), hex(circuit_out)))

        for ready_signal in sim_trace.trace['ready'][:19]:
            self.assertEqual(ready_signal, 0)
        self.assertEqual(sim_trace.trace['ready'][19], 1)

        for ready_signal in sim_trace.trace['ready'][20:23]:
            self.assertEqual(ready_signal, 0)
        self.assertEqual(sim_trace.trace['ready'][23], 1)

    def test_fibonacci_lfsr(self):
        bitwidth = random.choice(list(prngs.lfsr_tap_table.keys()))
        seed = pyrtl.Input(bitwidth, 'seed')
        load, shift = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'shift')
        bit_out = pyrtl.Output(1, 'bit_out')
        lfsr = prngs.fibonacci_lfsr(bitwidth, load, shift, seed)
        bit_out <<= lfsr[0]
        seed_vals = [random.randrange(1, 2**bitwidth) for i in range(5)]

        for trial in range(5):
            sim_trace = pyrtl.SimulationTrace()
            sim = pyrtl.Simulation(tracer=sim_trace)
            true_val = TestPrngs.sw_fibonacci_lfsr(bitwidth, seed_vals[trial])

            sim.step({'load': 1, 'shift': 0, 'seed': seed_vals[trial]})
            for cycle in range(1, 500):
                sim.step({'load': 0, 'shift': 1, 'seed': 0x0})

            for cycle in range(2, 500):
                circuit_out = sim_trace.trace['bit_out'][cycle]
                self.assertEqual(circuit_out, next(true_val),
                                 "\nAssertion failed for bitwidth {} on trial {} on cycle {}"
                                 .format(bitwidth, trial, cycle))

    def test_galois_lfsr(self):
        bitwidth = random.choice(list(prngs.lfsr_tap_table.keys()))
        seed = pyrtl.Input(bitwidth, 'seed')
        load, shift = pyrtl.Input(1, 'load'), pyrtl.Input(1, 'shift')
        bit_out = pyrtl.Output(1, 'bit_out')
        lfsr = prngs.galois_lfsr(bitwidth, load, shift, seed)
        bit_out <<= lfsr[-1]
        seed_vals = [random.randrange(1, 2**bitwidth) for i in range(5)]

        for trial in range(5):
            sim_trace = pyrtl.SimulationTrace()
            sim = pyrtl.Simulation(tracer=sim_trace)
            true_val = TestPrngs.sw_galois_lfsr(bitwidth, seed_vals[trial])

            sim.step({'load': 1, 'shift': 0, 'seed': seed_vals[trial]})
            for cycle in range(1, 500):
                sim.step({'load': 0, 'shift': 1, 'seed': 0x0})

            for cycle in range(1, 500):
                circuit_out = sim_trace.trace['bit_out'][cycle]
                self.assertEqual(circuit_out, next(true_val),
                                 "\nAssertion failed for bitwidth {} on trial {} on cycle {}"
                                 .format(bitwidth, trial, cycle))
