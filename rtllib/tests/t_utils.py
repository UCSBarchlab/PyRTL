import pyrtl
import random

__author__ = 'John Clow'

"""
testcase_utils

This file (intentionally misspelled) is created to store common utility
functions used for the test cases.

I am documenting this rather well because users have
a good reason to look at it - John Clow
"""


def generate_in_wire_and_values(bitwidth, num_test_vals=20, name=None):
    """
    Generates an input wire and a set of test values for
    testing purposes
    :param bitwidth: The bitwidth of the value you wish to generate
    :return: tuple consisting of input_wire, test_vaues
    """

    input_wire = pyrtl.Input(bitwidth, name=name)  # Creating a new input wire

    # Creating a list of test values
    # Values are between 0 and 2**bitwidth - 1.
    # Note that this is not uniformly distributed
    test_vals = [int(2**random.uniform(0, bitwidth)-1) for i in range(num_test_vals)]

    return input_wire, test_vals

def sim_and_ret_out(outwire, inwires, invals):
    """
    Simulates the net using the inwires, invalues and returns the output array
    Used for rapid test development

    :param outwire: The wire to return the output of
    :param [Input, ...] inwires: a list of wires to read in from
    :param [[int, ...], ...] invals: a list of input value lists
    :return: a list of values from the output wire simulation result
    """
    sim_trace = pyrtl.SimulationTrace()  # Creating a logger for the simulator
    sim = pyrtl.Simulation(tracer=sim_trace)  # Creating the simulation
    for cycle in range(len(invals[0])):
        # for each call to step(), we supply a dictionary of wires to their
        # corresponding value for the cycle (The simulator then simulates it)
        sim.step({wire: val[cycle] for wire, val in zip(inwires, invals)})

    return sim_trace.trace[outwire]  # Pulling the value of outwire straight from the log
