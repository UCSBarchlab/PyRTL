""" AES-128 """

from __future__ import division, absolute_import
import pyrtl
from pyrtl.rtllib import libutils


# TODO:
# 1) Right now all ROMs are global -- need to be moved into function so each
#    instance of the AES block creates it's own memories
# 2) All ROMs should be syncronous.  This should be easy once (3) is completed
# 3) Right now aes_decryption generates one GIANT combinational block. Instead
#    it should generate one of 2 options -- Either an interative design or a
#    pipelined design.  Both will add registers between each round of AES
# 4) aes_encryption should be added to this file as well so that an
#    aes encrypter similar to (3) above is generated
# 5) a single "aes-unit" combining encryption and decryption (without making
#    full independent hardware units) would be a plus as well
import rtllib.libutils


def _g(word, key_expand_round):
    # One-byte left circular rotation, substitution of each byte
    a = libutils.partition_wire(word, 8)
    sub = pyrtl.concat(sbox[a[1]], sbox[a[2]], sbox[a[3]], sbox[a[0]])
    # xor substituted bytes with round constant.
    round_const = pyrtl.concat(rcon[key_expand_round + 1], pyrtl.Const(0, bitwidth=24))
    return round_const ^ sub


def key_expansion(key):
    w = list(reversed(libutils.partition_wire(key, 32)))
    for key_expand_round in range(10):
        last = key_expand_round * 4
        w.append(w[last] ^ _g(w[last + 3], key_expand_round))
        w.append(w[-1] ^ w[last + 1])
        w.append(w[-1] ^ w[last + 2])
        w.append(w[-1] ^ w[last + 3])
    return pyrtl.concat(*w)


def inv_sub_bytes(in_vector):
    subbed = [inv_sbox[byte] for byte in libutils.partition_wire(in_vector, 8)]
    return pyrtl.concat(*subbed)


def inv_shift_rows(in_vector):
    a = libutils.partition_wire(in_vector, 8)
    out_vector = pyrtl.concat(a[0], a[7], a[10], a[13],
                              a[1], a[4], a[11], a[14],
                              a[2], a[5], a[8],  a[15],
                              a[3], a[6], a[9],  a[12])
    return out_vector


def inv_galois_mult(c, d):
    return _inv_gal_mult_dict[d][c]


def _mod_add(base, add, mod):
    base_mod_floor = base // mod
    return (base + add) % mod + base_mod_floor * mod


_igm_divisor = [14, 11, 13, 9]


def inv_mix_columns(in_vector):
    def _inv_mix_single(index):
        mult_items = [inv_galois_mult(a[_mod_add(index, loc, 4)], mult_table)
                      for loc, mult_table in enumerate(_igm_divisor)]
        return mult_items[0] ^ mult_items[1] ^ mult_items[2] ^ mult_items[3]

    a = libutils.partition_wire(in_vector, 8)
    inverted = [_inv_mix_single(index) for index in range(len(a))]
    return pyrtl.concat(*inverted)


def addroundkey(t, expanded_key, round):
    offset = round * 128
    return t ^ expanded_key[offset:offset + 128]


def aes_decryption(ciphertext, key):
    expanded_key = key_expansion(key)  # Expanding the key (key expansion).
    t = addroundkey(ciphertext, expanded_key, 0)  # Initial AddRoundKey.

    for round in range(1, 11):
        t = inv_shift_rows(t)
        t = inv_sub_bytes(t)
        t = addroundkey(t, expanded_key, round)
        if round != 10:
            t = inv_mix_columns(t)

    return t


sbox_data = libutils.str_to_int_array('''
    63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7 ab 76 ca 82 c9 7d fa 59 47 f0 ad d4 a2 af 9c a4 72 c0
    b7 fd 93 26 36 3f f7 cc 34 a5 e5 f1 71 d8 31 15 04 c7 23 c3 18 96 05 9a 07 12 80 e2 eb 27 b2 75
    09 83 2c 1a 1b 6e 5a a0 52 3b d6 b3 29 e3 2f 84 53 d1 00 ed 20 fc b1 5b 6a cb be 39 4a 4c 58 cf
    d0 ef aa fb 43 4d 33 85 45 f9 02 7f 50 3c 9f a8 51 a3 40 8f 92 9d 38 f5 bc b6 da 21 10 ff f3 d2
    cd 0c 13 ec 5f 97 44 17 c4 a7 7e 3d 64 5d 19 73 60 81 4f dc 22 2a 90 88 46 ee b8 14 de 5e 0b db
    e0 32 3a 0a 49 06 24 5c c2 d3 ac 62 91 95 e4 79 e7 c8 37 6d 8d d5 4e a9 6c 56 f4 ea 65 7a ae 08
    ba 78 25 2e 1c a6 b4 c6 e8 dd 74 1f 4b bd 8b 8a 70 3e b5 66 48 03 f6 0e 61 35 57 b9 86 c1 1d 9e
    e1 f8 98 11 69 d9 8e 94 9b 1e 87 e9 ce 55 28 df 8c a1 89 0d bf e6 42 68 41 99 2d 0f b0 54 bb 16
    ''')

inv_sbox_data = libutils.str_to_int_array('''
    52 09 6a d5 30 36 a5 38 bf 40 a3 9e 81 f3 d7 fb 7c e3 39 82 9b 2f ff 87 34 8e 43 44 c4 de e9 cb
    54 7b 94 32 a6 c2 23 3d ee 4c 95 0b 42 fa c3 4e 08 2e a1 66 28 d9 24 b2 76 5b a2 49 6d 8b d1 25
    72 f8 f6 64 86 68 98 16 d4 a4 5c cc 5d 65 b6 92 6c 70 48 50 fd ed b9 da 5e 15 46 57 a7 8d 9d 84
    90 d8 ab 00 8c bc d3 0a f7 e4 58 05 b8 b3 45 06 d0 2c 1e 8f ca 3f 0f 02 c1 af bd 03 01 13 8a 6b
    3a 91 11 41 4f 67 dc ea 97 f2 cf ce f0 b4 e6 73 96 ac 74 22 e7 ad 35 85 e2 f9 37 e8 1c 75 df 6e
    47 f1 1a 71 1d 29 c5 89 6f b7 62 0e aa 18 be 1b fc 56 3e 4b c6 d2 79 20 9a db c0 fe 78 cd 5a f4
    1f dd a8 33 88 07 c7 31 b1 12 10 59 27 80 ec 5f 60 51 7f a9 19 b5 4a 0d 2d e5 7a 9f 93 c9 9c ef
    a0 e0 3b 4d ae 2a f5 b0 c8 eb bb 3c 83 53 99 61 17 2b 04 7e ba 77 d6 26 e1 69 14 63 55 21 0c 7d
    ''')

rcon_data = libutils.str_to_int_array('''
    8d 01 02 04 08 10 20 40 80 1b 36 6c d8 ab 4d 9a 2f 5e bc 63 c6 97 35 6a d4 b3 7d fa ef c5 91 39
    72 e4 d3 bd 61 c2 9f 25 4a 94 33 66 cc 83 1d 3a 74 e8 cb 8d 01 02 04 08 10 20 40 80 1b 36 6c d8
    ab 4d 9a 2f 5e bc 63 c6 97 35 6a d4 b3 7d fa ef c5 91 39 72 e4 d3 bd 61 c2 9f 25 4a 94 33 66 cc
    83 1d 3a 74 e8 cb 8d 01 02 04 08 10 20 40 80 1b 36 6c d8 ab 4d 9a 2f 5e bc 63 c6 97 35 6a d4 b3
    7d fa ef c5 91 39 72 e4 d3 bd 61 c2 9f 25 4a 94 33 66 cc 83 1d 3a 74 e8 cb 8d 01 02 04 08 10 20
    40 80 1b 36 6c d8 ab 4d 9a 2f 5e bc 63 c6 97 35 6a d4 b3 7d fa ef c5 91 39 72 e4 d3 bd 61 c2 9f
    25 4a 94 33 66 cc 83 1d 3a 74 e8 cb 8d 01 02 04 08 10 20 40 80 1b 36 6c d8 ab 4d 9a 2f 5e bc 63
    c6 97 35 6a d4 b3 7d fa ef c5 91 39 72 e4 d3 bd 61 c2 9f 25 4a 94 33 66 cc 83 1d 3a 74 e8 cb 8d
    ''')

# Galois Multiplication tables for 9, 11, 13, and 14.

gm9_data = libutils.str_to_int_array('''
    00 09 12 1b 24 2d 36 3f 48 41 5a 53 6c 65 7e 77 90 99 82 8b b4 bd a6 af d8 d1 ca c3 fc f5 ee e7
    3b 32 29 20 1f 16 0d 04 73 7a 61 68 57 5e 45 4c ab a2 b9 b0 8f 86 9d 94 e3 ea f1 f8 c7 ce d5 dc
    76 7f 64 6d 52 5b 40 49 3e 37 2c 25 1a 13 08 01 e6 ef f4 fd c2 cb d0 d9 ae a7 bc b5 8a 83 98 91
    4d 44 5f 56 69 60 7b 72 05 0c 17 1e 21 28 33 3a dd d4 cf c6 f9 f0 eb e2 95 9c 87 8e b1 b8 a3 aa
    ec e5 fe f7 c8 c1 da d3 a4 ad b6 bf 80 89 92 9b 7c 75 6e 67 58 51 4a 43 34 3d 26 2f 10 19 02 0b
    d7 de c5 cc f3 fa e1 e8 9f 96 8d 84 bb b2 a9 a0 47 4e 55 5c 63 6a 71 78 0f 06 1d 14 2b 22 39 30
    9a 93 88 81 be b7 ac a5 d2 db c0 c9 f6 ff e4 ed 0a 03 18 11 2e 27 3c 35 42 4b 50 59 66 6f 74 7d
    a1 a8 b3 ba 85 8c 97 9e e9 e0 fb f2 cd c4 df d6 31 38 23 2a 15 1c 07 0e 79 70 6b 62 5d 54 4f 46
    ''')

gm11_data = libutils.str_to_int_array('''
    00 0b 16 1d 2c 27 3a 31 58 53 4e 45 74 7f 62 69 b0 bb a6 ad 9c 97 8a 81 e8 e3 fe f5 c4 cf d2 d9
    7b 70 6d 66 57 5c 41 4a 23 28 35 3e 0f 04 19 12 cb c0 dd d6 e7 ec f1 fa 93 98 85 8e bf b4 a9 a2
    f6 fd e0 eb da d1 cc c7 ae a5 b8 b3 82 89 94 9f 46 4d 50 5b 6a 61 7c 77 1e 15 08 03 32 39 24 2f
    8d 86 9b 90 a1 aa b7 bc d5 de c3 c8 f9 f2 ef e4 3d 36 2b 20 11 1a 07 0c 65 6e 73 78 49 42 5f 54
    f7 fc e1 ea db d0 cd c6 af a4 b9 b2 83 88 95 9e 47 4c 51 5a 6b 60 7d 76 1f 14 09 02 33 38 25 2e
    8c 87 9a 91 a0 ab b6 bd d4 df c2 c9 f8 f3 ee e5 3c 37 2a 21 10 1b 06 0d 64 6f 72 79 48 43 5e 55
    01 0a 17 1c 2d 26 3b 30 59 52 4f 44 75 7e 63 68 b1 ba a7 ac 9d 96 8b 80 e9 e2 ff f4 c5 ce d3 d8
    7a 71 6c 67 56 5d 40 4b 22 29 34 3f 0e 05 18 13 ca c1 dc d7 e6 ed f0 fb 92 99 84 8f be b5 a8 a3
    ''')

gm13_data = libutils.str_to_int_array('''
    00 0d 1a 17 34 39 2e 23 68 65 72 7f 5c 51 46 4b d0 dd ca c7 e4 e9 fe f3 b8 b5 a2 af 8c 81 96 9b
    bb b6 a1 ac 8f 82 95 98 d3 de c9 c4 e7 ea fd f0 6b 66 71 7c 5f 52 45 48 03 0e 19 14 37 3a 2d 20
    6d 60 77 7a 59 54 43 4e 05 08 1f 12 31 3c 2b 26 bd b0 a7 aa 89 84 93 9e d5 d8 cf c2 e1 ec fb f6
    d6 db cc c1 e2 ef f8 f5 be b3 a4 a9 8a 87 90 9d 06 0b 1c 11 32 3f 28 25 6e 63 74 79 5a 57 40 4d
    da d7 c0 cd ee e3 f4 f9 b2 bf a8 a5 86 8b 9c 91 0a 07 10 1d 3e 33 24 29 62 6f 78 75 56 5b 4c 41
    61 6c 7b 76 55 58 4f 42 09 04 13 1e 3d 30 27 2a b1 bc ab a6 85 88 9f 92 d9 d4 c3 ce ed e0 f7 fa
    b7 ba ad a0 83 8e 99 94 df d2 c5 c8 eb e6 f1 fc 67 6a 7d 70 53 5e 49 44 0f 02 15 18 3b 36 21 2c
    0c 01 16 1b 38 35 22 2f 64 69 7e 73 50 5d 4a 47 dc d1 c6 cb e8 e5 f2 ff b4 b9 ae a3 80 8d 9a 97
    ''')

gm14_data = libutils.str_to_int_array('''
    00 0e 1c 12 38 36 24 2a 70 7e 6c 62 48 46 54 5a e0 ee fc f2 d8 d6 c4 ca 90 9e 8c 82 a8 a6 b4 ba
    db d5 c7 c9 e3 ed ff f1 ab a5 b7 b9 93 9d 8f 81 3b 35 27 29 03 0d 1f 11 4b 45 57 59 73 7d 6f 61
    ad a3 b1 bf 95 9b 89 87 dd d3 c1 cf e5 eb f9 f7 4d 43 51 5f 75 7b 69 67 3d 33 21 2f 05 0b 19 17
    76 78 6a 64 4e 40 52 5c 06 08 1a 14 3e 30 22 2c 96 98 8a 84 ae a0 b2 bc e6 e8 fa f4 de d0 c2 cc
    41 4f 5d 53 79 77 65 6b 31 3f 2d 23 09 07 15 1b a1 af bd b3 99 97 85 8b d1 df cd c3 e9 e7 f5 fb
    9a 94 86 88 a2 ac be b0 ea e4 f6 f8 d2 dc ce c0 7a 74 66 68 42 4c 5e 50 0a 04 16 18 32 3c 2e 20
    ec e2 f0 fe d4 da c8 c6 9c 92 80 8e a4 aa b8 b6 0c 02 10 1e 34 3a 28 26 7c 72 60 6e 44 4a 58 56
    37 39 2b 25 0f 01 13 1d 47 49 5b 55 7f 71 63 6d d7 d9 cb c5 ef e1 f3 fd a7 a9 bb b5 9f 91 83 8d
    ''')


sbox = pyrtl.RomBlock(bitwidth=8, addrwidth=8, romdata=sbox_data, asynchronous=True)
inv_sbox = pyrtl.RomBlock(bitwidth=8, addrwidth=8, romdata=inv_sbox_data, asynchronous=True)
rcon = pyrtl.RomBlock(bitwidth=8, addrwidth=8, romdata=rcon_data, asynchronous=True)
GM9 = pyrtl.RomBlock(bitwidth=8, addrwidth=8, romdata=gm9_data, asynchronous=True)
GM11 = pyrtl.RomBlock(bitwidth=8, addrwidth=8, romdata=gm11_data, asynchronous=True)
GM13 = pyrtl.RomBlock(bitwidth=8, addrwidth=8, romdata=gm13_data, asynchronous=True)
GM14 = pyrtl.RomBlock(bitwidth=8, addrwidth=8, romdata=gm14_data, asynchronous=True)

_inv_gal_mult_dict = {9: GM9, 11: GM11, 13: GM13, 14: GM14}

# Hardware build.
aes_ciphertext = pyrtl.Input(bitwidth=128, name='aes_ciphertext')
aes_key = pyrtl.Input(bitwidth=128, name='aes_key')
aes_plaintext = pyrtl.Output(bitwidth=128, name='aes_plaintext')
aes_plaintext <<= aes_decryption(aes_ciphertext, aes_key)

sim_trace = pyrtl.SimulationTrace(wirevector_subset=[aes_ciphertext, aes_key, aes_plaintext])
sim = pyrtl.Simulation(tracer=sim_trace)

for cycle in range(1):
    sim.step({
        aes_ciphertext: 0x66e94bd4ef8a2c3b884cfa59ca342b2e,
        aes_key: 0x0
    })

sim_trace.render_trace(symbol_len=40, segment_size=1)
