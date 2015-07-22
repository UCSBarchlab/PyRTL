import pyrtl
import random

__author__ = 'John Clow'

"""
testcase_utils

This file (intentionally misspelled) is created to store common utility
functions used for the test cases.

The misspelling is so that the nosetests will not search this
file for unittests to run.
"""


def generate_in_wire_and_values(bitwidth, num_test_vals=20, name=None):
    """
    Generates an input wire and a set of test values for
    testing purposes
    :param bitwidth: The bitwidth of the value you wish to generate
    :return: tuple consisting of input_wire, test_vaues
    """
    input_wire = pyrtl.Input(bitwidth, name=name)
    test_vals = [int(2**random.uniform(0, bitwidth)-1) for i in range(num_test_vals)]
    return input_wire, test_vals
