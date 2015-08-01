import sys
sys.path.append("../..")

import pyrtl
import keyexpansion
import func_g
import subbytes
import shiftrows
import mixcolumns
import addroundkey
from pyrtl import *
from keyexpansion import *
from func_g import *
from subbytes import *
from shiftrows import *
from mixcolumns import *
from addroundkey import *

def aes_main(plaintext, key):
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
aes_output = pyrtl.Output(bitwidth=128, name='aes_output')
aes_output <<= aes_main(aes_plaintext, aes_key)

print pyrtl.working_block()
print

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

for cycle in range(1):
	sim.step({
		aes_plaintext: 0x00000000000000000000000000000000
		aes_key: 0x00000000000000000000000000000000
		})

sim_trace.render_trace(symbol_len=40, segment_size=1)
