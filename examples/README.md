# PyRTL's Examples

PyRTL's examples are Python scripts that demonstrate various PyRTL features.
These scripts can be run with `python $SCRIPT_FILE_NAME`.

Each script is converted to an equivalent Jupyter notebook in the
`ipynb-examples` directory. These conversions are done by the `to_ipynb.py`
script in the `examples/tools` directory.

If you update an example script, be sure to update its corresponding Jupyter
notebook. These updates are handled by the `Makefile` in this directory, so all
Jupyter notebooks can be updated by running `make`.
