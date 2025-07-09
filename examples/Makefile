PYTHON=python
PY_FILES=$(wildcard *.py)
IPYNB_FILES=$(addprefix ../ipynb-examples/, $(PY_FILES:.py=.ipynb))

all: $(IPYNB_FILES)

# Convert a PyRTL example Python script to a Jupyter notebook.
../ipynb-examples/%.ipynb: %.py tools/to_ipynb.py
	$(PYTHON) tools/to_ipynb.py $< $@
