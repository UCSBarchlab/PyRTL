""" AES-128 ENCRYPTION """

import pyrtl
import sys
sys.path.append("../..")

import pyrtl

# --- "G" FUNCTIONS ---

# S-box ROM.
sbox_data = [0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76, 0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0, 0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15, 0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75, 0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84, 0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf, 0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8, 0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2, 0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73, 0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb, 0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79, 0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08, 0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a, 0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e, 0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf, 0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16]
sbox = pyrtl.RomBlock(bitwidth=128, addrwidth=8, romdata=sbox_data)

# Rcon ROM.
rcon_data = [0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d]
rcon = pyrtl.RomBlock(bitwidth=128, addrwidth=8, romdata=rcon_data)

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


# --- KEY EXPANSION ---
def KeyExpansion(in_vector):
	""" KeyExpansion round of AES.

	Input: 16-byte key.
	Output: 176-byte expanded key.
	"""

	w0 = in_vector[96:128]
	w1 = in_vector[64:96]
	w2 = in_vector[32:64]
	w3 = in_vector[0:32]
	
	w4 = w0 ^ g_w3(w3)
	w5 = w4 ^ w1
	w6 = w5 ^ w2
	w7 = w6 ^ w3
	w8 = w4 ^ g_w7(w7)
	w9 = w8 ^ w5
	w10 = w9 ^ w6
	w11 = w10 ^ w7
	w12 = w8 ^ g_w11(w11)
	w13 = w12 ^ w9
	w14 = w13 ^ w10
	w15 = w14 ^ w11
	w16 = w12 ^ g_w15(w15)
	w17 = w16 ^ w13
	w18 = w17 ^ w14
	w19 = w18 ^ w15
	w20 = w16 ^ g_w19(w19)
	w21 = w20 ^ w17
	w22 = w21 ^ w18
	w23 = w22 ^ w19
	w24 = w20 ^ g_w23(w23)
	w25 = w24 ^ w21
	w26 = w25 ^ w22
	w27 = w26 ^ w23
	w28 = w24 ^ g_w27(w27)
	w29 = w28 ^ w25
	w30 = w29 ^ w26
	w31 = w30 ^ w27
	w32 = w28 ^ g_w31(w31)
	w33 = w32 ^ w29
	w34 = w33 ^ w30
	w35 = w34 ^ w31
	w36 = w32 ^ g_w35(w35)
	w37 = w36 ^ w33
	w38 = w37 ^ w34
	w39 = w38 ^ w35
	w40 = w36 ^ g_w39(w39)
	w41 = w40 ^ w37
	w42 = w41 ^ w38
	w43 = w42 ^ w39

	out_vector = pyrtl.concat(w0, w1, w2, w3, 
							w4, w5, w6, w7, 
							w8, w9, w10, w11, 
							w12, w13, w14, w15, 
							w16, w17, w18, w19, 
							w20, w21, w22, w23, 
							w24, w25, w26, w27, 
							w28, w29, w30, w31, 
							w32, w33, w34, w35, 
							w36, w37, w38, w39, 
							w40, w41, w42, w43)

	return out_vector


# --- SUB BYTES FUNCTION ---
def SubBytes(in_vector):
	""" SubBytes round of AES.

	Input: A single wirevector of bitwidth 128.
	Output: A single wirevector of bitwidth 128.
	"""

	a00 = in_vector[120:128]
	a01 = in_vector[112:120]
	a02 = in_vector[104:112]
	a03 = in_vector[96:104]
	a10 = in_vector[88:96]
	a11 = in_vector[80:88]
	a12 = in_vector[72:80]
	a13 = in_vector[64:72]
	a20 = in_vector[56:64]
	a21 = in_vector[48:56]
	a22 = in_vector[40:48]
	a23 = in_vector[32:40]
	a30 = in_vector[24:32]
	a31 = in_vector[16:24]
	a32 = in_vector[8:16]
	a33 = in_vector[0:8]
	
	b00 = pyrtl.WireVector(8)
	b01 = pyrtl.WireVector(8)
	b02 = pyrtl.WireVector(8)
	b03 = pyrtl.WireVector(8)
	b10 = pyrtl.WireVector(8)
	b11 = pyrtl.WireVector(8)
	b12 = pyrtl.WireVector(8)
	b13 = pyrtl.WireVector(8)
	b20 = pyrtl.WireVector(8)
	b21 = pyrtl.WireVector(8)
	b22 = pyrtl.WireVector(8)
	b23 = pyrtl.WireVector(8)
	b30 = pyrtl.WireVector(8)
	b31 = pyrtl.WireVector(8)
	b32 = pyrtl.WireVector(8)
	b33 = pyrtl.WireVector(8)

	b00 <<= sbox[a00]
	b01 <<= sbox[a01]
	b02 <<= sbox[a02]
	b03 <<= sbox[a03]
	b10 <<= sbox[a10]
	b11 <<= sbox[a11]
	b12 <<= sbox[a12]
	b13 <<= sbox[a13]
	b20 <<= sbox[a20]
	b21 <<= sbox[a21]
	b22 <<= sbox[a22]
	b23 <<= sbox[a23]
	b30 <<= sbox[a30]
	b31 <<= sbox[a31]
	b32 <<= sbox[a32]
	b33 <<= sbox[a33]

	out_vector = pyrtl.concat(b00, b01, b02, b03,
					b10, b11, b12, b13,
					b20, b21, b22, b23,
					b30, b31, b32, b33)

	return out_vector


# --- SHIFT ROWS FUNCTION ---
def ShiftRows(in_vector):
	""" ShiftRows round in AES.

	Input: A single wirevector of width 128.
	Output: A single wirevector of width 128.
	"""

	a00 = in_vector[120:128]
	a10 = in_vector[112:120]
	a20 = in_vector[104:112]
	a30 = in_vector[96:104]
	a01 = in_vector[88:96]
	a11 = in_vector[80:88]
	a21 = in_vector[72:80]
	a31 = in_vector[64:72]
	a02 = in_vector[56:64]
	a12 = in_vector[48:56]
	a22 = in_vector[40:48]
	a32 = in_vector[32:40]
	a03 = in_vector[24:32]
	a13 = in_vector[16:24]
	a23 = in_vector[8:16]
	a33 = in_vector[0:8]

	out_vector = pyrtl.concat(a00, a11, a22, a33, 
						a01, a12, a23, a30, 
						a02, a13, a20, a31, 
						a03, a10, a21, a32)

	return out_vector


# --- MIX COLUMNS FUNCTIONS ---

# Galois Multiplication tables for 2 and 3.
GM2_data = [0x00,0x02,0x04,0x06,0x08,0x0a,0x0c,0x0e,0x10,0x12,0x14,0x16,0x18,0x1a,0x1c,0x1e,0x20,0x22,0x24,0x26,0x28,0x2a,0x2c,0x2e,0x30,0x32,0x34,0x36,0x38,0x3a,0x3c,0x3e,0x40,0x42,0x44,0x46,0x48,0x4a,0x4c,0x4e,0x50,0x52,0x54,0x56,0x58,0x5a,0x5c,0x5e,0x60,0x62,0x64,0x66,0x68,0x6a,0x6c,0x6e,0x70,0x72,0x74,0x76,0x78,0x7a,0x7c,0x7e,0x80,0x82,0x84,0x86,0x88,0x8a,0x8c,0x8e,0x90,0x92,0x94,0x96,0x98,0x9a,0x9c,0x9e,0xa0,0xa2,0xa4,0xa6,0xa8,0xaa,0xac,0xae,0xb0,0xb2,0xb4,0xb6,0xb8,0xba,0xbc,0xbe,0xc0,0xc2,0xc4,0xc6,0xc8,0xca,0xcc,0xce,0xd0,0xd2,0xd4,0xd6,0xd8,0xda,0xdc,0xde,0xe0,0xe2,0xe4,0xe6,0xe8,0xea,0xec,0xee,0xf0,0xf2,0xf4,0xf6,0xf8,0xfa,0xfc,0xfe,0x1b,0x19,0x1f,0x1d,0x13,0x11,0x17,0x15,0x0b,0x09,0x0f,0x0d,0x03,0x01,0x07,0x05,0x3b,0x39,0x3f,0x3d,0x33,0x31,0x37,0x35,0x2b,0x29,0x2f,0x2d,0x23,0x21,0x27,0x25,0x5b,0x59,0x5f,0x5d,0x53,0x51,0x57,0x55,0x4b,0x49,0x4f,0x4d,0x43,0x41,0x47,0x45,0x7b,0x79,0x7f,0x7d,0x73,0x71,0x77,0x75,0x6b,0x69,0x6f,0x6d,0x63,0x61,0x67,0x65,0x9b,0x99,0x9f,0x9d,0x93,0x91,0x97,0x95,0x8b,0x89,0x8f,0x8d,0x83,0x81,0x87,0x85,0xbb,0xb9,0xbf,0xbd,0xb3,0xb1,0xb7,0xb5,0xab,0xa9,0xaf,0xad,0xa3,0xa1,0xa7,0xa5,0xdb,0xd9,0xdf,0xdd,0xd3,0xd1,0xd7,0xd5,0xcb,0xc9,0xcf,0xcd,0xc3,0xc1,0xc7,0xc5,0xfb,0xf9,0xff,0xfd,0xf3,0xf1,0xf7,0xf5,0xeb,0xe9,0xef,0xed,0xe3,0xe1,0xe7,0xe5]
GM3_data = [0x00,0x03,0x06,0x05,0x0c,0x0f,0x0a,0x09,0x18,0x1b,0x1e,0x1d,0x14,0x17,0x12,0x11,0x30,0x33,0x36,0x35,0x3c,0x3f,0x3a,0x39,0x28,0x2b,0x2e,0x2d,0x24,0x27,0x22,0x21,0x60,0x63,0x66,0x65,0x6c,0x6f,0x6a,0x69,0x78,0x7b,0x7e,0x7d,0x74,0x77,0x72,0x71,0x50,0x53,0x56,0x55,0x5c,0x5f,0x5a,0x59,0x48,0x4b,0x4e,0x4d,0x44,0x47,0x42,0x41,0xc0,0xc3,0xc6,0xc5,0xcc,0xcf,0xca,0xc9,0xd8,0xdb,0xde,0xdd,0xd4,0xd7,0xd2,0xd1,0xf0,0xf3,0xf6,0xf5,0xfc,0xff,0xfa,0xf9,0xe8,0xeb,0xee,0xed,0xe4,0xe7,0xe2,0xe1,0xa0,0xa3,0xa6,0xa5,0xac,0xaf,0xaa,0xa9,0xb8,0xbb,0xbe,0xbd,0xb4,0xb7,0xb2,0xb1,0x90,0x93,0x96,0x95,0x9c,0x9f,0x9a,0x99,0x88,0x8b,0x8e,0x8d,0x84,0x87,0x82,0x81,0x9b,0x98,0x9d,0x9e,0x97,0x94,0x91,0x92,0x83,0x80,0x85,0x86,0x8f,0x8c,0x89,0x8a,0xab,0xa8,0xad,0xae,0xa7,0xa4,0xa1,0xa2,0xb3,0xb0,0xb5,0xb6,0xbf,0xbc,0xb9,0xba,0xfb,0xf8,0xfd,0xfe,0xf7,0xf4,0xf1,0xf2,0xe3,0xe0,0xe5,0xe6,0xef,0xec,0xe9,0xea,0xcb,0xc8,0xcd,0xce,0xc7,0xc4,0xc1,0xc2,0xd3,0xd0,0xd5,0xd6,0xdf,0xdc,0xd9,0xda,0x5b,0x58,0x5d,0x5e,0x57,0x54,0x51,0x52,0x43,0x40,0x45,0x46,0x4f,0x4c,0x49,0x4a,0x6b,0x68,0x6d,0x6e,0x67,0x64,0x61,0x62,0x73,0x70,0x75,0x76,0x7f,0x7c,0x79,0x7a,0x3b,0x38,0x3d,0x3e,0x37,0x34,0x31,0x32,0x23,0x20,0x25,0x26,0x2f,0x2c,0x29,0x2a,0x0b,0x08,0x0d,0x0e,0x07,0x04,0x01,0x02,0x13,0x10,0x15,0x16,0x1f,0x1c,0x19,0x1a]
GM2 = pyrtl.RomBlock(bitwidth=256, addrwidth=8, romdata=GM2_data)
GM3 = pyrtl.RomBlock(bitwidth=256, addrwidth=8, romdata=GM3_data)

def galoisMult(c, d):
	assert d == 2 or d == 3
	if d == 2:
		return GM2[c]
	elif d == 3:
		return GM3[c]


def MixColumns(in_vector):
	""" MixColumns round of AES.

	Input: A single wirevector of bitwidth 128.
	Output: A single wirevector of bitwidth 128.
	"""
	a0 = in_vector[120:128]
	a1 = in_vector[112:120]
	a2 = in_vector[104:112]
	a3 = in_vector[96:104]
	a4 = in_vector[88:96]
	a5 = in_vector[80:88]
	a6 = in_vector[72:80]
	a7 = in_vector[64:72]
	a8 = in_vector[56:64]
	a9 = in_vector[48:56]
	a10 = in_vector[40:48]
	a11 = in_vector[32:40]
	a12 = in_vector[24:32]
	a13 = in_vector[16:24]
	a14 = in_vector[8:16]
	a15 = in_vector[0:8]

	b0 = pyrtl.WireVector(bitwidth=8)
	b1 = pyrtl.WireVector(bitwidth=8)
	b2 = pyrtl.WireVector(bitwidth=8)
	b3 = pyrtl.WireVector(bitwidth=8)
	b4 = pyrtl.WireVector(bitwidth=8)
	b5 = pyrtl.WireVector(bitwidth=8)
	b6 = pyrtl.WireVector(bitwidth=8)
	b7 = pyrtl.WireVector(bitwidth=8)
	b8 = pyrtl.WireVector(bitwidth=8)
	b9 = pyrtl.WireVector(bitwidth=8)
	b10 = pyrtl.WireVector(bitwidth=8)
	b11 = pyrtl.WireVector(bitwidth=8)
	b12 = pyrtl.WireVector(bitwidth=8)
	b13 = pyrtl.WireVector(bitwidth=8)
	b14 = pyrtl.WireVector(bitwidth=8)
	b15 = pyrtl.WireVector(bitwidth=8)

	b0 <<= galoisMult(a0, 2) ^ galoisMult(a1, 3) ^ a2 ^ a3
	b1 <<= galoisMult(a1, 2) ^ galoisMult(a2, 3) ^ a3 ^ a0
	b2 <<= galoisMult(a2, 2) ^ galoisMult(a3, 3) ^ a0 ^ a1
	b3 <<= galoisMult(a3, 2) ^ galoisMult(a0, 3) ^ a1 ^ a2

	b4 <<= galoisMult(a4, 2) ^ galoisMult(a5, 3) ^ a6 ^ a7
	b5 <<= galoisMult(a5, 2) ^ galoisMult(a6, 3) ^ a7 ^ a4
	b6 <<= galoisMult(a6, 2) ^ galoisMult(a7, 3) ^ a4 ^ a5
	b7 <<= galoisMult(a7, 2) ^ galoisMult(a4, 3) ^ a5 ^ a6

	b8 <<= galoisMult(a8, 2) ^ galoisMult(a9, 3) ^ a10 ^ a11
	b9 <<= galoisMult(a9, 2) ^ galoisMult(a10, 3) ^ a11 ^ a8
	b10 <<= galoisMult(a10, 2) ^ galoisMult(a11, 3) ^ a8 ^ a9
	b11 <<= galoisMult(a11, 2) ^ galoisMult(a8, 3) ^ a9 ^ a10

	b12 <<= galoisMult(a12, 2) ^ galoisMult(a13, 3) ^ a14 ^ a15
	b13 <<= galoisMult(a13, 2) ^ galoisMult(a14, 3) ^ a15 ^ a12
	b14 <<= galoisMult(a14, 2) ^ galoisMult(a15, 3) ^ a12 ^ a13
	b15 <<= galoisMult(a15, 2) ^ galoisMult(a12, 3) ^ a13 ^ a14

	out_vector = pyrtl.concat(b0, b1, b2, b3, 
							b4, b5, b6, b7, 
							b8, b9, b10, b11, 
							b12, b13, b14, b15)
	return out_vector


# --- ADD ROUND KEY FUNCTIONS ---
def addroundkey_initial(state, expanded_key):

	input_wire_1 = pyrtl.WireVector(bitwidth=128, name='input_wire_1')
	input_wire_1 <<= state

	new_1 = pyrtl.WireVector(bitwidth=128, name='new_1')
	new_1 <<= state ^ expanded_key[1280:1408]
	return new_1


def addroundkey_1(state, expanded_key):

	input_wire_2 = pyrtl.WireVector(bitwidth=128, name='input_wire_2')
	input_wire_2 <<= state

	new_2 = pyrtl.WireVector(bitwidth=128, name='new_2')
	new_2 <<= state ^ expanded_key[1152:1280]
	return new_2


def addroundkey_2(state, expanded_key):

	input_wire_3 = pyrtl.WireVector(bitwidth=128, name='input_wire_3')
	input_wire_3 <<= state

	new_3 = pyrtl.WireVector(bitwidth=128, name='new_3')
	new_3 <<= state ^ expanded_key[1024:1152]
	return new_3


def addroundkey_3(state, expanded_key):

	input_wire_4 = pyrtl.WireVector(bitwidth=128, name='input_wire_4')
	input_wire_4 <<= state

	new_4 = pyrtl.WireVector(bitwidth=128, name='new_4')
	new_4 <<= state ^ expanded_key[896:1024]
	return new_4


def addroundkey_4(state, expanded_key):

	input_wire_5 = pyrtl.WireVector(bitwidth=128, name='input_wire_5')
	input_wire_5 <<= state

	new_5 = pyrtl.WireVector(bitwidth=128, name='new_5')
	new_5 <<= state ^ expanded_key[768:896]
	return new_5


def addroundkey_5(state, expanded_key):

	input_wire_6 = pyrtl.WireVector(bitwidth=128, name='input_wire_6')
	input_wire_6 <<= state

	new_6 = pyrtl.WireVector(bitwidth=128, name='new_6')
	new_6 <<= state ^ expanded_key[640:768]
	return new_6


def addroundkey_6(state, expanded_key):

	input_wire_7 = pyrtl.WireVector(bitwidth=128, name='input_wire_7')
	input_wire_7 <<= state

	new_7 = pyrtl.WireVector(bitwidth=128, name='new_7')
	new_7 <<= state ^ expanded_key[512:640]
	return new_7


def addroundkey_7(state, expanded_key):

	input_wire_8 = pyrtl.WireVector(bitwidth=128, name='input_wire_8')
	input_wire_8 <<= state

	new_8 = pyrtl.WireVector(bitwidth=128, name='new_8')
	new_8 <<= state ^ expanded_key[384:512]
	return new_8


def addroundkey_8(state, expanded_key):

	input_wire_9 = pyrtl.WireVector(bitwidth=128, name='input_wire_9')
	input_wire_9 <<= state

	new_9 = pyrtl.WireVector(bitwidth=128, name='new_9')
	new_9 <<= state ^ expanded_key[256:384]
	return new_9


def addroundkey_9(state, expanded_key):

	input_wire_10 = pyrtl.WireVector(bitwidth=128, name='input_wire_10')
	input_wire_10 <<= state

	new_10 = pyrtl.WireVector(bitwidth=128, name='new_10')
	new_10 <<= state ^ expanded_key[128:256]
	return new_10


def addroundkey_10(state, expanded_key):

	input_wire_11 = pyrtl.WireVector(bitwidth=128, name='input_wire_11')
	input_wire_11 <<= state

	new_11 = pyrtl.WireVector(bitwidth=128, name='new_11')
	new_11 <<= state ^ expanded_key[0:128]
	return new_11


# --- MAIN FUNCTION ---
def aes_encryption(plaintext, key):
	""" Main function of the AES encryption algorithm.

	Inputs: 128-bit plaintext.
			128-bit key.

	Output: 128-bit ciphertext.
	"""
	# Wire declarations.
	temp_1 = pyrtl.WireVector(bitwidth=128, name='temp_1')
	temp_2 = pyrtl.WireVector(bitwidth=128, name='temp_2')
	temp_3 = pyrtl.WireVector(bitwidth=128, name='temp_3')
	temp_4 = pyrtl.WireVector(bitwidth=128, name='temp_4')
	temp_5 = pyrtl.WireVector(bitwidth=128, name='temp_5')
	temp_6 = pyrtl.WireVector(bitwidth=128, name='temp_6')
	temp_7 = pyrtl.WireVector(bitwidth=128, name='temp_7')
	temp_8 = pyrtl.WireVector(bitwidth=128, name='temp_8')
	temp_9 = pyrtl.WireVector(bitwidth=128, name='temp_9')
	temp_10 = pyrtl.WireVector(bitwidth=128, name='temp_10')
	temp_11 = pyrtl.WireVector(bitwidth=128, name='temp_11')
	temp_12 = pyrtl.WireVector(bitwidth=128, name='temp_12')
	temp_13 = pyrtl.WireVector(bitwidth=128, name='temp_13')
	temp_14 = pyrtl.WireVector(bitwidth=128, name='temp_14')
	temp_15 = pyrtl.WireVector(bitwidth=128, name='temp_15')
	temp_16 = pyrtl.WireVector(bitwidth=128, name='temp_16')
	temp_17 = pyrtl.WireVector(bitwidth=128, name='temp_17')
	temp_18 = pyrtl.WireVector(bitwidth=128, name='temp_18')
	temp_19 = pyrtl.WireVector(bitwidth=128, name='temp_19')
	temp_20 = pyrtl.WireVector(bitwidth=128, name='temp_20')
	temp_21 = pyrtl.WireVector(bitwidth=128, name='temp_21')
	temp_22 = pyrtl.WireVector(bitwidth=128, name='temp_22')
	temp_23 = pyrtl.WireVector(bitwidth=128, name='temp_23')
	temp_24 = pyrtl.WireVector(bitwidth=128, name='temp_24')
	temp_25 = pyrtl.WireVector(bitwidth=128, name='temp_25')
	temp_26 = pyrtl.WireVector(bitwidth=128, name='temp_26')
	temp_27 = pyrtl.WireVector(bitwidth=128, name='temp_27')
	temp_28 = pyrtl.WireVector(bitwidth=128, name='temp_28')
	temp_29 = pyrtl.WireVector(bitwidth=128, name='temp_29')
	temp_30 = pyrtl.WireVector(bitwidth=128, name='temp_30')
	temp_31 = pyrtl.WireVector(bitwidth=128, name='temp_31')
	temp_32 = pyrtl.WireVector(bitwidth=128, name='temp_32')
	temp_33 = pyrtl.WireVector(bitwidth=128, name='temp_33')
	temp_34 = pyrtl.WireVector(bitwidth=128, name='temp_34')
	temp_35 = pyrtl.WireVector(bitwidth=128, name='temp_35')
	temp_36 = pyrtl.WireVector(bitwidth=128, name='temp_36')
	temp_37 = pyrtl.WireVector(bitwidth=128, name='temp_37')
	temp_38 = pyrtl.WireVector(bitwidth=128, name='temp_38')
	temp_39 = pyrtl.WireVector(bitwidth=128, name='temp_39')

	# Expanding the key (KeyExpansion).
	expanded_key = pyrtl.WireVector(bitwidth=1408, name='expanded_key')
	expanded_key <<= KeyExpansion(key)

	# Initial AddRoundKey.
	new_state = pyrtl.WireVector(bitwidth=128, name='new_state')
	new_state <<= addroundkey_initial(plaintext, expanded_key)
	
	# # Round 1.
	temp_1 <<= SubBytes(new_state)
	temp_2 <<= ShiftRows(temp_1)
	temp_3 <<= MixColumns(temp_2)
	temp_4 <<= addroundkey_1(temp_3, expanded_key)

	# Round 2.
	temp_5 <<= SubBytes(temp_4)
	temp_6 <<= ShiftRows(temp_5)
	temp_7 <<= MixColumns(temp_6)
	temp_8 <<= addroundkey_2(temp_7, expanded_key)

	# Round 3.
	temp_9 <<= SubBytes(temp_8)
	temp_10 <<= ShiftRows(temp_9)
	temp_11 <<= MixColumns(temp_10)
	temp_12 <<= addroundkey_3(temp_11, expanded_key)

	# Round 4.
	temp_13 <<= SubBytes(temp_12)
	temp_14 <<= ShiftRows(temp_13)
	temp_15 <<= MixColumns(temp_14)
	temp_16 <<= addroundkey_4(temp_15, expanded_key)

	# Round 5.
	temp_17 <<= SubBytes(temp_16)
	temp_18 <<= ShiftRows(temp_17)
	temp_19 <<= MixColumns(temp_18)
	temp_20 <<= addroundkey_5(temp_19, expanded_key)

	# Round 6.
	temp_21 <<= SubBytes(temp_20)
	temp_22 <<= ShiftRows(temp_21)
	temp_23 <<= MixColumns(temp_22)
	temp_24 <<= addroundkey_6(temp_23, expanded_key)

	# Round 7.
	temp_25 <<= SubBytes(temp_24)
	temp_26 <<= ShiftRows(temp_25)
	temp_27 <<= MixColumns(temp_26)
	temp_28 <<= addroundkey_7(temp_27, expanded_key)

	# Round 8.
	temp_29 <<= SubBytes(temp_28)
	temp_30 <<= ShiftRows(temp_29)
	temp_31 <<= MixColumns(temp_30)
	temp_32 <<= addroundkey_8(temp_31, expanded_key)

	# Round 9.
	temp_33 <<= SubBytes(temp_32)
	temp_34 <<= ShiftRows(temp_33)
	temp_35 <<= MixColumns(temp_34)
	temp_36 <<= addroundkey_9(temp_35, expanded_key)

	# Final round.
	temp_37 <<= SubBytes(temp_36)
	temp_38 <<= ShiftRows(temp_37)
	temp_39 <<= addroundkey_10(temp_38, expanded_key)
	return temp_39

# Hardware build.
aes_plaintext = pyrtl.Input(bitwidth=128, name='aes_plaintext')
aes_key = pyrtl.Input(bitwidth=128, name='aes_key')
aes_ciphertext = pyrtl.Output(bitwidth=128, name='aes_ciphertext')
aes_ciphertext <<= aes_encryption(aes_plaintext, aes_key)

#print pyrtl.working_block()
#print

sim_trace = pyrtl.SimulationTrace(wirevector_subset=[aes_plaintext, aes_key, aes_ciphertext])
sim = pyrtl.Simulation(tracer=sim_trace)

for cycle in range(1):
	sim.step({
		aes_plaintext: 0x0,
		aes_key: 0x0
		})

sim_trace.render_trace(symbol_len=40, segment_size=1)
