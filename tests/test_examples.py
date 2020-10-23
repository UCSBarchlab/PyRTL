import glob
import os
import subprocess
import pyrtl

import nose  # using the advanced features of nose to do this


"""
Tests all of the files in the example folder

Note that this file is structure dependent, so don't forget to change it if the
relative location of the examples changes
"""


def test_all_examples():
    x = __file__
    for file in glob.iglob(os.path.dirname(__file__) + "/../examples/*.py"):
        yield example_t, os.path.realpath(file)


# note that this function cannot start with "test"
def example_t(file):
    # print("testing file: " + file)
    pyrtl.reset_working_block()
    try:
        output = subprocess.check_output(['python', file])
    except subprocess.CalledProcessError as e:
        raise e
