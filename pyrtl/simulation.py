"""Classes for executing and tracing circuit simulations."""

from __future__ import print_function, unicode_literals

import sys
import re
import numbers
import collections

from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .core import working_block, PostSynthBlock
from .wire import Input, Register, Const, Output, WireVector
from .memory import RomBlock
from .helperfuncs import check_rtl_assertions, _currently_in_ipython, PythonSanitizer

# ----------------------------------------------------------------
#    __                         ___    __
#   /__` |  |\/| |  | |     /\   |  | /  \ |\ |
#   .__/ |  |  | \__/ |___ /~~\  |  | \__/ | \|
#


class Simulation(object):
    """A class for simulating blocks of logic step by step."""

    simple_func = {  # OPS
        'w': lambda x: x,
        '~': lambda x: ~x,
        '&': lambda l, r: l & r,
        '|': lambda l, r: l | r,
        '^': lambda l, r: l ^ r,
        'n': lambda l, r: ~(l & r),
        '+': lambda l, r: l + r,
        '-': lambda l, r: l - r,
        '*': lambda l, r: l * r,
        '<': lambda l, r: int(l < r),
        '>': lambda l, r: int(l > r),
        '=': lambda l, r: int(l == r),
        'x': lambda sel, f, t: f if (sel == 0) else t
    }

    def __init__(
            self, tracer=None, register_value_map=None, memory_value_map=None,
            default_value=0, block=None):
        """ Creates a new circuit simulator

        :param tracer: an instance of SimulationTrace used to store execution results.
        :param register_value_map: is a map of {Register: value}.
        :param memory_value_map: is a map of maps {Memory: {address: Value}}.
        :param default_value: is the value that all unspecified registers and memories will
         default to. If no default_value is specified, it will use the value stored in the
         object (default to 0)
        :param block: the hardware block to be traced (which might be of type PostSynthesisBlock).
        """

        """ Creates object and initializes it with self._initialize.
        register_value_map, memory_value_map, and default_value are passed on to _initialize.
        """

        block = working_block(block)
        block.sanity_check()  # check that this is a good hw block

        self.value = {}  # map from signal->value
        self.memvalue = {}  # map from {memid :{address: value}}
        self.block = block
        self.default_value = default_value
        self.tracer = tracer
        self._initialize(register_value_map, memory_value_map)

    def _initialize(self, register_value_map=None, memory_value_map=None, default_value=None):
        """ Sets the wire, register, and memory values to default or as specified.

        :param register_value_map: is a map of {Register: value}.
        :param memory_value_map: is a map of maps {Memory: {address: Value}}.
        :param default_value: is the value that all unspecified registers and memories will
         default to. If no default_value is specified, it will use the value stored in the
         object (default to 0)
        """

        if default_value is None:
            default_value = self.default_value

        # set registers to their values
        reg_set = self.block.wirevector_subset(Register)
        if register_value_map is not None:
            for r in reg_set:
                if r in register_value_map:
                    self.value[r] = register_value_map[r]
                else:
                    self.value[r] = default_value

        # set constants to their set values
        for w in self.block.wirevector_subset(Const):
            self.value[w] = w.val
            assert isinstance(w.val, numbers.Integral)  # for now

        # set memories to their passed values

        for mem_net in self.block.logic_subset('m@'):
            memid = mem_net.op_param[1].id
            if memid not in self.memvalue:
                self.memvalue[memid] = {}

        if memory_value_map is not None:
            for (mem, mem_map) in memory_value_map.items():
                if isinstance(self.block, PostSynthBlock):
                    mem = self.block.mem_map[mem]  # pylint: disable=maybe-no-member
                self.memvalue[mem.id] = mem_map
                max_addr_val, max_bit_val = 2**mem.addrwidth, 2**mem.bitwidth
                for (addr, val) in mem_map.items():
                    if addr < 0 or addr >= max_addr_val:
                        raise PyrtlError('error, address %s in %s outside of bounds' %
                                         (str(addr)), mem.name)
                    if val < 0 or val >= max_bit_val:
                        raise PyrtlError('error, %s at %s in %s outside of bounds' %
                                         (str(val), str(addr), mem.name))

        defined_roms = []
        # set ROMs to their default values
        for romNet in self.block.logic_subset('m'):
            rom = romNet.op_param[1]
            rom_dict = self.memvalue[rom.id]
            if isinstance(rom, RomBlock) and rom not in defined_roms:
                for address in range(2**rom.addrwidth):
                    rom_dict[address] = rom._get_read_data(address)

        # set all other variables to default value
        for w in self.block.wirevector_set:
            if w not in self.value:
                self.value[w] = default_value

        self.ordered_nets = tuple((i for i in self.block))
        self.edge_update_nets = tuple((self.block.logic_subset('r@')))

    def step(self, provided_inputs):
        """ Take the simulation forward one cycle

        :param provided_inputs: a dictionary mapping wirevectors to their values for this step
        """

        # To avoid weird loops, we need a copy of the old values which
        # we can then use to make our updates from
        prior_value = self.value.copy()

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
            if len(bin(provided_inputs[i]))-2 > sim_wire.bitwidth:
                raise PyrtlError(
                    'the bitwidth for "%s" is %d, but the provided input '
                    '%d requires %d bits to represent'
                    % (name, sim_wire.bitwidth,
                       provided_inputs[i], len(bin(provided_inputs[i]))-2))

            self.value[sim_wire] = provided_inputs[i]
            supplied_inputs.add(sim_wire)

        # Check that only inputs are specified, and set the values
        if input_set != supplied_inputs:
            for i in input_set.difference(supplied_inputs):
                raise PyrtlError('Input "%s" has no input value specified' % i.name)

        # Do all of the clock-edge triggered operations based off of the priors
        for net in self.edge_update_nets:
            self._edge_update(net, prior_value)

        for net in self.ordered_nets:
            self._execute(net)

        # at the end of the step, record the values to the trace
        # print self.value # Helpful Debug Print
        if self.tracer is not None:
            self.tracer.add_step(self.value)

        # finally, if any of the rtl_assert assertions are failing then we should
        # raise the appropriate exceptions
        check_rtl_assertions(self)

    def inspect(self, w):
        """ Get the value of a wirevector in the current simulation cycle.

        :param w: the wirevector to inspect
        :return: value of w in the current step of simulation

        Will throw KeyError if w does not exist in the simulation.
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
        of the primitive ops.  Function updates self.value accordingly.
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
            read_addr = self.value[net.args[0]]
            result = self.memvalue[memid].get(read_addr, self.default_value)
        else:
            raise PyrtlInternalError('error, unknown op type')

        self.value[net.dests[0]] = self._sanitize(result, net.dests[0])

    def _edge_update(self, net, prior_value):
        """Handle the posedge event for the simulation of the given net.

        Combinational logic should have no posedge behavior, but registers and
        memory should.  This function, along with _execute, defined the
        semantics of the primitive ops.  Function updates self.value and
        self.memvalue accordingly (using prior_value)
        """
        if net.op in 'w~&|^n+-*<>=xcsm':
            return  # stateless elements and memory-read
        else:
            if net.op == 'r':
                # copy result from input to output of register
                argval = prior_value[net.args[0]]
                self.value[net.dests[0]] = self._sanitize(argval, net.dests[0])
            elif net.op == '@':
                memid = net.op_param[0]
                write_addr = prior_value[net.args[0]]
                write_val = prior_value[net.args[1]]
                write_enable = prior_value[net.args[2]]
                if write_enable:
                    self.memvalue[memid][write_addr] = write_val
            else:
                raise PyrtlInternalError

    def _print_values(self):
        print(' '.join([str(v) for _, v in sorted(self.value.items())]))


# ----------------------------------------------------------------
#    ___       __  ___     __
#   |__   /\  /__`  |     /__` |  |\/|
#   |    /~~\ .__/  |     .__/ |  |  |
#


class FastSimulation(object):
    """A class for running JIT implementations of blocks.

    As of right now (5/26/2016), the interface is the same as Simulation.
    They should still be similar in the future
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
            self, register_value_map=None, memory_value_map=None,
            default_value=0, tracer=None, block=None, code_file=None):
        """
        :param code_file: The file in which to store a copy of the generated
        python code
        """

        block = working_block(block)
        block.sanity_check()  # check that this is a good hw block

        self.block = block
        self.default_value = default_value
        self.tracer = tracer
        self.sim_func = None
        self.code_file = code_file
        self.mems = {}
        self.regs = {}
        self.internal_names = PythonSanitizer('_fastsim_tmp_')
        self._initialize(register_value_map, memory_value_map)

    def _initialize(self, register_value_map=None, memory_value_map=None, default_value=None):
        if default_value is None:
            default_value = self.default_value
        if register_value_map is None:
            register_value_map = {}

        for wire in self.block.wirevector_set:
            self.internal_names.make_valid_string(wire.name)

        # set registers to their values
        reg_set = self.block.wirevector_subset(Register)
        for r in reg_set:
            if r in register_value_map:
                self.regs[r.name] = register_value_map[r]
            else:
                self.regs[r.name] = default_value

        self._initialize_mems(memory_value_map)

        s = self._compiled()
        if self.code_file is not None:
            with open(self.code_file, 'w') as file:
                file.write(s)

        context = {}
        logic_creator = compile(s, '<string>', 'exec')
        exec(logic_creator, context)
        self.sim_func = context['sim_func']

    def _initialize_mems(self, memory_value_map):
        if memory_value_map is not None:
            for (mem, mem_map) in memory_value_map.items():
                self.mems[self._mem_varname(mem)] = mem_map

        for net in self.block.logic_subset('m@'):
            mem = net.op_param[1]
            if self._mem_varname(mem) not in self.mems:
                if isinstance(mem, RomBlock):
                    self.mems[self._mem_varname(mem)] = mem
                else:
                    self.mems[self._mem_varname(mem)] = {}

    def step(self, provided_inputs):
        """ Run the simulation for a cycle

        :param provided_inputs: a dictionary mapping WireVectors (or their names)
          to their values for this step
          eg: {wire: 3, "wire_name": 17}
        """
        # validate_inputs
        for wire, value in provided_inputs.items():
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
        self.context.update(self.regs)
        self.context.update(ins)
        if self.tracer is not None:
            self.tracer.add_fast_step(self)

        # check the rtl assertions
        check_rtl_assertions(self)

    def inspect(self, w):
        """ Get the value of a wirevector in the current simulation cycle.

        :param w: WireVector object or name of WireVector to inspect
        :return: value of w in the current step of simulation

        Will throw KeyError if w does not exist in the simulation.

        Note for multiple blocks: If w is a wirevector, and is not part of
        the block currently simulated, inspect will look for a wire with
        the same name in the simulated block
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
            return str(wire.val)  # hardcoded
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
         code that can be execed to get a function to execute"""
        # Dev Notes:
        # Because of fast locals in functions in both CPython and PyPy, getting a
        # function to execute makes the code a few times faster than
        # just executing it in the global exec scope.
        prog = [self._prog_start]

        simple_func = {  # OPS
            'w': lambda x: x,
            'r': lambda x: x,
            '~': lambda x: '(~' + x + ')',
            '&': lambda l, r: '(' + l + '&' + r + ')',
            '|': lambda l, r: '(' + l + '|' + r + ')',
            '^': lambda l, r: '(' + l + '^' + r + ')',
            'n': lambda l, r: '(~(' + l + '&' + r + '))',
            '+': lambda l, r: '(' + l + '+' + r + ')',
            '-': lambda l, r: '(' + l + '-' + r + ')',
            '*': lambda l, r: '(' + l + '*' + r + ')',
            '<': lambda l, r: 'int(' + l + '<' + r + ')',
            '>': lambda l, r: 'int(' + l + '>' + r + ')',
            '=': lambda l, r: 'int(' + l + '==' + r + ')',
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
                    if expr is not '':
                        expr += ' | '
                    shiftby = sum(len(j) for j in net.args[i+1:])
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
                write_addr = self._arg_varname(net.args[0])
                write_val = self._arg_varname(net.args[1])
                write_enable = self._arg_varname(net.args[2])
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
                v_wire_name = self._varname(wire)
                if not isinstance(wire, (Input, Const, Register, Output)):
                    prog.append('    outs["%s"] = %s' % (wire_name, v_wire_name))

        prog.append("    return regs, outs, mem_ws")
        return '\n'.join(prog)


# ----------------------------------------------------------------
#    ___  __        __   ___
#     |  |__)  /\  /  ` |__
#     |  |  \ /~~\ \__, |___
#


class _WaveRendererBase(object):
    _tick, _up, _down, _x, _low, _high, _revstart, _revstop = ('' for i in range(8))

    def __init__(self):
        super(_WaveRendererBase, self).__init__()
        self.prior_val = None
        self.prev_wire = None

    def tick_segment(self, n, symbol_len, segment_size):
        num_tick = self._tick + str(n)
        return num_tick.ljust(symbol_len * segment_size)

    def render_val(self, w, n, current_val, symbol_len):
        if w is not self.prev_wire:
            self.prev_wire = w
            self.prior_val = current_val
        out = self._render_val_with_prev(w, n, current_val, symbol_len)
        self.prior_val = current_val
        return out

    def _render_val_with_prev(self, w, n, current_val, symbol_len):
        """Return a string encoding the given value in a waveform.

        :param w: The WireVector we are rendering to a waveform
        :param n: An integer from 0 to segment_len-1
        :param current_val: the value to be rendered
        :param symbol_len: and integer for how big to draw the current value

        Returns a string of printed length symbol_len that will draw the
        representation of current_val.  The input prior_val is used to
        render transitions.
        """
        sl = symbol_len-1
        if len(w) > 1:
            out = self._revstart
            if current_val != self.prior_val:
                out += self._x + hex(current_val).rstrip('L').ljust(sl)[:sl]
            elif n == 0:
                out += hex(current_val).rstrip('L').ljust(symbol_len)[:symbol_len]
            else:
                out += ' '*symbol_len
            out += self._revstop
        else:
            pretty_map = {
                (0, 0): self._low + self._low * sl,
                (0, 1): self._up + self._high * sl,
                (1, 0): self._down + self._low * sl,
                (1, 1): self._high + self._high * sl,
            }
            out = pretty_map[(self.prior_val, current_val)]
        return out


class Utf8WaveRenderer(_WaveRendererBase):
    _tick = u'\u258f'
    _up, _down = u'\u2571', u'\u2572'
    _x, _low, _high = u'\u2573', u'\u005f', u'\u203e'
    _revstart, _revstop = '\x1B[7m', '\x1B[0m'


class AsciiWaveRenderer(_WaveRendererBase):
    """ Poor Man's wave renderer (for windows cmd compatibility)"""
    _tick = '-'
    _up, _down = '/', '\\'
    _x, _low, _high = 'x', '_', '-'
    _revstart, _revstop = ' ', ' '


def default_renderer():
    import sys
    try:
        if str(sys.stdout.encoding).lower() == "utf-8":
            return Utf8WaveRenderer
    except Exception:
        pass
    return AsciiWaveRenderer


def _trace_sort_key(w):
    def tryint(s):
        try:
            return int(s)
        except ValueError:
            return s
    return [tryint(c) for c in re.split('([0-9]+)', w)]


class TraceStorage(collections.Mapping):
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
        return self.__data[key]


class SimulationTrace(object):
    """ Storage and presentation of simulation waveforms. """

    def __init__(self, wirevector_subset=None, block=None):
        block = working_block(block)

        def is_internal_name(name):
            return (name.startswith('tmp') or name.startswith('const') or
                    # or name.startswith('synth_')
                    name.endswith("'"))

        if wirevector_subset is None:
            wirevector_subset = [w for w in block.wirevector_set if not is_internal_name(w.name)]
        elif wirevector_subset == 'all':
            wirevector_subset = block.wirevector_set

        self.trace = TraceStorage(wirevector_subset)
        self._wires = {wv.name: wv for wv in wirevector_subset}

    def __len__(self):
        """ Return the current length of the trace in cycles. """
        if len(self.trace) == 0:
            raise PyrtlError('error, length of trace undefined if no signals tracked')
        # return the length of the list of some element in the dictionary (all should be the same)
        wire, value_list = next(x for x in self.trace.items())
        return len(value_list)

    def add_step(self, value_map):
        """ Add the values in value_map to the end of the trace. """
        if len(self.trace) == 0:
            raise PyrtlError('error, simulation trace needs at least 1 signal to track '
                             '(by default, unnamed signals are not traced -- try either passing '
                             'a name to a WireVector or setting a "wirevector_subset" option)')
        for wire in self.trace:
            tracelist = self.trace[wire]
            wirevec = self._wires[wire]
            tracelist.append(value_map[wirevec])

    def add_fast_step(self, fastsim):
        """ Add the fastsim context to the trace. """
        for wire_name in self.trace:
            self.trace[wire_name].append(fastsim.context[wire_name])

    def print_trace(self, file=sys.stdout):
        if len(self.trace) == 0:
            raise PyrtlError('error, cannot print an empty trace')
        maxlen = max(len(w) for w in self.trace)
        for w in sorted(self.trace, key=_trace_sort_key):
            file.write(' '.join([w.rjust(maxlen),
                       ''.join(str(x) for x in self.trace[w])+'\n']))
            file.flush()

    def print_vcd(self, file=sys.stdout):
        """ Print the trace out as a VCD File for use in other tools. """
        # dump header info
        # file_timestamp = time.strftime("%a, %d %b %Y %H:%M:%S (UTC/GMT)", time.gmtime())
        # print >>file, " ".join(["$date", file_timestamp, "$end"])
        print(' '.join(['$timescale', '1ns', '$end']), file=file)
        print(' '.join(['$scope', 'module logic', '$end']), file=file)

        def print_trace_strs(time):
            for w in sorted(self.trace, key=_trace_sort_key):
                print(' '.join([str(bin(self.trace[w][time]))[1:], w]), file=file)

        # dump variables
        for w in sorted(self.trace, key=_trace_sort_key):
            print(' '.join(['$var', 'wire', str(self._wires[w].bitwidth), w, w, '$end']), file=file)
        print(' '.join(['$upscope', '$end']), file=file)
        print(' '.join(['$enddefinitions', '$end']), file=file)
        print(' '.join(['$dumpvars']), file=file)
        print_trace_strs(0)
        print(' '.join(['$end']), file=file)

        # dump values
        endtime = max([len(self.trace[w]) for w in self.trace])
        for timestamp in range(endtime):
            print(''.join(['#', str(timestamp)]), file=file)
            print_trace_strs(timestamp)
        print(''.join(['#', str(endtime)]), file=file)
        file.flush()

    def render_trace(
            self, trace_list=None, file=sys.stdout, render_cls=default_renderer(),
            symbol_len=5, segment_size=5, segment_delim=' ', extra_line=True):

        """ Render the trace to a file using unicode and ASCII escape sequences.

        The resulting output can be viewed directly on the terminal or looked
        at with "more" or "less -R" which both should handle the ASCII escape
        sequences used in rendering. render_trace takes the following optional
        arguments.
        :param trace_list: A list of signals to be output in the specified order.
        :param file: The place to write output, default to stdout.
        :param render_cls: A class that translates traces into output bytes.
        :param symbol_len: The "length" of each rendered cycle in characters.
        :param segment_size: Traces are broken in the segments of this number of cycles.
        :param segment_delim: The character to be output between segments.
        :param extra_line: A Boolean to determin if we should print a blank line between signals.
        """
        if _currently_in_ipython():
            from IPython.display import display, HTML, Javascript  # pylint: disable=import-error
            from .inputoutput import trace_to_html
            htmlstring = trace_to_html(self, trace_list=trace_list, sortkey=_trace_sort_key)
            display(HTML(htmlstring))
            display(Javascript('WaveDrom.ProcessAll()'))
        else:
            self.render_trace_to_text(
                trace_list=trace_list, file=file, render_cls=render_cls,
                symbol_len=symbol_len, segment_size=segment_size,
                segment_delim=segment_delim, extra_line=extra_line)

    def render_trace_to_text(
            self, trace_list, file, render_cls,
            symbol_len, segment_size, segment_delim, extra_line):

        renderer = render_cls()

        def formatted_trace_line(wire, trace):
            heading = wire.rjust(maxnamelen) + ' '
            trace_line = ''
            for i in range(len(trace)):
                if (i % segment_size == 0) and i > 0:
                    trace_line += segment_delim
                trace_line += renderer.render_val(
                    self._wires[wire],
                    i % segment_size,
                    trace[i],
                    symbol_len)
            return heading + trace_line

        # default to printing all signals in sorted order
        if trace_list is None:
            trace_list = sorted(self.trace, key=_trace_sort_key)
        elif any(isinstance(x, WireVector) for x in trace_list):
            import warnings
            warnings.warn(
                'Access to trace by WireVector instead of name is deprecated.',
                DeprecationWarning)
            trace_list = [getattr(x, 'name', x) for x in trace_list]

        # print the 'ruler' which is just a list of 'ticks'
        # mapped by the pretty map

        maxnamelen = max(len(w) for w in self.trace)
        maxtracelen = max(len(v) for v in self.trace.values())
        if segment_size is None:
            segment_size = maxtracelen
        spaces = ' '*(maxnamelen+1)
        ticks = [renderer.tick_segment(n, symbol_len, segment_size)
                 for n in range(0, maxtracelen, segment_size)]
        print(spaces + segment_delim.join(ticks), file=file)

        # now all the traces
        for w in trace_list:
            if extra_line:
                print(file=file)
            print(formatted_trace_line(w, self.trace[w]), file=file)
        if extra_line:
            print(file=file)
