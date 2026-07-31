# PyRTL uses `just` instead of `make` because:
# * `make` is not installed by default on Windows.
# * `uv` can install `just` on all supported platforms from PyPI.

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

presubmit: tests docs www

tests:
        # Run `pytest` with the latest version of Python supported by PyRTL,
        # which is the default for `uv`. The default is set with `uv python
        # pin` and written to `.python_version`.
        uv run pytest -rsx -n auto --cov=pyrtl --cov-report=xml

        # Run `pytest` in an isolated virtual environment, with the earliest
        # version of Python supported by PyRTL.
        uv run --python=3.10 --isolated pytest -rsx -n auto

        # Run `ruff format` to check that code is formatted properly.
        #
        # If this fails, try running
        #
        # $ uv run ruff format
        #
        # to automatically reformat any changed code.
        uv run ruff format --diff

        # Run `ruff check` to check for lint errors.
        #
        # If this fails, try running
        #
        # $ uv run ruff check --fix
        #
        # to automatically apply fixes, when possible.
        uv run ruff check

docs:
        # Run `sphinx-build` to generate documentation.
        #
        # Output: docs/_build/html/index.html
        uv run sphinx-build -M html docs/ docs/_build

www:
        # Run `sphinx-build` to generate github.io webpage.
        #
        # Output: www/_build/html/index.html
        uv run sphinx-build -M html www/ www/_build
