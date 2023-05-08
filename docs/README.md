# Building PyRTL's Documentation

## Install Sphinx

Sphinx and its dependencies are all pinned to specific versions for [reproducible documentation builds](https://docs.readthedocs.io/en/stable/guides/reproducible-builds.html). Use of an environment manager like `conda` or `virtualenv` is strongly recommende. Run the following commands from the repository root:

```shell
# Install Sphinx.
$ pip install -r docs/requirements.txt
```

## Install Graphviz

[Install graphviz](https://www.graphviz.org/download/#executable-packages). Instructions vary depending on your operating system, see the installation link
for details.

## Run Sphinx

```shell
# Run Sphinx to build PyRTL's documentation.
$ make -C docs
```

The documentation should be available in `docs/_build/html`.

## Updating Sphinx

To update the pinned version of Sphinx, run

```shell
# Run pip-compile to update requirements.txt.
$ make -C docs requirements.txt
```
