import os
import subprocess
import sys
from itertools import chain
from pathlib import Path

import pytest


def get_scripts(directory: str) -> Path:
    return (Path(os.path.dirname(__file__)) / ".." / directory).glob("*.py")


@pytest.mark.parametrize(
    "file",
    chain(get_scripts("examples"), get_scripts("www/examples")),
    ids=lambda path: path.name,
)
def test_all_examples(file):
    """Test all Python scripts in ``examples/`` and ``www/examples``.

    This just checks that all Python scripts terminate with exit status 0.
    """
    # Always use the ASCII renderer for deterministic example output.
    os.environ["PYRTL_RENDERER"] = "ascii"

    try:
        subprocess.check_output(["uv", "run", file])
    except subprocess.CalledProcessError:
        pytest.fail(f"Failed to execute {file}")


if __name__ == "__main__":
    print(
        "ERROR: This test must be run with `pytest`. Try "
        "`uv run pytest tests/test_examples.py`."
    )
    sys.exit(1)
