""" The function "g" in the KeyExpansion step of AES. """

import sys
sys.path.append("../..")

import pyrtl
from pyrtl import *

# S-box table.
sbox_data = [0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76, 0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0, 0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15, 0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75, 0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84, 0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf, 0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8, 0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2, 0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73, 0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb, 0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79, 0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08, 0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a, 0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e, 0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf, 0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16]
sbox = RomBlock(bitwidth=128, addrwidth=8, data=sbox_data)

# Rcon table.
rcon_data = [0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d]
rcon = RomBlock(bitwidth=128, addrwidth=8, data=rcon_data)

def g_w3(word):
	# STEP 1: One-byte left circular rotation.
	a1_w3 = pyrtl.WireVector(8, 'a1_w3')
	a2_w3 = pyrtl.WireVector(8, 'a2_w3')
	a3_w3 = pyrtl.WireVector(8, 'a3_w3')
	a4_w3 = pyrtl.WireVector(8, 'a4_w3')

	a1_w3 <<= word[24:32]
	a2_w3 <<= word[16:24]
	a3_w3 <<= word[8:16]
	a4_w3 <<= word[0:8]

	shifted_w3 = pyrtl.WireVector(32, 'shifted_w3')
	shifted_w3 <<= pyrtl.concat(a2_w3, a3_w3, a4_w3, a1_w3)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w3 = pyrtl.WireVector(8, 'b1_w3')
	b2_w3 = pyrtl.WireVector(8, 'b2_w3')
	b3_w3 = pyrtl.WireVector(8, 'b3_w3')
	b4_w3 = pyrtl.WireVector(8, 'b4_w3')

	b1_w3 <<= shifted_w3[24:32]
	b2_w3 <<= shifted_w3[16:24]
	b3_w3 <<= shifted_w3[8:16]
	b4_w3 <<= shifted_w3[0:8]

	c1_w3 = pyrtl.WireVector(8, 'c1_w3')
	c2_w3 = pyrtl.WireVector(8, 'c2_w3')
	c3_w3 = pyrtl.WireVector(8, 'c3_w3')
	c4_w3 = pyrtl.WireVector(8, 'c4_w3')

	c1_w3 <<= sbox[b1_w3]
	c2_w3 <<= sbox[b2_w3]
	c3_w3 <<= sbox[b3_w3]
	c4_w3 <<= sbox[b4_w3]

	substituted_w3 = pyrtl.WireVector(32, 'substituted_w3')
	substituted_w3 <<= pyrtl.concat(c1_w3, c2_w3, c3_w3, c4_w3)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w3 = pyrtl.WireVector(bitwidth=32, name='xor_w3')
	rc1_w3 = pyrtl.WireVector(bitwidth=8, name='rc1_w3')
	rc2_w3 = pyrtl.WireVector(bitwidth=8, name='rc2_w3')
	rc3_w3 = pyrtl.WireVector(bitwidth=8, name='rc3_w3')
	rc4_w3 = pyrtl.WireVector(bitwidth=8, name='rc4_w3')

	rc1_w3 <<= rcon[1]
	rc2_w3 <<= 0x00
	rc3_w3 <<= 0x00
	rc4_w3<<= 0x00

	concat_w3 = pyrtl.WireVector(32, 'concat_w3')
	concat_w3 <<= pyrtl.concat(rc1_w3, rc2_w3, rc3_w3, rc4_w3)
	xor_w3 <<= concat_w3 ^ substituted_w3
	return xor_w3


def g_w7(word):
	# STEP 1: One-byte left circular rotation.
	a1_w7 = pyrtl.WireVector(8, 'a1_w7')
	a2_w7 = pyrtl.WireVector(8, 'a2_w7')
	a3_w7 = pyrtl.WireVector(8, 'a3_w7')
	a4_w7 = pyrtl.WireVector(8, 'a4_w7')

	a1_w7 <<= word[24:32]
	a2_w7 <<= word[16:24]
	a3_w7 <<= word[8:16]
	a4_w7 <<= word[0:8]

	shifted_w7 = pyrtl.WireVector(32, 'shifted_w7')
	shifted_w7 <<= pyrtl.concat(a2_w7, a3_w7, a4_w7, a1_w7)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w7 = pyrtl.WireVector(8, 'b1_w7')
	b2_w7 = pyrtl.WireVector(8, 'b2_w7')
	b3_w7 = pyrtl.WireVector(8, 'b3_w7')
	b4_w7 = pyrtl.WireVector(8, 'b4_w7')

	b1_w7 <<= shifted_w7[24:32]
	b2_w7 <<= shifted_w7[16:24]
	b3_w7 <<= shifted_w7[8:16]
	b4_w7 <<= shifted_w7[0:8]

	c1_w7 = pyrtl.WireVector(8, 'c1_w7')
	c2_w7 = pyrtl.WireVector(8, 'c2_w7')
	c3_w7 = pyrtl.WireVector(8, 'c3_w7')
	c4_w7 = pyrtl.WireVector(8, 'c4_w7')

	c1_w7 <<= sbox[b1_w7]
	c2_w7 <<= sbox[b2_w7]
	c3_w7 <<= sbox[b3_w7]
	c4_w7 <<= sbox[b4_w7]

	substituted_w7 = pyrtl.WireVector(32, 'substituted_w7')
	substituted_w7 <<= pyrtl.concat(c1_w7, c2_w7, c3_w7, c4_w7)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w7 = pyrtl.WireVector(bitwidth=32, name='xor_w7')
	rc1_w7 = pyrtl.WireVector(bitwidth=8, name='rc1_w7')
	rc2_w7 = pyrtl.WireVector(bitwidth=8, name='rc2_w7')
	rc3_w7 = pyrtl.WireVector(bitwidth=8, name='rc3_w7')
	rc4_w7 = pyrtl.WireVector(bitwidth=8, name='rc4_w7')

	rc1_w7 <<= rcon[2]
	rc2_w7 <<= 0x00
	rc3_w7 <<= 0x00
	rc4_w7<<= 0x00

	concat_w7 = pyrtl.WireVector(32, 'concat_w7')
	concat_w7 <<= pyrtl.concat(rc1_w7, rc2_w7, rc3_w7, rc4_w7)
	xor_w7 <<= concat_w7 ^ substituted_w7
	return xor_w7


def g_w11(word):
	# STEP 1: One-byte left circular rotation.
	a1_w11 = pyrtl.WireVector(8, 'a1_w11')
	a2_w11 = pyrtl.WireVector(8, 'a2_w11')
	a3_w11 = pyrtl.WireVector(8, 'a3_w11')
	a4_w11 = pyrtl.WireVector(8, 'a4_w11')

	a1_w11 <<= word[24:32]
	a2_w11 <<= word[16:24]
	a3_w11 <<= word[8:16]
	a4_w11 <<= word[0:8]

	shifted_w11 = pyrtl.WireVector(32, 'shifted_w11')
	shifted_w11 <<= pyrtl.concat(a2_w11, a3_w11, a4_w11, a1_w11)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w11 = pyrtl.WireVector(8, 'b1_w11')
	b2_w11 = pyrtl.WireVector(8, 'b2_w11')
	b3_w11 = pyrtl.WireVector(8, 'b3_w11')
	b4_w11 = pyrtl.WireVector(8, 'b4_w11')

	b1_w11 <<= shifted_w11[24:32]
	b2_w11 <<= shifted_w11[16:24]
	b3_w11 <<= shifted_w11[8:16]
	b4_w11 <<= shifted_w11[0:8]

	c1_w11 = pyrtl.WireVector(8, 'c1_w11')
	c2_w11 = pyrtl.WireVector(8, 'c2_w11')
	c3_w11 = pyrtl.WireVector(8, 'c3_w11')
	c4_w11 = pyrtl.WireVector(8, 'c4_w11')

	c1_w11 <<= sbox[b1_w11]
	c2_w11 <<= sbox[b2_w11]
	c3_w11 <<= sbox[b3_w11]
	c4_w11 <<= sbox[b4_w11]

	substituted_w11 = pyrtl.WireVector(32, 'substituted_w11')
	substituted_w11 <<= pyrtl.concat(c1_w11, c2_w11, c3_w11, c4_w11)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w11 = pyrtl.WireVector(bitwidth=32, name='xor_w11')
	rc1_w11 = pyrtl.WireVector(bitwidth=8, name='rc1_w11')
	rc2_w11 = pyrtl.WireVector(bitwidth=8, name='rc2_w11')
	rc3_w11 = pyrtl.WireVector(bitwidth=8, name='rc3_w11')
	rc4_w11 = pyrtl.WireVector(bitwidth=8, name='rc4_w11')

	rc1_w11 <<= rcon[3]
	rc2_w11 <<= 0x00
	rc3_w11 <<= 0x00
	rc4_w11<<= 0x00

	concat_w11 = pyrtl.WireVector(32, 'concat_w11')
	concat_w11 <<= pyrtl.concat(rc1_w11, rc2_w11, rc3_w11, rc4_w11)
	xor_w11 <<= concat_w11 ^ substituted_w11
	return xor_w11


def g_w15(word):
	# STEP 1: One-byte left circular rotation.
	a1_w15 = pyrtl.WireVector(8, 'a1_w15')
	a2_w15 = pyrtl.WireVector(8, 'a2_w15')
	a3_w15 = pyrtl.WireVector(8, 'a3_w15')
	a4_w15 = pyrtl.WireVector(8, 'a4_w15')

	a1_w15 <<= word[24:32]
	a2_w15 <<= word[16:24]
	a3_w15 <<= word[8:16]
	a4_w15 <<= word[0:8]

	shifted_w15 = pyrtl.WireVector(32, 'shifted_w15')
	shifted_w15 <<= pyrtl.concat(a2_w15, a3_w15, a4_w15, a1_w15)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w15 = pyrtl.WireVector(8, 'b1_w15')
	b2_w15 = pyrtl.WireVector(8, 'b2_w15')
	b3_w15 = pyrtl.WireVector(8, 'b3_w15')
	b4_w15 = pyrtl.WireVector(8, 'b4_w15')

	b1_w15 <<= shifted_w15[24:32]
	b2_w15 <<= shifted_w15[16:24]
	b3_w15 <<= shifted_w15[8:16]
	b4_w15 <<= shifted_w15[0:8]

	c1_w15 = pyrtl.WireVector(8, 'c1_w15')
	c2_w15 = pyrtl.WireVector(8, 'c2_w15')
	c3_w15 = pyrtl.WireVector(8, 'c3_w15')
	c4_w15 = pyrtl.WireVector(8, 'c4_w15')

	c1_w15 <<= sbox[b1_w15]
	c2_w15 <<= sbox[b2_w15]
	c3_w15 <<= sbox[b3_w15]
	c4_w15 <<= sbox[b4_w15]

	substituted_w15 = pyrtl.WireVector(32, 'substituted_w15')
	substituted_w15 <<= pyrtl.concat(c1_w15, c2_w15, c3_w15, c4_w15)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w15 = pyrtl.WireVector(bitwidth=32, name='xor_w15')
	rc1_w15 = pyrtl.WireVector(bitwidth=8, name='rc1_w15')
	rc2_w15 = pyrtl.WireVector(bitwidth=8, name='rc2_w15')
	rc3_w15 = pyrtl.WireVector(bitwidth=8, name='rc3_w15')
	rc4_w15 = pyrtl.WireVector(bitwidth=8, name='rc4_w15')

	rc1_w15 <<= rcon[4]
	rc2_w15 <<= 0x00
	rc3_w15 <<= 0x00
	rc4_w15<<= 0x00

	concat_w15 = pyrtl.WireVector(32, 'concat_w15')
	concat_w15 <<= pyrtl.concat(rc1_w15, rc2_w15, rc3_w15, rc4_w15)
	xor_w15 <<= concat_w15 ^ substituted_w15
	return xor_w15


def g_w19(word):
	# STEP 1: One-byte left circular rotation.
	a1_w19 = pyrtl.WireVector(8, 'a1_w19')
	a2_w19 = pyrtl.WireVector(8, 'a2_w19')
	a3_w19 = pyrtl.WireVector(8, 'a3_w19')
	a4_w19 = pyrtl.WireVector(8, 'a4_w19')

	a1_w19 <<= word[24:32]
	a2_w19 <<= word[16:24]
	a3_w19 <<= word[8:16]
	a4_w19 <<= word[0:8]

	shifted_w19 = pyrtl.WireVector(32, 'shifted_w19')
	shifted_w19 <<= pyrtl.concat(a2_w19, a3_w19, a4_w19, a1_w19)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w19 = pyrtl.WireVector(8, 'b1_w19')
	b2_w19 = pyrtl.WireVector(8, 'b2_w19')
	b3_w19 = pyrtl.WireVector(8, 'b3_w19')
	b4_w19 = pyrtl.WireVector(8, 'b4_w19')

	b1_w19 <<= shifted_w19[24:32]
	b2_w19 <<= shifted_w19[16:24]
	b3_w19 <<= shifted_w19[8:16]
	b4_w19 <<= shifted_w19[0:8]

	c1_w19 = pyrtl.WireVector(8, 'c1_w19')
	c2_w19 = pyrtl.WireVector(8, 'c2_w19')
	c3_w19 = pyrtl.WireVector(8, 'c3_w19')
	c4_w19 = pyrtl.WireVector(8, 'c4_w19')

	c1_w19 <<= sbox[b1_w19]
	c2_w19 <<= sbox[b2_w19]
	c3_w19 <<= sbox[b3_w19]
	c4_w19 <<= sbox[b4_w19]

	substituted_w19 = pyrtl.WireVector(32, 'substituted_w19')
	substituted_w19 <<= pyrtl.concat(c1_w19, c2_w19, c3_w19, c4_w19)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w19 = pyrtl.WireVector(bitwidth=32, name='xor_w19')
	rc1_w19 = pyrtl.WireVector(bitwidth=8, name='rc1_w19')
	rc2_w19 = pyrtl.WireVector(bitwidth=8, name='rc2_w19')
	rc3_w19 = pyrtl.WireVector(bitwidth=8, name='rc3_w19')
	rc4_w19 = pyrtl.WireVector(bitwidth=8, name='rc4_w19')

	rc1_w19 <<= rcon[5]
	rc2_w19 <<= 0x00
	rc3_w19 <<= 0x00
	rc4_w19<<= 0x00

	concat_w19 = pyrtl.WireVector(32, 'concat_w19')
	concat_w19 <<= pyrtl.concat(rc1_w19, rc2_w19, rc3_w19, rc4_w19)
	xor_w19 <<= concat_w19 ^ substituted_w19
	return xor_w19


def g_w23(word):
	# STEP 1: One-byte left circular rotation.
	a1_w23 = pyrtl.WireVector(8, 'a1_w23')
	a2_w23 = pyrtl.WireVector(8, 'a2_w23')
	a3_w23 = pyrtl.WireVector(8, 'a3_w23')
	a4_w23 = pyrtl.WireVector(8, 'a4_w23')

	a1_w23 <<= word[24:32]
	a2_w23 <<= word[16:24]
	a3_w23 <<= word[8:16]
	a4_w23 <<= word[0:8]

	shifted_w23 = pyrtl.WireVector(32, 'shifted_w23')
	shifted_w23 <<= pyrtl.concat(a2_w23, a3_w23, a4_w23, a1_w23)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w23 = pyrtl.WireVector(8, 'b1_w23')
	b2_w23 = pyrtl.WireVector(8, 'b2_w23')
	b3_w23 = pyrtl.WireVector(8, 'b3_w23')
	b4_w23 = pyrtl.WireVector(8, 'b4_w23')

	b1_w23 <<= shifted_w23[24:32]
	b2_w23 <<= shifted_w23[16:24]
	b3_w23 <<= shifted_w23[8:16]
	b4_w23 <<= shifted_w23[0:8]

	c1_w23 = pyrtl.WireVector(8, 'c1_w23')
	c2_w23 = pyrtl.WireVector(8, 'c2_w23')
	c3_w23 = pyrtl.WireVector(8, 'c3_w23')
	c4_w23 = pyrtl.WireVector(8, 'c4_w23')

	c1_w23 <<= sbox[b1_w23]
	c2_w23 <<= sbox[b2_w23]
	c3_w23 <<= sbox[b3_w23]
	c4_w23 <<= sbox[b4_w23]

	substituted_w23 = pyrtl.WireVector(32, 'substituted_w23')
	substituted_w23 <<= pyrtl.concat(c1_w23, c2_w23, c3_w23, c4_w23)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w23 = pyrtl.WireVector(bitwidth=32, name='xor_w23')
	rc1_w23 = pyrtl.WireVector(bitwidth=8, name='rc1_w23')
	rc2_w23 = pyrtl.WireVector(bitwidth=8, name='rc2_w23')
	rc3_w23 = pyrtl.WireVector(bitwidth=8, name='rc3_w23')
	rc4_w23 = pyrtl.WireVector(bitwidth=8, name='rc4_w23')

	rc1_w23 <<= rcon[6]
	rc2_w23 <<= 0x00
	rc3_w23 <<= 0x00
	rc4_w23<<= 0x00

	concat_w23 = pyrtl.WireVector(32, 'concat_w23')
	concat_w23 <<= pyrtl.concat(rc1_w23, rc2_w23, rc3_w23, rc4_w23)
	xor_w23 <<= concat_w23 ^ substituted_w23
	return xor_w23


def g_w27(word):
	# STEP 1: One-byte left circular rotation.
	a1_w27 = pyrtl.WireVector(8, 'a1_w27')
	a2_w27 = pyrtl.WireVector(8, 'a2_w27')
	a3_w27 = pyrtl.WireVector(8, 'a3_w27')
	a4_w27 = pyrtl.WireVector(8, 'a4_w27')

	a1_w27 <<= word[24:32]
	a2_w27 <<= word[16:24]
	a3_w27 <<= word[8:16]
	a4_w27 <<= word[0:8]

	shifted_w27 = pyrtl.WireVector(32, 'shifted_w27')
	shifted_w27 <<= pyrtl.concat(a2_w27, a3_w27, a4_w27, a1_w27)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w27 = pyrtl.WireVector(8, 'b1_w27')
	b2_w27 = pyrtl.WireVector(8, 'b2_w27')
	b3_w27 = pyrtl.WireVector(8, 'b3_w27')
	b4_w27 = pyrtl.WireVector(8, 'b4_w27')

	b1_w27 <<= shifted_w27[24:32]
	b2_w27 <<= shifted_w27[16:24]
	b3_w27 <<= shifted_w27[8:16]
	b4_w27 <<= shifted_w27[0:8]

	c1_w27 = pyrtl.WireVector(8, 'c1_w27')
	c2_w27 = pyrtl.WireVector(8, 'c2_w27')
	c3_w27 = pyrtl.WireVector(8, 'c3_w27')
	c4_w27 = pyrtl.WireVector(8, 'c4_w27')

	c1_w27 <<= sbox[b1_w27]
	c2_w27 <<= sbox[b2_w27]
	c3_w27 <<= sbox[b3_w27]
	c4_w27 <<= sbox[b4_w27]

	substituted_w27 = pyrtl.WireVector(32, 'substituted_w27')
	substituted_w27 <<= pyrtl.concat(c1_w27, c2_w27, c3_w27, c4_w27)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w27 = pyrtl.WireVector(bitwidth=32, name='xor_w27')
	rc1_w27 = pyrtl.WireVector(bitwidth=8, name='rc1_w27')
	rc2_w27 = pyrtl.WireVector(bitwidth=8, name='rc2_w27')
	rc3_w27 = pyrtl.WireVector(bitwidth=8, name='rc3_w27')
	rc4_w27 = pyrtl.WireVector(bitwidth=8, name='rc4_w27')

	rc1_w27 <<= rcon[7]
	rc2_w27 <<= 0x00
	rc3_w27 <<= 0x00
	rc4_w27<<= 0x00

	concat_w27 = pyrtl.WireVector(32, 'concat_w27')
	concat_w27 <<= pyrtl.concat(rc1_w27, rc2_w27, rc3_w27, rc4_w27)
	xor_w27 <<= concat_w27 ^ substituted_w27
	return xor_w27


def g_w31(word):
	# STEP 1: One-byte left circular rotation.
	a1_w31 = pyrtl.WireVector(8, 'a1_w31')
	a2_w31 = pyrtl.WireVector(8, 'a2_w31')
	a3_w31 = pyrtl.WireVector(8, 'a3_w31')
	a4_w31 = pyrtl.WireVector(8, 'a4_w31')

	a1_w31 <<= word[24:32]
	a2_w31 <<= word[16:24]
	a3_w31 <<= word[8:16]
	a4_w31 <<= word[0:8]

	shifted_w31 = pyrtl.WireVector(32, 'shifted_w31')
	shifted_w31 <<= pyrtl.concat(a2_w31, a3_w31, a4_w31, a1_w31)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w31 = pyrtl.WireVector(8, 'b1_w31')
	b2_w31 = pyrtl.WireVector(8, 'b2_w31')
	b3_w31 = pyrtl.WireVector(8, 'b3_w31')
	b4_w31 = pyrtl.WireVector(8, 'b4_w31')

	b1_w31 <<= shifted_w31[24:32]
	b2_w31 <<= shifted_w31[16:24]
	b3_w31 <<= shifted_w31[8:16]
	b4_w31 <<= shifted_w31[0:8]

	c1_w31 = pyrtl.WireVector(8, 'c1_w31')
	c2_w31 = pyrtl.WireVector(8, 'c2_w31')
	c3_w31 = pyrtl.WireVector(8, 'c3_w31')
	c4_w31 = pyrtl.WireVector(8, 'c4_w31')

	c1_w31 <<= sbox[b1_w31]
	c2_w31 <<= sbox[b2_w31]
	c3_w31 <<= sbox[b3_w31]
	c4_w31 <<= sbox[b4_w31]

	substituted_w31 = pyrtl.WireVector(32, 'substituted_w31')
	substituted_w31 <<= pyrtl.concat(c1_w31, c2_w31, c3_w31, c4_w31)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w31 = pyrtl.WireVector(bitwidth=32, name='xor_w31')
	rc1_w31 = pyrtl.WireVector(bitwidth=8, name='rc1_w31')
	rc2_w31 = pyrtl.WireVector(bitwidth=8, name='rc2_w31')
	rc3_w31 = pyrtl.WireVector(bitwidth=8, name='rc3_w31')
	rc4_w31 = pyrtl.WireVector(bitwidth=8, name='rc4_w31')

	rc1_w31 <<= rcon[8]
	rc2_w31 <<= 0x00
	rc3_w31 <<= 0x00
	rc4_w31<<= 0x00

	concat_w31 = pyrtl.WireVector(32, 'concat_w31')
	concat_w31 <<= pyrtl.concat(rc1_w31, rc2_w31, rc3_w31, rc4_w31)
	xor_w31 <<= concat_w31 ^ substituted_w31
	return xor_w31


def g_w35(word):
	# STEP 1: One-byte left circular rotation.
	a1_w35 = pyrtl.WireVector(8, 'a1_w35')
	a2_w35 = pyrtl.WireVector(8, 'a2_w35')
	a3_w35 = pyrtl.WireVector(8, 'a3_w35')
	a4_w35 = pyrtl.WireVector(8, 'a4_w35')

	a1_w35 <<= word[24:32]
	a2_w35 <<= word[16:24]
	a3_w35 <<= word[8:16]
	a4_w35 <<= word[0:8]

	shifted_w35 = pyrtl.WireVector(32, 'shifted_w35')
	shifted_w35 <<= pyrtl.concat(a2_w35, a3_w35, a4_w35, a1_w35)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w35 = pyrtl.WireVector(8, 'b1_w35')
	b2_w35 = pyrtl.WireVector(8, 'b2_w35')
	b3_w35 = pyrtl.WireVector(8, 'b3_w35')
	b4_w35 = pyrtl.WireVector(8, 'b4_w35')

	b1_w35 <<= shifted_w35[24:32]
	b2_w35 <<= shifted_w35[16:24]
	b3_w35 <<= shifted_w35[8:16]
	b4_w35 <<= shifted_w35[0:8]

	c1_w35 = pyrtl.WireVector(8, 'c1_w35')
	c2_w35 = pyrtl.WireVector(8, 'c2_w35')
	c3_w35 = pyrtl.WireVector(8, 'c3_w35')
	c4_w35 = pyrtl.WireVector(8, 'c4_w35')

	c1_w35 <<= sbox[b1_w35]
	c2_w35 <<= sbox[b2_w35]
	c3_w35 <<= sbox[b3_w35]
	c4_w35 <<= sbox[b4_w35]

	substituted_w35 = pyrtl.WireVector(32, 'substituted_w35')
	substituted_w35 <<= pyrtl.concat(c1_w35, c2_w35, c3_w35, c4_w35)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w35 = pyrtl.WireVector(bitwidth=32, name='xor_w35')
	rc1_w35 = pyrtl.WireVector(bitwidth=8, name='rc1_w35')
	rc2_w35 = pyrtl.WireVector(bitwidth=8, name='rc2_w35')
	rc3_w35 = pyrtl.WireVector(bitwidth=8, name='rc3_w35')
	rc4_w35 = pyrtl.WireVector(bitwidth=8, name='rc4_w35')

	rc1_w35 <<= rcon[9]
	rc2_w35 <<= 0x00
	rc3_w35 <<= 0x00
	rc4_w35<<= 0x00

	concat_w35 = pyrtl.WireVector(32, 'concat_w35')
	concat_w35 <<= pyrtl.concat(rc1_w35, rc2_w35, rc3_w35, rc4_w35)
	xor_w35 <<= concat_w35 ^ substituted_w35
	return xor_w35


def g_w39(word):
	# STEP 1: One-byte left circular rotation.
	a1_w39 = pyrtl.WireVector(8, 'a1_w39')
	a2_w39 = pyrtl.WireVector(8, 'a2_w39')
	a3_w39 = pyrtl.WireVector(8, 'a3_w39')
	a4_w39 = pyrtl.WireVector(8, 'a4_w39')

	a1_w39 <<= word[24:32]
	a2_w39 <<= word[16:24]
	a3_w39 <<= word[8:16]
	a4_w39 <<= word[0:8]

	shifted_w39 = pyrtl.WireVector(32, 'shifted_w39')
	shifted_w39 <<= pyrtl.concat(a2_w39, a3_w39, a4_w39, a1_w39)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w39 = pyrtl.WireVector(8, 'b1_w39')
	b2_w39 = pyrtl.WireVector(8, 'b2_w39')
	b3_w39 = pyrtl.WireVector(8, 'b3_w39')
	b4_w39 = pyrtl.WireVector(8, 'b4_w39')

	b1_w39 <<= shifted_w39[24:32]
	b2_w39 <<= shifted_w39[16:24]
	b3_w39 <<= shifted_w39[8:16]
	b4_w39 <<= shifted_w39[0:8]

	c1_w39 = pyrtl.WireVector(8, 'c1_w39')
	c2_w39 = pyrtl.WireVector(8, 'c2_w39')
	c3_w39 = pyrtl.WireVector(8, 'c3_w39')
	c4_w39 = pyrtl.WireVector(8, 'c4_w39')

	c1_w39 <<= sbox[b1_w39]
	c2_w39 <<= sbox[b2_w39]
	c3_w39 <<= sbox[b3_w39]
	c4_w39 <<= sbox[b4_w39]

	substituted_w39 = pyrtl.WireVector(32, 'substituted_w39')
	substituted_w39 <<= pyrtl.concat(c1_w39, c2_w39, c3_w39, c4_w39)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w39 = pyrtl.WireVector(bitwidth=32, name='xor_w39')
	rc1_w39 = pyrtl.WireVector(bitwidth=8, name='rc1_w39')
	rc2_w39 = pyrtl.WireVector(bitwidth=8, name='rc2_w39')
	rc3_w39 = pyrtl.WireVector(bitwidth=8, name='rc3_w39')
	rc4_w39 = pyrtl.WireVector(bitwidth=8, name='rc4_w39')

	rc1_w39 <<= rcon[10]
	rc2_w39 <<= 0x00
	rc3_w39 <<= 0x00
	rc4_w39<<= 0x00

	concat_w39 = pyrtl.WireVector(32, 'concat_w39')
	concat_w39 <<= pyrtl.concat(rc1_w39, rc2_w39, rc3_w39, rc4_w39)
	xor_w39 <<= concat_w39 ^ substituted_w39
	return xor_w39


def g_w43(word):
	# STEP 1: One-byte left circular rotation.
	a1_w43 = pyrtl.WireVector(8, 'a1_w43')
	a2_w43 = pyrtl.WireVector(8, 'a2_w43')
	a3_w43 = pyrtl.WireVector(8, 'a3_w43')
	a4_w43 = pyrtl.WireVector(8, 'a4_w43')

	a1_w43 <<= word[24:32]
	a2_w43 <<= word[16:24]
	a3_w43 <<= word[8:16]
	a4_w43 <<= word[0:8]

	shifted_w43 = pyrtl.WireVector(32, 'shifted_w43')
	shifted_w43 <<= pyrtl.concat(a2_w43, a3_w43, a4_w43, a1_w43)

	# STEP 2: Substitution of each byte of shifted word.
	b1_w43 = pyrtl.WireVector(8, 'b1_w43')
	b2_w43 = pyrtl.WireVector(8, 'b2_w43')
	b3_w43 = pyrtl.WireVector(8, 'b3_w43')
	b4_w43 = pyrtl.WireVector(8, 'b4_w43')

	b1_w43 <<= shifted_w43[24:32]
	b2_w43 <<= shifted_w43[16:24]
	b3_w43 <<= shifted_w43[8:16]
	b4_w43 <<= shifted_w43[0:8]

	c1_w43 = pyrtl.WireVector(8, 'c1_w43')
	c2_w43 = pyrtl.WireVector(8, 'c2_w43')
	c3_w43 = pyrtl.WireVector(8, 'c3_w43')
	c4_w43 = pyrtl.WireVector(8, 'c4_w43')

	c1_w43 <<= sbox[b1_w43]
	c2_w43 <<= sbox[b2_w43]
	c3_w43 <<= sbox[b3_w43]
	c4_w43 <<= sbox[b4_w43]

	substituted_w43 = pyrtl.WireVector(32, 'substituted_w43')
	substituted_w43 <<= pyrtl.concat(c1_w43, c2_w43, c3_w43, c4_w43)

	# STEP 3: XOR substituted bytes with round constant.
	xor_w43 = pyrtl.WireVector(bitwidth=32, name='xor_w43')
	rc1_w43 = pyrtl.WireVector(bitwidth=8, name='rc1_w43')
	rc2_w43 = pyrtl.WireVector(bitwidth=8, name='rc2_w43')
	rc3_w43 = pyrtl.WireVector(bitwidth=8, name='rc3_w43')
	rc4_w43 = pyrtl.WireVector(bitwidth=8, name='rc4_w43')

	rc1_w43 <<= rcon[11]
	rc2_w43 <<= 0x00
	rc3_w43 <<= 0x00
	rc4_w43<<= 0x00

	concat_w43 = pyrtl.WireVector(32, 'concat_w43')
	concat_w43 <<= pyrtl.concat(rc1_w43, rc2_w43, rc3_w43, rc4_w43)
	xor_w43 <<= concat_w43 ^ substituted_w43
	return xor_w43
