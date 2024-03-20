# Minimal makefile for Sphinx documentation.

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Route the 'html' target to Sphinx using the "make mode" option.  $(O) is
# meant as a shortcut for $(SPHINXOPTS).
html: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

requirements.txt: requirements.in FORCE
	pip-compile --upgrade requirements.in

FORCE:
