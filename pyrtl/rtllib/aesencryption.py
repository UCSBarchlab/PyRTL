""" AES-128 """

from __future__ import division, absolute_import
import pyrtl
from pyrtl.rtllib import libutils

# TODO:
# 2) All ROMs should be synchronous.  This should be easy once (3) is completed
# 3) Right now decryption generates one GIANT combinatorial block. Instead
#    it should generate one of 2 options -- Either an iterative design or a
#    pipelined design.  Both will add registers between each round of AES
# 4) aes_encryption should be added to this file as well so that an
#    aes encrypter similar to (3) above is generated
# 5) a single "aes-unit" combining encryption and decryption (without making
#    full independent hardware units) would be a plus as well


class AES_Encrypt(object):
    def __init__(self):
        self.memories_built = False
        """
        One-byte left circular rotation, substitution of each byte
        """
    def _g(self, word, key_expand_round):
        self.build_memories_if_not_exists()
        a = libutils.partition_wire(word, 8)
        sub = [self.sbox[a[index]] for index in (3, 0, 1, 2)]
        sub[3] = sub[3] ^ self.rcon[key_expand_round + 1]
        return pyrtl.concat_list(sub)

    def key_expansion(self, old_key, key_expand_round):
        self.build_memories_if_not_exists()
        w = libutils.partition_wire(old_key, 32)
        x = [w[3] ^ self._g(w[0], key_expand_round)]
        x.insert(0, x[0] ^ w[2])
        x.insert(0, x[0] ^ w[1])
        x.insert(0, x[0] ^ w[0])
        return pyrtl.concat_list(x)

    def sub_bytes(self, in_vector):
        self.build_memories_if_not_exists()
        subbed = [self.sbox[byte] for byte in libutils.partition_wire(in_vector, 8)]
        return pyrtl.concat_list(subbed)

    @staticmethod
    def shift_rows(in_vector):
        a = libutils.partition_wire(in_vector, 8)
        return pyrtl.concat_list((a[4], a[9],  a[14],  a[3],
                                  a[8],  a[13], a[2], a[7],
                                  a[12],  a[1],  a[6], a[11],
                                  a[0],  a[5],  a[10],  a[15]))

    def galois_mult(self, c, mult_table):
        if mult_table == 1:
            return c
        else:
            return self._inv_gal_mult_dict[mult_table][c]

    def mix_columns(self, in_vector):
        self.build_memories_if_not_exists()
        igm_mults = [2, 1, 1, 3]
        subgroups = libutils.partition_wire(in_vector, 32)
        return pyrtl.concat_list([self._mix_col_subgroup(sg, igm_mults) for sg in subgroups])

    def _mix_col_subgroup(self, in_vector, gm_multipliers):
        def _mix_single(index):
            mult_items = [self.galois_mult(a[(index + loc) % 4], mult_table)
                          for loc, mult_table in enumerate(gm_multipliers)]
            return mult_items[0] ^ mult_items[1] ^ mult_items[2] ^ mult_items[3]
        a = libutils.partition_wire(in_vector, 8)
        return pyrtl.concat_list([_mix_single(index) for index in range(len(a))])

    @staticmethod
    def add_round_key(t, key):
        return t ^ key

    def encryption_statem(self, plaintext_in, key_in, reset):
        """
        return ready, encryption_result: ready is a one bit signal showing
        that the answer encryption result has been calculated.
        """
        if len(key_in) != len(plaintext_in):
            raise pyrtl.PyrtlError("AES key and plaintext should be the same length")

        plain_text, key = (pyrtl.Register(len(plaintext_in)) for i in range(2))
        key_exp_in, add_round_in = (pyrtl.WireVector(len(plaintext_in)) for i in range(2))

        # list of generated keys, not stored in memory
        key_list = (self.encryption_key_gen(key_exp_in))
        counter = pyrtl.Register(4, 'counter')
        round = pyrtl.WireVector(4)
        counter.next <<= round
        sub_out = self.sub_bytes(plain_text)
        pyrtl.probe(sub_out, 'sub_row round ' + str(round))
        shift_out = self.shift_rows(sub_out)
        pyrtl.probe(shift_out, 'shift_row round ' + str(round))
        mix_out = self.mix_columns(shift_out)
        pyrtl.probe(mix_out, 'mix_row round ' + str(round))
        key_out = pyrtl.mux(round, *key_list, default=0)
        pyrtl.probe(key_out, 'key round ' + str(round))
        add_round_out = self.add_round_key(add_round_in, key_out)
        pyrtl.probe(add_round_out, 'add key round ' + str(round))
        pyrtl.probe(plain_text, 'plain text' + str(round))
        with pyrtl.conditional_assignment:
            with reset == 1:
                round |= 0
                key.next |= key_in
                key_exp_in |= key_in  # to lower the number of cycles needed
                plain_text.next |= add_round_out
                add_round_in |= plaintext_in

            with counter == 10:  # keep everything the same
                round |= counter
                plain_text.next |= plain_text

            with pyrtl.otherwise:  # running through AES
                round |= counter + 1
                key.next |= key
                key_exp_in |= key
                plain_text.next |= add_round_out
                with counter == 9:
                    add_round_in |= shift_out
                with pyrtl.otherwise:
                    add_round_in |= mix_out

        ready = (counter == 10)
        return ready, plain_text

    def encryption_key_gen(self, key):
        keys = [key]
        for enc_round in range(10):
            key = self.key_expansion(key, enc_round)
            keys.append(key)
        return keys

    def encryption(self, plaintext, key):
        key_list = self.encryption_key_gen(key)
        t = self.add_round_key(plaintext, key_list[0])
        pyrtl.probe(t, 'add key')

        for round in range(1, 11):
            t = self.sub_bytes(t)
            pyrtl.probe(t, 'sub' + str(round))
            t = self.shift_rows(t)
            pyrtl.probe(t, 'shift_row round ' + str(round))
            if round != 10:
                t = self.mix_columns(t)
                pyrtl.probe(t, 'mix columns round ' + str(round))
            # print 'after shift rows ' + t
            t = self.add_round_key(t, key_list[round])
        return t

    def build_memories_if_not_exists(self):
        if not self.memories_built:
            self.build_memories()

    def build_memories(self):
        def build_mem(data):
            return pyrtl.RomBlock(bitwidth=8, addrwidth=8, romdata=data, asynchronous=True)

        self.sbox = build_mem(self.sbox_data)
        self.rcon = build_mem(self.rcon_data)
        self.GM2 = build_mem(self.GM2_data)
        self.GM3 = build_mem(self.GM3_data)
        self._inv_gal_mult_dict = {3: self.GM3, 2: self.GM2}
        self.memories_built = True

    rcon_data = libutils.str_to_int_array('''
        8d 01 02 04 08 10 20 40 80 1b 36 6c d8 ab 4d 9a 2f 5e bc 63 c6 97 35 6a
        d4 b3 7d fa ef c5 91 39 72 e4 d3 bd 61 c2 9f 25 4a 94 33 66 cc 83 1d 3a
        74 e8 cb 8d 01 02 04 08 10 20 40 80 1b 36 6c d8 ab 4d 9a 2f 5e bc 63 c6
        97 35 6a d4 b3 7d fa ef c5 91 39 72 e4 d3 bd 61 c2 9f 25 4a 94 33 66 cc
        83 1d 3a 74 e8 cb 8d 01 02 04 08 10 20 40 80 1b 36 6c d8 ab 4d 9a 2f 5e
        bc 63 c6 97 35 6a d4 b3 7d fa ef c5 91 39 72 e4 d3 bd 61 c2 9f 25 4a 94
        33 66 cc 83 1d 3a 74 e8 cb 8d 01 02 04 08 10 20 40 80 1b 36 6c d8 ab 4d
        9a 2f 5e bc 63 c6 97 35 6a d4 b3 7d fa ef c5 91 39 72 e4 d3 bd 61 c2 9f
        25 4a 94 33 66 cc 83 1d 3a 74 e8 cb 8d 01 02 04 08 10 20 40 80 1b 36 6c
        d8 ab 4d 9a 2f 5e bc 63 c6 97 35 6a d4 b3 7d fa ef c5 91 39 72 e4 d3 bd
        61 c2 9f 25 4a 94 33 66 cc 83 1d 3a 74 e8 cb 8d
        ''')
    sbox_data = libutils.str_to_int_array('''
        63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7 ab 76 ca 82 c9 7d fa 59 47 f0
        ad d4 a2 af 9c a4 72 c0 b7 fd 93 26 36 3f f7 cc 34 a5 e5 f1 71 d8 31 15
        04 c7 23 c3 18 96 05 9a 07 12 80 e2 eb 27 b2 75 09 83 2c 1a 1b 6e 5a a0
        52 3b d6 b3 29 e3 2f 84 53 d1 00 ed 20 fc b1 5b 6a cb be 39 4a 4c 58 cf
        d0 ef aa fb 43 4d 33 85 45 f9 02 7f 50 3c 9f a8 51 a3 40 8f 92 9d 38 f5
        bc b6 da 21 10 ff f3 d2 cd 0c 13 ec 5f 97 44 17 c4 a7 7e 3d 64 5d 19 73
        60 81 4f dc 22 2a 90 88 46 ee b8 14 de 5e 0b db e0 32 3a 0a 49 06 24 5c
        c2 d3 ac 62 91 95 e4 79 e7 c8 37 6d 8d d5 4e a9 6c 56 f4 ea 65 7a ae 08
        ba 78 25 2e 1c a6 b4 c6 e8 dd 74 1f 4b bd 8b 8a 70 3e b5 66 48 03 f6 0e
        61 35 57 b9 86 c1 1d 9e e1 f8 98 11 69 d9 8e 94 9b 1e 87 e9 ce 55 28 df
        8c a1 89 0d bf e6 42 68 41 99 2d 0f b0 54 bb 16
        ''')
    GM2_data = libutils.str_to_int_array('''
        00 02 04 06 08 0a 0c 0e 10 12 14 16 18 1a 1c 1e 20 22 24 26 28 2a 2c 2e
        30 32 34 36 38 3a 3c 3e 40 42 44 46 48 4a 4c 4e 50 52 54 56 58 5a 5c 5e
        60 62 64 66 68 6a 6c 6e 70 72 74 76 78 7a 7c 7e 80 82 84 86 88 8a 8c 8e
        90 92 94 96 98 9a 9c 9e a0 a2 a4 a6 a8 aa ac ae b0 b2 b4 b6 b8 ba bc be
        c0 c2 c4 c6 c8 ca cc ce d0 d2 d4 d6 d8 da dc de e0 e2 e4 e6 e8 ea ec ee
        f0 f2 f4 f6 f8 fa fc fe 1b 19 1f 1d 13 11 17 15 0b 09 0f 0d 03 01 07 05
        3b 39 3f 3d 33 31 37 35 2b 29 2f 2d 23 21 27 25 5b 59 5f 5d 53 51 57 55
        4b 49 4f 4d 43 41 47 45 7b 79 7f 7d 73 71 77 75 6b 69 6f 6d 63 61 67 65
        9b 99 9f 9d 93 91 97 95 8b 89 8f 8d 83 81 87 85 bb b9 bf bd b3 b1 b7 b5
        ab a9 af ad a3 a1 a7 a5 db d9 df dd d3 d1 d7 d5 cb c9 cf cd c3 c1 c7 c5
        fb f9 ff fd f3 f1 f7 f5 eb e9 ef ed e3 e1 e7 e5
        ''')
    GM3_data = libutils.str_to_int_array('''
        00 03 06 05 0c 0f 0a 09 18 1b 1e 1d 14 17 12 11 30 33 36 35 3c 3f 3a 39
        28 2b 2e 2d 24 27 22 21 60 63 66 65 6c 6f 6a 69 78 7b 7e 7d 74 77 72 71
        50 53 56 55 5c 5f 5a 59 48 4b 4e 4d 44 47 42 41 c0 c3 c6 c5 cc cf ca c9
        d8 db de dd d4 d7 d2 d1 f0 f3 f6 f5 fc ff fa f9 e8 eb ee ed e4 e7 e2 e1
        a0 a3 a6 a5 ac af aa a9 b8 bb be bd b4 b7 b2 b1 90 93 96 95 9c 9f 9a 99
        88 8b 8e 8d 84 87 82 81 9b 98 9d 9e 97 94 91 92 83 80 85 86 8f 8c 89 8a
        ab a8 ad ae a7 a4 a1 a2 b3 b0 b5 b6 bf bc b9 ba fb f8 fd fe f7 f4 f1 f2
        e3 e0 e5 e6 ef ec e9 ea cb c8 cd ce c7 c4 c1 c2 d3 d0 d5 d6 df dc d9 da
        5b 58 5d 5e 57 54 51 52 43 40 45 46 4f 4c 49 4a 6b 68 6d 6e 67 64 61 62
        73 70 75 76 7f 7c 79 7a 3b 38 3d 3e 37 34 31 32 23 20 25 26 2f 2c 29 2a
        0b 08 0d 0e 07 04 01 02 13 10 15 16 1f 1c 19 1a
        ''')

# Hardware build.
"""
aes = AES_Encrypt()
aes_plaintext = pyrtl.Input(bitwidth=128, name='aes_plaintext')
aes_key = pyrtl.Input(bitwidth=128, name='aes_key')
aes_ciphertext = pyrtl.Output(bitwidth=128, name='aes_ciphertext')
reset = pyrtl.Input(1)
ready = pyrtl.Output(1, name='ready')
ready_out, aes_ciphertext_out = aes.encryption_statem(aes_plaintext, aes_key, reset)
ready <<= ready_out
aes_ciphertext <<= aes_ciphertext_out
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
sim.step ({
                aes_plaintext: 0x00112233445566778899aabbccddeeff,
                aes_key: 0x000102030405060708090a0b0c0d0e0f,
                reset: 1
         })
for cycle in range(1,10):
    sim.step ({
                aes_plaintext: 0x00112233445566778899aabbccddeeff,
                aes_key: 0x000102030405060708090a0b0c0d0e0f,
                reset: 0
             })
sim_trace.render_trace(symbol_len=40, segment_size=1)
"""
