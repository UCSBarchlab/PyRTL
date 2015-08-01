import sys
sys.path.append("../..")

import pyrtl
from pyrtl import *

import keyexpansion
from keyexpansion import *

""" AddRoundKey round of AES.

Input: 128-bit state array.
Output: 128-bit state array.
"""

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


# Hardware build.
aes_input = pyrtl.Input(bitwidth=128, name='aes_input')
aes_output = pyrtl.Output(bitwidth=128, name='aes_output')
aes_output <<= addroundkey_x(aes_input)

print pyrtl.working_block()
print

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

for cycle in range(1):
	sim.step({aes_input: 0xff})

sim_trace.render_trace(symbol_len=5, segment_size=5)
