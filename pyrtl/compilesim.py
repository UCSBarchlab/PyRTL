from __future__ import annotations

import _ctypes
import ctypes
import platform
import shutil
import subprocess
import tempfile
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from os import path
from typing import TextIO

from pyrtl.core import Block, working_block
from pyrtl.helperfuncs import infer_val_and_bitwidth
from pyrtl.memory import MemBlock, RomBlock
from pyrtl.pyrtlexceptions import PyrtlError, PyrtlInternalError
from pyrtl.simulation import (
    ConsecutiveSlice,
    SimulationTrace,
    _trace_sort_key,
    make_consecutive_slices,
    shift,
)
from pyrtl.wire import Const, Input, Output, Register, WireVector

__all__ = ["CompiledSimulation"]


class DllMemInspector(Mapping):
    """Dictionary-like access to a hashmap in a CompiledSimulation."""

    def __init__(self, sim, mem):
        self._addr_width = mem.addrwidth
        self._limbs = sim._limbs(mem)
        self._var_name = var_name = sim.var_names[mem]
        self._mem = ctypes.c_void_p.in_dll(sim._dll, var_name)
        self._sim = sim  # keep reference to avoid freeing dll

    def __getitem__(self, index):
        array = self._sim._mem_lookup(self._mem, index)
        value = 0
        for limb in reversed(range(self._limbs)):
            value = (value << 64) | array[limb]
        return value

    def __iter__(self):
        return iter(range(len(self)))

    def __len__(self):
        return 1 << self._addr_width

    def __eq__(self, other):
        if (
            isinstance(other, DllMemInspector)
            and self._sim is other._sim
            and self._var_name == other._var_name
        ):
            return True
        return all(self[x] == other.get(x, 0) for x in self)

    def __hash__(self):
        return hash(self._sim) ^ hash(self._var_name)


class CompiledSimulation:
    """Simulate a block by generating, compiling, and running C code.

    ``CompiledSimulation`` provides significant execution speed improvements over
    :class:`FastSimulation`, at the cost of even longer start-up time. Generally this
    will do better than :class:`FastSimulation` for simulations requiring over 1000
    steps.

    ``CompiledSimulation`` is not built to be a debugging tool, though it may help with
    debugging. Note that only :class:`Input` and :class:`Output` wires can be traced
    with ``CompiledSimulation``.

    .. note::

        For very large circuits, :class:`FastSimulation` can sometimes be a better
        choice than ``CompiledSimulation`` because ``CompiledSimulation`` will generate
        an extremely large ``.c`` file, which can take prohibitively long to compile and
        optimize. :class:`FastSimulation` will generate an extremely large ``.py``
        file, but Python will interpret that generated code as needed, instead of trying
        to process all the generated code at once.

    .. WARNING::

        This code is still experimental, but has been used on designs of significant
        scale to good effect.

    To use ``CompiledSimulation``, you'll need:

    - A 64-bit processor

    - GCC (tested on version 4.8.4)

    - A 64-bit build of Python

    If using the multiplication operand, only some architectures are supported:

    - ``x86-64`` / ``amd64``

    - ``arm64`` / ``aarch64``

    - ``mips64`` (untested)

    ``default_value`` is currently only implemented for :class:`Registers<Register>`,
    not :class:`MemBlocks<MemBlock>`.

    ``CompiledSimulation`` is a drop-in replacement for :class:`Simulation`, so the two
    classes share the same interface. See :class:`Simulation` for interface
    documentation, and more details about PyRTL simulations.
    """

    def __init__(
        self,
        tracer: SimulationTrace = True,
        register_value_map: dict[Register, int] | None = None,
        memory_value_map: dict[MemBlock, dict[int, int]] | None = None,
        default_value: int = 0,
        block: Block = None,
    ):
        if memory_value_map is None:
            memory_value_map = {}
        if register_value_map is None:
            register_value_map = {}
        self._dll = self._dir = None
        self.block = working_block(block)
        self.block.sanity_check()

        if tracer is True:
            tracer = SimulationTrace()
        self.tracer = tracer
        self._remove_untraceable()

        self.default_value = default_value
        self._register_value_map = {}  # Updated below
        self._memory_value_map = memory_value_map
        self._uid_counter = 0
        self.var_names = {}  # Map from WireVectors and MemBlocks to C variable names.

        for reg in self.block.wirevector_subset(Register):
            reset_value = register_value_map.get(reg, reg.reset_value)
            if reset_value is None:
                reset_value = self.default_value
            self._register_value_map[reg] = reset_value

        self.tracer._set_initial_values(
            default_value, register_value_map, memory_value_map
        )

        self._create_dll()
        self._initialize_mems()

    def inspect_mem(self, mem: MemBlock) -> dict[int, int]:
        return DllMemInspector(self, mem)

    def inspect(self, wire_name: str) -> int:
        if isinstance(wire_name, WireVector):
            wire_name = wire_name.name
        try:
            vals = self.tracer.trace[wire_name]
        except KeyError:
            pass
        else:
            if not vals:
                msg = "No context available. Please run a simulation step"
                raise PyrtlError(msg)
            return vals[-1]
        msg = "CompiledSimulation does not support inspecting internal WireVectors"
        raise PyrtlError(msg)

    def step(self, provided_inputs: dict[str, int] | None = None, inputs=None):
        if provided_inputs is None:
            provided_inputs = {}
        if inputs is not None:
            warnings.warn(
                "CompiledSimulation.step: `inputs` was renamed to `provided_inputs`",
                DeprecationWarning,
                stacklevel=2,
            )
            provided_inputs = inputs
        self.run([provided_inputs])

    def step_multiple(
        self,
        provided_inputs: dict[str, list[int]] | None = None,
        expected_outputs: dict[str, int] | None = None,
        nsteps: int | None = None,
        file: TextIO | None = None,
        stop_after_first_error: bool = False,
    ):
        if expected_outputs is None:
            expected_outputs = {}
        if provided_inputs is None:
            provided_inputs = {}
        if not nsteps and len(provided_inputs) == 0:
            msg = "need to supply either input values or a number of steps to simulate"
            raise PyrtlError(msg)

        if len(provided_inputs) > 0:
            longest = max(provided_inputs.items(), key=lambda t: len(t[1]))
            provided_steps = len(longest[1])
            if nsteps:
                if nsteps > provided_steps:
                    msg = (
                        "nsteps is specified but is greater than the number of values "
                        "supplied for each input"
                    )
                    raise PyrtlError(msg)
            else:
                nsteps = provided_steps

        if nsteps < 1:
            msg = "must simulate at least one step"
            raise PyrtlError(msg)

        if list(filter(lambda value: len(value) < nsteps, provided_inputs.values())):
            msg = (
                "must supply a value for each provided wire for each step of simulation"
            )
            raise PyrtlError(msg)

        if list(filter(lambda value: len(value) < nsteps, expected_outputs.values())):
            msg = (
                "any expected outputs must have a supplied value each step of "
                "simulation"
            )
            raise PyrtlError(msg)

        failed = []
        for step in range(nsteps):
            self.step(
                {name: int(value[step]) for name, value in provided_inputs.items()}
            )

            for expvar in expected_outputs:
                expected = expected_outputs[expvar][step]
                if expected == "?":
                    continue
                expected = int(expected)
                actual = self.inspect(expvar)
                if expected != actual:
                    failed.append((step, expvar, expected, actual))

            if failed and stop_after_first_error:
                break

        if failed:
            if stop_after_first_error:
                suffix = "(stopped after step with first error):"
            else:
                suffix = "on one or more steps:"
            print("Unexpected output " + suffix, file=file)
            print(f"{'step':>5} {'name':>10} {'expected':>8} {'actual':>8}", file=file)

            def _sort_tuple(t):
                # Sort by step and then wire name
                return (t[0], _trace_sort_key(t[1]))

            failed = sorted(failed, key=_sort_tuple)
            for step, name, expected, actual in failed:
                print(f"{step:>5} {name:>10} {expected:>8} {actual:>8}", file=file)

    def run(self, inputs: list[dict[str, int]]):
        """Run many steps of the ``CompiledSimulation``.

        :meth:`CompiledSimulation.step` and :meth:`CompiledSimulation.step_multiple` are
        wrappers around this lower-level method.

        :param inputs: A list of input mappings for each step; its length is the number
            of steps to be executed.
        """
        steps = len(inputs)
        # Create arrays for Inputs and Outputs.
        inputs_array_type = ctypes.c_uint64 * (steps * self._inputs_array_length)
        outputs_array_type = ctypes.c_uint64 * (steps * self._outputs_array_length)
        inputs_array = inputs_array_type()
        outputs_array = outputs_array_type()
        # These arrays will be passed to `_sim_run_all`.
        self._sim_run_all.argtypes = [
            ctypes.c_uint64,
            inputs_array_type,
            outputs_array_type,
        ]

        # Build `inputs_array` from `inputs`. `inputs` is a list of `provided_inputs`
        # for each step. Each `provided_input` is a map from `WireVector` name to value.
        mask = (1 << 64) - 1
        for step, provided_inputs in enumerate(inputs):
            for input_name, input_value in provided_inputs.items():
                if isinstance(input_name, WireVector):
                    input_name = input_name.name
                # Figure out where to store `input_value` in `inputs_array` for this
                # `step`.
                input_metadata = self._inputs_metadata[input_name]
                start = input_metadata.start + step * self._inputs_array_length
                input_value = infer_val_and_bitwidth(
                    input_value, bitwidth=input_metadata.bitwidth
                ).value
                # Pack `input_value` into 64-bit limbs.
                for pos in range(start, start + input_metadata.length):
                    inputs_array[pos] = input_value & mask
                    input_value = input_value >> 64

        # Run the simulation with `inputs_array` and `outputs_array`. This invokes the
        # compiled C `sim_run_all` function.
        self._sim_run_all(steps, inputs_array, outputs_array)

        # Copy values for any traced wires from `outputs_array` and `inputs_array` to
        # the SimulationTrace.
        for name, values in self.tracer.trace.items():
            actual_name = self._probe_mapping.get(name, name)
            if actual_name in self._outputs_metadata:
                metadata = self._outputs_metadata[actual_name]
                array = outputs_array
                array_length = self._outputs_array_length
            elif actual_name in self._inputs_metadata:
                metadata = self._inputs_metadata[actual_name]
                array = inputs_array
                array_length = self._inputs_array_length
            else:
                msg = "Untraceable wire in tracer"
                raise PyrtlInternalError(msg)

            for _step in range(steps):
                value = 0
                # Unpack output from 64-bit limbs.
                start = metadata.start
                end = metadata.start + metadata.length
                for index in reversed(range(start, end)):
                    value = (value << 64) | array[index]
                values.append(value)
                start += array_length

    def _traceable(self, wire: WireVector) -> bool:
        """Check if wire is able to be traced.

        If it is traceable due to a probe, record that probe in _probe_mapping.
        """
        if isinstance(wire, (Input, Output)):
            return True
        for wire_net in self.block.logic_subset("w"):
            if wire_net.args[0].name == wire.name and isinstance(
                wire_net.dests[0], Output
            ):
                self._probe_mapping[wire.name] = wire_net.dests[0].name
                return True
        return False

    def _remove_untraceable(self):
        """Remove from the tracer those wires that CompiledSimulation cannot track.

        Create _probe_mapping for wires only traceable via probes.
        """
        self._probe_mapping = {}
        wires = {wire for wire in self.tracer.wires_to_track if self._traceable(wire)}
        self.tracer.wires_to_track = wires
        self.tracer._wires = {wire.name: wire for wire in wires}
        self.tracer.trace.__init__(wires)

    def _create_dll(self):
        """Create a dynamically-linked library implementing the simulation logic."""
        self._dir = tempfile.mkdtemp()
        with open(path.join(self._dir, "pyrtlsim.c"), "w") as f:
            self._create_code(lambda s: f.write(f"{s}\n"))
        if platform.system() == "Darwin":
            shared = "-dynamiclib"
            march = ""
        else:
            shared = "-shared"
            march = "-march=native"

        subprocess.check_call(
            [
                "gcc",
                "-O1",
                march,
                "-std=c99",
                "-m64",
                shared,
                "-fPIC",
                path.join(self._dir, "pyrtlsim.c"),
                "-o",
                path.join(self._dir, "pyrtlsim.so"),
            ],
            shell=(platform.system() == "Windows"),
        )
        self._dll = ctypes.CDLL(path.join(self._dir, "pyrtlsim.so"))
        self._sim_run_all = self._dll.sim_run_all
        self._sim_run_all.restype = None  # argtypes set on use
        self._initialize_mems = self._dll.initialize_mems
        self._initialize_mems.restype = None
        self._mem_lookup = self._dll.lookup
        self._mem_lookup.restype = ctypes.POINTER(ctypes.c_uint64)

    def _limbs(self, wire: WireVector) -> int:
        """Number of 64-bit words needed to store a WireVector's value."""
        return (wire.bitwidth + 63) // 64

    def _make_initializer(self, wire: WireVector, value: int):
        """Return a C initializer string that initializes ``wire``'s limbs to ``value``.

        For example, if the value 0x4444_3333_2222_1111_0000 (80 bits) is assigned to a
        ``wire`` with two limbs, this returns "{0x4444, 0x3333222211110000}".
        """
        values = []
        mask = (1 << 64) - 1
        for _ in range(self._limbs(wire)):
            values.append(hex(value & mask))
            value = value >> 64
        values_str = ",".join(values)
        return f"{{{values_str}}}"

    def _rom_width(self, rom: RomBlock) -> int:
        """Return the bitwidth of an integer type sufficient to hold an element of
        ``rom``.

        Returns 64 for large memories; an array will be needed.
        """
        if rom.bitwidth <= 8:
            return 8
        if rom.bitwidth <= 16:
            return 16
        if rom.bitwidth <= 32:
            return 32
        return 64

    def _make_mask(
        self, dest: WireVector, value_bitwidth: int | None, dest_limb: int
    ) -> str:
        """Return an expression that applies a bitmask to the value assigned to
        ``dest``, if necessary.

        The value has width ``value_bitwidth``, and we are assigning to limb number
        ``dest_limb`` of ``dest``.
        """
        # We must bitmask `value` if:
        # 1. `value_needs_mask`: The value has high bits that will not be copied to
        #    `dest`, AND
        # 2. `partial_dest_limb`: We are assigning fewer than 64 bits to the `dest`
        #    limb.
        value_needs_mask = value_bitwidth is None or dest.bitwidth < value_bitwidth
        partial_dest_limb = 0 < (dest.bitwidth - 64 * dest_limb) < 64
        if value_needs_mask and partial_dest_limb:
            return f"&0x{(1 << (dest.bitwidth % 64)) - 1:X}"
        return ""

    def _limb_name(self, wire: WireVector, wire_limb: int) -> str:
        """Return the name of the ``wire_limb``'th limb of ``wire``.

        Returns "0" when ``wire`` does not have sufficient limbs. This is useful when
        generating code for comparisons, see ``_build_eq`` and ``_build_cmp``.
        """
        if wire.bitwidth > 64 * wire_limb:
            return f"{self.var_names[wire]}[{wire_limb}]"
        return "0"

    def _clean_name(self, prefix: str, obj: WireVector | MemBlock) -> str:
        """Return a C variable name with the given ``prefix`` based on the name of
        ``obj``.
        """
        suffix = "".join(char for char in obj.name if char.isalnum())
        return f"{prefix}{self._uid()}_{suffix}"

    def _uid(self) -> int:
        """Postincrement a counter. The returned number can be used as a unique
        identifier.
        """
        x = self._uid_counter
        self._uid_counter += 1
        return x

    def _declare_roms(self, write: Callable, roms: set[RomBlock]):
        for rom in roms:
            self.var_names[rom] = var_name = self._clean_name("m", rom)
            # Make initialization strings for each of the ROM's elements.
            rom_initializers = []
            for addr in range(1 << rom.addrwidth):
                rom_initializers.append(
                    self._make_initializer(rom, rom._get_read_data(addr))
                )
            rom_initializer = ",".join(rom_initializers)
            write(
                f"static const uint{self._rom_width(rom)}_t {var_name}[]"
                f"[{self._limbs(rom)}] = {{{rom_initializer}}};"
            )

    def _declare_mems(self, write: Callable, mems: set[MemBlock]):
        for mem in mems:
            self.var_names[mem] = var_name = self._clean_name("m", mem)
            write("EXPORT")
            write(f"hashmap_t *{var_name};")

        next_tmp = 0
        write("EXPORT")
        write("void initialize_mems() {")
        for mem in mems:
            # Create hashmap
            write(f"{self.var_names[mem]} = create_hash_map(256, {self._limbs(mem)});")
            values = self._memory_value_map.get(mem)
            if values is None:
                continue
            # Insert default values
            for addr, value in values.items():
                write(f"val_t t{next_tmp}[] = {self._make_initializer(mem, value)};")
                write(f"insert({self.var_names[mem]}, {addr}, t{next_tmp});")
                next_tmp += 1
        write("}")

    def _declare_wirevector(self, write: Callable, wire: WireVector):
        self.var_names[wire] = var_name = self._clean_name("w", wire)
        wire_name = f"{var_name}[{self._limbs(wire)}]"
        if isinstance(wire, Const):
            write(
                f"const uint64_t {wire_name} = "
                f"{self._make_initializer(wire, wire.val)};"
            )
        elif isinstance(wire, Register):
            reset_value = self._register_value_map[wire]
            write(
                f"static uint64_t {wire_name} = "
                f"{self._make_initializer(wire, reset_value)};"
            )
        else:
            write(f"uint64_t {wire_name};")

    def _build_mem_read(
        self,
        write: Callable,
        op: str,
        op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "m":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)
        mem = op_param[1]
        for dest_limb in range(self._limbs(dest)):
            dest_name = self._limb_name(dest, dest_limb)
            # This code assumes read addresses are 64-bits or less.
            if self._limbs(args[0]) > 1:
                msg = "Read addresses longer than 64 bits are not supported."
                raise PyrtlInternalError(msg)
            read_addr = self._limb_name(args[0], 0)
            mask = self._make_mask(dest, mem.bitwidth, dest_limb)
            if isinstance(mem, RomBlock):
                expr = f"{self.var_names[mem]}[{read_addr}][{dest_limb}]{mask};"
            else:
                expr = f"lookup({self.var_names[mem]}, {read_addr})[{dest_limb}]{mask};"
            write(f"{dest_name} = {expr}")

    def _write_assignments(
        self,
        write: Callable,
        args: list[WireVector],
        dest: WireVector,
        arg_index: int,
        indent: int = 0,
    ) -> str:
        """Assign each limb of `args[arg_index]` to each limb of `dest`."""
        for dest_limb in range(self._limbs(dest)):
            dest_name = self._limb_name(dest, dest_limb)
            arg_name = self._limb_name(args[arg_index], dest_limb)
            # Assignment copies all the arg's bits, so we don't need a mask.
            if dest.bitwidth != args[arg_index].bitwidth:
                msg = (
                    f"Assignment dest {dest} and arg {args[arg_index]} bitwidths do "
                    "not match"
                )
                raise PyrtlInternalError(msg)
            write(f"{' ' * indent}{dest_name} = {arg_name};")

    def _build_wire(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "w":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)
        self._write_assignments(write, args, dest, arg_index=0)

    def _build_not(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "~":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        for dest_limb in range(self._limbs(dest)):
            dest_name = self._limb_name(dest, dest_limb)
            arg0_name = self._limb_name(args[0], dest_limb)
            mask = self._make_mask(dest, None, dest_limb)
            write(f"{dest_name} = (~{arg0_name}){mask};")

    def _build_bitwise(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "&" and op != "|" and op != "^":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        for dest_limb in range(self._limbs(dest)):
            dest_name = self._limb_name(dest, dest_limb)
            arg0_name = self._limb_name(args[0], dest_limb)
            arg1_name = self._limb_name(args[1], dest_limb)
            mask = self._make_mask(
                dest, max(args[0].bitwidth, args[1].bitwidth), dest_limb
            )
            write(f"{dest_name} = ({arg0_name}{op}{arg1_name}){mask};")

    def _build_nand(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "n":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        for dest_limb in range(self._limbs(dest)):
            dest_name = self._limb_name(dest, dest_limb)
            arg0_name = self._limb_name(args[0], dest_limb)
            arg1_name = self._limb_name(args[1], dest_limb)
            mask = self._make_mask(dest, None, dest_limb)
            write(f"{dest_name} = (~({arg0_name}&{arg1_name})){mask};")

    def _build_eq(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "=":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        condition_parts = []
        for arg_limb in range(max(self._limbs(args[0]), self._limbs(args[1]))):
            arg0_name = self._limb_name(args[0], arg_limb)
            arg1_name = self._limb_name(args[1], arg_limb)
            condition_parts.append(f"({arg0_name}=={arg1_name})")

        dest_name = self._limb_name(dest, 0)
        condition = "&&".join(condition_parts)
        write(f"{dest_name} = {condition};")

    def _build_lt_gt(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "<" and op != ">":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        condition = None
        for arg_limb in range(max(self._limbs(args[0]), self._limbs(args[1]))):
            arg0_name = self._limb_name(args[0], arg_limb)
            arg1_name = self._limb_name(args[1], arg_limb)
            comparison = f"({arg0_name}{op}{arg1_name})"
            if condition is None:
                condition = comparison
            else:
                condition = f"({comparison}||(({arg0_name}=={arg1_name})&&{condition}))"

        dest_name = self._limb_name(dest, 0)
        write(f"{dest_name} = {condition};")

    def _build_mux(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "x":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        arg0_name = self._limb_name(args[0], 0)
        write(f"if ({arg0_name}) {{")
        self._write_assignments(write, args, dest, arg_index=2, indent=2)
        write("} else {")
        self._write_assignments(write, args, dest, arg_index=1, indent=2)
        write("}")

    def _build_add(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "+":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        write("carry = 0;")
        for dest_limb in range(self._limbs(dest)):
            arg0_name = self._limb_name(args[0], dest_limb)
            arg1_name = self._limb_name(args[1], dest_limb)
            write(f"tmp = {arg0_name}+{arg1_name};")

            dest_name = self._limb_name(dest, dest_limb)
            mask = self._make_mask(
                dest, max(args[0].bitwidth, args[1].bitwidth) + 1, dest_limb
            )
            write(f"{dest_name} = (tmp + carry){mask};")
            write(f"carry = (tmp < {arg0_name})|({dest_name} < tmp);")

    def _build_sub(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "-":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        write("carry = 0;")
        for dest_limb in range(self._limbs(dest)):
            arg0_name = self._limb_name(args[0], dest_limb)
            arg1_name = self._limb_name(args[1], dest_limb)
            write(f"tmp = {arg0_name}-{arg1_name};")

            dest_name = self._limb_name(dest, dest_limb)
            mask = self._make_mask(dest, None, dest_limb)
            write(f"{dest_name} = (tmp - carry){mask};")
            write(f"carry = (tmp > {arg0_name})|({dest_name} > tmp);")

    def _build_mul(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "*":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        total_arg_bitwidth = args[0].bitwidth + args[1].bitwidth

        for dest_limb in range(self._limbs(dest)):
            dest_name = self._limb_name(dest, dest_limb)
            write(f"{dest_name} = 0;")

        # Roughly, this computes (ignoring carries):
        #
        # for arg0_limb in self._limbs(args[0]):
        #   for arg1_limb in self._limbs(args[1]):
        #     dest[arg0_limb + arg1_limb] += args[0][arg0_limb] * args[1][arg1_limb]
        for arg0_limb in range(self._limbs(args[0])):
            write("carry = 0;")
            arg0_name = self._limb_name(args[0], arg0_limb)

            for arg1_limb in range(self._limbs(args[1])):
                arg1_name = self._limb_name(args[1], arg1_limb)
                write(f"mul128({arg0_name}, {arg1_name}, tmplo, tmphi);")

                dest_limb = arg0_limb + arg1_limb
                if dest_limb >= self._limbs(dest):
                    msg = (
                        f"Insufficient dest limbs ({self._limbs(dest)}) for arg limbs "
                        f"{arg0_limb}, {arg1_limb}"
                    )
                    raise PyrtlInternalError(msg)
                dest_name = self._limb_name(dest, dest_limb)
                write(f"tmplo += carry; carry = tmplo < carry; tmplo += {dest_name};")
                write(f"tmphi += carry + (tmplo < {dest_name}); carry = tmphi;")

                mask = self._make_mask(dest, total_arg_bitwidth, dest_limb)
                write(f"{dest_name} = tmplo{mask};")

            # Finished multiplying arg1 with one limb of arg0. Write any remaining carry
            # bits and move on to the next most significant limb of arg0.
            dest_carry_limb = arg0_limb + self._limbs(args[1])
            if dest_carry_limb < self._limbs(dest):
                dest_name = self._limb_name(dest, dest_carry_limb)
                mask = self._make_mask(dest, total_arg_bitwidth, dest_carry_limb)
                write(f"{dest_name} = carry{mask};")

    def _build_concat(
        self,
        write: Callable,
        op: str,
        _op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "c":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        total_arg_bitwidth = sum(x.bitwidth for x in args)

        @dataclass
        class ArgLimbPiece:
            """Tracks sources for ``concat``'s ``arg`` bits.

            ``ArgLimbPiece`` represents a consecutive range of an ``arg``'s bits within
            an arg limb.
            """

            name: str
            """C variable name for this arg limb."""

            start: int
            """Starting offset within this arg limb. Must be in the range [0, 64)."""

            length: int
            """The arg's remaining length within this arg limb. Must be in the range [1,
            64).
            """

        arg_limb_pieces = (
            ArgLimbPiece(
                name=self._limb_name(arg, arg_limb),
                start=0,
                length=min(64, arg.bitwidth - 64 * arg_limb),
            )
            for arg in reversed(args)
            for arg_limb in range(self._limbs(arg))
        )

        arg_limb_piece = next(arg_limb_pieces)
        for dest_limb in range(self._limbs(dest)):
            expr_parts = []
            dest_start = 0

            # Keep copying `arg` bits until this `dest` limb is full, or we're out of
            # `args`.
            while dest_start < 64:
                if arg_limb_piece.start >= 64:
                    msg = (
                        f"arg_limb_piece.start {arg_limb_piece.start} exceeds limb "
                        "bitwidth"
                    )
                    raise PyrtlInternalError(msg)

                # Copy bits from the current `arg` limb to the current `dest` limb. The
                # second shift may throw away some of `arg` limb's bits, but we will
                # track that below, and copy any thrown-away `arg` limb bits to the next
                # `dest` limb.
                expr = shift(arg_limb_piece.name, ">>", arg_limb_piece.start)
                expr = shift(expr, "<<", dest_start)
                # Concat copies all bits from each arg, so we don't need to mask args.
                expr_parts.append(expr)

                dest_start += arg_limb_piece.length
                if dest_start > 64:
                    # We've reached the end of the current `dest` limb, but the current
                    # `arg` limb still has more bits. The `arg` limb's remaining bits
                    # must be copied to the next `dest` limb. Update `arg_limb_piece` so
                    # we remember where to resume copying from this `arg` limb.
                    arg_limb_piece = ArgLimbPiece(
                        name=arg_limb_piece.name,
                        start=64 - (dest_start - arg_limb_piece.length),
                        length=dest_start - 64,
                    )
                    break
                if dest_start >= dest.bitwidth - 64 * dest_limb:
                    # Done with the last `arg`.
                    break
                # We finished the current `arg` limb, but the current `dest` limb still
                # has room for more bits. Move on to the next `arg`.
                arg_limb_piece = next(arg_limb_pieces)

            dest_name = self._limb_name(dest, dest_limb)
            expr = "|".join(expr_parts)
            mask = self._make_mask(dest, total_arg_bitwidth, dest_limb)
            write(f"{dest_name} = ({expr}){mask};")

    def _next_limb_start(self, bit_position: int) -> int:
        """Given a bit position, return the bit position of the first bit in the next
        64-bit limb.

        This rounds ``bit_position`` up to the next even multiple of 64. For example,
        all integers in the range [0, 63] return 64, and all integers in the range [64,
        127] return 128.
        """
        return bit_position + (64 - bit_position % 64)

    def _split_consecutive_slices(
        self, dest: WireVector, op_param: list[int], n: int
    ) -> list[ConsecutiveSlice]:
        """Make ConsecutiveSlices for the ``n``th dest limb.

        To simplify processing, split ConsecutiveSlices that fetch bits from multiple
        arg limbs into ConsecutiveSlices that don't fetch bits from multiple arg limbs.
        """
        # Get op_params for the `n`th dest limb.
        current_op_param = op_param[64 * n : min(dest.bitwidth, 64 * (n + 1))]

        split_slices = []
        for consecutive_slice in make_consecutive_slices(current_op_param):
            next_limb_arg_start = self._next_limb_start(consecutive_slice.arg_start)
            arg_end = consecutive_slice.arg_start + consecutive_slice.length

            if next_limb_arg_start >= arg_end:
                # consecutive_slice fetches bits from one arg limb.
                split_slices.append(consecutive_slice)
            else:
                # consecutive_slice fetches bits from two arg limbs. Split it into two
                # ConsecutiveSlices that each fetch bits from one arg limb.
                first_limb_length = next_limb_arg_start - consecutive_slice.arg_start
                split_slices.extend(
                    [
                        ConsecutiveSlice(
                            length=first_limb_length,
                            arg_start=consecutive_slice.arg_start,
                            dest_start=consecutive_slice.dest_start,
                        ),
                        ConsecutiveSlice(
                            length=consecutive_slice.length - first_limb_length,
                            arg_start=next_limb_arg_start,
                            dest_start=consecutive_slice.dest_start + first_limb_length,
                        ),
                    ]
                )

        return split_slices

    def _build_slice(
        self,
        write: Callable,
        op: str,
        op_param,
        args: list[WireVector],
        dest: WireVector,
    ):
        if op != "s":
            msg = f"Unexpected op {op}"
            raise PyrtlInternalError(msg)

        # Iterate over the slice's dest limbs.
        for dest_limb in range(self._limbs(dest)):
            split_slices = self._split_consecutive_slices(dest, op_param, dest_limb)

            expr_parts = []
            for split_slice in split_slices:
                # We only need to fetch bits from one arg limb because
                # _split_consecutive_slices split up any slices that fetch bits from
                # multiple arg limbs.
                expr = self._limb_name(args[0], split_slice.arg_start // 64)
                expr = shift(expr, ">>", split_slice.arg_start % 64)

                slice_arg_end = split_slice.arg_start + split_slice.length
                next_limb_arg_start = self._next_limb_start(split_slice.arg_start)
                assert slice_arg_end <= next_limb_arg_start
                actual_arg_end = min(args[0].bitwidth, next_limb_arg_start)
                # If this split_slice does not fetch all of the arg limb's remaining
                # bits, we must mask the arg limb.
                if slice_arg_end < actual_arg_end:
                    expr = f"({expr} & 0x{(1 << split_slice.length) - 1:X})"

                assert split_slice.dest_start < 64
                assert split_slice.length <= 64 - split_slice.dest_start
                expr_parts.append(shift(expr, "<<", split_slice.dest_start))

            expr = "|".join(expr_parts)

            dest_name = self._limb_name(dest, dest_limb)
            write(f"{dest_name} = {expr};")

    def _declare_mem_helpers(self, write):
        helpers = """
            typedef uint64_t val_t;

            typedef struct node {
                uint64_t key;
                val_t *val;
                struct node *next;
            } node_t;

            typedef struct hashmap {
                int size;
                int val_limbs;
                val_t *default_value;
                node_t **list;
            } hashmap_t;

            hashmap_t *create_hash_map(int size, int val_limbs) {
                int i;
                hashmap_t *h = (hashmap_t *) malloc(sizeof(hashmap_t));
                h->size = size;
                h->val_limbs = val_limbs;
                h->list = (node_t **) malloc(sizeof(node_t *) * size);
                h->default_value = (val_t *) malloc(sizeof(val_t) * val_limbs);
                for (i = 0; i < val_limbs; i++)
                    h->default_value[i] = 0;
                for (i = 0; i < size; i++)
                    h->list[i] = NULL;
                return h;
            }

            int hash_code(hashmap_t *h, uint64_t key) {
                return key % h->size;
            }

            void insert(hashmap_t *h, uint64_t key, val_t val[]) {
                int pos = hash_code(h, key);
                struct node *list = h->list[pos];
                struct node *new_node = (node_t *) malloc(sizeof(node_t));
                struct node *temp = list;
                while (temp) {
                    if (temp->key == key) {
                        memcpy(temp->val, val, sizeof(val_t) * h->val_limbs);
                        return;
                    }
                    temp = temp->next;
                }
                new_node->key = key;
                new_node->val = (val_t *) malloc(sizeof(val_t) * h->val_limbs);
                memcpy(new_node->val, val, sizeof(val_t) * h->val_limbs);
                new_node->next = list;
                h->list[pos] = new_node;
            }

            EXPORT
            val_t* lookup(hashmap_t *h, uint64_t key) {
                int pos = hash_code(h, key);
                node_t *list = h->list[pos];
                node_t *temp = list;
                while (temp) {
                    if (temp->key == key) {
                        return temp->val;
                    }
                    temp = temp->next;
                }
                return h->default_value;
            }
        """
        write(helpers)

    @dataclass
    class InputMetadata:
        """Tracks an ``Input``'s location in ``inputs_array``.

        The ``Input`` is stored at ``inputs_array[start:start + length]``.
        """

        start: int
        """Index of ``Input``'s first word in ``inputs_array``.

        ``start`` points to the ``Input``'s least significant bits.
        """

        length: int
        """Number of 64-bit limbs used to store this ``Input``."""

        bitwidth: int
        """Total bitwidth of the ``Input``."""

    @dataclass
    class OutputMetadata:
        """Tracks an ``Output``'s location in ``outputs_array``.

        The ``Output`` is stored at ``outputs_array[start:start + length]``.
        """

        start: int
        """Index of ``Output``'s first word in ``outputs_array``.

        ``start`` points to the ``Output``'s least significant bits.
        """

        length: int
        """Number of 64-bit limbs used to store this ``Output``."""

    def _create_code(self, write):
        write("#include <stdint.h>")
        write("#include <stdlib.h>")
        write("#include <string.h>")

        # `dllexport` is needed to make symbols visible on Windows.
        if platform.system() == "Windows":
            write("#define EXPORT __declspec(dllexport)")
        else:
            write("#define EXPORT")

        # Multiplication macros for efficient 64x64 -> 128 bit multiplication without
        # uint128_t. -O1 optimization does not handle uint128_t well.
        machine_alias = {"amd64": "x86_64", "aarch64": "arm64", "aarch64_be": "arm64"}
        machine = platform.machine().lower()
        machine = machine_alias.get(machine, machine)
        mul_asm = {
            "x86_64": '"mulq %q3":"=a"(pl),"=d"(ph):"%0"(t0),"r"(t1):"cc"',
            "arm64": (
                '"mul %0, %2, %3\\n\\t" \\\n'
                '"umulh %1, %2, %3":"=&r"(pl),"=r"(ph):"r"(t0),"r"(t1):"cc"'
            ),
            "mips64": (
                '"dmultu %2, %3\\n\\t" \\\n'
                '"tmflo %0\\n\\t" \\\n'
                '"mfhi %1":"=r"(pl),"=r"(ph):"r"(t0),"r"(t1)'
            ),
        }
        if machine in mul_asm:
            write(f"#define mul128(t0, t1, pl, ph) __asm__({mul_asm[machine]})")

        # Declare memories.
        self._declare_mem_helpers(write)

        # Find all of the Block's MemBlocks and RomBlocks.
        memblocks = set()
        romblocks = set()
        for memblock in {net.op_param[1] for net in self.block.logic_subset("m@")}:
            if isinstance(memblock, RomBlock):
                romblocks.add(memblock)
            else:
                memblocks.add(memblock)

        for memblock in self._memory_value_map:
            if memblock not in memblocks:
                msg = "unrecognized MemBlock in memory_value_map"
                raise PyrtlError(msg)
            if isinstance(memblock, RomBlock):
                msg = "RomBlock in memory_value_map"
                raise PyrtlError(msg)

        self._declare_roms(write, romblocks)
        self._declare_mems(write, memblocks)

        # Define `sim_run_step`, which simulates one cycle. `step_inputs` and
        # `step_outputs` are arrays of the step's input and output values, respectively.
        write(
            "static void sim_run_step("
            "uint64_t step_inputs[], uint64_t step_outputs[]) {"
        )
        write("uint64_t tmp, carry, tmphi, tmplo;")  # temporary variables

        # Declare all WireVectors.
        for w in self.block.wirevector_set:
            self._declare_wirevector(write, w)

        # Initialize Input WireVectors from `step_inputs`.
        #
        # `_inputs_metadata` maps each Input to its (start, length, bitwidth) in
        # `step_inputs`. This will be used by `run` to pack its `inputs_array`.
        self._inputs_metadata = {}
        inputs_index = 0
        for input_wire in self.block.wirevector_subset(Input):
            self._inputs_metadata[input_wire.name] = self.InputMetadata(
                inputs_index, self._limbs(input_wire), input_wire.bitwidth
            )
            for input_wire_limb in range(self._limbs(input_wire)):
                input_wire_name = self._limb_name(input_wire, input_wire_limb)
                write(f"{input_wire_name} = step_inputs[{inputs_index}];")
                inputs_index += 1
        self._inputs_array_length = inputs_index  # total length of `inputs` array

        # Build combinational logic.
        op_builders = {
            "m": self._build_mem_read,
            "w": self._build_wire,
            "~": self._build_not,
            "&": self._build_bitwise,
            "|": self._build_bitwise,
            "^": self._build_bitwise,
            "n": self._build_nand,
            "=": self._build_eq,
            "<": self._build_lt_gt,
            ">": self._build_lt_gt,
            "x": self._build_mux,
            "+": self._build_add,
            "-": self._build_sub,
            "*": self._build_mul,
            "c": self._build_concat,
            "s": self._build_slice,
        }
        for net in self.block:  # topological order
            if net.op in "r@":
                continue  # skip synchronized nets
            op = net.op
            op_param = net.op_param
            args = net.args
            dest = net.dests[0]

            args_names = ", ".join(self.var_names[x] for x in args)
            dest_name = self.var_names[dest]
            write(f"// net {op} : {args_names} -> {dest_name}")
            op_builders[op](write, op, op_param, args, dest)

        # Write memories.
        for write_net in self.block.logic_subset("@"):
            mem = write_net.op_param[1]
            write_enabled = self._limb_name(write_net.args[2], 0)
            write(f"if ({write_enabled}) {{")
            # This code assumes write addresses are 64-bits or less.
            if self._limbs(write_net.args[0]) > 1:
                msg = "Write addresses longer than 64 bits are not supported."
                raise PyrtlInternalError(msg)
            write_addr = self._limb_name(write_net.args[0], 0)
            write(
                f"insert({self.var_names[mem]}, {write_addr}, "
                f"{self.var_names[write_net.args[1]]});"
            )
            write("}")

        # Update registers. This is done in two passes to ensure register chains update
        # correctly. The first pass colllects every `Register.next` value in a temporary
        # array.
        reg_nets = list(self.block.logic_subset("r"))
        for reg_index, reg_net in enumerate(reg_nets):
            reg_next = reg_net.args[0]
            write(f"uint64_t regtmp{reg_index}[{self._limbs(reg_next)}];")
            for reg_next_limb in range(self._limbs(reg_next)):
                reg_next_name = self._limb_name(reg_next, reg_next_limb)
                write(f"regtmp{reg_index}[{reg_next_limb}] = {reg_next_name};")
        # The second pass actually assigns the collected `Register.next` values to
        # registers.
        for reg_index, reg_net in enumerate(reg_nets):
            reg = reg_net.dests[0]
            for reg_limb in range(self._limbs(reg)):
                reg_name = self._limb_name(reg, reg_limb)
                write(f"{reg_name} = regtmp{reg_index}[{reg_limb}];")

        # Copy all Output values to the `step_outputs` array.
        outputs = list(self.block.wirevector_subset(Output))
        # `_outputs_metadata` maps from Output name to its (start, length) in
        # `step_outputs`. This will be used by `run` to unpack its `outputs_array`.
        self._outputs_metadata = {}
        output_index = 0
        for output in outputs:
            self._outputs_metadata[output.name] = self.OutputMetadata(
                output_index, self._limbs(output)
            )
            for output_limb in range(self._limbs(output)):
                output_name = self._limb_name(output, output_limb)
                write(f"step_outputs[{output_index}] = {output_name};")
                output_index += 1
        self._outputs_array_length = output_index  # total length of output array
        write("}")

        # `sim_run_all` is the compiled simulator's main entry point. `sim_run_all` runs
        # multiple simulation steps by calling `sim_run_step` in a loop. Arguments:
        #
        # `nsteps` is the number of steps to simulate.
        # `inputs` is a flattened array of input values for all steps, stored in
        #    step-major order. Input value `i` for step `s` is located at index:
        #    `s * self._inputs_array_length + i`
        # `outputs` is a flattened array of output values for all steps, stored in
        #    step-major order. Output value `o` for step `s` is located at index:
        #    `s * self._outputs_array_length + o`
        write("EXPORT")
        write(
            "void sim_run_all(uint64_t nsteps, uint64_t inputs[], uint64_t outputs[]) {"
        )
        write("uint64_t input_index = 0, output_index = 0;")
        write("for (uint64_t step = 0; step < nsteps; step++) {")
        write("sim_run_step(inputs + input_index, outputs + output_index);")
        write(f"input_index += {self._inputs_array_length};")
        write(f"output_index += {self._outputs_array_length};")
        write("}}")

    def __del__(self):
        """Handle removal of the DLL when the simulator is deleted."""
        # TODO: Should this free the memory allocated by `create_hash_map` and `insert`?
        if self._dll is not None:
            handle = self._dll._handle
            if platform.system() == "Windows":
                _ctypes.FreeLibrary(handle)
            else:
                _ctypes.dlclose(handle)
            self._dll = None
        if self._dir is not None:
            shutil.rmtree(self._dir)
            self._dir = None
