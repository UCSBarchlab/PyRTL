import os
import subprocess
from pathlib import Path

import pytest

import pyrtl

"""
Tests all of the files in the example folder

Note that this file is structure dependent, so don't forget to change it if the relative
location of the examples changes
"""


@pytest.mark.parametrize(
    "file",
    (Path(os.path.dirname(__file__)) / ".." / "examples").glob("*.py"),
    ids=lambda path: path.name,
)
def test_all_examples(file):
    # Always use the ASCII renderer for deterministic example output.
    os.environ["PYRTL_RENDERER"] = "ascii"
    pyrtl.reset_working_block()
    try:
        subprocess.check_output(["uv", "run", file])
    except subprocess.CalledProcessError as e:
        raise e
