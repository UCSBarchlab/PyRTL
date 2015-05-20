__author__ = 'Deeksha'

# NOTES:
# create a neuron in pyrtl which takes in a list of inputs as 
# arguments and return the output as one single wire 
# have L1 as [N(i) for i in inputlist]
# have L2 as [N[L1] for i in L1]

import sys
sys.path.append("..")
import random
import pyrtl
from pyrtl import *
import math


def main():
	return test()


# def sigmoid(x):
    # return 1.0/(1.0 + exp(-x)) # change to piecewise linear instead

# Defining the threshold function/activation function within each neuron
# This threshold function is a piece-wise linear operator
def threshold(x):
	if x < 0.1:
		out = 0
	elif x > 0.1 & x < 0.3:
		out = x
	elif x == 0.1:
		out = x
	elif x == 0.3:
		out = x
	elif x > 0.3:
		out = 0.5
	return out

# you have a neuron, which takes in multiple inputs as a list
# def matrixgen():
# def weights():

def neuron(x1, x2, x3, x4): 
	# x1, x2, etc are the inputs to the neuron
	# these are wirevectors 
	# convert this into a list? so that we don't need to mention 
	# all the inputs
	# Will do this later
	# ======================= T O - D O ==========================
	# w = []
	# w[1] = 0.1
	# w[2] = 0.2
	# w[3] = 0.2
	# w[4] = 0.5
	x1 = pyrtl.WireVector(bitwidth=1, name='x1')
	x2 = pyrtl.WireVector(bitwidth=1, name='x2')
	x3 = pyrtl.WireVector(bitwidth=1, name='x3')
	x4 = pyrtl.WireVector(bitwidth=1, name='x4')
	w1 = pyrtl.Const(0.1)
	w2 = pyrtl.Const(0.2)
	w3 = pyrtl.Const(0.2)
	w4 = pyrtl.Const(0.5)
	# Do the weights really need to be wirevectors?

	# These are the weights for the inputs
	sum = 0.0
	# for i in range(4):
	sum = x1*w1 + x2*w2+ x3*w3+ x3*w3 + x4*w4 # no plus equal
	out = threshold(sum)
	print out
	return out


def test():
	pyrtl.reset_working_block()
	x1, x2 = pyrtl.Input(1, 'x1'), pyrtl.Input(1, 'x2') 
	x3, x4 = pyrtl.Input(1, 'x3'), pyrtl.Input(1, 'x4')
	out = pyrtl.Output(2, 'out')
	out <<= neuron(x1, x2, x3, x4)
	sim_trace = pyrtl.SimulationTrace()
	sim = pyrtl.Simulation(tracer=sim_trace)
	for cycle in range(5):
		sim.step({x1: 2, x2: 3, x4: 4, x5: 5})
	expected_out = 4.1
	neuron_out = sim_trace.trace[out]
	sim_trace.render_trace()
	assert(neuron_out == expected_out)
	print "Pass!!"


if __name__ == "__main__":
	main()
