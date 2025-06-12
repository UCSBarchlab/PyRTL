# Changelog

All notable changes to this project will be documented in this file. Only
releases published to PyPI are tracked here. No release candidates!

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.11.3] - 2025-06-12

### Added

- An optimization pass to [optimize inverter chains](https://github.com/UCSBarchlab/PyRTL/blob/d5f8dbe53f54e61e1d54722449e4894b885243c7/pyrtl/passes.py#L130)
- `one_hot_to_binary` encoder ([documentation](https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.helperfuncs.one_hot_to_binary))
- `binary_to_one_hot` decoder ([documentation](https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.helperfuncs.binary_to_one_hot))

### Changed

- More support for signed integers: Signed integers can now be used in `RomBlock`'s
  `romdata`, `Simulation`'s `mem_value_map`, and Verilog-style register reset values.
- Improved documentation:
  - [conditional_assignment](https://pyrtl.readthedocs.io/en/latest/basic.html#module-pyrtl.conditional)
  - [WireVector equality](https://pyrtl.readthedocs.io/en/latest/basic.html#wirevector-equality)

### Fixed

- Use iteration instead of recursion to avoid stack overflow in `find_producer`.

## [0.11.2] - 2024-07-16

### Added

- Added an `initialize_registers` option to `output_to_verilog`
  ([documentation](https://pyrtl.readthedocs.io/en/latest/export.html#pyrtl.importexport.output_to_verilog))

### Changed

- Improved handling of signed integers.

### Fixed

- Fixed a `wire_matrix` bug involving single-element matrices of `Inputs` or `Registers`.

## [0.11.1] - 2024-04-22

### Added

- Named `WireVector` slices with `wire_struct` and `wire_matrix`. See documentation:
  - [wire_struct](https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.helperfuncs.wire_struct)
  - [wire_matrix](https://pyrtl.readthedocs.io/en/latest/helpers.html#pyrtl.helperfuncs.wire_matrix)

### Changed

- Major changes to `render_trace` visualization. See [examples and
  documentation](https://pyrtl.readthedocs.io/en/latest/simtest.html#wave-renderer)
- Many documentation and release process improvements.

### Fixed

- Python 3.11 compatibility.

### Removed

- Python 2.7 support.
