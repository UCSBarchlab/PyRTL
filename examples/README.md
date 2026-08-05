# PyRTL's Examples

PyRTL's examples are Python scripts that demonstrate various PyRTL features.

These scripts can be run with:

```shell
$ uv run $SCRIPT_FILE
```

or interactively with:

```shell
uv run python3 -i $SCRIPT_FILE
```

PyRTL has examples in two directories:
[`examples`](https://github.com/UCSBarchlab/PyRTL/tree/development/examples)
and
[`www/examples`](https://github.com/UCSBarchlab/PyRTL/tree/development/www/examples).

## Generating Jupyter Notebooks

Each example script is automatically converted to a Jupyter notebook in a
corresponding `ipynb-examples` directory,
[`ipynb-examples`](https://github.com/UCSBarchlab/PyRTL/tree/development/ipynb-examples)
and
[`www/ipynb-examples`](https://github.com/UCSBarchlab/PyRTL/tree/development/www/ipynb-examples).
[`examples/tools/to_ipynb.py`](https://github.com/UCSBarchlab/PyRTL/blob/development/examples/tools/to_ipynb.py)
does these automatic conversions. Do not manually edit the generated Jupyter
notebooks! Any manual changes will be lost the next time someone runs
`to_ipynb.py`.

If you update an example script, re-run `to_ipynb.py` to update its
corresponding Jupyter notebook. This process is automated with
[`examples/Makefile`](https://github.com/UCSBarchlab/PyRTL/blob/development/examples/Makefile)
and
[`www/examples/Makefile`](https://github.com/UCSBarchlab/PyRTL/blob/development/www/examples/Makefile).
Running `make` in these directories will re-generate Jupyter notebooks for any
modified examples in their `examples` directory.
