import random
import unittest
from itertools import islice

import pyrtl
from pyrtl.rtllib import prngs


class TestPrngs(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    @staticmethod
    def fibonacci_lfsr(seed):
        lfsr = seed
        while True:
            bit = (lfsr >> 126 ^ lfsr >> 125) & 1
            lfsr = lfsr << 1 | bit
            yield bit

    @staticmethod
    def xoroshiro128plus(seed):
        mask = 2**64 - 1
        s = [seed & mask, seed >> 64]
        while True:
            s0 = s[0]
            s1 = s[1]
            word = (s1 + s0) & mask
            s1 ^= s0
            s[0] = (s0 << 55 | s0 >> 9) ^ s1 ^ s1 << 14
            s[1] = s1 << 36 | s1 >> 28
            yield word

    def test_prng_lfsr(self):
        seed = pyrtl.Input(127, "seed")
        load, req = pyrtl.Input(1, "load"), pyrtl.Input(1, "req")
        rand = pyrtl.Output(128, "rand")
        rand <<= prngs.prng_lfsr(128, load, req, seed)
        sim = pyrtl.Simulation()
        in_vals = [random.randrange(1, 2**127) for i in range(5)]

        for trial in range(5):
            true_val = 0
            for bit in islice(TestPrngs.fibonacci_lfsr(in_vals[trial]), 128):
                true_val = true_val << 1 | bit
            sim.step({"load": 1, "req": 0, "seed": in_vals[trial]})
            sim.step({"load": 0, "req": 1, "seed": 0x0})
            sim.step({"load": 0, "req": 0, "seed": 0x0})
            circuit_out = sim.inspect(rand)
            self.assertEqual(
                circuit_out,
                true_val,
                f"\nAssertion failed on trial {trial}\n"
                f"Expected value: {hex(true_val)}\nGotten value: {hex(circuit_out)}",
            )

    def test_prng_xoroshiro128(self):
        seed = pyrtl.Input(128, "seed")
        load, req = pyrtl.Input(1, "load"), pyrtl.Input(1, "req")
        ready = pyrtl.Output(1, "ready")
        rand = pyrtl.Output(128, "rand")
        ready_out, rand_out = prngs.prng_xoroshiro128(128, load, req, seed)
        ready <<= ready_out
        rand <<= rand_out
        sim = pyrtl.Simulation()
        in_vals = [random.randrange(1, 2**128) for i in range(5)]

        for trial in range(5):
            true_val = 0
            for word in islice(TestPrngs.xoroshiro128plus(in_vals[trial]), 2):
                true_val = true_val << 64 | word
            sim.step({"load": 1, "req": 0, "seed": in_vals[trial]})
            sim.step({"load": 0, "req": 1, "seed": 0x0})
            for _cycle in range(2, 4):
                sim.step({"load": 0, "req": 0, "seed": 0x0})
            circuit_out = sim.inspect(rand)
            self.assertEqual(
                circuit_out,
                true_val,
                f"\nAssertion failed on trial {trial}\n"
                f"Expected value: {hex(true_val)}\nGotten value: {hex(circuit_out)}",
            )

        for ready_signal in sim.tracer.trace["ready"][:3]:
            self.assertEqual(ready_signal, 0)
        self.assertEqual(sim.tracer.trace["ready"][3], 1)
        self.assertEqual(sim.tracer.trace["ready"][4], 0)

    def test_csprng_trivium(self):
        """
        Trivium test vectors retrived from:
        https://www.sheffield.ac.uk/polopoly_fs/1.12164!/file/eSCARGOt_full_datasheet_v1.3.pdf
        bit ordering is modified to adapt to the Pyrtl implementation
        """
        in_vector = pyrtl.Input(160, "in_vector")
        load, req = pyrtl.Input(1, "load"), pyrtl.Input(1, "req")
        ready = pyrtl.Output(1, "ready")
        out_vector = pyrtl.Output(128, "out_vector")
        ready_out, rand_out = prngs.csprng_trivium(128, load, req, in_vector)
        ready <<= ready_out
        out_vector <<= rand_out
        sim = pyrtl.Simulation()

        in_vals = [
            0x0100000000000000000000000000000000000000,
            0x0A09080706050403020100000000000000000000,
            0xFFFEFDFCFBFAF9F8F7F600000000000000000000,
            0xFAA75401AE5B08B5620FC760F9922BC45DF68F28,
            0xF5A24FFCA95603B05D0ABE57F08922BB54ED861F,
        ]

        true_vals = [
            0x1CD761FFCEB05E39F5B18F5C22042AB0,
            0x372E6B86524AFA71B5FEE86D5CEBB07D,
            0xC100BACA274287277FF49B9FB512AF1C,
            0xCB5996FCFF373A953FC169E899E02F46,
            0xF142D1DF4B36C7652CBA2E4A22EE51A0,
        ]

        for trial in range(5):
            sim.step({"load": 1, "req": 0, "in_vector": in_vals[trial]})
            for _cycle in range(1, 20):
                sim.step({"load": 0, "req": 0, "in_vector": 0x0})
            sim.step({"load": 0, "req": 1, "in_vector": 0x0})
            for _cycle in range(21, 23):
                sim.step({"load": 0, "req": 0, "in_vector": 0x0})
            circuit_out = sim.inspect(out_vector)
            self.assertEqual(
                circuit_out,
                true_vals[trial],
                f"\nAssertion failed on trial {trial}\n"
                f"Expected value: {hex(true_vals[trial])}\n"
                f"Gotten value: {hex(circuit_out)}",
            )

        for ready_signal in sim.tracer.trace["ready"][:19]:
            self.assertEqual(ready_signal, 0)
        self.assertEqual(sim.tracer.trace["ready"][19], 1)

        for ready_signal in sim.tracer.trace["ready"][20:22]:
            self.assertEqual(ready_signal, 0)
        self.assertEqual(sim.tracer.trace["ready"][22], 1)
        self.assertEqual(sim.tracer.trace["ready"][23], 0)


if __name__ == "__main__":
    unittest.main()
