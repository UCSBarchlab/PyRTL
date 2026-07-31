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

There is additional PyRTL documentation in [GitHub
Pages](https://ucsbarchlab.github.io/PyRTL/), see
[`www/README.md`](https://github.com/UCSBarchlab/PyRTL/blob/development/www/README.md).

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

## Running Sphinx

Run Sphinx with the provided
[`justfile`](https://github.com/UCSBarchlab/PyRTL/blob/development/justfile),
from the repository's root directory:

```shell
# Run Sphinx to build PyRTL's documentation.
$ uv run just docs
```

This builds a local copy of PyRTL's documentation in `docs/_build/html`.
`docs/_build/html/index.html` is the home page.

## Screenshots

PyRTL is difficult to screenshot consistently, because it typically runs in a
terminal window, and we rarely want to capture the whole window. To make our
screenshots more consistent, we post-process them with `ImageMagick`, automated
with `docs/screenshots/Makefile`:

```shell
$ make -C docs/screenshots
```

When including screenshots into documentation, we must set the image's width
relative to the page's text size, because our screenshots typically contain
text, and the screenshot's text should be about the same size as the page's
surrounding text. We can't assume the surrounding text has a fixed pixel size,
because that depends on factors beyond our control, such as the reader's
display hardware and their browser zoom level.

To compensate, we manually set each screenshot's `:width:` in reStructuredText.
To compute the proper `:width:`, take the width of the screenshot's text in
characters (`">>> sim.tracer.render_trace()"` is 29 characters, for example),
add two (for the uniform borders added by `ImageMagick`), then divide by two.
Set width to `:width: {n}em`, where `{n}` is the computed number (`{n}` is `15`
for the example).

PyRTL's current screenshots were taken in the Ghostty terminal, with 15-point
"JetBrains Mono", using the "Peppermint" theme, with ligatures disabled.
