"""Classes for executing and tracing circuit simulations."""

from __future__ import annotations

import math
import numbers
import os
import re
import sys
import warnings
from collections.abc import Mapping
from typing import Callable

from pyrtl.core import Block, PostSynthBlock, _PythonSanitizer, working_block
from pyrtl.helperfuncs import (
    _currently_in_jupyter_notebook,
    check_rtl_assertions,
    infer_val_and_bitwidth,
    val_to_signed_integer,
)
from pyrtl.importexport import _VerilogSanitizer
from pyrtl.memory import MemBlock, RomBlock
from pyrtl.pyrtlexceptions import PyrtlError, PyrtlInternalError
from pyrtl.wire import Const, Input, Output, Register, WireVector

# ----------------------------------------------------------------
#    __                         ___    __
#   /__` |  |\/| |  | |     /\   |  | /  \ |\ |
#   .__/ |  |  | \__/ |___ /~~\  |  | \__/ | \|
#


class Simulation:
    """A class for simulating :class:`Blocks<Block>` of logic step by step.

    A ``Simulation`` step works as follows:

    1. :class:`Registers<Register>` are updated:

    1. (If this is the first step) With the default values passed in to the
       ``Simulation`` during instantiation and/or any ``reset_values`` specified in the
       individual :class:`Registers<Register>`.

    2. (Otherwise) With their next values calculated in the previous step (``r``
       :class:`LogicNets<LogicNet>`).

    2. The new values of these :class:`Registers<Register>` as well as the values of
       :class:`Block` :class:`Inputs<Input>` are propagated through the combinational
       logic.

    3. :class:`MemBlock` writes are performed (``@`` :class:`LogicNets<LogicNet>`).

    4. The current values of all wires are recorded in the :attr:`tracer`.

    5. The next values for the :class:`Registers<Register>` are saved, ready to be
       applied at the beginning of the next step.

    Note that the :class:`Register` values saved in the :attr:`tracer` after each
    simulation step are from *before* the :class:`Register` has latched in its newly
    calculated values, since that latching occurs at the beginning of the *next* step.

    In addition to the functions methods listed below, it is sometimes useful to reach
    into this class and access internal state directly. Of particular usefulness are:

    - ``.value``: a map from every signal in the :class:`Block` to its current
      simulation value.

    - ``.regvalue``: a map from :class:`Register` to its value on the next cycle.

    - ``.memvalue``: a map from ``memid`` to a dictionary of ``{address: value}``.
    """

    tracer: SimulationTrace
    """
    Stores the simulation results for each cycle.

    ``tracer`` is typically used to render simulation waveforms with
    :meth:`~SimulationTrace.render_trace`, for example::

        sim = pyrtl.Simulation()
        sim.step_multiple(nsteps=10)
        sim.tracer.render_trace()

    See :class:`SimulationTrace` for more display options.
    """

    def __init__(
        self,
        tracer: SimulationTrace = True,
        register_value_map: dict[Register, int] | None = None,
        memory_value_map: dict[MemBlock, dict[int, int]] | None = None,
        default_value: int = 0,
        block: Block = None,
    ):
        """Creates a new circuit simulator.

        .. WARNING::

            Warning: ``Simulation`` initializes some things in :meth:`__init__`, so
            changing items in the :class:`Block` during ``Simulation`` will likely break
            the ``Simulation``.

        :param tracer: Stores execution results. If ``None`` is passed, no
            :attr:`tracer` is used, which improves performance for long running
            simulations. If the default (``True``) is passed, ``Simulation`` will create
            a new :class:`SimulationTrace` automatically, which can be referenced as
            :attr:`tracer`.
        :param register_value_map: Defines the initial value for the
            :class:`Registers<Register>` specified; overrides the :class:`Register`'s
            ``reset_value``.
        :param memory_value_map: Defines initial values for
            :class:`MemBlocks<MemBlock>`. Format: ``{memory: {address: value}}``.
            ``memory`` is a :class:`MemBlock`, ``address`` is the address of ``value``
        :param default_value: The value that all unspecified
            :class:`Registers<Register>` and :class:`MemBlocks<MemBlock>` will
            initialize to (default ``0``). For :class:`Registers<Register>`, this is the
            value that will be used if the particular :class:`Register` doesn't have a
            specified ``reset_value``, and isn't found in the ``register_value_map``.
        :param block: The hardware :class:`Block` to be simulated (which might be of
            type :class:`PostSynthBlock`). Defaults to the :ref:`working_block`.
        """
        # Creates object and initializes it with self._initialize. register_value_map,
        # memory_value_map, and default_value are passed on to _initialize.
        block = working_block(block)
        block.sanity_check()  # check that this is a good hw block

        self.value = {}  # map from signal->value
        self.regvalue = {}  # map from register->value on next tick
        self.memvalue = {}  # map from {memid :{address: value}}
        self.block = block
        self.default_value = default_value
        if tracer is True:
            tracer = SimulationTrace()
        self.tracer = tracer
        self._initialize(register_value_map, memory_value_map)

    def _initialize(self, register_value_map=None, memory_value_map=None):
        """Sets the wire, register, and memory values to default or as specified.

        :param register_value_map: is a map of {Register: value}.
        :param memory_value_map: is a map of maps {Memory: {address: Value}}.
        :param default_value: is the value that all unspecified registers and memories
            will initialize to (default 0). For registers, this is the value that will
            be used if the particular register doesn't have a specified reset_value, and
            isn't found in the register_value_map.
        """
        # set registers to their values
        if memory_value_map is None:
            memory_value_map = {}
        if register_value_map is None:
            register_value_map = {}
        reg_set = self.block.wirevector_subset(Register)
        for r in reg_set:
            rval = register_value_map.get(r, r.reset_value)
            if rval is None:
                rval = self.default_value
            self.value[r] = self.regvalue[r] = rval

        # set constants to their set values
        for w in self.block.wirevector_subset(Const):
            self.value[w] = w.val
            assert isinstance(w.val, numbers.Integral)  # for now

        # set memories to their passed values
        for mem_net in self.block.logic_subset("m@"):
            memid = mem_net.op_param[1].id
            if memid not in self.memvalue:
                self.memvalue[memid] = {}

        for mem, mem_map in memory_value_map.items():
            if isinstance(mem, RomBlock):
                msg = "error, one or more of the memories in the map is a RomBlock"
                raise PyrtlError(msg)
            if isinstance(self.block, PostSynthBlock):
                mem = self.block.mem_map[mem]
            self.memvalue[mem.id] = mem_map.copy()

            max_addr_val = 2**mem.addrwidth
            for addr, val in mem_map.items():
                val = infer_val_and_bitwidth(val, bitwidth=mem.bitwidth).value
                if addr < 0 or addr >= max_addr_val:
                    msg = f"error, address {addr} in {mem.name} outside of bounds"
                    raise PyrtlError(msg)

        # set all other variables to default value
        for w in self.block.wirevector_set:
            if w not in self.value:
                self.value[w] = self.default_value

        self.ordered_nets = tuple(i for i in self.block)
        self.reg_update_nets = tuple(self.block.logic_subset("r"))
        self.mem_update_nets = tuple(self.block.logic_subset("@"))

        if self.tracer is not None:
            self.tracer._set_initial_values(
                self.default_value, register_value_map, memory_value_map
            )

    def step(self, provided_inputs: dict[str, int] | None = None):
        """Take the simulation forward one cycle.

        ``step`` causes the :class:`Block` to be updated as follows, in order:

        1. :class:`Registers<Register>` are updated with their :attr:`~Register.next`
           values computed at the end of the previous cycle.

        2. :class:`Inputs<Input>` and these new :class:`Register` values propagate
           through the combinational logic

        3. :class:`MemBlocks<MemBlock>` are updated

        4. The :attr:`~Register.next` values of the :class:`Registers<Register>` are
           saved for use at the beginning of the next cycle.

        All :class:`Input` wires must be in the ``provided_inputs``.

        Example: if we have :class:`Inputs<Input>` named ``a`` and ``x``, we can call::

            sim.step({'a': 1, 'x': 23})

        to simulate a cycle where ``a == 1`` and ``x == 23`` respectively.

        :param provided_inputs: A dictionary mapping :class:`Input`
            :class:`WireVectors<WireVector>` to their values for this step.
        """

        # Check that all Input have a corresponding provided_input
        if provided_inputs is None:
            provided_inputs = {}
        input_set = self.block.wirevector_subset(Input)
        supplied_inputs = set()
        for i in provided_inputs:
            if isinstance(i, WireVector):
                name = i.name
            else:
                name = i
            sim_wire = self.block.wirevector_by_name[name]
            if sim_wire not in input_set:
                msg = (
                    f'step provided a value for input for "{name}" which is not a '
                    "known input "
                )
                raise PyrtlError(msg)
            if not isinstance(provided_inputs[i], numbers.Integral):
                msg = (
                    f'step provided an input "{provided_inputs[i]}" which is not a '
                    "valid integer"
                )
                raise PyrtlError(msg)
            provided_inputs[i] = infer_val_and_bitwidth(
                provided_inputs[i], bitwidth=sim_wire.bitwidth
            ).value

            self.value[sim_wire] = provided_inputs[i]
            supplied_inputs.add(sim_wire)

        # Check that only inputs are specified, and set the values
        if input_set != supplied_inputs:
            for i in input_set.difference(supplied_inputs):
                msg = f'Input "{i.name}" has no input value specified'
                raise PyrtlError(msg)

        self.value.update(self.regvalue)  # apply register updates from previous step

        for net in self.ordered_nets:
            self._execute(net)

        # Do all of the mem operations based off the new values changed in _execute()
        for net in self.mem_update_nets:
            self._mem_update(net)

        # at the end of the step, record the values to the trace
        if self.tracer is not None:
            self.tracer.add_step(self.value)

        # Do all of the reg updates based off of the new values
        for net in self.reg_update_nets:
            argval = self.value[net.args[0]]
            self.regvalue[net.dests[0]] = self._sanitize(argval, net.dests[0])

        # finally, if any of the rtl_assert assertions are failing then we should raise
        # the appropriate exceptions
        check_rtl_assertions(self)

    def step_multiple(
        self,
        provided_inputs: dict[str, list[int]] | None = None,
        expected_outputs: dict[str, list[int]] | None = None,
        nsteps: int | None = None,
        file=sys.stdout,
        stop_after_first_error: bool = False,
    ):
        """Take the simulation forward ``N`` cycles, based on ``provided_inputs`` for
        each cycle.

        All :class:`Input` wires must be in ``provided_inputs``. Additionally, the
        length of the array of provided values for each :class:`Input` must be the same.

        When ``nsteps`` is specified, then it must be *less than or equal* to the number
        of values supplied for each :class:`Input` when ``provided_inputs`` is
        non-empty. When ``provided_inputs`` is empty (which may be a legitimate case for
        a design that takes no :class:`Input`), then ``nsteps`` will be used. When
        ``nsteps`` is not specified, then the simulation will take the number of steps
        equal to the number of values supplied for each :class:`Input`.

        Example: if we have :class:`Inputs<Input>` named ``a`` and ``b`` and
        :class:`Output` ``o``, we can call::

            sim.step_multiple({'a': [0,1], 'b': [23,32]}, {'o': [42, 43]})

        to simulate 2 cycles. In the first cycle, ``a`` and ``b`` take on ``0`` and
        ``23``, respectively, and ``o`` is expected to have the value ``42``. In the
        second cycle, ``a`` and ``b`` take on ``1`` and ``32``, respectively, and ``o``
        is expected to have the value ``43``.

        If your values are all single digit, you can also specify them in a single
        string, e.g.::

            sim.step_multiple({'a': '01', 'b': '01'})

        will simulate 2 cycles. In the first cycle, ``a`` and ``b`` take on ``0`` and
        ``0``, respectively. In the second cycle, they take on ``1`` and ``1``,
        respectively.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        If a design has no :class:`Inputs<Input>`, use ``nsteps`` to specify the number
        of cycles to simulate::

            >>> counter = pyrtl.Register(name="counter", bitwidth=8)
            >>> counter.next <<= counter + 1

            >>> sim = pyrtl.Simulation()
            >>> sim.step_multiple(nsteps=3)
            >>> sim.inspect("counter")
            2

        :param provided_inputs: A dictionary mapping :class:`WireVectors<WireVector>` to
            their values for ``N`` steps.
        :param expected_outputs: A dictionary mapping :class:`WireVectors<WireVector>`
            to their expected values for ``N`` steps; use ``?`` to indicate you don't
            care what the value at that step is.
        :param nsteps: A number of steps to take (defaults to ``None``, meaning step for
            each supplied input value in ``provided_inputs``)
        :param file: Where to write the output (if there are unexpected outputs
            detected).
        :param stop_after_first_error: A boolean flag indicating whether to stop the
            simulation after encountering the first error (defaults to ``False``).
        """

        if expected_outputs is None:
            expected_outputs = {}
        if provided_inputs is None:
            provided_inputs = {}
        if not nsteps and len(provided_inputs) == 0:
            msg = "need to supply either input values or a number of steps to simulate"
            raise PyrtlError(msg)

        if len(provided_inputs) > 0:
            longest = sorted(
                provided_inputs.items(), key=lambda t: len(t[1]), reverse=True
            )[0]
            msteps = len(longest[1])
            if nsteps:
                if nsteps > msteps:
                    msg = (
                        "nsteps is specified but is greater than the number of values "
                        "supplied for each input"
                    )
                    raise PyrtlError(msg)
            else:
                nsteps = msteps

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
        for i in range(nsteps):
            self.step({w: int(v[i]) for w, v in provided_inputs.items()})

            for expvar in expected_outputs:
                expected = expected_outputs[expvar][i]
                if expected == "?":
                    continue
                expected = int(expected)
                actual = self.inspect(expvar)
                if expected != actual:
                    failed.append((i, expvar, expected, actual))

            if failed and stop_after_first_error:
                break

        if failed:
            if stop_after_first_error:
                s = "(stopped after step with first error):"
            else:
                s = "on one or more steps:"
            file.write("Unexpected output " + s + "\n")
            file.write(
                "{:>5} {:>10} {:>8} {:>8}\n".format(
                    "step", "name", "expected", "actual"
                )
            )

            def _sort_tuple(t):
                # Sort by step and then wire name
                return (t[0], _trace_sort_key(t[1]))

            failed_sorted = sorted(failed, key=_sort_tuple)
            for step, name, expected, actual in failed_sorted:
                file.write(f"{step:>5} {name:>10} {expected:>8} {actual:>8}\n")
            file.flush()

    def inspect(self, w: str) -> int:
        """Get the value of a :class:`WireVector` in the current ``Simulation`` cycle.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> counter = pyrtl.Register(name="counter", bitwidth=3)
            >>> counter.next <<= counter + 1

            >>> sim = pyrtl.Simulation()
            >>> sim.step()
            >>> sim.inspect("counter")
            0

            >>> sim.step()
            >>> sim.inspect("counter")
            1

        :param w: The name of the :class:`WireVector` to inspect (passing in a
                  :class:`WireVector` instead of a name is deprecated).

        :raise KeyError: If ``w`` does not exist in the ``Simulation``.

        :return: The value of ``w`` in the current ``Simulation`` cycle.
        """
        wire = self.block.wirevector_by_name.get(w, w)
        return self.value[wire]

    def inspect_mem(self, mem: MemBlock) -> dict[int, int]:
        """Get :class:`MemBlock` values in the current ``Simulation`` cycle.

        .. note::

            This returns the current contents of the :class:`MemBlock`. Modifying the
            returned :class:`dict` will modify the ``Simulation``'s state.

        .. doctest only::

            >>> import pyrtl
            >>> pyrtl.reset_working_block()

        Example::

            >>> mem = pyrtl.MemBlock(bitwidth=8, addrwidth=2)

            >>> write_addr = pyrtl.Register(name="write_addr", bitwidth=2)
            >>> write_addr.next <<= write_addr + 1
            >>> mem[write_addr] <<= write_addr + 10

            >>> sim = pyrtl.Simulation()
            >>> sim.step_multiple(nsteps=4)
            >>> sorted(sim.inspect_mem(mem).items())
            [(0, 10), (1, 11), (2, 12), (3, 13)]

        :param mem: The memory to inspect.

        :return: A :class:`dict` mapping from memory address to memory value.
        """
        return self.memvalue[mem.id]

    @staticmethod
    def _sanitize(val, wirevector):
        """Return a modified version of val that would fit in wirevector.

        This function should be applied to every primitive call, and it's default
        behavior is to mask the upper bits of value and return that new value.
        """
        return val & wirevector.bitmask

    def _execute(self, net):
        """Handle the combinational logic update rules for the given net.

        This function, along with edge_update, defined the semantics of the primitive
        ops. Function updates self.value accordingly.
        """
        simple_func = {  # OPS
            "w": lambda x: x,
            "~": lambda x: ~int(x),
            "&": lambda left, right: left & right,
            "|": lambda left, right: left | right,
            "^": lambda left, right: left ^ right,
            "n": lambda left, right: ~(left & right),
            "+": lambda left, right: left + right,
            "-": lambda left, right: left - right,
            "*": lambda left, right: left * right,
            "<": lambda left, right: int(left < right),
            ">": lambda left, right: int(left > right),
            "=": lambda left, right: int(left == right),
            "x": lambda sel, f, t: f if (sel == 0) else t,
        }

        if net.op in "r@":
            return  # registers and memory write ports have no logic function
        if net.op in simple_func:
            argvals = (self.value[arg] for arg in net.args)
            result = simple_func[net.op](*argvals)
        elif net.op == "c":
            result = 0
            for arg in net.args:
                result = result << len(arg)
                result = result | self.value[arg]
        elif net.op == "s":
            result = 0
            source = self.value[net.args[0]]
            for b in net.op_param[::-1]:
                result = (result << 1) | (0x1 & (source >> b))
        elif net.op == "m":
            # memories act async for reads
            memid = net.op_param[0]
            mem = net.op_param[1]
            read_addr = self.value[net.args[0]]
            if isinstance(mem, RomBlock):
                result = mem._get_read_data(read_addr)
            else:
                result = self.memvalue[memid].get(read_addr, self.default_value)
        else:
            msg = "error, unknown op type"
            raise PyrtlInternalError(msg)

        self.value[net.dests[0]] = self._sanitize(result, net.dests[0])

    def _mem_update(self, net):
        """Handle the mem update for the simulation of the given net (which is a
        memory).

        Combinational logic should have no posedge behavior, but registers and memory
        should. This function, used after _execute, defines the semantics of the
        primitive ops. Function updates self.memvalue accordingly (using prior_value)
        """
        if net.op != "@":
            raise PyrtlInternalError
        memid = net.op_param[0]
        write_addr = self.value[net.args[0]]
        write_val = self.value[net.args[1]]
        write_enable = self.value[net.args[2]]
        if write_enable:
            self.memvalue[memid][write_addr] = write_val


# ----------------------------------------------------------------
#    ___       __  ___     __
#   |__   /\  /__`  |     /__` |  |\/|
#   |    /~~\ .__/  |     .__/ |  |  |
#


class FastSimulation:
    """Simulate a block by generating and running Python code.

    ``FastSimulation`` re-implements :class:`Simulation`, with slower start-up and
    faster execution. This can be a good trade-off when simulating large circuits, or
    simulating many cycles.

    ``FastSimulation`` is a drop-in replacement for :class:`Simulation`, so the two
    classes share the same interface. See :class:`Simulation` for interface
    documentation, and more details about PyRTL simulations.
    """

    # Dev Notes on Wire name processing:
    #
    # Sanitized names are only used when using and assigning variables inside of the
    # generated function. Normal names are used when interacting with the dictionaries
    # passed in and created by the exec'ed function. Therefore, everything outside of
    # this function uses normal WireVector names. Careful use of repr() is used to make
    # sure that strings stay the same when put into the generated code

    def __init__(
        self,
        register_value_map: dict[Register, int] | None = None,
        memory_value_map: dict[MemBlock, dict[int, int]] | None = None,
        default_value: int = 0,
        tracer: SimulationTrace = True,
        block: Block = None,
        code_file: str | None = None,
    ):
        """
        The interfaces for ``FastSimulation`` and :class:`Simulation` are nearly
        identical, so only the differences are described here. See
        :meth:`Simulation.__init__` for descriptions of the remaining constructor
        arguments.

        .. note::

            This constructor generates Python code for the :class:`Block`, so any
            changes to the circuit after instantiating a ``FastSimulation`` will not be
            reflected in the ``FastSimulation``.

        In addition to :meth:`Simulation.__init__`'s arguments, this constructor
        additionally takes:

        :param code_file: The name of the file in which to store a copy of the generated
            Python code. By default, the generated code is not saved.
        """

        if memory_value_map is None:
            memory_value_map = {}
        if register_value_map is None:
            register_value_map = {}
        block = working_block(block)
        block.sanity_check()  # check that this is a good hw block

        self.block = block
        self.default_value = default_value
        if tracer is True:
            tracer = SimulationTrace()
        self.tracer = tracer
        self.sim_func = None
        self.code_file = code_file
        self.mems = {}
        self.regs = {}
        self.internal_names = _PythonSanitizer("_fastsim_tmp_")
        self._initialize(register_value_map, memory_value_map)

    def _initialize(self, register_value_map=None, memory_value_map=None):
        if memory_value_map is None:
            memory_value_map = {}
        if register_value_map is None:
            register_value_map = {}
        for wire in self.block.wirevector_set:
            self.internal_names.make_valid_string(wire.name)

        # set registers to their values
        reg_set = self.block.wirevector_subset(Register)
        for r in reg_set:
            rval = register_value_map.get(r, r.reset_value)
            if rval is None:
                rval = self.default_value
            self.regs[r.name] = rval

        self._initialize_mems(memory_value_map)

        s = self._compiled()
        if self.code_file is not None:
            with open(self.code_file, "w") as file:
                file.write(s)

        if self.tracer is not None:
            self.tracer._set_initial_values(
                self.default_value, register_value_map, memory_value_map
            )

        context = {}
        logic_creator = compile(s, "<string>", "exec")
        exec(logic_creator, context)
        self.sim_func = context["sim_func"]

    def _initialize_mems(self, memory_value_map):
        for mem, mem_map in memory_value_map.items():
            if isinstance(mem, RomBlock):
                msg = "error, one or more of the memories in the map is a RomBlock"
                raise PyrtlError(msg)
            name = self._mem_varname(mem)
            self.mems[name] = mem_map.copy()

        for net in self.block.logic_subset("m@"):
            mem = net.op_param[1]
            if self._mem_varname(mem) not in self.mems:
                if isinstance(mem, RomBlock):
                    self.mems[self._mem_varname(mem)] = mem
                else:
                    self.mems[self._mem_varname(mem)] = {}

    def step(self, provided_inputs: dict[str, int] | None = None):
        # Validate and collect simulation inputs.
        if provided_inputs is None:
            provided_inputs = {}
        inputs = {}
        for wire, value in provided_inputs.items():
            wire = (
                self.block.get_wirevector_by_name(wire)
                if isinstance(wire, str)
                else wire
            )
            value = infer_val_and_bitwidth(value, bitwidth=wire.bitwidth).value
            inputs[self._to_name(wire)] = value

        inputs.update(self.regs)
        inputs.update(self.mems)

        # propagate through logic
        self.regs, self.outs, mem_writes = self.sim_func(inputs)

        for mem, addr, value in mem_writes:
            self.mems[mem][addr] = value

        # for tracer compatibility
        self.context = self.outs.copy()
        self.context.update(inputs)  # also gets old register values
        if self.tracer is not None:
            self.tracer.add_fast_step(self)

        # check the rtl assertions
        check_rtl_assertions(self)

    def step_multiple(
        self,
        provided_inputs: dict[str, list[int]] | None = None,
        expected_outputs: dict[str, list[int]] | None = None,
        nsteps: int | None = None,
        file=sys.stdout,
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
            longest = sorted(
                provided_inputs.items(), key=lambda t: len(t[1]), reverse=True
            )[0]
            msteps = len(longest[1])
            if nsteps:
                if nsteps > msteps:
                    msg = (
                        "nsteps is specified but is greater than the number of values "
                        "supplied for each input"
                    )
                    raise PyrtlError(msg)
            else:
                nsteps = msteps

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

        def to_num(v):
            if isinstance(v, str):
                # Don't use infer_val_and_bitwidth because they aren't in Verilog-style
                # format, but are instead in plain decimal.
                return int(v)
            # Don't just call int(v) on all of them since it's nice to retain class info
            # if they were a subclass of int.
            return v

        failed = []
        for i in range(nsteps):
            self.step({w: to_num(v[i]) for w, v in provided_inputs.items()})

            for expvar in expected_outputs:
                expected = expected_outputs[expvar][i]
                if expected == "?":
                    continue
                expected = int(expected)
                actual = self.inspect(expvar)
                if expected != actual:
                    failed.append((i, expvar, expected, actual))

            if failed and stop_after_first_error:
                break

        if failed:
            if stop_after_first_error:
                s = "(stopped after step with first error):"
            else:
                s = "on one or more steps:"
            file.write("Unexpected output " + s + "\n")
            file.write(
                "{:>5} {:>10} {:>8} {:>8}\n".format(
                    "step", "name", "expected", "actual"
                )
            )

            def _sort_tuple(t):
                # Sort by step and then wire name
                return (t[0], _trace_sort_key(t[1]))

            failed_sorted = sorted(failed, key=_sort_tuple)
            for step, name, expected, actual in failed_sorted:
                file.write(f"{step:>5} {name:>10} {expected:>8} {actual:>8}\n")
            file.flush()

    def inspect(self, w: str) -> int:
        try:
            return self.context[self._to_name(w)]
        except AttributeError as exc:
            msg = (
                "No context available. Please run a simulation step in order to "
                "populate values for wires"
            )
            raise PyrtlError(msg) from exc

    def inspect_mem(self, mem: MemBlock) -> dict[int, int]:
        if isinstance(mem, RomBlock):
            msg = "ROM blocks are not stored in the simulation object"
            raise PyrtlError(msg)
        return self.mems[self._mem_varname(mem)]

    def _to_name(self, name):
        """Converts Wires to strings, keeps strings as is"""
        if isinstance(name, WireVector):
            return name.name
        return name

    def _varname(self, val):
        """Converts WireVectors to internal names"""
        return self.internal_names[val.name]

    def _mem_varname(self, val):
        return "fs_mem" + str(val.id)

    def _arg_varname(self, wire):
        """
        Input, Const, and Registers have special input values
        """
        if isinstance(wire, (Input, Register)):
            return "d[" + repr(wire.name) + "]"  # passed in
        if isinstance(wire, Const):
            return str(int(wire.val))  # hardcoded
        return self._varname(wire)

    def _dest_varname(self, wire):
        if isinstance(wire, Output):
            return "outs[" + repr(wire.name) + "]"
        if isinstance(wire, Register):
            return "regs[" + repr(wire.name) + "]"
        return self._varname(wire)

    # Yeah, triple quotes don't respect indentation (aka the 4 spaces on the start of
    # each line is part of the string)
    _prog_start = """def sim_func(d):
    regs = {}
    outs = {}
    mem_ws = []"""

    def _compiled(self):
        """Return a string of the self.block compiled to a block of code that can be
        executed to get a function to execute
        """
        # bitwidth that the dest has to have in order to not need masking.
        no_mask_bitwidth = {
            "w": lambda net: len(net.args[0]),
            "r": lambda net: len(net.args[0]),
            "~": lambda _net: -1,  # bitflips always need masking
            "&": lambda net: len(net.args[0]),
            "|": lambda net: len(net.args[0]),
            "^": lambda net: len(net.args[0]),
            "n": lambda _net: -1,  # bitflips always need masking
            "+": lambda net: len(net.args[0]) + 1,
            "-": lambda _net: -1,  # need to handle negative numbers correctly
            "*": lambda net: len(net.args[0]) + len(net.args[1]),
            "<": lambda _net: 1,
            ">": lambda _net: 1,
            "=": lambda _net: 1,
            "x": lambda net: len(net.args[1]),
            "c": lambda net: sum(len(a) for a in net.args),
            "s": lambda net: len(net.op_param),
            "m": lambda _net: -1,  # just not going to optimize this right now
        }

        # Dev Notes:
        #
        # Because of fast locals in functions in both CPython and PyPy, getting a
        # function to execute makes the code a few times faster than just executing it
        # in the global exec scope.
        prog = [self._prog_start]

        simple_func = {  # OPS
            "w": lambda x: x,
            "r": lambda x: x,
            "~": lambda x: "(~" + x + ")",
            "&": lambda left, right: "(" + left + "&" + right + ")",
            "|": lambda left, right: "(" + left + "|" + right + ")",
            "^": lambda left, right: "(" + left + "^" + right + ")",
            "n": lambda left, right: "(~(" + left + "&" + right + "))",
            "+": lambda left, right: "(" + left + "+" + right + ")",
            "-": lambda left, right: "(" + left + "-" + right + ")",
            "*": lambda left, right: "(" + left + "*" + right + ")",
            "<": lambda left, right: "int(" + left + "<" + right + ")",
            ">": lambda left, right: "int(" + left + ">" + right + ")",
            "=": lambda left, right: "int(" + left + "==" + right + ")",
            "x": lambda sel, f, t: f"({f}) if ({sel}==0) else ({t})",
        }

        def shift(value, direction, shift_amt):
            if shift_amt == 0:
                return value
            return f"({value} {direction} {shift_amt})"

        def make_split(source, split_length, split_start_bit, split_res_start_bit):
            if split_start_bit == 0:
                bit = f"({(1 << split_length) - 1} & {source})"
            elif len(net.args[0]) - split_start_bit == split_length:
                bit = f"({source} >> {split_start_bit})"
            else:
                bit = f"({(1 << split_length) - 1} & ({source} >> {split_start_bit}))"
            return shift(bit, "<<", split_res_start_bit)

        for net in self.block:
            if net.op in simple_func:
                argvals = (self._arg_varname(arg) for arg in net.args)
                expr = simple_func[net.op](*argvals)
            elif net.op == "c":
                expr = ""
                for i in range(len(net.args)):
                    if expr != "":
                        expr += " | "
                    shiftby = sum(len(j) for j in net.args[i + 1 :])
                    expr += shift(self._arg_varname(net.args[i]), "<<", shiftby)
            elif net.op == "s":
                source = self._arg_varname(net.args[0])
                expr = ""
                split_length = 0
                split_start_bit = -2
                split_res_start_bit = -1

                for i, b in enumerate(net.op_param):
                    if b != split_start_bit + split_length:
                        if split_start_bit >= 0:
                            # create a wire
                            expr += (
                                make_split(
                                    source,
                                    split_length,
                                    split_start_bit,
                                    split_res_start_bit,
                                )
                                + "|"
                            )
                        split_length = 1
                        split_start_bit = b
                        split_res_start_bit = i
                    else:
                        split_length += 1
                expr += make_split(
                    source, split_length, split_start_bit, split_res_start_bit
                )
            elif net.op == "m":
                read_addr = self._arg_varname(net.args[0])
                mem = net.op_param[1]
                if isinstance(net.op_param[1], RomBlock):
                    expr = f'd["{self._mem_varname(mem)}"]._get_read_data({read_addr})'
                else:  # memories act async for reads
                    expr = (
                        f'd["{self._mem_varname(mem)}"].get('
                        f"{read_addr}, {self.default_value})"
                    )
            elif net.op == "@":
                mem = self._mem_varname(net.op_param[1])
                write_addr, write_val, write_enable = (
                    self._arg_varname(a) for a in net.args
                )
                prog.append(f"    if {write_enable}:")
                prog.append(
                    f'        mem_ws.append(("{mem}", {write_addr}, {write_val}))'
                )
                continue  # memwrites are special
            else:
                msg = f'FastSimulation cannot handle primitive "{net.op}"'
                raise PyrtlError(msg)

            # prog.append('    #  ' + str(net))
            result = self._dest_varname(net.dests[0])
            if len(net.dests[0]) == no_mask_bitwidth[net.op](net):
                prog.append(f"    {result} = {expr}")
            else:
                mask = str(net.dests[0].bitmask)
                prog.append(f"    {result} = {mask} & {expr}")

        # add traced wires to dict
        if self.tracer is not None:
            for wire_name in self.tracer.trace:
                wire = self.block.wirevector_by_name[wire_name]
                if not isinstance(wire, (Input, Register, Output)):
                    value = (
                        int(wire.val)
                        if isinstance(wire, Const)
                        else self._varname(wire)
                    )
                    prog.append(f'    outs["{wire_name}"] = {value}')

        prog.append("    return regs, outs, mem_ws")
        return "\n".join(prog)


# ----------------------------------------------------------------
#    ___  __        __   ___
#     |  |__)  /\  /  ` |__
#     |  |  \ /~~\ \__, |___
#


class WaveRenderer:
    """Render a SimulationTrace to the terminal.

    Most users should not interact with this class directly, unless they are customizing
    trace appearance.

    Export the ``PYRTL_RENDERER`` environment variable to change the default renderer.
    See the documentation for :class:`RendererConstants`' subclasses for valid values of
    ``PYRTL_RENDERER``, as well as sample screenshots.

    Try `renderer-demo.py
    <https://github.com/UCSBarchlab/PyRTL/blob/development/examples/renderer-demo.py>`_,
    which renders traces with different options, to see what works in your terminal.
    """

    def __init__(self, constants: RendererConstants):
        """Instantiate a ``WaveRenderer``.

        :param constants: Subclass of :class:`RendererConstants` that specifies the
            ASCII/Unicode characters to use for rendering waveforms.
        """
        self.constants = constants

    def render_ruler_segment(
        self, n: int, cycle_len: int, segment_size: int, maxtracelen: int
    ):
        """Render a major tick padded to segment_size.

        :param n: Cycle number for the major tick mark.
        :param cycle_len: Rendered length of each cycle, in characters.
        :param segment_size: Length between major tick marks, in cycles.
        :param maxtracelen: Length of the longest trace, in cycles.
        """
        # Render a major tick mark followed by the cycle number (n).
        major_tick = self.constants._tick + str(n)
        # If the cycle number can't fit in this segment, drop most significant
        # digits of the cycle number until it fits.
        excess_characters = len(major_tick) - cycle_len * segment_size
        if excess_characters > 0:
            major_tick = self.constants._tick + str(n)[excess_characters:]

        # Do not render past maxtracelen.
        if n + segment_size >= maxtracelen:
            segment_size = maxtracelen - n
        # Pad major_tick out to segment_size.
        return major_tick.ljust(cycle_len * segment_size)

    def val_to_str(
        self,
        value: int,
        wire: WireVector,
        repr_func: Callable[[int], str],
        repr_per_name: dict[str, Callable[[int], str]],
    ) -> str:
        """Return a string representing 'value'.

        :param value: The value to convert to string.
        :param wire: Wire that produced this value.
        :param repr_func: function to use for representing the current_val; examples are
            'hex', 'oct', 'bin', 'str' (for decimal), or the function returned by
            :func:`enum_name`. Defaults to 'hex'.
        :param repr_per_name: Map from signal name to a function that takes in the
            signal's value and returns a user-defined representation. If a signal name
            is not found in the map, the argument `repr_func` will be used instead.

        :return: a string representing 'value'.
        """
        f = repr_per_name.get(wire.name)

        def invoke_f(f, value):
            if f is val_to_signed_integer:
                return str(val_to_signed_integer(value=value, bitwidth=wire.bitwidth))
            return str(f(value))

        if f is not None:
            return invoke_f(f, value)
        return invoke_f(repr_func, value)

    def render_val(
        self,
        w: WireVector,
        prior_val: int,
        current_val: int,
        symbol_len: int,
        cycle_len: int,
        repr_func: Callable[[int], str],
        repr_per_name: dict[str, Callable[[int], str]],
        prev_line: bool,
        is_last: bool,
    ) -> str:
        """Return a string encoding the given value in a waveform.

        Returns a string of printed length symbol_len that will draw the representation
        of current_val. The input prior_val is used to render transitions.

        :param w: The WireVector we are rendering to a waveform
        :param prior_val: Last value rendered. None if there was no last value.
        :param current_val: the value to be rendered
        :param symbol_len: Width of each value, in characters.
        :param cycle_len: Width of each cycle, in characters.
        :param repr_func: function to use for representing the current_val; examples are
            'hex', 'oct', 'bin', 'str' (for decimal), or the function returned by
            :func:`enum_name`. Defaults to 'hex'.
        :param repr_per_name: Map from signal name to a function that takes in the
            signal's value and returns a user-defined representation. If a signal name
            is not found in the map, the argument `repr_func` will be used instead.
        :param prev_line: If True, render the gap between signals. If False, render the
            main signal. This is useful for rendering signals across two lines, see the
            _prev_line* fields in RendererConstants.
        :param is_last: If True, current_val is in the last cycle.
        """
        if len(w) > 1 or w.name in repr_per_name:
            # Render values in boxes for multi-bit wires ("bus"), or single-bit wires
            # with a specific representation.
            #
            # We display multi-wire zero values as a centered horizontal line when a
            # specific `repr_per_name` is not requested for this trace, and a standard
            # numeric format is requested.
            flat_zero = w.name not in repr_per_name and (
                repr_func is hex
                or repr_func is oct
                or repr_func is int
                or repr_func is str
                or repr_func is bin
                or repr_func is val_to_signed_integer
            )
            if prev_line:
                # Bus wires are currently never rendered across multiple lines.
                return ""

            out = ""
            if current_val != prior_val:
                if prior_val is not None:
                    if flat_zero and prior_val == 0:
                        # Value changed from zero to non-zero.
                        out += self.constants._zero_x
                    elif flat_zero and current_val == 0:
                        # Value changed from non-zero to zero.
                        out += self.constants._x_zero
                    else:
                        # Value changed from non-zero to non-zero.
                        out += self.constants._x
                if flat_zero and current_val == 0:
                    # Display the current zero value.
                    out += self.constants._zero * symbol_len
                else:
                    if prior_val is None:
                        out += self.constants._bus_start
                    # Display the current non-zero value.
                    out += (
                        self.val_to_str(current_val, w, repr_func, repr_per_name)
                        .rstrip("L")
                        .ljust(symbol_len)[:symbol_len]
                    )
                    if is_last:
                        out += self.constants._bus_stop
            elif flat_zero and current_val == 0:
                # Extend an unchanged zero value into the current cycle.
                out += self.constants._zero * cycle_len
            else:
                # Extend an unchanged non-zero value into the current cycle.
                out += " " * cycle_len
                if is_last:
                    out += self.constants._bus_stop
        else:
            # Render lines for single-bit wires.
            if prev_line:
                low = self.constants._prev_line_low
                high = self.constants._prev_line_high
                up = self.constants._prev_line_up
                down = self.constants._prev_line_down
            else:
                low = self.constants._low
                high = self.constants._high
                up = self.constants._up
                down = self.constants._down

            pretty_map = {
                (None, 0): low * symbol_len,
                (None, 1): high * symbol_len,
                (0, 0): low * cycle_len,
                (0, 1): up + high * symbol_len,
                (1, 0): down + low * symbol_len,
                (1, 1): high * cycle_len,
            }
            out = pretty_map[(prior_val, current_val)]
        return out


class RendererConstants:
    """Abstract base class for renderer constants.

    These constants determine which characters are used to render waveforms in a
    terminal.

    .. inheritance-diagram:: pyrtl.simulation.Utf8RendererConstants
                             pyrtl.simulation.Utf8AltRendererConstants
                             pyrtl.simulation.PowerlineRendererConstants
                             pyrtl.simulation.Cp437RendererConstants
                             pyrtl.simulation.AsciiRendererConstants
        :parts: 1

    """

    # Print _tick before rendering a ruler segment. Must have a display length of 1
    # character.
    _tick = ""

    # Print _up when a binary wire transitions from low to high. Print _down when a
    # binary wire transitions from high to low. _up and _down must have display length
    # of _chars_between_cycles characters.
    _up, _down = "", ""

    # Print _low when a binary wire maintains a low value, and print _high when a binary
    # wire maintains a high value. _low and _high must have display length of 1
    # character.
    _low, _high = "", ""

    # These are like _up, _down, _low, _high, except they are printed on the previous
    # line. These are useful for displaying a binary wire across two lines.
    _prev_line_up, _prev_line_down = "", ""
    _prev_line_low, _prev_line_high = "", ""

    # Print _bus_start before rendering a bus wire, and print _bus_stop after rendering
    # a bus wire. _bus_start and _bus_stop must have zero display length characters.
    # Escape codes never count towards display length.
    _bus_start, _bus_stop = "", ""

    # Print _x when a bus wire changes from one non-zero value to another non-zero
    # value. _x must have display length of _chars_between_cycles characters.
    _x = ""

    # Print _zero_x when a bus wire changes from a zero value to a non-zero value.
    # _zero_x must have display length of _chars_between_cycles characters.
    _zero_x = ""

    # Print _x_zero when a bus wire changes from a non-zero value to a zero value.
    # _x_zero must have display length of _chars_between_cycles characters.
    _x_zero = ""

    # Print _zero when a bus wire maintains a zero value. _zero must have display length
    # of 1 character.
    _zero = ""

    # Number of characters between cycles. The cycle changes halfway between this width.
    # The first half of this width belongs to the previous cycle and the second half of
    # this width belongs to the next cycle.
    _chars_between_cycles = 0


class Utf8RendererConstants(RendererConstants):
    """UTF-8 renderer constants. These should work in most terminals.

    Single-bit :class:`WireVectors<WireVector>` are rendered as square waveforms, with
    vertical rising and falling edges. Multi-bit :class:`WireVector` values are rendered
    in reverse-video rectangles.

    This is the default renderer on non-Windows platforms.

    Enable this renderer by default by setting the ``PYRTL_RENDERER`` environment
    variable to ``utf-8``::

        export PYRTL_RENDERER=utf-8

    .. image:: ../docs/screenshots/pyrtl-renderer-demo-utf-8.png
    """

    # Start reverse-video, reset all attributes
    _bus_start, _bus_stop = "\x1b[7m", "\x1b[0m"

    _tick = "▕"

    _up, _down = "▁▏", "▕▁"
    _low, _high = "▁", " "

    _prev_line_up, _prev_line_down = " ▁", "▁ "
    _prev_line_low, _prev_line_high = " ", "▁"

    _x = "▕ "
    _zero_x = "─" + _bus_start + "▏"
    _x_zero = "▕" + _bus_stop + "─"
    _zero = "─"

    # Number of characters needed between cycles. The cycle changes halfway between this
    # width (2), so the first character belongs to the previous cycle and the second
    # character belongs to the next cycle.
    _chars_between_cycles = 2


class Utf8AltRendererConstants(RendererConstants):
    """Alternative UTF-8 renderer constants.

    Single-bit :class:`WireVectors<WireVector>` are rendered as waveforms with sloped
    rising and falling edges. Multi-bit :class:`WireVector` values are rendered in
    reverse-video rectangles.

    Compared to :class:`Utf8RendererConstants`, this renderer is more compact because it
    uses one character between cycles instead of two.

    Enable this renderer by default by setting the ``PYRTL_RENDERER`` environment
    variable to ``utf-8-alt``::

        export PYRTL_RENDERER=utf-8-alt

    .. image:: ../docs/screenshots/pyrtl-renderer-demo-utf-8-alt.png
    """

    # Start reverse-video, reset all attributes
    _bus_start, _bus_stop = "\x1b[7m", "\x1b[0m"

    _tick = "│"

    _up, _down = "╱", "╲"
    _low, _high = "▁", "▔"

    _x = _bus_stop + " " + _bus_start
    _zero_x = " " + _bus_start
    _x_zero = _bus_stop + " "
    _zero = "─"

    # Number of characters needed between cycles. The cycle changes halfway between this
    # width (1), so the first character belongs to the previous cycle and the second
    # character belongs to the next cycle.
    _chars_between_cycles = 1


class PowerlineRendererConstants(Utf8RendererConstants):
    """Powerline renderer constants. Font must include powerline glyphs.

    This render's appearance is the most similar to a traditional logic analyzer.
    Single-bit :class:`WireVectors<WireVector>` are rendered as square waveforms, with
    vertical rising and falling edges. Multi-bit :class:`WireVector` values are rendered
    in reverse-video hexagons.

    This renderer requires a `terminal font that supports Powerline glyphs
    <https://github.com/powerline/fonts>`_

    Enable this renderer by default by setting the ``PYRTL_RENDERER`` environment
    variable to ``powerline``::

        export PYRTL_RENDERER=powerline

    .. image:: ../docs/screenshots/pyrtl-renderer-demo-powerline.png
    """

    # Start reverse-video, reset all attributes
    _bus_start, _bus_stop = "\x1b[7m", "\x1b[0m"

    _x = _bus_stop + "" + _bus_start
    _zero_x = "─" + _bus_start
    _x_zero = _bus_stop + "─"
    _zero = "─"


class Cp437RendererConstants(RendererConstants):
    """Code page 437 renderer constants (for windows ``cmd`` compatibility).

    Single-bit :class:`WireVectors<WireVector>` are rendered as square waveforms, with
    vertical rising and falling edges. Multi-bit :class:`WireVector` values are rendered
    between vertical bars.

    `Code page 437 <https://en.wikipedia.org/wiki/Code_page_437>`_ is also known as
    8-bit ASCII. This is the default renderer on Windows platforms.

    Compared to :class:`Utf8RendererConstants`, this renderer is more compact because it
    uses one character between cycles instead of two, but the wire names are vertically
    aligned at the bottom of each waveform.

    Enable this renderer by default by setting the ``PYRTL_RENDERER`` environment
    variable to ``cp437``::

        export PYRTL_RENDERER=cp437

    .. image:: ../docs/screenshots/pyrtl-renderer-demo-cp437.png
    """

    _tick = "│"

    _up, _down = "┘", "└"
    _low, _high = "─", " "

    _prev_line_up, _prev_line_down = "┌", "┐"
    _prev_line_low, _prev_line_high = " ", "─"

    _x = "│"
    _zero_x = "┤"
    _x_zero = "├"
    _zero = "─"

    _chars_between_cycles = 1


class AsciiRendererConstants(RendererConstants):
    """7-bit ASCII renderer constants. These should work anywhere.

    Single-bit :class:`WireVectors<WireVector>` are rendered as waveforms with sloped
    rising and falling edges. Multi-bit :class:`WireVector` values are rendered between
    vertical bars.

    Enable this renderer by default by setting the ``PYRTL_RENDERER`` environment
    variable to ``ascii``::

        export PYRTL_RENDERER=ascii

    .. image:: ../docs/screenshots/pyrtl-renderer-demo-ascii.png
    """

    _tick = "|"

    _up, _down = ",", "."
    _low, _high = "_", "-"

    _x = "|"
    _zero_x = "|"
    _x_zero = "|"
    _zero = "-"

    _chars_between_cycles = 1


def default_renderer() -> WaveRenderer:
    """Select renderer constants based on environment or auto-detection."""
    renderer = ""
    if "PYRTL_RENDERER" in os.environ:
        # Use user-specified renderer constants.
        renderer = os.environ["PYRTL_RENDERER"]
    elif "PROMPT" in os.environ:
        # Windows Command Prompt, use code page 437 renderer constants.
        renderer = "cp437"
    else:
        # Use UTF-8 renderer constants by default.
        renderer = "utf-8"

    renderer_map = {
        "powerline": PowerlineRendererConstants(),
        "utf-8": Utf8RendererConstants(),
        "utf-8-alt": Utf8AltRendererConstants(),
        "cp437": Cp437RendererConstants(),
        "ascii": AsciiRendererConstants(),
    }

    if renderer in renderer_map:
        constants = renderer_map[renderer]
    else:
        print(
            f"WARNING: Unsupported $PYRTL_RENDERER value '{renderer}' supported values "
            f"are ({' '.join(renderer_map.keys())}). Defaulting to utf-8"
        )
        constants = Utf8RendererConstants()

    return WaveRenderer(constants)


def _trace_sort_key(w):
    def tryint(s):
        try:
            return int(s)
        except ValueError:
            return s

    return [tryint(c) for c in re.split("([0-9]+)", w)]


class TraceStorage(Mapping):
    __slots__ = ("__data",)

    def __init__(self, wvs):
        self.__data = {wv.name: [] for wv in wvs}

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return iter(self.__data)

    def __getitem__(self, key):
        if isinstance(key, WireVector):
            warnings.warn(
                "Access to trace by WireVector instead of name is deprecated.",
                DeprecationWarning,
                stacklevel=2,
            )
            key = key.name
        if key not in self.__data:
            msg = (
                f'Cannot find "{key}" in trace -- if using CompiledSim, you may be '
                "attempting to access internal states but only inputs/outputs are "
                "available."
            )
            raise PyrtlError(msg)
        return self.__data[key]


_default_renderer = default_renderer()


class SimulationTrace:
    """Storage and presentation of simulation waveforms.

    :class:`Simulation` writes data from each simulation cycle to its
    :attr:`Simulation.tracer`, which is an instance of ``SimulationTrace``.

    Users can visualize this simulation data with methods like :meth:`render_trace`.
    """

    trace: dict[str, list[int]]
    """
    A :class:`dict` mapping from a :class:`WireVector`'s name to a :class:`list` of its
    values in each cycle.
    """

    def __init__(
        self, wires_to_track: list[WireVector] | None = None, block: Block = None
    ):
        """Creates a new Simulation Trace

        :param wires_to_track: The wires that the tracer should track. If unspecified,
            will track all explicitly-named wires. If set to ``'all'``, will track all
            wires, including internal wires.
        :param block: :class:`Block` containing logic to trace. Defaults to the
            :ref:`working_block`.
        """
        self.block = working_block(block)

        def is_internal_name(name):
            return (
                name.startswith("tmp")
                or name.startswith("const_")
                # or name.startswith('synth_')
                or name.endswith("'")
            )

        if wires_to_track is None:
            wires_to_track = [
                w for w in self.block.wirevector_set if not is_internal_name(w.name)
            ]
        elif wires_to_track == "all":
            wires_to_track = self.block.wirevector_set

        non_const_tracked = list(
            filter(lambda w: not isinstance(w, Const), wires_to_track)
        )
        if not non_const_tracked:
            msg = (
                "There needs to be at least one named non-constant wire for simulation "
                "to be useful"
            )
            raise PyrtlError(msg)
        self.wires_to_track = wires_to_track
        self.trace = TraceStorage(wires_to_track)
        self._wires = {wv.name: wv for wv in wires_to_track}
        # remember for initializing during Verilog testbench output
        self.default_value = 0
        self.register_value_map = {}
        self.memory_value_map = {}

    def __len__(self):
        """Return the current length of the trace in cycles."""
        if len(self.trace) == 0:
            msg = "error, length of trace undefined if no signals tracked"
            raise PyrtlError(msg)
        # return the length of the list of some element in the dictionary (all should be
        # the same)
        wire, value_list = next(x for x in self.trace.items())
        return len(value_list)

    def add_step(self, value_map):
        """Add the values in ``value_map`` to the end of the trace."""
        if len(self.trace) == 0:
            msg = (
                "error, simulation trace needs at least 1 signal to track (by default, "
                "unnamed signals are not traced -- try either passing a name to a "
                'WireVector or setting a "wirevector_subset" option)'
            )
            raise PyrtlError(msg)
        for wire_name in self.trace:
            tracelist = self.trace[wire_name]
            wirevec = self._wires[wire_name]
            tracelist.append(value_map[wirevec])

    def add_step_named(self, value_map):
        for wire_name in value_map:
            if wire_name in self.trace:
                self.trace[wire_name].append(value_map[wire_name])

    def add_fast_step(self, fastsim):
        """Add the ``fastsim`` context to the trace."""
        for wire_name in self.trace:
            self.trace[wire_name].append(fastsim.context[wire_name])

    def print_trace(self, file=sys.stdout, base: int = 10, compact: bool = False):
        """Prints a list of wires and their current values.

        :param base: The base the values are to be printed in.
        :param compact: Whether to omit spaces in output lines.
        """
        if len(self.trace) == 0:
            msg = "error, cannot print an empty trace"
            raise PyrtlError(msg)
        if base not in (2, 8, 10, 16):
            msg = "please choose a valid base (2,8,10,16)"
            raise PyrtlError(msg)

        basekey = {2: "b", 8: "o", 10: "d", 16: "x"}[base]
        ident_len = max(len(w) for w in self.trace)

        if compact:
            for w in sorted(self.trace, key=_trace_sort_key):
                vals = "".join("{0:{1}}".format(x, basekey) for x in self.trace[w])
                file.write(w.rjust(ident_len) + " " + vals + "\n")
        else:
            maxlenval = max(
                len("{0:{1}}".format(x, basekey))
                for w in self.trace
                for x in self.trace[w]
            )
            file.write(" " * (ident_len - 3) + f"--- Values in base {base} ---\n")
            for w in sorted(self.trace, key=_trace_sort_key):
                vals = " ".join(
                    "{0:>{1}{2}}".format(x, maxlenval, basekey) for x in self.trace[w]
                )
                file.write(w.ljust(ident_len + 1) + vals + "\n")

        file.flush()

    def print_vcd(self, file=sys.stdout, include_clock=False):
        """Print the trace out as a VCD File for use in other tools.

        Dumps the current trace to file as a `value change dump
        <https://en.wikipedia.org/wiki/Value_change_dump>`_ file. Examples::

            sim_trace.print_vcd()
            sim_trace.print_vcd("my_waveform.vcd", include_clock=True)

        :param file: File to open and output vcd dump to. Defaults to ``stdout``.
        :param include_clock: Boolean specifying if the implicit ``clk`` should be
            included. Defaults to ``False``.
        """
        self.internal_names = _VerilogSanitizer("_vcd_tmp_")
        for wire in self.wires_to_track:
            self.internal_names.make_valid_string(wire.name)

        def _varname(wireName):
            """Converts WireVector names to internal names"""
            return self.internal_names[wireName]

        print("$timescale 1ns $end", file=file)
        print("$scope module logic $end", file=file)

        def print_trace_strs(time):
            for wn in sorted(self.trace, key=_trace_sort_key):
                print(
                    " ".join([str(bin(self.trace[wn][time]))[1:], _varname(wn)]),
                    file=file,
                )

        # dump variables
        if include_clock:
            print("$var wire 1 clk clk $end", file=file)
        for wn in sorted(self.trace, key=_trace_sort_key):
            print(
                " ".join(
                    [
                        "$var",
                        "wire",
                        str(self._wires[wn].bitwidth),
                        _varname(wn),
                        _varname(wn),
                        "$end",
                    ]
                ),
                file=file,
            )
        print("$upscope $end", file=file)
        print("$enddefinitions $end", file=file)
        print("$dumpvars", file=file)
        print_trace_strs(0)
        print("$end", file=file)

        # dump values
        endtime = max([len(self.trace[w]) for w in self.trace])
        for timestamp in range(endtime):
            print("".join(["#", str(timestamp * 10)]), file=file)
            print_trace_strs(timestamp)
            if include_clock:
                print("b1 clk", file=file)
                print(file=file)
                print("".join(["#", str(timestamp * 10 + 5)]), file=file)
                print("b0 clk", file=file)
            print(file=file)
        print("".join(["#", str(endtime * 10)]), file=file)
        file.flush()

    def render_trace(
        self,
        trace_list: list[str] | None = None,
        file=sys.stdout,
        renderer: WaveRenderer = _default_renderer,
        symbol_len: int | None = None,
        repr_func: Callable[[int], str] = hex,
        repr_per_name: dict[str, Callable[[int], str]] | None = None,
        segment_size: int = 1,
    ):
        """Render the trace to a file using unicode and ASCII escape sequences.

        The resulting output can be viewed directly on the terminal or viewed with
        :program:`less -R` which should handle the ASCII escape sequences used in
        rendering.

        :param trace_list: A list of signal names to be output in the specified order.
        :param file: The place to write output, default to stdout.
        :param renderer: An object that translates traces into output bytes.
        :param symbol_len: The "length" of each rendered value in characters. If
            ``None``, the length will be automatically set such that the largest
            represented value fits.
        :param repr_func: Function to use for representing each value in the trace.
            Examples include :func:`hex`, :func:`oct`, :func:`bin`, and :class:`str`
            (for decimal), :func:`val_to_signed_integer` (for signed decimal) or the
            function returned by :func:`enum_name` (for :class:`~enum.IntEnum`).
            Defaults to :func:`hex`.
        :param repr_per_name: Map from signal name to a function that takes in the
            signal's value and returns a user-defined representation. If a signal name
            is not found in the map, the argument ``repr_func`` will be used instead.
        :param segment_size: Traces are broken in the segments of this number of cycles.
        """
        if repr_per_name is None:
            repr_per_name = {}
        if _currently_in_jupyter_notebook():
            from IPython.display import (
                HTML,
                Javascript,
                display,
            )

            from pyrtl.visualization import trace_to_html

            htmlstring = trace_to_html(
                self, trace_list=trace_list, sortkey=_trace_sort_key
            )
            html_elem = HTML(htmlstring)
            display(html_elem)
            # print(htmlstring)
            js_stuff = """
            $.when(
            $.getScript("https://cdnjs.cloudflare.com/ajax/libs/wavedrom/1.6.2/skins/default.js"),
            $.getScript("https://cdnjs.cloudflare.com/ajax/libs/wavedrom/1.6.2/wavedrom.min.js"),
            $.Deferred(function( deferred ){
                $( deferred.resolve );
            })).done(function(){
                WaveDrom.ProcessAll();
            });"""
            display(Javascript(js_stuff))
        else:
            self.render_trace_to_text(
                trace_list=trace_list,
                file=file,
                renderer=renderer,
                symbol_len=symbol_len,
                repr_func=repr_func,
                repr_per_name=repr_per_name,
                segment_size=segment_size,
            )

    def render_trace_to_text(
        self,
        trace_list,
        file,
        renderer,
        symbol_len,
        repr_func,
        repr_per_name,
        segment_size,
    ):
        def formatted_trace_line(wire, trace):
            first_trace_line = ""
            second_trace_line = ""
            prior_val = None
            for i in range(len(trace)):
                # There is no cycle change before the first cycle or after the last
                # cycle, so the first and last cycles may have additional width. These
                # additional widths make each cycle line up under the ruler, and appear
                # the same length.
                additional_symbol_len = 0
                additional_cycle_len = 0
                half_chars_between_cycles = math.floor(
                    renderer.constants._chars_between_cycles / 2
                )
                is_first = i == 0
                is_last = i == len(trace) - 1
                if is_last:
                    additional_cycle_len = half_chars_between_cycles
                if is_first or is_last:
                    additional_symbol_len = half_chars_between_cycles
                first_trace_line += renderer.render_val(
                    self._wires[wire],
                    prior_val,
                    trace[i],
                    symbol_len + additional_symbol_len,
                    cycle_len + additional_cycle_len,
                    repr_func,
                    repr_per_name,
                    prev_line=True,
                    is_last=is_last,
                )
                second_trace_line += renderer.render_val(
                    self._wires[wire],
                    prior_val,
                    trace[i],
                    symbol_len + additional_symbol_len,
                    cycle_len + additional_cycle_len,
                    repr_func,
                    repr_per_name,
                    prev_line=False,
                    is_last=is_last,
                )
                prior_val = trace[i]
            heading_gap = " " * (maxnamelen + 1)
            heading = wire.rjust(maxnamelen) + " "
            return heading_gap + first_trace_line + "\n" + heading + second_trace_line

        # default to printing all signals in sorted order
        if trace_list is None:
            trace_list = sorted(self.trace, key=_trace_sort_key)
        elif any(isinstance(x, WireVector) for x in trace_list):
            warnings.warn(
                "Access to trace by WireVector instead of name is deprecated.",
                DeprecationWarning,
                stacklevel=2,
            )
            trace_list = [getattr(x, "name", x) for x in trace_list]

        if not trace_list:
            msg = (
                "Empty trace list. This may have occurred because untraceable wires "
                "were removed prior to simulation, if a CompiledSimulation was used."
            )
            raise PyrtlError(msg)

        if symbol_len is None:
            max_symbol_len = 0
            for trace_name in trace_list:
                trace = self.trace[trace_name]
                current_symbol_len = max(
                    len(
                        renderer.val_to_str(
                            v, self._wires[trace_name], repr_func, repr_per_name
                        )
                    )
                    for v in trace
                )
                max_symbol_len = max(max_symbol_len, current_symbol_len)
            symbol_len = max_symbol_len

        cycle_len = symbol_len + renderer.constants._chars_between_cycles

        # print the 'ruler' which is just a list of 'ticks' mapped by the pretty map
        maxnamelen = max(len(trace_name) for trace_name in trace_list)
        maxtracelen = max(len(self.trace[trace_name]) for trace_name in trace_list)
        if segment_size is None:
            segment_size = maxtracelen
        spaces = " " * (maxnamelen)
        ticks = [
            renderer.render_ruler_segment(n, cycle_len, segment_size, maxtracelen)
            for n in range(0, maxtracelen, segment_size)
        ]
        print(spaces + "".join(ticks), file=file)

        # now all the traces
        for trace_name in trace_list:
            print(formatted_trace_line(trace_name, self.trace[trace_name]), file=file)

    def _set_initial_values(
        self,
        default_value: int,
        register_value_map: dict[Register, int],
        memory_value_map: dict[MemBlock, dict[int, int]],
    ):
        """Remember the default values that were used when starting the trace.

        This is needed when using this trace for outputting a Verilog testbench, and is
        automatically called during simulation.

        :param default_value: Default value to be used for all registers and memory
            locations if not found in the other passed in maps
        :param register_value_map: Default value for each ``Register``. Maps from
            ``Register`` to the ``Register``'s initial value.
        :param memory_value_map: Default value for each ``MemBlock``. Maps from
            ``MemBlock`` to a ``{addr: data}`` ``dict`` with the ``MemBlock``'s initial
            values.
        """
        self.default_value = default_value
        self.register_value_map = register_value_map
        self.memory_value_map = memory_value_map

    def print_perf_counters(self, *trace_names: str, file=sys.stdout):
        """Print performance counter statistics for ``trace_names``.

        This function prints the number of cycles where each trace's value is one. This
        is useful for counting the number of times important events occur in a
        simulation, such as cache misses and branch mispredictions.

        :param trace_names: List of trace names. Each trace must be a single-bit wire.
        :param file: The place to write output, defaults to stdout.
        """
        name_values = []
        for trace_name in trace_names:
            wire_length = len(self._wires[trace_name])
            if wire_length != 1:
                msg = (
                    "print_perf_counters can only be used with single-bit wires but "
                    f"wire {trace_name} has bitwidth {wire_length}"
                )
                raise PyrtlError(msg)

            name_values.append([trace_name, str(sum(self.trace[trace_name]))])

        max_name_length = max(len(name) for name, value in name_values)
        max_value_length = max(len(value) for name, value in name_values)
        for name, value in name_values:
            print(name.rjust(max_name_length), value.rjust(max_value_length), file=file)


def enum_name(EnumClass: type) -> Callable[[int], str]:
    """Returns a function that returns the name of an :class:`enum.IntEnum` value.

    .. doctest only::

        >>> import pyrtl
        >>> import enum
        >>> pyrtl.reset_working_block()

    Use ``enum_name`` as a ``repr_func`` or ``repr_per_name`` for
    :meth:`SimulationTrace.render_trace` to display :class:`enum.IntEnum` names in
    traces, instead of their numeric value. Example::

        >>> class State(enum.IntEnum):
        ...     FOO = 0
        ...     BAR = 1
        >>> state = pyrtl.Input(name="state", bitwidth=1)

        >>> sim = pyrtl.Simulation()
        >>> sim.step_multiple({"state": [State.FOO, State.BAR]})
        >>> sim.tracer.render_trace(repr_per_name={"state": pyrtl.enum_name(State)})

    Which prints::

             │0  │1

        state FOO│BAR

    :param EnumClass: ``enum`` to convert. This is the enum class, like ``State``, not
        an enum value, like ``State.FOO`` or ``1``.

    :return: A function that accepts an enum value, like ``State.FOO`` or ``1``, and
             returns the value's name as a string, like ``"FOO"``.
    """

    def value_to_name(value: int) -> str:
        return EnumClass(value).name

    return value_to_name
