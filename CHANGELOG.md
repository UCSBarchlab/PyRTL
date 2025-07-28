# Changelog

All notable changes to this project will be documented in this file. Only
releases published to PyPI are tracked here. No release candidates!

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.12] - 2025-07-28

### Added

- [`GateGraph`](https://pyrtl.readthedocs.io/en/latest/blocks.html#module-pyrtl.gate_graph) is an alternative PyRTL logic representation, designed to simplify analysis.

### Changed

- Rewrote [`output_to_verilog`](https://pyrtl.readthedocs.io/en/latest/export.html#pyrtl.output_to_verilog) and [`output_verilog_testbench`](https://pyrtl.readthedocs.io/en/latest/export.html#pyrtl.output_verilog_testbench). The new implementation's output should be much easier to read:
  - Single-use expressions are inlined.
  - Try mangling unusable `WireVector` and `MemBlock` names first, before assigning them entirely new names.
  - Add comments to the generated Verilog that show the un-mangled names.
- Many documentation improvements:
  - Most methods and functions now have examples.
  - Consistently use canonical top-level `pyrtl.*` names, rather than module-level names (`pyrtl.WireVector`, not `pyrtl.wire.WireVector`).
  - Enabled `intersphinx` for clickable standard library references (`list`, `dict`, etc).
  - Set up `doctest` for examples, to verify that documentation examples still work.
- Switched from `pylint` and `pycodestyle` to `ruff`:
  - Applied many `ruff` fixes.
  - Reformatted the code with `ruff format`.
  - Updated `tox` to run `ruff check` and `ruff format`.

### Removed

- Removed remaining Python 2 support.

### Fixed

- Fixed XOR implementation in `and_inverter_synth` pass ([@EdwinChang24](https://github.com/EdwinChang24))
- `output_verilog_testbench` should not re-initialize RomBlocks.
- `FastSimulation` was not setting `init_memvalue` correctly (renamed to `SimulationTrace.memory_value_map`).
- Specify bitwidths for Verilog initial register and memory values. They were previously unsized constants, which are implicitly 32-bit signed, which could cause surprises.

## [0.11.3] - 2025-06-12

### Added

- An optimization pass to [optimize inverter chains](https://github.com/UCSBarchlab/PyRTL/blob/d5f8dbe53f54e61e1d54722449e4894b885243c7/pyrtl/passes.py#L130) ([@gaborszita](https://github.com/gaborszita))
- `one_hot_to_binary` encoder ([documentation](https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.one_hot_to_binary)) ([@vaaniarora](https://github.com/vaaniarora))
- `binary_to_one_hot` decoder ([documentation](https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.binary_to_one_hot)) ([@vaaniarora](https://github.com/vaaniarora))

### Changed

- More support for signed integers: Signed integers can now be used in `RomBlock`'s
  `romdata`, `Simulation`'s `mem_value_map`
  - And Verilog-style register reset values ([@PrajwalVandana](https://github.com/PrajwalVandana))
- Improved documentation:
  - [conditional_assignment](https://pyrtl.readthedocs.io/en/latest/basic.html#module-pyrtl.conditional)
  - [WireVector equality](https://pyrtl.readthedocs.io/en/latest/basic.html#wirevector-equality)

### Fixed

- Use iteration instead of recursion to avoid stack overflow in `find_producer` ([@gaborszita](https://github.com/gaborszita))

## [0.11.2] - 2024-07-16

### Added

- Added an `initialize_registers` option to `output_to_verilog`
  ([documentation](https://pyrtl.readthedocs.io/en/latest/export.html#pyrtl.output_to_verilog))

### Changed

- Improved handling of signed integers.

### Fixed

- Fixed a `wire_matrix` bug involving single-element matrices of `Inputs` or `Registers`.

## [0.11.1] - 2024-04-22

### Added

- Named `WireVector` slices with `wire_struct` and `wire_matrix`. See documentation:
  - [wire_struct](https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.wire_struct)
  - [wire_matrix](https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.wire_matrix)

### Changed

- Major changes to `render_trace` visualization. See [examples and documentation](https://pyrtl.readthedocs.io/en/latest/simtest.html#wave-renderer)
- Many documentation and release process improvements.

### Fixed

- Python 3.11 compatibility.

### Removed

- Python 2.7 support.
