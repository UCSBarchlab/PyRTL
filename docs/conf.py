# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import inspect
import os
import subprocess
import sys

import pyrtl

sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------

project = "PyRTL"
copyright = "2026, Timothy Sherwood"
author = "Timothy Sherwood"

# -- General configuration ---------------------------------------------------

master_doc = "index"

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.intersphinx",
    "sphinx.ext.linkcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
]

graphviz_output_format = "svg"

# Omit redundant method names in right sidebar (step() instead of Simulation.step()).
toc_object_entries_show_parents = "hide"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Enable links to Python standard library classes (str, list, dict, etc).
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# sphinx_copybutton excludes line numbers, prompts, and outputs.
copybutton_exclude = ".linenos, .gp, .go"

# sphinx-autodoc-typehints configuration: Always display Unions with vertical bars,
# show default values, and don't document :rtype: None.
always_use_bars_union = True
typehints_defaults = "comma"
typehints_document_rtype_none = False

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_baseurl = "https://pyrtl.readthedocs.io/en/latest"
html_extra_path = ["html_root"]
html_theme = "furo"
html_theme_options = {
    "sidebar_hide_name": True,
    # For view/edit this page buttons.
    "source_repository": "https://github.com/UCSBarchlab/pyrtl",
    "source_branch": "development",
    "source_directory": "docs/",
    # Add a GitHub repository link to the footer.
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/UCSBarchlab/pyrtl",
            "html": """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
            """,  # noqa: E501
            "class": "",
        },
    ],
}
html_logo = "brand/pyrtl_logo.png"

# Force a light blue background color for inheritance-diagrams. The default is
# transparent, which does not work well with Furo's dark mode.
inheritance_graph_attrs = {
    "bgcolor": "aliceblue",
}

# -- linkcode_resolve --------------------------------------------------------

# linkcode generates GitHub "[source]" links for documentation. linkcode_resolve returns
# a GitHub link for a documented item (class, method, object, etc).
#
# Based on https://gist.github.com/rainbowphysics/505e35a7a1e9545d5a6cde22f6ca9558, with
# some hacks to support PyRTL's top-level globals `conditional_assignment` and
# `otherwise`.

# Link to your GitHub repo here:
REPO_LINK = "https://github.com/UCSBarchlab/PyRTL"
# Specify main branch
MAIN_BRANCH = "development"


def run_git_command(cmd: str) -> str | None:
    try:
        # Run command and get the output
        output: str = subprocess.check_output(cmd.split()).strip().decode("utf-8")

        # In case command failed, return None
        if output.startswith("fatal:"):
            return None

        # Return the raw command output
        return output
    except subprocess.CalledProcessError:
        return None


# lock to current commit number
head_commit = run_git_command("git log -n1 --pretty=%H")
if head_commit is not None:
    linkcode_revision = head_commit

    # if we are on main's HEAD, use main as reference instead
    main_head_commit = run_git_command(
        f"git log --first-parent {MAIN_BRANCH} -n1 --pretty=%H"
    )
    if head_commit == main_head_commit:
        linkcode_revision = MAIN_BRANCH

    # if we have a tag, use tag as reference
    tag = run_git_command(f"git describe --exact-match --tags {linkcode_revision}")
    if tag is not None:
        linkcode_revision = tag

else:
    # If for some reason git command didn't work then default to main branch
    linkcode_revision = MAIN_BRANCH


def get_line_range(obj):
    source, lineno = inspect.getsourcelines(obj)
    return lineno, lineno + len(source) - 1


def get_link_info(
    modname: str, fullname: str
) -> tuple[str, tuple[int, int]] | tuple[str, None]:
    # Fallback in case git repo is missing or malformed, or another error occurs
    fallback = modname.replace(".", "/")

    # Get module based on module name
    module = sys.modules.get(modname)
    if module is None:
        return fallback, None

    repo_main_folder = run_git_command("git rev-parse --show-toplevel")
    if repo_main_folder is None:
        return fallback, None

    parent_obj = None
    obj = module
    for part in fullname.split("."):
        next_obj = getattr(obj, part, None)
        if next_obj is None:
            parent_obj = obj
            obj = part
        else:
            parent_obj = obj
            obj = next_obj

    if isinstance(obj, property):
        obj = obj.fget

    try:
        src_file = inspect.getsourcefile(obj)
    except TypeError:
        src_file = inspect.getsourcefile(parent_obj)

    # Special cases for `pyrtl.conditional_assignment` and `pyrtl.otherwise`.
    conditional_assignment = False
    if obj is pyrtl.conditional_assignment or obj is pyrtl.otherwise:
        conditional_assignment = True
        parent_obj = pyrtl.conditional
        src_file = inspect.getsourcefile(parent_obj)

    filepath = os.path.relpath(src_file, repo_main_folder)

    try:
        source, lineno = inspect.getsourcelines(obj)
        linestart, linestop = lineno, lineno + len(source) - 1
    except OSError:
        return filepath, None
    except TypeError:
        source, lineno = inspect.getsourcelines(parent_obj)
        found_in_source = False
        for idx, line in enumerate(source):
            if line.lstrip().startswith(fullname.split(".")[-1]):
                linestart = lineno + idx
                if conditional_assignment:
                    linestart = linestart + 1
                linestop = linestart
                found_in_source = True
                break

        if not found_in_source:
            return filepath, None

    return filepath, (linestart, linestop)


def linkcode_resolve(domain, info):
    if domain != "py" or not info["module"]:
        return None

    filepath, linenos = get_link_info(info["module"], info["fullname"])
    result = f"{REPO_LINK}/blob/{linkcode_revision}/{filepath}"
    if linenos is not None:
        linestart, linestop = linenos
        result += f"#L{linestart}-L{linestop}"

    return result
