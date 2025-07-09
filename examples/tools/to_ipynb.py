"""Convert a PyRTL example script to a Jupyter notebook.

Usage::

    python to_ipynb.py example1-combologic.py example1-combologic.ipynb

This converts comment blocks to Markdown cells, and code blocks to code cells, with some
PyRTL-specific transformations:

- Add `%pip install` magic to install PyRTL in the notebook environment.

- Add a `reset_working_block()` call to reset PyRTL's state when re-running the
  notebook.

- Convert some code references to documentation hyperlinks. For example, `WireVector`
  will be replaced with
  [WireVector](https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.WireVector).

- Convert indented comments to Markdown code blocks::

      #     def foo(bar):
      #         pass

  will be converted to::

      ```python
      def foo(bar):
          pass
      ```

Note the five spaces between `#` and `def`. We could instead write these code links and
code blocks directly in the source example scripts, but that would make the scripts
harder to read outside of a Jupyter notebook.

The transformation is very simple, and many edge cases are not handled. For example, any
line with a `#` character in column 0 is considered a comment, even if that line occurs
within a triple-quoted block.
"""

import argparse
import json

# Map from link anchor text to link target. This will be used to create hyperlinks for
# code references in the generated Jupyter notebook.
_link_map = {
    "Block": "https://pyrtl.readthedocs.io/en/latest/blocks.html#pyrtl.Block",
    "Const": "https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.Const",
    "Input": "https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.Input",
    "MemBlock": "https://pyrtl.readthedocs.io/en/latest/regmem.html#pyrtl.MemBlock",
    "Output": "https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.Output",
    "Register": "https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.Register",
    "RomBlock": "https://pyrtl.readthedocs.io/en/latest/regmem.html#pyrtl.RomBlock",
    "Simulation": "https://pyrtl.readthedocs.io/en/latest/simtest.html#pyrtl.Simulation",
    "SimulationTrace": "https://pyrtl.readthedocs.io/en/latest/simtest.html#pyrtl.SimulationTrace",
    "WireVector": "https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.WireVector",
    "concat()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.concat",
    "conditional_assignment": "https://pyrtl.readthedocs.io/en/latest/basic.html#conditional-assignment",
    "input_from_blif()": "https://pyrtl.readthedocs.io/en/latest/export.html#pyrtl.input_from_blif",
    "kogge_stone()": "https://pyrtl.readthedocs.io/en/latest/rtllib.html#pyrtl.rtllib.adders.kogge_stone",
    "mux()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.mux",
    "otherwise": "https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.otherwise",
    "output_to_svg()": "https://pyrtl.readthedocs.io/en/latest/export.html#pyrtl.block_to_svg",
    "output_to_trivialgraph()": "https://pyrtl.readthedocs.io/en/latest/export.html#pyrtl.output_to_trivialgraph",
    "output_verilog_testbench()": "https://pyrtl.readthedocs.io/en/latest/export.html#pyrtl.output_verilog_testbench",
    "probe()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.probe",
    "render_trace()": "https://pyrtl.readthedocs.io/en/latest/simtest.html#pyrtl.SimulationTrace.render_trace",
    "reset_working_block()": "https://pyrtl.readthedocs.io/en/latest/blocks.html#pyrtl.reset_working_block",
    "set_debug_mode()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.set_debug_mode",
    "sign_extended()": "https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.WireVector.sign_extended",
    "signed_add()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.signed_add",
    "signed_lt()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.signed_lt",
    "signed_mult()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.signed_mult",
    "signed_sub()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.signed_sub",
    "step()": "https://pyrtl.readthedocs.io/en/latest/simtest.html#pyrtl.Simulation.step",
    "step_multiple()": "https://pyrtl.readthedocs.io/en/latest/simtest.html#pyrtl.Simulation.step_multiple",
    "synthesize()": "https://pyrtl.readthedocs.io/en/latest/analysis.html#pyrtl.synthesize",
    "tree_multiplier()": "https://pyrtl.readthedocs.io/en/latest/rtllib.html#pyrtl.rtllib.multipliers.tree_multiplier",
    "truncate()": "https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.WireVector.truncate",
    "val_to_signed_integer()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.val_to_signed_integer",
    "wire_matrix()": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.wire_matrix",
    "wire_struct": "https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.wire_struct",
    "working_block()": "https://pyrtl.readthedocs.io/en/latest/blocks.html#pyrtl.working_block",
    "zero_extended()": "https://pyrtl.readthedocs.io/en/latest/basic.html#pyrtl.WireVector.zero_extended",
}


# Convert _link_map to _replacement_map, which will be used for search-and-replace. This
# converts all the link anchor text that we search for to Markdown `code format`, and
# creates Markdown links for the replacement text. This also adds plurals to the
# _replacement_map, for example `WireVectors` will be linked to pyrtl.WireVector.
def _make_replacement_map(link_map: dict[str, str]) -> dict[str, str]:
    replacement_map = {}
    for anchor, target in link_map.items():
        replacement_map[f"`{anchor}`"] = f"[{anchor}]({target})"
        replacement_map[f"`{anchor}s`"] = f"[{anchor}s]({target})"
    return replacement_map


_replacement_map = _make_replacement_map(_link_map)

# Template for markdown cells. "source" will be added later, and it will contain the
# actual contents of the Markdown cell.
_markdown_template = {
    "cell_type": "markdown",
    "metadata": {},
}

# Template for code cells. "source" will be added later, and it will contain the actual
# contents of the code cell.
_code_template = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {"collapsed": True},
    "outputs": [],
}

# ipynb metadata.
_metadata = {
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.6.4",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 2,
}


def to_ipynb(source_name: str, target_name: str):
    """Create a Jupyter notebook from a Python script.

    Comment blocks will be converted to markdown cells, and code blocks will be
    converted to code cells.

    :param source_name: Name of the Python script to convert.
    :param target_name: Name of the Jupyter notebook to generate.
    """
    # Collection of all markdown and code cells.
    cells = []
    # Current markdown cell contents. This will be the value for the markdown cell's
    # "source" key. If this is nonempty, `current_code_source` should be empty.
    current_markdown_source = []
    # Current code cell contents. This will be the valued for the code cell's "source"
    # key. If this is nonempty, `current_markdown_source` should be empty.
    current_code_source = []
    # Becomes True after emitting a code cell containing `import` statements.
    found_imports = False
    # Current code block within a markdown cell. Will be appended to
    # `current_markdown_source`, as a markdown code block.
    current_markdown_code_block = []

    def _emit_code():
        """Create a code cell for `current_code_source`, if necessary."""
        nonlocal current_code_source, found_imports
        if len(current_code_source) > 0:
            # Remove any trailing blank lines from the code cell.
            while current_code_source[-1].rstrip() == "":
                current_code_source = current_code_source[:-1]

                for code_line in current_code_source:
                    if not found_imports and (
                        code_line.startswith("import pyrtl")
                        or code_line.startswith("from pyrtl")
                    ):
                        found_imports = True
                        pip_packages = "pyrtl"
                        if "verilog" in source_name:
                            pip_packages = "pyrtl pyparsing"

                        current_code_source = [
                            f"%pip install {pip_packages}\n",
                            "\n",
                            *current_code_source,
                            "\n",
                            "pyrtl.reset_working_block()\n",
                        ]
                        break

            cells.append(_code_template | {"source": current_code_source})
            current_code_source = []

    def _emit_markdown_code_block():
        """Add a code block within `current_markdown_source`, if necessary."""
        nonlocal current_markdown_code_block
        if len(current_markdown_code_block) > 0:
            current_markdown_source.extend(
                ["```python\n", *current_markdown_code_block, "```\n"]
            )
            current_markdown_code_block = []

    def _emit_markdown():
        """Create a markdown cell for `current_markdown_source`, if necessary."""
        nonlocal current_markdown_source
        _emit_markdown_code_block()
        if len(current_markdown_source) > 0:
            cells.append(_markdown_template | {"source": current_markdown_source})
            current_markdown_source = []

    with open(source_name) as source_file:
        for current_line in source_file:
            if current_line.startswith("#"):
                # `current_line` is a comment. Append contiguous comment lines to
                # `current_markdown_source` or `current_markdown_code_block`.
                _emit_code()
                # Drop the "#" at the start of the line.
                current_line = current_line[1:]

                if current_line.startswith("     "):
                    # Current line starts or extends a code block.
                    current_markdown_code_block.append(current_line[5:])
                else:
                    _emit_markdown_code_block()
                    for old, new in _replacement_map.items():
                        current_line = current_line.replace(old, new)
                    current_markdown_source.append(current_line)

            elif current_line.rstrip() == "":
                if len(current_markdown_code_block) > 0:
                    # In a code block, a blank line extends the code block.
                    current_markdown_code_block.append(current_line)
                elif len(current_markdown_source) > 0:
                    # In a markdown cell, a blank line ends the markdown cell.
                    _emit_markdown()
                elif len(current_code_source) > 0:
                    # In a code cell, a blank line extends the code cell.
                    current_code_source.append(current_line)

            else:
                # Else `current_line` is code. Add it to `current_code_source`.
                _emit_markdown()
                current_code_source.append(current_line)

    # Emit any remaining cell data.
    _emit_markdown()
    _emit_code()

    # Generate the .ipynb file.
    ipynb = {"cells": cells} | _metadata
    with open(target_name, "w") as target_file:
        json.dump(ipynb, target_file, indent=1)


def main():
    parser = argparse.ArgumentParser(prog="to_ipynb.py")
    parser.add_argument("source_name", type=str)
    parser.add_argument("target_name", type=str)
    args = parser.parse_args()

    to_ipynb(args.source_name, args.target_name)


if __name__ == "__main__":
    main()
