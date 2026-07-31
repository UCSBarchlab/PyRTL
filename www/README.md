# PyRTL's GitHub Pages Webpage

PyRTL's GitHub Pages webpage is at https://ucsbarchlab.github.io/PyRTL/ .

The sources for this webpage are in this `www` directory. The page is built
with [Sphinx](https://www.sphinx-doc.org/en/master/), and written in
[reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html).
The main Sphinx configuration file is
[`www/conf.py`](https://github.com/UCSBarchlab/PyRTL/blob/development/www/conf.py),
and source for the main page is
[`www/index.rst`](https://github.com/UCSBarchlab/PyRTL/blob/development/www/index.rst)

Follow the instructions on this page to build a local copy of PyRTL's webpage.
This is useful for verifying that PyRTL's webpage still renders correctly after
making a local change.

There is additional PyRTL documentation in [Read the
Docs](https://pyrtl.readthedocs.io/), see
[`docs/README.md`](https://github.com/UCSBarchlab/PyRTL/blob/development/docs/README.md).

## Running Sphinx

Run Sphinx with the provided
[`justfile`](https://github.com/UCSBarchlab/PyRTL/blob/development/justfile),
from the repository's root directory:

```shell
# Run Sphinx to build PyRTL's webpage.
$ uv run just www
```

This builds a local copy of PyRTL's webpage in `www/_build/html`.
`www/_build/html/index.html` is the home page.

## GitHub Actions Workflow

When a commit is pushed that changes `www/`, the
[`pages-deploy`](https://github.com/UCSBarchlab/PyRTL/blob/development/.github/workflows/pages-deploy.yml)
workflow automatically runs Sphinx to regenerate the webpage and deploy it to
GitHub Pages.
