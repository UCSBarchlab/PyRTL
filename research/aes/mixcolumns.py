# mixcolumns.py

import sys
sys.path.append("../..")

import pyrtl
from pyrtl import *

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

	b0 <<= 2*a0 ^ 3*a1 ^ a2 ^ a3
	b1 <<= 2*a1 ^ 3*a2 ^ a3 ^ a0
	b2 <<= 2*a2 ^ 3*a3 ^ a0 ^ a1
	b3 <<= 2*a3 ^ 3*a0 ^ a1 ^ a2

	b4 <<= 2*a4 ^ 3*a5 ^ a6 ^ a7
	b5 <<= 2*a5 ^ 3*a6 ^ a7 ^ a4
	b6 <<= 2*a6 ^ 3*a7 ^ a4 ^ a5
	b7 <<= 2*a7 ^ 3*a4 ^ a5 ^ a6

	b8 <<= 2*a8 ^ 3*a9 ^ a10 ^ a11
	b9 <<= 2*a9 ^ 3*a10 ^ a11 ^ a8
	b10 <<= 2*a10 ^ 3*a11 ^ a8 ^ a9
	b11 <<= 2*a11 ^ 3*a8 ^ a9 ^ a10

	b12 <<= 2*a12 ^ 3*a13 ^ a14 ^ a15
	b13 <<= 2*a13 ^ 3*a14 ^ a15 ^ a12
	b14 <<= 2*a14 ^ 3*a15 ^ a12 ^ a13
	b15 <<= 2*a15 ^ 3*a12 ^ a13 ^ a14

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
	sim.step({aes_input: 0xdb135345f20a225c01010101c6c6c6c6})

sim_trace.render_trace(symbol_len=40, segment_size=1)
