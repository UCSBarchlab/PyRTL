# PyRTL's Documentation

PyRTL's documentation is published to [Read the Docs](https://readthedocs.org/)
at https://pyrtl.readthedocs.io/ . There is a
[build dashboard](https://readthedocs.org/projects/pyrtl/builds/)
and the main configuration file is
[`.readthedocs.yaml`](https://github.com/UCSBarchlab/PyRTL/blob/development/.readthedocs.yaml)
in the repository's root directory.

PyRTL's documentation is in this `docs` directory. It is built with
[Sphinx](https://www.sphinx-doc.org/en/master/), and written in
[reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html).
The main Sphinx configuration file is
[`docs/conf.py`](https://github.com/UCSBarchlab/PyRTL/blob/development/docs/conf.py).

Most of PyRTL's documentation is automatically extracted from Python docstrings, see
[docstring formating](https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#signatures) for supported directives and fields.

Follow the instructions on this page to build a local copy of PyRTL's
documentation. This is useful for verifying that PyRTL's documentation still
renders correctly after making a local change.

There is additional PyRTL documentation in the
[`gh-pages` branch](https://github.com/UCSBarchlab/PyRTL/tree/gh-pages).
This additional documentation is pushed to https://ucsbarchlab.github.io/PyRTL/
by the `pages-build-deployment` GitHub Action. The additional documentation is
written in [GitHub MarkDown](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax),
and is not described further in this README.

## Installing Sphinx

Sphinx and its dependencies are all pinned to specific versions for
[reproducible documentation builds](https://docs.readthedocs.io/en/stable/guides/reproducible-builds.html).
This avoids problems where documentation builds randomly fail due to bugs or
incompatibilities in the newest version of Sphinx or one of its
dependencies.

Use of an environment manager like [`conda`](https://docs.conda.io/en/latest/)
or [`virtualenv`](https://virtualenv.pypa.io/en/latest/) is strongly
recommended. To install Sphinx locally, run the following commands from the
repository root:

```shell
# Install Sphinx.
$ pip install -r docs/requirements.txt
```

## Installing Graphviz

[Install graphviz](https://www.graphviz.org/download/#executable-packages). Use
of a package manager like
[`apt`](https://ubuntu.com/server/docs/package-management) or
[`brew`](https://brew.sh/) is strongly recommended. Instructions vary depending
on your operating system, see the installation link for details.

## Running Sphinx

Run Sphinx with the provided [`docs/Makefile`](https://github.com/UCSBarchlab/PyRTL/blob/development/docs/Makefile):

```shell
# Run Sphinx to build PyRTL's documentation.
$ make -C docs
```

A local copy of PyRTL's documentation should be available in
`docs/_build/html`. `docs/_build/html/index.html` is the home page.

## Updating Sphinx

To update the pinned version of Sphinx, run

```shell
# Run pip-compile to generate docs/requirements.txt from docs/requirements.in.
$ make -C docs requirements.txt
```

It's a good idea to update the pinned version of Sphinx whenever you update the
documentation.
