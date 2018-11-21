import random
import unittest

import pyrtl
from pyrtl.rtllib import lfsr


class TestLFSR(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    @staticmethod
    def sw_fibonacci_lfsr(seed, bitwidth):
        fib_lfsr = seed
        while True:
            yield fib_lfsr
            feedback = 0
            for tap in lfsr.tap_table[bitwidth]:
                feedback ^= fib_lfsr >> (bitwidth - tap)
            fib_lfsr = (feedback & 1) << (bitwidth - 1) | fib_lfsr >> 1

    @staticmethod
    def sw_galois_lfsr(seed, bitwidth):
        gal_lfsr = seed
        while True:
            yield gal_lfsr
            lsb = gal_lfsr & 1
            gal_lfsr = gal_lfsr >> 1
            if lsb:
                for tap in lfsr.tap_table[bitwidth]:
                    gal_lfsr ^= 1 << (tap - 1)

    def test_fibonacci_lfsr(self):
        for bitwidth in (random.randrange(2, 33) for i in range(10)):
            seed, reset, enable = pyrtl.Input(bitwidth, 'seed'), pyrtl.Input(
                1, 'reset'), pyrtl.Input(1, 'enable')
            seed_vals = [random.randrange(1, 2**bitwidth) for i in range(3)]
            lfsr_out = lfsr.fibonacci_lfsr(seed, bitwidth, reset, enable)
            sim_trace = pyrtl.SimulationTrace()
            sim = pyrtl.Simulation(tracer=sim_trace)

            disable_cycle = random.randrange(1, 19)
            for cycle in range(20):
                sim.step({
                    'seed': seed_vals[0],
                    'reset': 1 if cycle == 0 else 0,
                    'enable': 0 if cycle >= disable_cycle else 1
                })
            self.assertEqual(sim_trace.trace[lfsr_out][disable_cycle + 1:],
                             [sim_trace.trace[lfsr_out][disable_cycle]]
                             * (19 - disable_cycle))

            true_val = TestLFSR.sw_fibonacci_lfsr(seed_vals[0], bitwidth)
            sim.step({'seed': seed_vals[0], 'reset': 1, 'enable': 1})
            for cycle in range(1000 if bitwidth > 10 else 2**bitwidth - 1):
                sim.step({'seed': seed_vals[1], 'reset': 0, 'enable': 1})
                self.assertEqual(sim.value[lfsr_out], next(true_val))

            true_val = TestLFSR.sw_fibonacci_lfsr(seed_vals[1], bitwidth)
            sim.step({'seed': seed_vals[1], 'reset': 1, 'enable': 1})
            for cycle in range(1000 if bitwidth > 10 else 2**bitwidth - 1):
                sim.step({'seed': seed_vals[2], 'reset': 0, 'enable': 1})
                self.assertEqual(sim.value[lfsr_out], next(true_val))
            pyrtl.reset_working_block()

    def test_galois_lfsr(self):
        for bitwidth in (random.randrange(2, 33) for i in range(10)):
            seed, reset, enable = pyrtl.Input(bitwidth, 'seed'), pyrtl.Input(
                1, 'reset'), pyrtl.Input(1, 'enable')
            seed_vals = [random.randrange(1, 2**bitwidth) for i in range(3)]
            lfsr_out = lfsr.galois_lfsr(seed, bitwidth, reset, enable)
            sim_trace = pyrtl.SimulationTrace()
            sim = pyrtl.Simulation(tracer=sim_trace)

            disable_cycle = random.randrange(1, 19)
            for cycle in range(20):
                sim.step({
                    'seed': seed_vals[0],
                    'reset': 1 if cycle == 0 else 0,
                    'enable': 0 if cycle >= disable_cycle else 1
                })
            self.assertEqual(sim_trace.trace[lfsr_out][disable_cycle + 1:],
                             [sim_trace.trace[lfsr_out][disable_cycle]]
                             * (19 - disable_cycle))

            true_val = TestLFSR.sw_galois_lfsr(seed_vals[0], bitwidth)
            sim.step({'seed': seed_vals[0], 'reset': 1, 'enable': 1})
            for cycle in range(1000 if bitwidth > 10 else 2**bitwidth - 1):
                sim.step({'seed': seed_vals[1], 'reset': 0, 'enable': 1})
                self.assertEqual(sim.value[lfsr_out], next(true_val))

            true_val = TestLFSR.sw_galois_lfsr(seed_vals[1], bitwidth)
            sim.step({'seed': seed_vals[1], 'reset': 1, 'enable': 1})
            for cycle in range(1000 if bitwidth > 10 else 2**bitwidth - 1):
                sim.step({'seed': seed_vals[2], 'reset': 0, 'enable': 1})
                self.assertEqual(sim.value[lfsr_out], next(true_val))
            pyrtl.reset_working_block()
