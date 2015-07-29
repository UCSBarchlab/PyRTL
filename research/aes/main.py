# main.py

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

	Output: 128-it ciphertext.
	"""
	# Expanding the key (KeyExpansion).
	expanded_key = pyrtl.WireVector(bitwidth=1408, name='expanded_key')
	expanded_key <<= KeyExpansion(key)

	# Initial AddRoundKey.
	new_state = pyrtl.WireVector(bitwidth=128, name='new_state')
	new_state <<= addroundkey_1(plaintext, expanded_key)
	
	# Round 1.

	# Round 2.

	# Round 3.

	# Round 4.

	# Round 5.

	# Round 6.

	# Round 7.

	# Round 8.

	# Round 9.

	# Final round.


# Hardware build.
aes_input = pyrtl.Input(bitwidth=128, name='aes_input')
aes_output = pyrtl.Output(bitwidth=128, name='aes_output')
aes_output <<= aes_main(aes_input)

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
