import unittest

import pyrtl
import pyrtl.corecircuits
from pyrtl.rtllib import aes, testingutils


class TestAESDecrypt(unittest.TestCase):
    """
    Test vectors are retrieved from:
    http://csrc.nist.gov/publications/fips/fips197/fips-197.pdf
    """

    def setUp(self):
        pyrtl.reset_working_block()
        self.aes_decrypt = aes.AES()
        self.in_vector = pyrtl.Input(bitwidth=128, name="in_vector")
        self.out_vector = pyrtl.Output(bitwidth=128, name="out_vector")

    def test_inv_shift_rows(self):
        self.out_vector <<= self.aes_decrypt._inv_shift_rows(self.in_vector)

        in_vals = [
            0x3E1C22C0B6FCBF768DA85067F6170495,
            0x2D6D7EF03F33E334093602DD5BFB12C7,
        ]
        true_result = [
            0x3E175076B61C04678DFC2295F6A8BFC0,
            0x2DFB02343F6D12DD09337EC75B36E3F0,
        ]
        calculated_result = testingutils.sim_and_ret_out(
            self.out_vector, (self.in_vector,), (in_vals,)
        )
        self.assertEqual(calculated_result, true_result)

    def test_inv_sub_bytes(self):
        self.out_vector <<= self.aes_decrypt._sub_bytes(self.in_vector, True)

        in_vals = [
            0x3E175076B61C04678DFC2295F6A8BFC0,
            0x2DFB02343F6D12DD09337EC75B36E3F0,
        ]
        true_result = [
            0xD1876C0F79C4300AB45594ADD66FF41F,
            0xFA636A2825B339C940668A3157244D17,
        ]
        calculated_result = testingutils.sim_and_ret_out(
            self.out_vector, (self.in_vector,), (in_vals,)
        )
        self.assertEqual(calculated_result, true_result)

    def test_inv_mix_columns(self):
        self.out_vector <<= self.aes_decrypt._mix_columns(self.in_vector, True)

        in_vals = [
            0xE9F74EEC023020F61BF2CCF2353C21C7,
            0xBAA03DE7A1F9B56ED5512CBA5F414D23,
        ]
        real_res = [
            0x54D990A16BA09AB596BBF40EA111702F,
            0x3E1C22C0B6FCBF768DA85067F6170495,
        ]
        calculated_result = testingutils.sim_and_ret_out(
            self.out_vector, (self.in_vector,), (in_vals,)
        )
        self.assertEqual(calculated_result, real_res)

    def test_aes_full(self):
        aes_key = pyrtl.Input(bitwidth=128, name="aes_key")
        self.out_vector <<= self.aes_decrypt.decryption(self.in_vector, aes_key)

        ciphers = [
            0x3AD77BB40D7A3660A89ECAF32466EF97,
            0x66E94BD4EF8A2C3B884CFA59CA342B2E,
        ]
        keys = [0x2B7E151628AED2A6ABF7158809CF4F3C, 0x0]
        plain_text = [0x6BC1BEE22E409F96E93D7E117393172A, 0x0]
        calculated_result = testingutils.sim_and_ret_out(
            self.out_vector, (self.in_vector, aes_key), (ciphers, keys)
        )
        self.assertEqual(calculated_result, plain_text)

    def test_aes_state_machine(self):
        # self.longMessage = True

        aes_key = pyrtl.Input(bitwidth=128, name="aes_key")
        reset = pyrtl.Input(1)
        ready = pyrtl.Output(1, name="ready")

        decrypt_ready, decrypt_out = self.aes_decrypt.decryption_statem(
            self.in_vector, aes_key, reset
        )
        self.out_vector <<= decrypt_out
        ready <<= decrypt_ready

        sim = pyrtl.Simulation()

        sim.step(
            {
                self.in_vector: 0x69C4E0D86A7B0430D8CDB78070B4C55A,
                aes_key: 0x000102030405060708090A0B0C0D0E0F,
                reset: 1,
            }
        )

        true_vals = [
            0x69C4E0D86A7B0430D8CDB78070B4C55A,
            0x7AD5FDA789EF4E272BCA100B3D9FF59F,
            0x54D990A16BA09AB596BBF40EA111702F,
            0x3E1C22C0B6FCBF768DA85067F6170495,
            0xB458124C68B68A014B99F82E5F15554C,
            0xE8DAB6901477D4653FF7F5E2E747DD4F,
            0x36339D50F9B539269F2C092DC4406D23,
            0x2D6D7EF03F33E334093602DD5BFB12C7,
            0x3BD92268FC74FB735767CBE0C0590E2D,
            0xA7BE1A6997AD739BD8C9CA451F618B61,
            0x6353E08C0960E104CD70B751BACAD0E7,
            0x00112233445566778899AABBCCDDEEFF,
            0x00112233445566778899AABBCCDDEEFF,
        ]

        for cycle in range(1, 13):  # Bogus data for while the state machine churns
            sim.step({self.in_vector: 0x0, aes_key: 0x1, reset: 0})
            circuit_out = sim.tracer.trace["out_vector"][cycle]
            self.assertEqual(
                circuit_out,
                true_vals[cycle],
                f"\nAssertion failed on cycle: {cycle} Gotten value: "
                f"{hex(circuit_out)}",
            )

        for ready_signal in sim.tracer.trace["ready"][:11]:
            self.assertEqual(ready_signal, 0)

        for ready_signal in sim.tracer.trace["ready"][11:]:
            self.assertEqual(ready_signal, 1)


class TestAESEncrypt(unittest.TestCase):
    """
    Test vectors are retrieved from:
    http://csrc.nist.gov/publications/fips/fips197/fips-197.pdf
    """

    def setUp(self):
        pyrtl.reset_working_block()
        self.aes_encrypt = aes.AES()
        self.in_vector = pyrtl.Input(bitwidth=128, name="in_vector")
        self.out_vector = pyrtl.Output(bitwidth=128, name="out_vector")

    def test_shift_rows(self):
        self.out_vector <<= self.aes_encrypt._shift_rows(self.in_vector)

        in_vals = [
            0x3B59CB73FCD90EE05774222DC067FB68,
            0xB415F8016858552E4BB6124C5F998A4C,
        ]
        true_result = [
            0x3BD92268FC74FB735767CBE0C0590E2D,
            0xB458124C68B68A014B99F82E5F15554C,
        ]
        calculated_result = testingutils.sim_and_ret_out(
            self.out_vector, (self.in_vector,), (in_vals,)
        )
        self.assertEqual(calculated_result, true_result)

    def test_sub_bytes(self):
        self.out_vector <<= self.aes_encrypt._sub_bytes(self.in_vector)

        in_vals = [
            0x4915598F55E5D7A0DACA94FA1F0A63F7,
            0xC62FE109F75EEDC3CC79395D84F9CF5D,
        ]
        true_result = [
            0x3B59CB73FCD90EE05774222DC067FB68,
            0xB415F8016858552E4BB6124C5F998A4C,
        ]
        calculated_result = testingutils.sim_and_ret_out(
            self.out_vector, (self.in_vector,), (in_vals,)
        )
        self.assertEqual(calculated_result, true_result)

    def test_mix_columns(self):
        self.out_vector <<= self.aes_encrypt._mix_columns(self.in_vector)

        in_vals = [
            0x6353E08C0960E104CD70B751BACAD0E7,
            0xA7BE1A6997AD739BD8C9CA451F618B61,
        ]
        real_res = [
            0x5F72641557F5BC92F7BE3B291DB9F91A,
            0xFF87968431D86A51645151FA773AD009,
        ]
        calculated_result = testingutils.sim_and_ret_out(
            self.out_vector, (self.in_vector,), (in_vals,)
        )
        self.assertEqual(calculated_result, real_res)

    def test_aes_full(self):
        aes_key = pyrtl.Input(bitwidth=128, name="aes_key")
        self.out_vector <<= self.aes_encrypt.encryption(self.in_vector, aes_key)

        plain_text = [0x00112233445566778899AABBCCDDEEFF, 0x0]
        keys = [0x000102030405060708090A0B0C0D0E0F, 0x0]
        ciphers = [
            0x69C4E0D86A7B0430D8CDB78070B4C55A,
            0x66E94BD4EF8A2C3B884CFA59CA342B2E,
        ]
        calculated_result = testingutils.sim_and_ret_out(
            self.out_vector, (self.in_vector, aes_key), (plain_text, keys)
        )
        self.assertEqual(calculated_result, ciphers)

    def test_aes_state_machine(self):
        # self.longMessage = True

        aes_key = pyrtl.Input(bitwidth=128, name="aes_key")
        reset = pyrtl.Input(1)
        ready = pyrtl.Output(1, name="ready")

        encrypt_ready, encrypt_out = self.aes_encrypt.encrypt_state_m(
            self.in_vector, aes_key, reset
        )
        self.out_vector <<= encrypt_out
        ready <<= encrypt_ready

        sim = pyrtl.Simulation()

        sim.step(
            {
                self.in_vector: 0x00112233445566778899AABBCCDDEEFF,
                aes_key: 0x000102030405060708090A0B0C0D0E0F,
                reset: 1,
            }
        )

        true_vals = [
            0x00112233445566778899AABBCCDDEEFF,
            0x00102030405060708090A0B0C0D0E0F0,
            0x89D810E8855ACE682D1843D8CB128FE4,
            0x4915598F55E5D7A0DACA94FA1F0A63F7,
            0xFA636A2825B339C940668A3157244D17,
            0x247240236966B3FA6ED2753288425B6C,
            0xC81677BC9B7AC93B25027992B0261996,
            0xC62FE109F75EEDC3CC79395D84F9CF5D,
            0xD1876C0F79C4300AB45594ADD66FF41F,
            0xFDE3BAD205E5D0D73547964EF1FE37F1,
            0xBD6E7C3DF2B5779E0B61216E8B10B689,
            0x69C4E0D86A7B0430D8CDB78070B4C55A,
            0x69C4E0D86A7B0430D8CDB78070B4C55A,
        ]

        for cycle in range(1, 13):  # Bogus data for while the state machine churns
            sim.step({self.in_vector: 0x0, aes_key: 0x1, reset: 0})
            circuit_out = sim.tracer.trace["out_vector"][cycle]
            # sim.tracer.render_trace(symbol_len=40)
            self.assertEqual(
                circuit_out,
                true_vals[cycle],
                f"\nAssertion failed on cycle: {cycle} Gotten value: "
                f"{hex(circuit_out)}",
            )

        for ready_signal in sim.tracer.trace["ready"][:11]:
            self.assertEqual(ready_signal, 0)

        for ready_signal in sim.tracer.trace["ready"][11:]:
            self.assertEqual(ready_signal, 1)


if __name__ == "__main__":
    unittest.main()
