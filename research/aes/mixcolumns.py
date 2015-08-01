import sys
sys.path.append("../..")

import pyrtl
from pyrtl import *

def software_galoisMult(a, b):
	p = 0
	hiBitSet = 0
	for i in range(8):
		if b & 1 == 1:
			p = p ^ a
		hiBitSet = a & 0x80
		a = a << 1
		if hiBitSet == 0x80:
			a = a ^ 0x1b
		b = b >> 1
	return p % 256

GM_data = [software_galoisMult(i, 2) for i in range(256)]
GM_table = pyrtl.RomBlock(bitwidth=256, addrwidth=8, data=GM_data)

def galoisMult(c, d):
	assert d == 2 or d == 3
	if d == 2:
		return GM_table[c]
	elif d == 3:
		return GM_table[c] ^ c


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

	b0 = pyrtl.WireVector(bitwidth=8, name='b0')
	b1 = pyrtl.WireVector(bitwidth=8, name='b1')
	b2 = pyrtl.WireVector(bitwidth=8, name='b2')
	b3 = pyrtl.WireVector(bitwidth=8, name='b3')
	b4 = pyrtl.WireVector(bitwidth=8, name='b4')
	b5 = pyrtl.WireVector(bitwidth=8, name='b5')
	b6 = pyrtl.WireVector(bitwidth=8, name='b6')
	b7 = pyrtl.WireVector(bitwidth=8, name='b7')
	b8 = pyrtl.WireVector(bitwidth=8, name='b8')
	b9 = pyrtl.WireVector(bitwidth=8, name='b9')
	b10 = pyrtl.WireVector(bitwidth=8, name='b10')
	b11 = pyrtl.WireVector(bitwidth=8, name='b11')
	b12 = pyrtl.WireVector(bitwidth=8, name='b12')
	b13 = pyrtl.WireVector(bitwidth=8, name='b13')
	b14 = pyrtl.WireVector(bitwidth=8, name='b14')
	b15 = pyrtl.WireVector(bitwidth=8, name='b15')

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

	out_vector = pyrtl.WireVector(bitwidth=128, name='out_vector')
	out_vector <<= pyrtl.concat(b0, b1, b2, b3, 
							b4, b5, b6, b7, 
							b8, b9, b10, b11, 
							b12, b13, b14, b15)
	return out_vector

# Hardware build.
aes_input = pyrtl.Input(bitwidth=128, name='aes_input')
aes_output = pyrtl.Output(bitwidth=128, name='aes_output')
aes_output <<= MixColumns(aes_input)

print pyrtl.working_block()

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

for cycle in range(1):
	sim.step({aes_input: 0xc6c6c6c6d4d4d4d52d26314cdb135345})

sim_trace.render_trace(symbol_len=40, segment_size=1)
