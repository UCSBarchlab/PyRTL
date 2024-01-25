"""Classes for executing and tracing circuit simulations."""

import copy
import math
import numbers
import os
import re
import sys

from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .core import working_block, PostSynthBlock, _PythonSanitizer
from .wire import Input, Register, Const, Output, WireVector
from .memory import RomBlock
from .helperfuncs import check_rtl_assertions, _currently_in_jupyter_notebook
from .importexport import _VerilogSanitizer

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

# ----------------------------------------------------------------
#    __                         ___    __
#   /__` |  |\/| |  | |     /\   |  | /  \ |\ |
#   .__/ |  |  | \__/ |___ /~~\  |  | \__/ | \|
#


class Simulation(object):
    """A class for simulating blocks of logic step by step.

    A Simulation step works as follows:

    1. Registers are updated:

        1. (If this is the first step) With the default values passed in
           to the Simulation during instantiation and/or any reset values
           specified in the individual registers.
        2. (Otherwise) With their next values calculated in the previous step
           (``r`` logic nets).

    2. The new values of these registers as well as the values of block inputs
       are propagated through the combinational logic.
    3. Memory writes are performed (``@`` logic nets).
    4. The current values of all wires are recorded in the trace.
    5. The next values for the registers are saved, ready to be applied at the
       beginning of the next step.

    Note that the register values saved in the trace after each simulation step
    are from *before* the register has latched in its newly calculated values,
    since that latching in occurs at the beginning of the *next* step.

    In addition to the functions methods listed below, it is sometimes
    useful to reach into this class and access internal state directly.
    Of particular usefulness are:

    * ``.tracer``: stores the :class:`.SimulationTrace` in which results are stored
    * ``.value``: a map from every signal in the block to its current simulation value
    * ``.regvalue``: a map from register to its value on the next tick
    * ``.memvalue``: a map from memid to a dictionary of address: value
    """

    simple_func = {  # OPS
        'w': lambda x: x,
        '~': lambda x: ~x,
        '&': lambda left, right: left & right,
        '|': lambda left, right: left | right,
        '^': lambda left, right: left ^ right,
        'n': lambda left, right: ~(left & right),
        '+': lambda left, right: left + right,
        '-': lambda left, right: left - right,
        '*': lambda left, right: left * right,
        '<': lambda left, right: int(left < right),
        '>': lambda left, right: int(left > right),
        '=': lambda left, right: int(left == right),
        'x': lambda sel, f, t: f if (sel == 0) else t
    }

    def __init__(
            self, tracer=True, register_value_map={}, memory_value_map={},
            default_value=0, block=None):
        """Creates a new circuit simulator.

        :param SimulationTrace tracer: Stores execution results.  Defaults to a
            new :class:`.SimulationTrace` with no params passed to it.  If None
            is passed, no tracer is instantiated (which is good for long
            running simulations).  If the default (true) is passed, Simulation
            will create a new tracer automatically which can be referenced by
            the member variable ``.tracer``
        :param dict[Register, int] register_value_map: Defines the initial
            value for the registers specified; overrides the registers's
            ``reset_value``.
        :param memory_value_map: Defines initial values for many
            addresses in a single or multiple memory. Format: {Memory: {address: Value}}.
            Memory is a memory block, address is the address of a value
        :param int default_value: The value that all unspecified registers and
            memories will initialize to (default 0). For registers, this is the
            value that will be used if the particular register doesn't have a
            specified ``reset_value``, and isn't found in the
            `register_value_map`.
        :param Block block: the hardware block to be traced (which might be of
            type :class:`.PostSynthBlock`).  Defaults to the working block

        Warning: Simulation initializes some things when called with
        :meth:`~.Simulation.__init__`, so changing items in the block for
        Simulation will likely break the simulation.

        """

        """ Creates object and initializes it with self._initialize.
        register_value_map, memory_value_map, and default_value are passed on to _initialize.
        """

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

    def _initialize(self, register_value_map={}, memory_value_map={}):
        """ Sets the wire, register, and memory values to default or as specified.

        :param register_value_map: is a map of {Register: value}.
        :param memory_value_map: is a map of maps {Memory: {address: Value}}.
        :param default_value: is the value that all unspecified registers and
            memories will initialize to (default 0). For registers, this is the value that
            will be used if the particular register doesn't have a specified reset_value,
            and isn't found in the register_value_map.
        """
        # set registers to their values
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
        for mem_net in self.block.logic_subset('m@'):
            memid = mem_net.op_param[1].id
            if memid not in self.memvalue:
                self.memvalue[memid] = {}

        for (mem, mem_map) in memory_value_map.items():
            if isinstance(mem, RomBlock):
                raise PyrtlError('error, one or more of the memories in the map is a RomBlock')
            if isinstance(self.block, PostSynthBlock):
                mem = self.block.mem_map[mem]  # pylint: disable=maybe-no-member
            self.memvalue[mem.id] = mem_map
            max_addr_val, max_bit_val = 2**mem.addrwidth, 2**mem.bitwidth
            for (addr, val) in mem_map.items():
                if addr < 0 or addr >= max_addr_val:
                    raise PyrtlError('error, address %s in %s outside of bounds' %
                                     (str(addr), mem.name))
                if val < 0 or val >= max_bit_val:
                    raise PyrtlError('error, %s at %s in %s outside of bounds' %
                                     (str(val), str(addr), mem.name))

        # set all other variables to default value
        for w in self.block.wirevector_set:
            if w not in self.value:
                self.value[w] = self.default_value

        self.ordered_nets = tuple((i for i in self.block))
        self.reg_update_nets = tuple((self.block.logic_subset('r')))
        self.mem_update_nets = tuple((self.block.logic_subset('@')))

        self.tracer._set_initial_values(self.default_value, self.regvalue.copy(),
                                        copy.deepcopy(self.memvalue))

    def step(self, provided_inputs):
        """Take the simulation forward one cycle.

        :param provided_inputs: a dictionary mapping WireVectors to their
            values for this step

        A step causes the block to be updated as follows, in order:

        1. Registers are updated with their :attr:`~.Register.next` values
           computed in the previous cycle
        2. Block inputs and these new register values propagate through the
           combinational logic
        3. Memories are updated
        4. The :attr:`~.Register.next` values of the registers are saved for
           use in step 1 of the next cycle.

        All input wires must be in the `provided_inputs` in order for the
        simulation to accept these values.

        Example: if we have inputs named ``a`` and ``x``, we can call::

            sim.step({'a': 1, 'x': 23})

        to simulate a cycle with values 1 and 23 respectively.

        """

        # Check that all Input have a corresponding provided_input
        input_set = self.block.wirevector_subset(Input)
        supplied_inputs = set()
        for i in provided_inputs:
            if isinstance(i, WireVector):
                name = i.name
            else:
                name = i
            sim_wire = self.block.wirevector_by_name[name]
            if sim_wire not in input_set:
                raise PyrtlError(
                    'step provided a value for input for "%s" which is '
                    'not a known input ' % name)
            if not isinstance(provided_inputs[i], numbers.Integral) or provided_inputs[i] < 0:
                raise PyrtlError(
                    'step provided an input "%s" which is not a valid '
                    'positive integer' % provided_inputs[i])
            if len(bin(provided_inputs[i])) - 2 > sim_wire.bitwidth:
                raise PyrtlError(
                    'the bitwidth for "%s" is %d, but the provided input '
                    '%d requires %d bits to represent'
                    % (name, sim_wire.bitwidth,
                       provided_inputs[i], len(bin(provided_inputs[i])) - 2))

            self.value[sim_wire] = provided_inputs[i]
            supplied_inputs.add(sim_wire)

        # Check that only inputs are specified, and set the values
        if input_set != supplied_inputs:
            for i in input_set.difference(supplied_inputs):
                raise PyrtlError('Input "%s" has no input value specified' % i.name)

        self.value.update(self.regvalue)  # apply register updates from previous step

        for net in self.ordered_nets:
            self._execute(net)

        # Do all of the mem operations based off the new values changed in _execute()
        for net in self.mem_update_nets:
            self._mem_update(net)

        # at the end of the step, record the values to the trace
        # print self.value # Helpful Debug Print
        if self.tracer is not None:
            self.tracer.add_step(self.value)

        # Do all of the reg updates based off of the new values
        for net in self.reg_update_nets:
            argval = self.value[net.args[0]]
            self.regvalue[net.dests[0]] = self._sanitize(argval, net.dests[0])

        # finally, if any of the rtl_assert assertions are failing then we should
        # raise the appropriate exceptions
        check_rtl_assertions(self)

    def step_multiple(self, provided_inputs={}, expected_outputs={}, nsteps=None,
                      file=sys.stdout, stop_after_first_error=False):
        """Take the simulation forward N cycles, based on the number of values
        for each input

        :param provided_inputs: a dictionary mapping WireVectors to their
            values for N steps
        :param expected_outputs: a dictionary mapping WireVectors to their
            expected values for N steps; use ``?`` to indicate you don't care
            what the value at that step is
        :param nsteps: number of steps to take (defaults to None, meaning step
            for each supplied input value)
        :param file: where to write the output (if there are unexpected outputs
            detected)
        :param stop_after_first_error: a boolean flag indicating whether to
            stop the simulation after encountering the first error (defaults to
            False)

        All input wires must be in the `provided_inputs` in order for the
        simulation to accept these values. Additionally, the length of the
        array of provided values for each input must be the same.

        When `nsteps` is specified, then it must be *less than or equal* to the
        number of values supplied for each input when `provided_inputs` is
        non-empty. When `provided_inputs` is empty (which may be a legitimate
        case for a design that takes no inputs), then `nsteps` will be used.
        When `nsteps` is not specified, then the simulation will take the
        number of steps equal to the number of values supplied for each input.

        Example: if we have inputs named ``a`` and ``b`` and output ``o``, we
        can call::

            sim.step_multiple({'a': [0,1], 'b': [23,32]}, {'o': [42, 43]})

        to simulate 2 cycles, where in the first cycle ``a`` and ``b`` take on
        0 and 23, respectively, and ``o`` is expected to have the value 42, and
        in the second cycle ``a`` and ``b`` take on 1 and 32, respectively, and
        ``o`` is expected to have the value 43.

        If your values are all single digit, you can also specify them in a
        single string, e.g.::

            sim.step_multiple({'a': '01', 'b': '01'})

        will simulate 2 cycles, with ``a`` and ``b`` taking on 0 and 0,
        respectively, on the first cycle and 1 and 1, respectively, on the
        second cycle.

        Example: if the design had no inputs, like so::

            a = pyrtl.Register(8)
            b = pyrtl.Output(8, 'b')

            a.next <<= a + 1
            b <<= a

            sim = pyrtl.Simulation()
            sim.step_multiple(nsteps=3)

        Using ``sim.step_multiple(nsteps=3)`` simulates 3 cycles, after which
        we would expect the value of ``b`` to be 2.

        """

        if not nsteps and len(provided_inputs) == 0:
            raise PyrtlError('need to supply either input values or a number of steps to simulate')

        if len(provided_inputs) > 0:
            longest = sorted(list(provided_inputs.items()),
                             key=lambda t: len(t[1]),
                             reverse=True)[0]
            msteps = len(longest[1])
            if nsteps:
                if (nsteps > msteps):
                    raise PyrtlError('nsteps is specified but is greater than the '
                                     'number of values supplied for each input')
            else:
                nsteps = msteps

        if nsteps < 1:
            raise PyrtlError("must simulate at least one step")

        if list(filter(lambda value: len(value) < nsteps,
                       provided_inputs.values())):
            raise PyrtlError(
                "must supply a value for each provided wire "
                "for each step of simulation")

        if list(filter(lambda value: len(value) < nsteps,
                       expected_outputs.values())):
            raise PyrtlError(
                "any expected outputs must have a supplied value "
                "each step of simulation")

        failed = []
        for i in range(nsteps):
            self.step({w: int(v[i]) for w, v in provided_inputs.items()})

            for expvar in expected_outputs.keys():
                expected = expected_outputs[expvar][i]
                if expected == '?':
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
            file.write("{0:>5} {1:>10} {2:>8} {3:>8}\n"
                       .format("step", "name", "expected", "actual"))

            def _sort_tuple(t):
                # Sort by step and then wire name
                return (t[0], _trace_sort_key(t[1]))

            failed_sorted = sorted(failed, key=_sort_tuple)
            for (step, name, expected, actual) in failed_sorted:
                file.write("{0:>5} {1:>10} {2:>8} {3:>8}\n".format(step, name, expected, actual))
            file.flush()

    def inspect(self, w):
        """ Get the value of a WireVector in the last simulation cycle.

        :param str w: the name of the WireVector to inspect
            (passing in a WireVector instead of a name is deprecated)
        :return: value of w in the current step of simulation

        Will throw KeyError if w does not exist in the simulation.

        Example::

            sim.inspect('a') == 10  # returns value of wire 'a' at current step
        """
        wire = self.block.wirevector_by_name.get(w, w)
        return self.value[wire]

    def inspect_mem(self, mem):
        """ Get the values in a map during the current simulation cycle.

        :param mem: the memory to inspect
        :return: {address: value}

        Note that this returns the current memory state. Modifying the dictonary
        will also modify the state in the simulator
        """
        return self.memvalue[mem.id]

    @staticmethod
    def _sanitize(val, wirevector):
        """Return a modified version of val that would fit in wirevector.

        This function should be applied to every primitive call, and it's
        default behavior is to mask the upper bits of value and return that
        new value.
        """
        return val & wirevector.bitmask

    def _execute(self, net):
        """Handle the combinational logic update rules for the given net.

        This function, along with edge_update, defined the semantics
        of the primitive ops. Function updates self.value accordingly.
        """
        if net.op in 'r@':
            return  # registers and memory write ports have no logic function
        elif net.op in self.simple_func:
            argvals = (self.value[arg] for arg in net.args)
            result = self.simple_func[net.op](*argvals)
        elif net.op == 'c':
            result = 0
            for arg in net.args:
                result = result << len(arg)
                result = result | self.value[arg]
        elif net.op == 's':
            result = 0
            source = self.value[net.args[0]]
            for b in net.op_param[::-1]:
                result = (result << 1) | (0x1 & (source >> b))
        elif net.op == 'm':
            # memories act async for reads
            memid = net.op_param[0]
            mem = net.op_param[1]
            read_addr = self.value[net.args[0]]
            if isinstance(mem, RomBlock):
                result = mem._get_read_data(read_addr)
            else:
                result = self.memvalue[memid].get(read_addr, self.default_value)
        else:
            raise PyrtlInternalError('error, unknown op type')

        self.value[net.dests[0]] = self._sanitize(result, net.dests[0])

    def _mem_update(self, net):
        """Handle the mem update for the simulation of the given net (which is a memory).

        Combinational logic should have no posedge behavior, but registers and
        memory should.  This function, used after _execute, defines the
        semantics of the primitive ops.  Function updates self.memvalue accordingly
        (using prior_value)
        """
        if net.op != '@':
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


class FastSimulation(object):
    """A class for running JIT-to-python implementations of blocks.

    A Simulation step works as follows:

    1. Registers are updated:

        1. (If this is the first step) With the default values passed in
           to the Simulation during instantiation and/or any reset values
           specified in the individual registers.
        2. (Otherwise) With their next values calculated in the previous step
           (``r`` logic nets).

    2. The new values of these registers as well as the values of block inputs
       are propagated through the combinational logic.
    3. Memory writes are performed (``@`` logic nets).
    4. The current values of all wires are recorded in the trace.
    5. The next values for the registers are saved, ready to be applied at the
       beginning of the next step.

    Note that the register values saved in the trace after each simulation step
    are from *before* the register has latched in its newly calculated values,
    since that latching in occurs at the beginning of the *next* step.
    """

    # Dev Notes:
    #  Wire name processing:
    #  Sanitized names are only used when using and assigning variables inside of
    #  the generated function. Normal names are used when interacting with
    #  the dictionaries passed in and created by the exec'ed function.
    #  Therefore, everything outside of this function uses normal
    #  WireVector names.
    #  Careful use of repr() is used to make sure that strings stay the same
    #  when put into the generated code

    def __init__(
            self, register_value_map={}, memory_value_map={},
            default_value=0, tracer=True, block=None, code_file=None):
        """ Instantiates a Fast Simulation instance.

        The interface for FastSimulation and Simulation should be almost identical.
        In addition to the Simulation arguments, FastSimulation additionally takes:

        :param code_file: The file in which to store a copy of the generated
            Python code. Defaults to no code being stored.

        Look at :meth:`.Simulation.__init__` for descriptions for the other parameters.

        This builds the Fast Simulation compiled Python code, so all changes
        to the circuit after calling this function will not be reflected in
        the simulation.
        """

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
        self.internal_names = _PythonSanitizer('_fastsim_tmp_')
        self._initialize(register_value_map, memory_value_map)

    def _initialize(self, register_value_map={}, memory_value_map={}):
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
            with open(self.code_file, 'w') as file:
                file.write(s)

        self.tracer._set_initial_values(self.default_value, self.regs.copy(),
                                        copy.deepcopy(self.mems))

        context = {}
        logic_creator = compile(s, '<string>', 'exec')
        exec(logic_creator, context)
        self.sim_func = context['sim_func']

    def _initialize_mems(self, memory_value_map):
        for (mem, mem_map) in memory_value_map.items():
            if isinstance(mem, RomBlock):
                raise PyrtlError('error, one or more of the memories in the map is a RomBlock')
            name = self._mem_varname(mem)
            self.mems[name] = mem_map

        for net in self.block.logic_subset('m@'):
            mem = net.op_param[1]
            if self._mem_varname(mem) not in self.mems:
                if isinstance(mem, RomBlock):
                    self.mems[self._mem_varname(mem)] = mem
                else:
                    self.mems[self._mem_varname(mem)] = {}

    def step(self, provided_inputs):
        """ Run the simulation for a cycle.

        :param provided_inputs: a dictionary mapping WireVectors (or their
                                names) to their values for this step (eg:
                                `{wire: 3, "wire_name": 17}`)

        A step causes the block to be updated as follows, in order:

        1. Registers are updated with their :attr:`~.Register.next` values
           computed in the previous cycle
        2. Block inputs and these new register values propagate through the
           combinational logic
        3. Memories are updated
        4. The :attr:`~.Register.next` values of the registers are saved for
           use in step 1 of the next cycle.
        """
        # validate_inputs
        for wire, value in provided_inputs.items():
            wire = self.block.get_wirevector_by_name(wire) if isinstance(wire, str) else wire
            if value > wire.bitmask or value < 0:
                raise PyrtlError("Wire {} has value {} which cannot be represented"
                                 " using its bitwidth".format(wire, value))

        # building the simulation data
        ins = {self._to_name(wire): value for wire, value in provided_inputs.items()}
        ins.update(self.regs)
        ins.update(self.mems)

        # propagate through logic
        self.regs, self.outs, mem_writes = self.sim_func(ins)

        for mem, addr, value in mem_writes:
            self.mems[mem][addr] = value

        # for tracer compatibility
        self.context = self.outs.copy()
        self.context.update(ins)  # also gets old register values
        if self.tracer is not None:
            self.tracer.add_fast_step(self)

        # check the rtl assertions
        check_rtl_assertions(self)

    def step_multiple(self, provided_inputs={}, expected_outputs={}, nsteps=None,
                      file=sys.stdout, stop_after_first_error=False):
        """Take the simulation forward N cycles, where N is the number of
         values for each provided input.

        :param provided_inputs: a dictionary mapping WireVectors to their
            values for N steps
        :param expected_outputs: a dictionary mapping WireVectors to their
            expected values for N steps; use ``?`` to indicate you don't care
            what the value at that step is
        :param nsteps: number of steps to take (defaults to None, meaning step
            for each supplied input value)
        :param file: where to write the output (if there are unexpected outputs
            detected)
        :param stop_after_first_error: a boolean flag indicating whether to
            stop the simulation after the step where the first errors are
            encountered (defaults to False)

        All input wires must be in the `provided_inputs` in order for the
        simulation to accept these values. Additionally, the length of the
        array of provided values for each input must be the same.

        When `nsteps` is specified, then it must be *less than or equal* to the
        number of values supplied for each input when `provided_inputs` is
        non-empty. When `provided_inputs` is empty (which may be a legitimate
        case for a design that takes no inputs), then `nsteps` will be used.
        When `nsteps` is not specified, then the simulation will take the
        number of steps equal to the number of values supplied for each input.

        Example: if we have inputs named ``a`` and ``b`` and output ``o``, we
        can call::

            sim.step_multiple({'a': [0,1], 'b': [23,32]}, {'o': [42, 43]})

        to simulate 2 cycles, where in the first cycle ``a`` and ``b`` take on
        0 and 23, respectively, and ``o`` is expected to have the value 42, and
        in the second cycle ``a`` and ``b`` take on 1 and 32, respectively, and
        ``o`` is expected to have the value 43.

        If your values are all single digit, you can also specify them in a
        single string, e.g.::

            sim.step_multiple({'a': '01', 'b': '01'})

        will simulate 2 cycles, with ``a`` and ``b`` taking on 0 and 0,
        respectively, on the first cycle and 1 and 1, respectively, on the
        second cycle.

        Example: if the design had no inputs, like so::

            a = pyrtl.Register(8)
            b = pyrtl.Output(8, 'b')

            a.next <<= a + 1
            b <<= a

            sim = pyrtl.Simulation()
            sim.step_multiple(nsteps=3)

        Using ``sim.step_multiple(nsteps=3)`` simulates 3 cycles, after which
        we would expect the value of ``b`` to be 2.

        """

        if not nsteps and len(provided_inputs) == 0:
            raise PyrtlError('need to supply either input values or a number of steps to simulate')

        if len(provided_inputs) > 0:
            longest = sorted(list(provided_inputs.items()),
                             key=lambda t: len(t[1]),
                             reverse=True)[0]
            msteps = len(longest[1])
            if nsteps:
                if (nsteps > msteps):
                    raise PyrtlError('nsteps is specified but is greater than the '
                                     'number of values supplied for each input')
            else:
                nsteps = msteps

        if nsteps < 1:
            raise PyrtlError("must simulate at least one step")

        if list(filter(lambda value: len(value) < nsteps,
                       provided_inputs.values())):
            raise PyrtlError(
                "must supply a value for each provided wire "
                "for each step of simulation")

        if list(filter(lambda value: len(value) < nsteps,
                       expected_outputs.values())):
            raise PyrtlError(
                "any expected outputs must have a supplied value "
                "each step of simulation")

        def to_num(v):
            if isinstance(v, str):
                # Don't use infer_val_and_bitwidth because they aren't in
                # Verilog-style format, but are instead in plain decimal.
                return int(v)
            # Don't just call int(v) on all of them since it's nice
            # to retain class info if they were a subclass of int.
            return v

        failed = []
        for i in range(nsteps):
            self.step({w: to_num(v[i]) for w, v in provided_inputs.items()})

            for expvar in expected_outputs.keys():
                expected = expected_outputs[expvar][i]
                if expected == '?':
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
            file.write("{0:>5} {1:>10} {2:>8} {3:>8}\n"
                       .format("step", "name", "expected", "actual"))

            def _sort_tuple(t):
                # Sort by step and then wire name
                return (t[0], _trace_sort_key(t[1]))

            failed_sorted = sorted(failed, key=_sort_tuple)
            for (step, name, expected, actual) in failed_sorted:
                file.write("{0:>5} {1:>10} {2:>8} {3:>8}\n".format(step, name, expected, actual))
            file.flush()

    def inspect(self, w):
        """ Get the value of a WireVector in the last simulation cycle.

        :param str w: the name of the WireVector to inspect
            (passing in a WireVector instead of a name is deprecated)
        :return: value of `w` in the current step of simulation

        Will throw KeyError if `w` is not being tracked in the simulation.
        """
        try:
            return self.context[self._to_name(w)]
        except AttributeError:
            raise PyrtlError("No context available. Please run a simulation step in "
                             "order to populate values for wires")
        # except KeyError:
        #     raise PyrtlError("Wire {} is not in the simulation trace. Please probe it"
        #                      "and measure the probe value to measure this wire's value"
        #                     .format(w))

    def inspect_mem(self, mem):
        """ Get the values in a map during the current simulation cycle.

        :param mem: the memory to inspect
        :return: {address: value}

        Note that this returns the current memory state. Modifying the dictonary
        will also modify the state in the simulator
        """
        if isinstance(mem, RomBlock):
            raise PyrtlError("ROM blocks are not stored in the simulation object")
        return self.mems[self._mem_varname(mem)]

    def _to_name(self, name):
        """ Converts Wires to strings, keeps strings as is """
        if isinstance(name, WireVector):
            return name.name
        return name

    def _varname(self, val):
        """ Converts WireVectors to internal names """
        return self.internal_names[val.name]

    def _mem_varname(self, val):
        return 'fs_mem' + str(val.id)

    def _arg_varname(self, wire):
        """
        Input, Const, and Registers have special input values
        """
        if isinstance(wire, (Input, Register)):
            return 'd[' + repr(wire.name) + ']'  # passed in
        elif isinstance(wire, Const):
            return str(int(wire.val))  # hardcoded
        else:
            return self._varname(wire)

    def _dest_varname(self, wire):
        if isinstance(wire, Output):
            return 'outs[' + repr(wire.name) + ']'
        elif isinstance(wire, Register):
            return 'regs[' + repr(wire.name) + ']'
        else:
            return self._varname(wire)

    _no_mask_bitwidth = {  # bitwidth that the dest has to have in order to not need masking
        'w': lambda net: len(net.args[0]),
        'r': lambda net: len(net.args[0]),
        '~': lambda net: -1,  # bitflips always need masking
        '&': lambda net: len(net.args[0]),
        '|': lambda net: len(net.args[0]),
        '^': lambda net: len(net.args[0]),
        'n': lambda net: -1,  # bitflips always need masking
        '+': lambda net: len(net.args[0]) + 1,
        '-': lambda net: -1,  # need to handle negative numbers correctly
        '*': lambda net: len(net.args[0]) + len(net.args[1]),
        '<': lambda net: 1,
        '>': lambda net: 1,
        '=': lambda net: 1,
        'x': lambda net: len(net.args[1]),
        'c': lambda net: sum(len(a) for a in net.args),
        's': lambda net: len(net.op_param),
        'm': lambda net: -1,   # just not going to optimize this right now
    }

    # Yeah, triple quotes don't respect indentation (aka the 4 spaces on the
    # start of each line is part of the string)
    _prog_start = """def sim_func(d):
    regs = {}
    outs = {}
    mem_ws = []"""

    def _compiled(self):
        """Return a string of the self.block compiled to a block of
         code that can be executed to get a function to execute"""
        # Dev Notes:
        # Because of fast locals in functions in both CPython and PyPy, getting a
        # function to execute makes the code a few times faster than
        # just executing it in the global exec scope.
        prog = [self._prog_start]

        simple_func = {  # OPS
            'w': lambda x: x,
            'r': lambda x: x,
            '~': lambda x: '(~' + x + ')',
            '&': lambda left, right: '(' + left + '&' + right + ')',
            '|': lambda left, right: '(' + left + '|' + right + ')',
            '^': lambda left, right: '(' + left + '^' + right + ')',
            'n': lambda left, right: '(~(' + left + '&' + right + '))',
            '+': lambda left, right: '(' + left + '+' + right + ')',
            '-': lambda left, right: '(' + left + '-' + right + ')',
            '*': lambda left, right: '(' + left + '*' + right + ')',
            '<': lambda left, right: 'int(' + left + '<' + right + ')',
            '>': lambda left, right: 'int(' + left + '>' + right + ')',
            '=': lambda left, right: 'int(' + left + '==' + right + ')',
            'x': lambda sel, f, t: '({}) if ({}==0) else ({})'.format(f, sel, t),
        }

        def shift(value, direction, shift_amt):
            if shift_amt == 0:
                return value
            else:
                return '(%s %s %d)' % (value, direction, shift_amt)

        def make_split():
            if split_start_bit == 0:
                bit = '(%d & %s)' % ((1 << split_length) - 1, source)
            elif len(net.args[0]) - split_start_bit == split_length:
                bit = '(%s >> %d)' % (source, split_start_bit)
            else:
                bit = '(%d & (%s >> %d))' % ((1 << split_length) - 1, source, split_start_bit)
            return shift(bit, '<<', split_res_start_bit)

        for net in self.block:
            if net.op in simple_func:
                argvals = (self._arg_varname(arg) for arg in net.args)
                expr = simple_func[net.op](*argvals)
            elif net.op == 'c':
                expr = ''
                for i in range(len(net.args)):
                    if expr != '':
                        expr += ' | '
                    shiftby = sum(len(j) for j in net.args[i + 1:])
                    expr += shift(self._arg_varname(net.args[i]), '<<', shiftby)
            elif net.op == 's':
                source = self._arg_varname(net.args[0])
                expr = ''
                split_length = 0
                split_start_bit = -2
                split_res_start_bit = -1

                for i, b in enumerate(net.op_param):
                    if b != split_start_bit + split_length:
                        if split_start_bit >= 0:
                            # create a wire
                            expr += make_split() + '|'
                        split_length = 1
                        split_start_bit = b
                        split_res_start_bit = i
                    else:
                        split_length += 1
                expr += make_split()
            elif net.op == 'm':
                read_addr = self._arg_varname(net.args[0])
                mem = net.op_param[1]
                if isinstance(net.op_param[1], RomBlock):
                    expr = 'd["%s"]._get_read_data(%s)' % (self._mem_varname(mem), read_addr)
                else:  # memories act async for reads
                    expr = 'd["%s"].get(%s, %s)' % (self._mem_varname(mem),
                                                    read_addr, self.default_value)
            elif net.op == '@':
                mem = self._mem_varname(net.op_param[1])
                write_addr, write_val, write_enable = (self._arg_varname(a) for a in net.args)
                prog.append('    if {}:'.format(write_enable))
                prog.append('        mem_ws.append(("{}", {}, {}))'
                            .format(mem, write_addr, write_val))
                continue  # memwrites are special
            else:
                raise PyrtlError('FastSimulation cannot handle primitive "%s"' % net.op)

            # prog.append('    #  ' + str(net))
            result = self._dest_varname(net.dests[0])
            if len(net.dests[0]) == self._no_mask_bitwidth[net.op](net):
                prog.append("    %s = %s" % (result, expr))
            else:
                mask = str(net.dests[0].bitmask)
                prog.append('    %s = %s & %s' % (result, mask, expr))

        # add traced wires to dict
        if self.tracer is not None:
            for wire_name in self.tracer.trace:
                wire = self.block.wirevector_by_name[wire_name]
                if not isinstance(wire, (Input, Register, Output)):
                    value = int(wire.val) if isinstance(wire, Const) else self._varname(wire)
                    prog.append('    outs["%s"] = %s' % (wire_name, value))

        prog.append("    return regs, outs, mem_ws")
        return '\n'.join(prog)


# ----------------------------------------------------------------
#    ___  __        __   ___
#     |  |__)  /\  /  ` |__
#     |  |  \ /~~\ \__, |___
#


class WaveRenderer(object):
    """Render a SimulationTrace to the terminal.

    See ``examples/renderer-demo.py``, which renders traces with various
    options. You can choose a default renderer by exporting the
    ``PYRTL_RENDERER`` environment variable. See the documentation for subclasses
    of :py:class:`RendererConstants`.

    """
    def __init__(self, constants):
        """Instantiate a WaveRenderer.

        :param constants: Subclass of :py:class:`RendererConstants` that
            specifies the ASCII/Unicode characters to use for rendering
            waveforms.

        """
        self.constants = constants

    def render_ruler_segment(self, n, cycle_len, segment_size, maxtracelen):
        """Render a major tick padded to segment_size.

        :param n: Cycle number for the major tick mark.
        :param cycle_len: Rendered length of each cycle, in characters.
        :param segment_size: Length between major tick marks, in cycles.
        :param maxtracelen: Length of the longest trace, in cycles.
        """
        # Render a major tick mark followed by its label (n).
        major_tick = self.constants._tick + str(n)
        # Number of cycles occupied by major_tick.
        major_tick_cycles = math.ceil(len(major_tick) / cycle_len)
        # If major_tick can't fit in segment_size, drop most significant digits
        # until it fits.
        if major_tick_cycles > segment_size:
            major_tick = self.constants._tick + major_tick[:segment_size - 1]

        # Do not render past maxtracelen.
        if n + segment_size >= maxtracelen:
            segment_size = maxtracelen - n
        # Pad major_tick out to segment_size.
        ticks = major_tick.ljust(cycle_len * segment_size)
        return ticks

    def val_to_str(self, value, wire_name, repr_func, repr_per_name):
        """Return a string representing 'value'.

        :param value: The value to convert to string.
        :param wire_name: Name of the wire that produced this value.
        :param repr_func: function to use for representing the current_val;
            examples are 'hex', 'oct', 'bin', 'str' (for decimal), or even the name
            of an IntEnum class you know the value will belong to. Defaults to 'hex'.
        :param repr_per_name: Map from signal name to a function that takes in the signal's
            value and returns a user-defined representation. If a signal name is
            not found in the map, the argument `repr_func` will be used instead.

        :return: a string representing 'value'.

        """
        f = repr_per_name.get(wire_name)
        if f is not None:
            return str(f(value))
        else:
            return str(repr_func(value))

    def render_val(self, w, prior_val, current_val, symbol_len, cycle_len,
                   repr_func, repr_per_name, prev_line):
        """Return a string encoding the given value in a waveform.

        :param w: The WireVector we are rendering to a waveform
        :param n: An integer from 0 to segment_len-1
        :param prior_val: Last value rendered. None if there was no last value.
        :param current_val: the value to be rendered
        :param symbol_len: Width of each value, in characters.
        :param cycle_len: Width of each cycle, in characters.
        :param repr_func: function to use for representing the current_val;
            examples are 'hex', 'oct', 'bin', 'str' (for decimal), or even the name
            of an IntEnum class you know the value will belong to. Defaults to 'hex'.
        :param repr_per_name: Map from signal name to a function that takes in the signal's
            value and returns a user-defined representation. If a signal name is
            not found in the map, the argument `repr_func` will be used instead.
        :param prev_line: If True, render the gap between signals. If False,
            render the main signal. This is useful for rendering signals across
            two lines, see the _prev_line* fields in RendererConstants.

        Returns a string of printed length symbol_len that will draw the
        representation of current_val.  The input prior_val is used to
        render transitions.
        """
        if len(w) > 1:
            if prev_line:
                # Bus wires are currently never rendered across multiple lines.
                return ''

            out = ''
            if current_val != prior_val:
                if prior_val is not None:
                    out += self.constants._x
                out += (self.val_to_str(current_val, w.name, repr_func,
                                        repr_per_name).rstrip('L')
                        .ljust(symbol_len)[:symbol_len])
            else:
                out += ' ' * cycle_len
        else:
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


class RendererConstants():
    """Abstract base class for renderer constants.

    These constants determine which characters are used to render waveforms in
    a terminal.

    .. inheritance-diagram:: pyrtl.simulation.Utf8RendererConstants
                             pyrtl.simulation.Utf8AltRendererConstants
                             pyrtl.simulation.PowerlineRendererConstants
                             pyrtl.simulation.Cp437RendererConstants
                             pyrtl.simulation.AsciiRendererConstants
        :parts: 1

    """
    # Print _tick before rendering a ruler segment. Must have a display length
    # of 1 character.
    _tick = ''

    # Print _up when a binary wire transitions from low to high. Print _down
    # when a binary wire transitions from high to low. _up and _down must have
    # display length of _chars_between_cycles characters.
    _up, _down = '', ''

    # Print _low when a binary wire maintains a low value, and print _high when
    # a binary wire maintains a high value. _low and _high must have display
    # length of 1 character.
    _low, _high = '', ''

    # These are like _up, _down, _low, _high, except they are printed on the
    # previous line. These are useful for displaying a binary wire across two
    # lines.
    _prev_line_up, _prev_line_down = '', ''
    _prev_line_low, _prev_line_high = '', ''

    # Print _bus_start before rendering a bus wire, and print _bus_stop after
    # rendering a bus wire. _bus_start and _bus_stop must have zero display
    # length characters. Escape codes never count towards display length.
    _bus_start, _bus_stop = '', ''
    # Print _x when a bus wire changes value. _low must have display length
    # of _chars_between_cycles characters.
    _x = ''

    # Number of characters between cycles. The cycle changes halfway between
    # this width. The first half of this width belongs to the previous cycle and
    # the second half of this width belongs to the next cycle.
    _chars_between_cycles = 0


class Utf8RendererConstants(RendererConstants):
    """UTF-8 renderer constants. These should work in most terminals.

    Single-bit WireVectors are rendered as square waveforms, with vertical
    rising and falling edges. Multi-bit WireVector values are rendered in
    reverse-video rectangles.

    This is the default renderer on non-Windows platforms.

    Enable this renderer by default by setting the ``PYRTL_RENDERER``
    environment variable to ``utf-8``.

    .. image:: ../docs/screenshots/pyrtl-statemachine-utf-8.png

    """
    # Start reverse-video, reset all attributes
    _bus_start, _bus_stop = '\x1B[7m', '\x1B[0m'

    _tick = '▕'

    _up, _down = '▁▏', '▕▁'
    _low, _high = '▁', ' '

    _prev_line_up, _prev_line_down = ' ▁', '▁ '
    _prev_line_low, _prev_line_high = ' ', '▁'

    _x = '▕ '

    # Number of characters needed between cycles. The cycle changes halfway
    # between this width (2), so the first character belongs to the previous
    # cycle and the second character belongs to the next cycle.
    _chars_between_cycles = 2


class Utf8AltRendererConstants(RendererConstants):
    """Alternative UTF-8 renderer constants.

    Single-bit WireVectors are rendered as waveforms with sloped rising and
    falling edges. Multi-bit WireVector values are rendered in reverse-video
    rectangles.

    Compared to Utf8RendererConstants, this renderer is more compact because it
    uses one character between cycles instead of two.

    Enable this renderer by default by setting the ``PYRTL_RENDERER``
    environment variable to ``utf-8-alt``.

    .. image:: ../docs/screenshots/pyrtl-statemachine-utf-8-alt.png

    """
    # Start reverse-video, reset all attributes
    _bus_start, _bus_stop = '\x1B[7m', '\x1B[0m'

    _tick = '│'

    _up, _down = '╱', '╲'
    _low, _high = '▁', '▔'

    _x = '┃'

    # Number of characters needed between cycles. The cycle changes halfway
    # between this width (1), so the first character belongs to the previous
    # cycle and the second character belongs to the next cycle.
    _chars_between_cycles = 1


class PowerlineRendererConstants(Utf8RendererConstants):
    """Powerline renderer constants. Font must include powerline glyphs.

    This render is closest to a traditional logic analyzer. Single-bit
    WireVectors are rendered as square waveforms, with vertical rising and
    falling edges. Multi-bit WireVector values are rendered in reverse-video
    hexagons.

    This renderer requires a `terminal font that supports Powerline glyphs
    <https://github.com/powerline/fonts>`_

    Enable this renderer by default by setting the ``PYRTL_RENDERER``
    environment variable to ``powerline``.

    .. image:: ../docs/screenshots/pyrtl-statemachine.png

    """
    # Start reverse-video, reset all attributes
    _bus_start, _bus_stop = '\x1B[7m', '\x1B[0m'

    _x = _bus_stop + '' + _bus_start


class Cp437RendererConstants(RendererConstants):
    """Code page 437 renderer constants (for windows ``cmd`` compatibility).

    Single-bit WireVectors are rendered as square waveforms, with vertical
    rising and falling edges. Multi-bit WireVector values are rendered between
    vertical bars.

    `Code page 437 <https://en.wikipedia.org/wiki/Code_page_437>`_ is also
    known as 8-bit ASCII. This is the default renderer on Windows platforms.

    Compared to Utf8RendererConstants, this renderer is more compact because it
    uses one character between cycles instead of two, but the wire names are
    vertically aligned at the bottom of each waveform.

    Enable this renderer by default by setting the ``PYRTL_RENDERER``
    environment variable to ``cp437``.

    .. image:: ../docs/screenshots/pyrtl-statemachine-cp437.png

    """
    _tick = '│'

    _up, _down = '┘', '└'
    _low, _high = '─', ' '

    _prev_line_up, _prev_line_down = '┌', '┐'
    _prev_line_low, _prev_line_high = ' ', '─'

    _x = '│'

    _chars_between_cycles = 1


class AsciiRendererConstants(RendererConstants):
    """7-bit ASCII renderer constants. These should work anywhere.

    Single-bit WireVectors are rendered as waveforms with sloped rising and
    falling edges. Multi-bit WireVector values are rendered between vertical
    bars.

    Enable this renderer by default by setting the ``PYRTL_RENDERER``
    environment variable to ``ascii``.

    .. image:: ../docs/screenshots/pyrtl-statemachine-ascii.png

    """
    _tick = '|'

    _up, _down = ',', '.'
    _low, _high = '_', '-'

    _x = '|'

    _chars_between_cycles = 1


def default_renderer():
    """Select renderer constants based on environment or auto-detection."""
    renderer = ''
    if 'PYRTL_RENDERER' in os.environ:
        # Use user-specified renderer constants.
        renderer = os.environ['PYRTL_RENDERER']
    elif 'PROMPT' in os.environ:
        # Windows Command Prompt, use code page 437 renderer constants.
        renderer = 'cp437'
    else:
        # Use UTF-8 renderer constants by default.
        renderer = 'utf-8'

    renderer_map = {
        'powerline': PowerlineRendererConstants(),
        'utf-8': Utf8RendererConstants(),
        'utf-8-alt': Utf8AltRendererConstants(),
        'cp437': Cp437RendererConstants(),
        'ascii': AsciiRendererConstants()
    }

    if renderer in renderer_map:
        constants = renderer_map[renderer]
    else:
        print(f"WARNING: Unsupported $PYRTL_RENDERER value '{renderer}' "
              f"supported values are ({' '.join(renderer_map.keys())}). "
              'Defaulting to utf-8')
        constants = Utf8RendererConstants()

    return WaveRenderer(constants)


def _trace_sort_key(w):
    def tryint(s):
        try:
            return int(s)
        except ValueError:
            return s
    return [tryint(c) for c in re.split('([0-9]+)', w)]


class TraceStorage(Mapping):
    __slots__ = ('__data',)

    def __init__(self, wvs):
        self.__data = {wv.name: [] for wv in wvs}

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return iter(self.__data)

    def __getitem__(self, key):
        if isinstance(key, WireVector):
            import warnings
            warnings.warn(
                'Access to trace by WireVector instead of name is deprecated.',
                DeprecationWarning)
            key = key.name
        if key not in self.__data:
            raise PyrtlError('Cannot find "%s" in trace -- if using CompiledSim, you may be '
                             'attempting to access internal states but only inputs/outputs are '
                             'available.' % key)
        return self.__data[key]


class SimulationTrace(object):
    """ Storage and presentation of simulation waveforms. """

    def __init__(self, wires_to_track=None, block=None):
        """
        Creates a new Simulation Trace

        :param wires_to_track: The wires that the tracer should track.
            If unspecified, will track all explicitly-named wires.
            If set to ``'all'``, will track all wires, including internal wires.
        :param block: Block containing logic to trace
        """
        self.block = working_block(block)

        def is_internal_name(name):
            return (name.startswith('tmp') or name.startswith('const_')
                    # or name.startswith('synth_')
                    or name.endswith("'"))

        if wires_to_track is None:
            wires_to_track = [w for w in self.block.wirevector_set if not is_internal_name(w.name)]
        elif wires_to_track == 'all':
            wires_to_track = self.block.wirevector_set

        non_const_tracked = list(filter(lambda w: not isinstance(w, Const), wires_to_track))
        if not len(non_const_tracked):
            raise PyrtlError("There needs to be at least one named non-constant wire "
                             "for simulation to be useful")
        self.wires_to_track = wires_to_track
        self.trace = TraceStorage(wires_to_track)
        self._wires = {wv.name: wv for wv in wires_to_track}
        # remember for initializing during Verilog testbench output
        self.default_value = 0
        self.init_regvalue = {}
        self.init_memvalue = {}

    def __len__(self):
        """ Return the current length of the trace in cycles. """
        if len(self.trace) == 0:
            raise PyrtlError('error, length of trace undefined if no signals tracked')
        # return the length of the list of some element in the dictionary (all should be the same)
        wire, value_list = next(x for x in self.trace.items())
        return len(value_list)

    def add_step(self, value_map):
        """ Add the values in `value_map` to the end of the trace. """
        if len(self.trace) == 0:
            raise PyrtlError('error, simulation trace needs at least 1 signal to track '
                             '(by default, unnamed signals are not traced -- try either passing '
                             'a name to a WireVector or setting a "wirevector_subset" option)')
        for wire_name in self.trace:
            tracelist = self.trace[wire_name]
            wirevec = self._wires[wire_name]
            tracelist.append(value_map[wirevec])

    def add_step_named(self, value_map):
        for wire_name in value_map:
            if wire_name in self.trace:
                self.trace[wire_name].append(value_map[wire_name])

    def add_fast_step(self, fastsim):
        """ Add the `fastsim` context to the trace. """
        for wire_name in self.trace:
            self.trace[wire_name].append(fastsim.context[wire_name])

    def print_trace(self, file=sys.stdout, base=10, compact=False):
        """
        Prints a list of wires and their current values.

        :param int base: the base the values are to be printed in
        :param bool compact: whether to omit spaces in output lines
        """
        if len(self.trace) == 0:
            raise PyrtlError('error, cannot print an empty trace')
        if base not in (2, 8, 10, 16):
            raise PyrtlError('please choose a valid base (2,8,10,16)')

        basekey = {2: 'b', 8: 'o', 10: 'd', 16: 'x'}[base]
        ident_len = max(len(w) for w in self.trace)

        if compact:
            for w in sorted(self.trace, key=_trace_sort_key):
                vals = ''.join('{0:{1}}'.format(x, basekey) for x in self.trace[w])
                file.write(w.rjust(ident_len) + ' ' + vals + '\n')
        else:
            maxlenval = max(len('{0:{1}}'.format(x, basekey))
                            for w in self.trace for x in self.trace[w])
            file.write(' ' * (ident_len - 3) + "--- Values in base %d ---\n" % base)
            for w in sorted(self.trace, key=_trace_sort_key):
                vals = ' '.join('{0:>{1}{2}}'.format(x, maxlenval, basekey) for x in self.trace[w])
                file.write(w.ljust(ident_len + 1) + vals + '\n')

        file.flush()

    def print_vcd(self, file=sys.stdout, include_clock=False):
        """Print the trace out as a VCD File for use in other tools.

        :param file: file to open and output vcd dump to.
        :param include_clock: boolean specifying if the implicit clk should be
                              included.

        Dumps the current trace to file as a `value change dump
        <https://en.wikipedia.org/wiki/Value_change_dump>`_ file.  The file
        parameter defaults to ``stdout`` and the `include_clock` defaults to
        False.

        Examples::

            sim_trace.print_vcd()
            sim_trace.print_vcd("my_waveform.vcd", include_clock=True)

        """
        # dump header info
        # file_timestamp = time.strftime("%a, %d %b %Y %H:%M:%S (UTC/GMT)", time.gmtime())
        # print >>file, " ".join(["$date", file_timestamp, "$end"])
        self.internal_names = _VerilogSanitizer('_vcd_tmp_')
        for wire in self.wires_to_track:
            self.internal_names.make_valid_string(wire.name)

        def _varname(wireName):
            """ Converts WireVector names to internal names """
            return self.internal_names[wireName]

        print(' '.join(['$timescale', '1ns', '$end']), file=file)
        print(' '.join(['$scope', 'module logic', '$end']), file=file)

        def print_trace_strs(time):
            for wn in sorted(self.trace, key=_trace_sort_key):
                print(' '.join([str(bin(self.trace[wn][time]))[1:], _varname(wn)]), file=file)

        # dump variables
        if include_clock:
            print(' '.join(['$var', 'wire', '1', 'clk', 'clk', '$end']), file=file)
        for wn in sorted(self.trace, key=_trace_sort_key):
            print(' '.join(['$var', 'wire', str(self._wires[wn].bitwidth),
                            _varname(wn), _varname(wn), '$end']), file=file)
        print(' '.join(['$upscope', '$end']), file=file)
        print(' '.join(['$enddefinitions', '$end']), file=file)
        print(' '.join(['$dumpvars']), file=file)
        print_trace_strs(0)
        print(' '.join(['$end']), file=file)

        # dump values
        endtime = max([len(self.trace[w]) for w in self.trace])
        for timestamp in range(endtime):
            print(''.join(['#', str(timestamp * 10)]), file=file)
            print_trace_strs(timestamp)
            if include_clock:
                print('b1 clk', file=file)
                print('', file=file)
                print(''.join(['#', str(timestamp * 10 + 5)]), file=file)
                print('b0 clk', file=file)
            print('', file=file)
        print(''.join(['#', str(endtime * 10)]), file=file)
        file.flush()

    def render_trace(
            self, trace_list=None, file=sys.stdout, renderer=default_renderer(),
            symbol_len=None, repr_func=hex, repr_per_name={}, segment_size=1):

        """ Render the trace to a file using unicode and ASCII escape sequences.

        :param list[str] trace_list: A list of signal names to be output in the specified order.
        :param file: The place to write output, default to stdout.
        :param WaveRenderer renderer: An object that translates traces into output bytes.
        :param int symbol_len: The "length" of each rendered value in characters.
            If None, the length will be automatically set such that the largest
            represented value fits.
        :param repr_func: Function to use for representing each value in the trace;
            examples are ``hex``, ``oct``, ``bin``, and ``str`` (for decimal). Defaults to ``hex``.
        :param repr_per_name: Map from signal name to a function that takes in the signal's
            value and returns a user-defined representation. If a signal name is
            not found in the map, the argument `repr_func` will be used instead.
        :param int segment_size: Traces are broken in the segments of this number of cycles.

        The resulting output can be viewed directly on the terminal or looked
        at with :program:`more` or :program:`less -R` which both should handle the ASCII escape
        sequences used in rendering.
        """
        if _currently_in_jupyter_notebook():
            from IPython.display import display, HTML, Javascript  # pylint: disable=import-error
            from .visualization import trace_to_html
            htmlstring = trace_to_html(self, trace_list=trace_list, sortkey=_trace_sort_key)
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
                trace_list=trace_list, file=file, renderer=renderer,
                symbol_len=symbol_len, repr_func=repr_func, repr_per_name=repr_per_name,
                segment_size=segment_size)

    def render_trace_to_text(
            self, trace_list, file, renderer,
            symbol_len, repr_func, repr_per_name, segment_size):

        def formatted_trace_line(wire, trace):
            first_trace_line = ''
            second_trace_line = ''
            prior_val = None
            is_bus = len(self._wires[wire]) > 1
            if is_bus:
                second_trace_line += renderer.constants._bus_start
            for i in range(len(trace)):
                # There is no cycle change before the first cycle or after the
                # last cycle, so the first and last cycles may have additional
                # width. These additional widths make each cycle line up under
                # the ruler, and appear the same length.
                additional_symbol_len = 0
                additional_cycle_len = 0
                half_chars_between_cycles = (
                    math.floor(renderer.constants._chars_between_cycles / 2))
                if i == len(trace) - 1:
                    additional_cycle_len = half_chars_between_cycles
                if i == 0 or i == len(trace) - 1:
                    additional_symbol_len = half_chars_between_cycles
                first_trace_line += renderer.render_val(
                    self._wires[wire], prior_val, trace[i],
                    symbol_len + additional_symbol_len,
                    cycle_len + additional_cycle_len, repr_func,
                    repr_per_name, prev_line=True)
                second_trace_line += renderer.render_val(
                    self._wires[wire], prior_val, trace[i],
                    symbol_len + additional_symbol_len,
                    cycle_len + additional_cycle_len, repr_func,
                    repr_per_name, prev_line=False)
                prior_val = trace[i]
            if is_bus:
                second_trace_line += renderer.constants._bus_stop
            heading_gap = ' ' * (maxnamelen + 1)
            heading = wire.rjust(maxnamelen) + ' '
            return (heading_gap + first_trace_line + '\n'
                    + heading + second_trace_line)

        # default to printing all signals in sorted order
        if trace_list is None:
            trace_list = sorted(self.trace, key=_trace_sort_key)
        elif any(isinstance(x, WireVector) for x in trace_list):
            import warnings
            warnings.warn(
                'Access to trace by WireVector instead of name is deprecated.',
                DeprecationWarning)
            trace_list = [getattr(x, 'name', x) for x in trace_list]

        if not trace_list:
            raise PyrtlError(
                "Empty trace list. This may have occurred because "
                "untraceable wires were removed prior to simulation, "
                "if a CompiledSimulation was used.")

        if symbol_len is None:
            maxvallen = 0
            for trace_name in trace_list:
                trace = self.trace[trace_name]
                maxvallen = max(maxvallen, max(len(renderer.val_to_str(
                    v, trace_name, repr_func, repr_per_name)) for v in trace))
            symbol_len = maxvallen

        cycle_len = symbol_len + renderer.constants._chars_between_cycles

        # print the 'ruler' which is just a list of 'ticks'
        # mapped by the pretty map
        maxnamelen = max(len(trace_name) for trace_name in trace_list)
        maxtracelen = max(len(self.trace[trace_name])
                          for trace_name in trace_list)
        if segment_size is None:
            segment_size = maxtracelen
        spaces = ' ' * (maxnamelen)
        ticks = [renderer.render_ruler_segment(n, cycle_len, segment_size,
                                               maxtracelen)
                 for n in range(0, maxtracelen, segment_size)]
        print(spaces + ''.join(ticks), file=file)

        # now all the traces
        for trace_name in trace_list:
            print(formatted_trace_line(trace_name, self.trace[trace_name]),
                  file=file)

    def _set_initial_values(self, default_value, init_regvalue, init_memvalue):
        """ Remember the default values that were used when starting the trace.

        :param default_value: Default value to be used for all registers and
            memory locations if not found in the other passed in maps
        :param init_regvalue: Default value for all the registers
        :param init_memvvalue: Default value for memory locations of given maps

        This is needed when using this trace for outputting a Verilog testbench,
        and is automatically called during simulation.
        """
        self.default_value = default_value
        self.init_regvalue = init_regvalue
        self.init_memvalue = init_memvalue

    def print_perf_counters(self, *trace_names, file=sys.stdout):
        """Print performance counter statistics for `trace_names`.

        :param str trace_names: List of trace names. Each trace must be a
            single-bit wire.
        :param file: The place to write output, defaults to stdout.

        This function prints the number of cycles where each trace's value is
        one. This is useful for counting the number of times important events
        occur in a simulation, such as cache misses and branch mispredictions.

        """
        name_values = []
        for trace_name in trace_names:
            wire_length = len(self._wires[trace_name])
            if wire_length != 1:
                raise PyrtlError(
                    'print_perf_counters can only be used with single-bit '
                    f'wires but wire {trace_name} has bitwidth {wire_length}')

            name_values.append([trace_name, str(sum(self.trace[trace_name]))])

        max_name_length = max(len(name) for name, value in name_values)
        max_value_length = max(len(value) for name, value in name_values)
        for name, value in name_values:
            print(name.rjust(max_name_length),
                  value.rjust(max_value_length),
                  file=file)
