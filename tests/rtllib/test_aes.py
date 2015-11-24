import unittest
import pyrtl
from pyrtl.rtllib import aes
import random


class TestAES(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(15151515)

    def setUp(self):
        pyrtl.reset_working_block()
        self.aes = aes.AES()
        self.in_vector = pyrtl.Input(bitwidth=128, name='in_vector')
        self.out_vector = pyrtl.Output(bitwidth=128, name='out_vector')

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_inv_shift_rows(self):
        # Create logic net
        self.out_vector <<= self.aes.inv_shift_rows(self.in_vector)

        # Create test values and correct result
        true_result = [0xbd6e7c3df2b5779e0b61216e8b10b689]

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(1):
            sim.step({self.in_vector: 0xbdb52189f261b63d0b107c9e8b6e776e})

        inv_shift_rows_result = sim_trace.trace[self.out_vector]
        self.assertEqual(inv_shift_rows_result, true_result)

    def test_inv_sub_bytes(self):
        self.out_vector <<= self.aes.inv_sub_bytes(self.in_vector)

        true_result = [0xabdb52189f261b63d0b107c9e8b6e776e]

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(1):
            sim.step({self.in_vector: 0x7ad5fda789ef4e272bca100b3d9ff59f})

        inv_sub_bytes_result = sim_trace.trace[self.out_vector]
        self.assertEqual(inv_sub_bytes_result, true_result)

    def test_mix_columns(self):
        self.out_vector <<= self.aes.inv_mix_columns(self.in_vector)

        true_result = [0x4773b91ff72f354361cb018ea1e6cf2c]
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(1):
            sim.step({self.in_vector: 0xbd6e7c3df2b5779e0b61216e8b10b689})

        inv_mix_columns_result = sim_trace.trace[self.out_vector]
        self.assertEqual(inv_mix_columns_result, true_result)

    def xest_adroundkey(self):
        # !!!!!! NOT BEING TESTED !!!!!!!!
        self.out_vector <<= self.aes.addroundkey(self.in_vector)

        true_result = 0xc57e1c159a9bd286f05f4be098c63439
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(1):
            sim.step({self.in_vector: 0x14f9701ae35fe28c440adf4d4ea9c026})

        addroundkey_result = sim_trace.trace[self.out_vector]
        self.assertEqual(addroundkey_result, true_result)

    def test_aes_full(self):
        aes_key = pyrtl.Input(bitwidth=128, name='aes_key')
        self.out_vector <<= self.aes.decryption(self.in_vector, aes_key)

        sim_trace = pyrtl.SimulationTrace(wirevector_subset=[self.in_vector, aes_key,
                                                             self.out_vector])
        sim = pyrtl.Simulation(tracer=sim_trace)

        # ciphers = [0x3ad77bb40d7a3660a89ecaf32466ef97, ]
        # keys = [0x2b7e151628aed2a6abf7158809cf4f3c, ]
        # plain_text = [0x6bc1bee22e409f96e93d7e117393172a]
        ciphers = [0x66e94bd4ef8a2c3b884cfa59ca342b2e]
        keys = [0]
        plain_text = [0]
        for key, cipher in zip(keys, ciphers):
            sim.step({
                self.in_vector: cipher,
                aes_key: key
            })

        self.assertListEqual(sim_trace.trace[self.out_vector], plain_text)

        sim_trace.render_trace(symbol_len=40, segment_size=1)

    def test_aes_state_machine(self):
        aes_key = pyrtl.Input(bitwidth=128, name='aes_key')
        reset = pyrtl.Input(1)
        ready = pyrtl.Output(1)

        decrypt_out, decrypt_ready = self.aes.decryption_statem(self.in_vector, aes_key, reset)
        self.out_vector <<= decrypt_out
        ready <<= decrypt_ready

        sim_trace = pyrtl.SimulationTrace(wirevector_subset=[self.in_vector, aes_key, self.out_vector])
        sim = pyrtl.Simulation(tracer=sim_trace)

        sim.step({
            self.in_vector: 0x66e94bd4ef8a2c3b884cfa59ca342b2e,
            aes_key: 0x0,
            reset: 1
        })

        for cycle in range(10):
            sim.step({
                self.in_vector: 0x0,
                aes_key: 0x1,
                reset: 0
            })

        sim_trace.render_trace(symbol_len=40, segment_size=1)
