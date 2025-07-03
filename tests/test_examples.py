import glob
import os
import subprocess

import pytest

import pyrtl

"""
Tests all of the files in the example folder

Note that this file is structure dependent, so don't forget to change it if the relative
location of the examples changes
"""


@pytest.mark.parametrize(
    "file", glob.iglob(os.path.dirname(__file__) + "/../examples/*.py")
)
def test_all_examples(file):
    pyrtl.reset_working_block()
    try:
        _ = subprocess.check_output(["python", file])
    except subprocess.CalledProcessError as e:
        raise e
