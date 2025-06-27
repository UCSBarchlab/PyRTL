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

Most of PyRTL's documentation is automatically extracted from Python
docstrings, see [docstring
formating](https://www.sphinx-doc.org/en/master/usage/domains/python.html) for
supported directives and fields. Sphinx parses [Python type
annotations](https://docs.python.org/3/library/typing.html), so put type
information in annotations instead of docstrings.

Follow the instructions on this page to build a local copy of PyRTL's
documentation. This is useful for verifying that PyRTL's documentation still
renders correctly after making a local change.

There is additional PyRTL documentation in the [`gh-pages`
branch](https://github.com/UCSBarchlab/PyRTL/tree/gh-pages). This additional
documentation is pushed to https://ucsbarchlab.github.io/PyRTL/ by the
`pages-build-deployment` GitHub Action. This additional documentation is
written HTML and is not described further in this README.

## Testing Documentation Examples

PyRTL's documentation contains many examples that are tested with
[`doctest`](https://docs.python.org/3/library/doctest.html). It is important to
test these examples so we can be sure that they keep working as we change the
code. These tests run via test fixtures called `TestDocTest`, see the example
in
[`test_core.py`](https://github.com/UCSBarchlab/PyRTL/blob/development/tests/test_core.py).

When adding a new `doctest`, you'll need to to add a preceding comment block
that imports PyRTL and resets the working block before running your new
`doctest`. This comment block contains additional code necessary for `doctest`
to successfully run the test, but the lines are commented out because they are
not worth showing in every example. These blocks look like:

```
.. doctest only::

    >>> import pyrtl
    >>> pyrtl.reset_working_block()
```

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
$ pip install --upgrade -r docs/requirements.txt
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
