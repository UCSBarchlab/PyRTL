import sys
sys.path.append("../..")

import pyrtl
from pyrtl import *

import func_g
from func_g import *


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


# Hardware build.
aes_input = pyrtl.Input(bitwidth=128, name='aes_input')
aes_output = pyrtl.Output(bitwidth=1408, name='aes_output')
aes_output <<= KeyExpansion(aes_input)

print pyrtl.working_block()
print

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
# 000102030405060708090a0b0c0d0e0f
# 0f1571c947d9e8590cb7adaf7f6798
# ffffffffffffffffffffffffffffffff

for cycle in range(1):
	sim.step({aes_input: 0x00000000000000000000000000000000})

sim_trace.render_trace(symbol_len=40, segment_size=1)
