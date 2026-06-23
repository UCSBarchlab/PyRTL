# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------

project = "PyRTL"

# -- General configuration ---------------------------------------------------

master_doc = "index"

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "jupyterlite_sphinx",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    "sphinx_design",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["examples", "ipynb-examples", "_build", "Thumbs.db", ".DS_Store"]

# Enable links to Python standard library classes (str, list, dict, etc).
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pyrtl": ("https://pyrtl.readthedocs.io/en/latest/", None),
}

jupyterlite_contents = "../ipynb-examples"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_baseurl = "https://ucsbarchlab.github.io/PyRTL"
html_theme = "alabaster"
html_theme_options = {
    "font_family": '"Open Sans", "Helvetica Neue", Helvetica, Arial, sans-serif',
    "code_font_family": 'Consolas, "Liberation Mono", Menlo, Courier, monospace',
    "font_size": "1.1rem",
    "body_text": "#606c71",
    "link": "#1e6bb8",
}
html_title = "Home"
html_show_sphinx = False
html_show_copyright = False
html_show_sourcelink = False
html_static_path = ["_static"]
html_css_files = ["custom.css"]
