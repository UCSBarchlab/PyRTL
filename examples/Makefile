PYTHON := uv run
TO_IPYNB := tools/to_ipynb.py
PY_FILES := $(wildcard example*.py) introduction-to-hardware.py
IPYNB_FILES := $(addprefix ../www/, $(PY_FILES:.py=.ipynb))

all: $(IPYNB_FILES)

# Convert a PyRTL example Python script to a Jupyter notebook.
../ipynb-examples/%.ipynb: %.py $(TO_IPYNB)
	$(PYTHON) $(TO_IPYNB) $< $@
