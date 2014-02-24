"""
PyRTL is a framework for synthesizable logic specification in Python.

The module contains a collection of classes that are intended to work together
to provide RTL specification, simulation, tracing, and testing suitable for
teaching and research.  Simplicity, usability, clarity, and extendability
rather than performance or optimization is the overarching goal.
"""

import collections
import sys
import re


# todo list:
# * all user visible assert calls should be replaced with "raise PyrtlError"
# * all PyrtlError calls should have useful error message
# * all classes should have useful docstrings
# * all public functions and methods should have useful docstrings
# * all private methods and members should use "_" at the start of their names
# * should have set of unit tests for main abstractions
# * should be PEP8 compliant
# * multiple nested blocks should be supported
# * add verilog export option to block

# ASCII Art in "JS Stick Letters"


#-----------------------------------------------------------------
#    __        __   __
#   |__) |    /  \ /  ` |__/
#   |__) |___ \__/ \__, |  \
#

LogicNet = collections.namedtuple(
    'LogicNet',
    ['op', 'op_param', 'args', 'dests']
    )


class Block(object):
    """Data structure for holding a hardware connectivity graph.
    Structure is primarily contained in self.logic which holds a set of
    "LogicNet"s. Each LogicNet is describes a primitive unit (such as an adder
    or memory).  The primitive is described by a 4-tuple of the op (a single
    character describing the operation such as '+' or 'm'), a set of hard
    parameters to that primitives (such as the number of read ports for a
    memory), and two tuples (args and dests) that list the wirevectors hooked
    up as inputs and outputs to that primitive respectively.

    * Most logical and arithmetic ops ('&','|','^','+','-') are pretty self
      explanitory, they should perform the operation specified.
    * The op (None) is simply a directional wire and has no logic function.
    * The 'c' operator is the concatiation operator and combines any number of
      wirevectors (a,b,...,z) into a single new wirevector with "a" in the MSB
      and "z" (or whatever is last) in the LSB position.
    * The 's' operator is the selection operator and chooses, based in the
      op_param specificied, a subset of the logic bits from a wire vector to
      select.  Repeats are accepted.
    * The 'r' operator is a register and on posedge, simply copies the value
      from the input to the output of the register
    * The 'm' operator is a memory block, which supports async reads (acting
      like combonational logic), and syncronous writes (writes are "latched"
      at posedge).  Multiple read and write ports are possible, and op_param
      requires three numbers (memory id, num reads, num writes). It assumes
      that operator reads have one addr (an arg) and one data (a dest).
      Writes have two args (addr and data).  Reads are specified first and then
      writes.

    The connecting elements (args and dests) should be WireVectors or derived
    from WireVector, and registered seperately with the block using
    the method add_wirevector.
    """

    def __init__(self):
        """Creates and empty hardware block."""
        self.logic = set([])  # set of nets, each is a LogicNet named tuple
        self.wirevector_set = set([])  # set of all wirevectors
        self.wirevector_by_name = {}  # map from name->wirevector
        self.legal_ops = set('~&|^+-csrm') | set([None])

    def __str__(self):
        """String form has one LogicNet per line."""
        return '\n'.join(str(l) for l in self.logic)

    def add_wirevector(self, wirevector):
        """ Add a wirevector object to the module."""
        self.wirevector_set.add(wirevector)
        self.wirevector_by_name[wirevector.name] = wirevector

    def add_net(self, net):
        """ Connect new net to wirevectors previously added to the block."""
        for w in net.args + net.dests:
            if not isinstance(w, WireVector):
                raise PyrtlError(
                    'error attempting to create logic with input of type "%s" '
                    'instead of WireVector' % type(w))
            if w not in self.wirevector_set:
                raise PyrtlError(
                    'error making net with unknown source "%s"'
                    % w.name)
        if net.op not in self.legal_ops:
            raise PyrtlError(
                'error adding op "%s" not from known set %s'
                % (net.op, self.legal_ops))
        self.logic.add(net)

    def wirevector_subset(self, cls=None):
        """Return set of wirevectors, filtered by the types provided as cls."""
        if cls is None:
            return self.wirevector_set
        else:
            return set([x for x in self.wirevector_set if isinstance(x, cls)])

    def typecheck(self):
        """ Check logic and wires and throw PyrtlError if there is an issue."""
        # check for unique names
        wirevector_names = [x.name for x in self.wirevector_set]
        dup_list = [
            x
            for x, y in collections.Counter(wirevector_names).items()
            if y > 1
            ]
        if len(dup_list) > 0:
            raise PyrtlError('Duplicate wire names found: %s' % repr(dup_list))

        # check for dead input wires (not connected to anything)
        dest_set = set(wire for net in self.logic for wire in net.dests)
        arg_set = set(wire for net in self.logic for wire in net.args)
        full_set = dest_set | arg_set
        connected_minus_allwires = full_set.difference(self.wirevector_set)
        if len(connected_minus_allwires) > 0:
            raise PyrtlError(
                'Unknown wires found in net: %s'
                % repr(connected_minus_allwires))
        allwires_minus_connected = self.wirevector_set.difference(full_set)
        if len(allwires_minus_connected) > 0:
            raise PyrtlError(
                'Wires declared but never connected: %s'
                % repr([w.name for w in allwires_minus_connected]))

#-----------------------------------------------------------------
#    __                         ___    __
#   /__` |  |\/| |  | |     /\   |  | /  \ |\ |
#   .__/ |  |  | \__/ |___ /~~\  |  | \__/ | \|
#


class Simulation(object):

    """A class for simulating blocks of logic step by step."""

    def __init__(
            self, register_value_map=None, default_value=None,
            tracer=None, hw_description=None):
        if hw_description is None:
            hw_description = ParseState.current_block
        hw_description.typecheck()  # check that this is a good hw block
        self.value = {}   # map from signal->value
        self.memvalue = {}  # map from (memid,address)->value
        self.hw = hw_description
        self.default_value = default_value
        self.tracer = tracer
        self.initialize(register_value_map)
        self.max_iter = 1000

    def initialize(self, register_value_map, default_value=None):
        """ Sets the wire and register values to default or as specified """
        self.value = {}
        if default_value is None:
            default_value = self.default_value

        # set registers to their values
        reg_set = self.hw.wirevector_subset(Register)
        if register_value_map is not None:
            for r in reg_set:
                if r in register_value_map:
                    self.value[r] = register_value_map[r]
                else:
                    self.value[r] = default_value

        # set constants to their set values
        for w in self.hw.wirevector_subset(Const):
            self.value[w] = w.val
            assert isinstance(w.val, int)  # for now

        # set all other variables to default value
        for w in self.hw.wirevector_set:
            if w not in self.value:
                self.value[w] = default_value

    def print_values(self):
        print ' '.join([str(v) for _, v in sorted(self.value.iteritems())])

    def step(self, provided_inputs):
        """ Take the simulation forward one cycle """
        # check that all Input have a corresponding provided_input
        input_set = self.hw.wirevector_subset(Input)
        for i in input_set:
            if i not in provided_inputs:
                raise PyrtlError(
                    'Input "%s" has no input value specified'
                    % i.name)

        # check that only inputs are specified, and set the values
        for i in provided_inputs.keys():
            if i not in input_set:
                raise PyrtlError(
                    'step provided a value for input for "%s" which is '
                    'not a known input' % i.name)
            self.value[i] = provided_inputs[i]

        # do all of the clock-edge triggered operations
        for net in self.hw.logic:
            self.edge_update(net)

        # propagate inputs to outputs
        # wires  which are defined at the start are inputs and registers
        const_set = self.hw.wirevector_subset(Const)
        reg_set = self.hw.wirevector_subset(Register)
        defined_set = reg_set | const_set | input_set
        logic_left = self.hw.logic.copy()

        for _ in xrange(self.max_iter):
            logic_left = set(
                net
                for net in logic_left
                if not self._try_execute(defined_set, net)
                )
            if len(logic_left) == 0:
                break
        else:  # no break
            raise PyrtlInternalError(
                'error, "%d" appears to be waiting for value never produced'
                % str(logic_left))

        # at the end of the step, record the values to the trace
        if self.tracer is not None:
            self.tracer.add_step(self.value)

    def sanitize(self, val, wirevector):
        """Return a modified version of val that would fit in wirevector.

        This function should be applied to every primitive call, and it's
        default behavior is to mask the upper bits of value and return that
        new value.
        """
        return val & ((1 << len(wirevector))-1)

    def edge_update(self, net):
        """Handle the posedge event for the simulation of the given net.

        Combinational logic should have no posedge behavior, but registers and
        memory should.  This function, along with execute, defined the
        semantics of the primitive ops.  Function updates self.value and
        self.memvalue accordingly.
        """
        if net.op is None or net.op in '~ & | ^ + - c s'.split():
            return  # stateless elements
        else:
            if net.op == 'r':
                # copy result from input to output of register
                argval = self.value[net.args[0]]
                self.value[net.dests[0]] = self.sanitize(argval, net.dests[0])
            elif net.op == 'm':
                memid = net.op_param[0]
                num_reads = net.op_param[1]
                num_writes = net.op_param[2]
                if num_reads + 2*num_writes != len(net.args):
                    raise PyrtlInternalError
                for i in range(num_reads, num_reads + 2*num_writes, 2):
                    write_addr = self.value[net.args[i]]
                    write_val = self.value[net.args[i+1]]
                    self.memvalue[(memid, write_addr)] = write_val
            else:
                raise PyrtlInternalError

    def execute(self, net):
        """Handle the combinational logic update rules for the given net.

        This function, along with execute, defined the semantics
        of the primitive ops.  Function updates self.value accordingly.
        """
        simple_func = {
            None: lambda x: x,
            '~': lambda x: ~x,
            '&': lambda l, r: l & r,
            '|': lambda l, r: l | r,
            '^': lambda l, r: l ^ r,
            '+': lambda l, r: l + r,
            '-': lambda l, r: l - r
            }
        if net.op in simple_func:
            argvals = [self.value[arg] for arg in net.args]
            result = simple_func[net.op](*argvals)
            self.value[net.dests[0]] = self.sanitize(result, net.dests[0])
        elif net.op == 'c':
            result = 0
            for arg in net.args:
                result = result << len(arg)
                result = result | self.value[arg]
            self.value[net.dests[0]] = self.sanitize(result, net.dests[0])
        elif net.op == 's':
            result = 0
            source = self.value[net.args[0]]
            for b in net.op_param[::-1]:
                result = (result << 1) | (0x1 & (source >> b))
            self.value[net.dests[0]] = self.sanitize(result, net.dests[0])
        elif net.op == 'r':
            pass  # registers have no logic function
        elif net.op == 'm':
            # memories act async for reads
            memid = net.op_param[0]
            num_reads = net.op_param[1]
            if num_reads != len(net.dests):
                raise PyrtlInternalError
            for i in range(num_reads):
                read_addr = self.value[net.args[i]]
                mem_lookup_result = self.memvalue.get((memid, read_addr), 0)
                self.value[net.dests[i]] = mem_lookup_result
        else:
            raise PyrtlInternalError

    def _try_execute(self, defined_set, net):
        """ Try to Execute net but return False if not ready.

        Ready inputs will be fined in "defined_set" and if any
        inputs are not yet in this set, we know the we need to execute
        the prededing ops first.  If the net is sucessfully exectuted
        return True, otherwise return False so we can return to this net
        at a later time.
        """
        if self._is_ready_to_execute(defined_set, net):
            self.execute(net)
            for dest in net.dests:
                defined_set.add(dest)
            return True
        else:
            return False

    def _is_ready_to_execute(self, defined_set, net):
        """Return true if all of the arguments are ready"""
        return all(arg in defined_set for arg in net.args)


#-----------------------------------------------------------------
#    ___  __        __   ___
#     |  |__)  /\  /  ` |__
#     |  |  \ /~~\ \__, |___
#

def wave_trace_render(w, n, prior_val, current_val, symbol_len):
    """Return a unicode string encoding the given value in a  waveform.

    Given the inputs -
    w - The WireVector we are rendering to a waveform
    n - An integer from 0 to segment_len-1
    prior_val - the value in the cycle prior to the one being rendered
    current_val - the value to be rendered
    symbol_len - and integer for how big to draw the current value

    Returns a string of printed length symbol_len that will draw the
    representation of current_val.  The input prior_val is used to
    render transitions.
    """

    if current_val == 'tick':
        return unichr(0x258f)
    if prior_val is None:
        prior_val = current_val
    sl = symbol_len-1
    up, down = unichr(0x2571), unichr(0x2572)
    x, low, high = unichr(0x2573), unichr(0x005f), unichr(0x203e)
    revstart, revstop = '\x1B[7m', '\x1B[0m'
    pretty_map = {
        (0, 0): low + low*sl,
        (0, 1): up + high*sl,
        (1, 0): down + low*sl,
        (1, 1): high + high*sl,
        }
    if len(w) > 1:
        out = revstart
        if current_val != prior_val:
            out += x + hex(current_val).ljust(sl)[:sl]
        elif n == 0:
            out += hex(current_val).ljust(symbol_len)[:symbol_len]
        else:
            out += ' '*symbol_len
        out += revstop
    else:
        out = pretty_map[(prior_val, current_val)]
    return out


def trace_sort_key(w):
    def tryint(s):
        try:
            return int(s)
        except ValueError:
            return s
    return [tryint(c) for c in re.split('([0-9]+)', w.name)]


class SimulationTrace(object):

    def __init__(self, wirevector_subset=None, hw=None):
        if hw is None:
            hw = ParseState.current_block
        assert isinstance(hw, Block)

        def is_internal_name(name):
            if (
               name.startswith('tmp')
               or name.startswith('const')
               or name.endswith("'")
               ):
                return True
            else:
                return False

        if hw is None and wirevector_subset is None:
            raise PyrtlError(
                'simulation initialization requires either a wirevector_subset'
                ' or full hw to be specified')
        if wirevector_subset is None:
            self.trace = {
                w: []
                for w in hw.wirevector_set
                if not is_internal_name(w.name)
                }
        else:
            self.trace = {w: [] for w in wirevector_subset}

    def add_step(self, value_map):
        for w in self.trace:
            self.trace[w].append(value_map[w])

    def print_trace(self):
        maxlen = max([len(w.name) for w in self.trace])
        for w in sorted(self.trace, key=trace_sort_key):
            print w.name.rjust(maxlen), ''.join(str(x) for x in self.trace[w])

    def render_trace(
            self, renderer=wave_trace_render, symbol_len=5,
            segment_size=5, segment_delim=' ', extra_line=True):

        def formatted_trace_line(w, trace):
            heading = w.name.rjust(maxnamelen) + ' '
            trace_line = ''
            last_element = None
            for i in xrange(len(trace)):
                if (i % segment_size == 0) and i > 0:
                    trace_line += segment_delim
                trace_line += renderer(
                    w, i % segment_size,
                    last_element, trace[i], symbol_len)
                last_element = trace[i]
            return heading+trace_line

        # print the 'ruler' which is just a list of 'ticks'
        # mapped by the pretty map
        def tick_segment(n):
            num_tick = renderer(None, None, None, 'tick', symbol_len) + str(n)
            return num_tick.ljust(symbol_len * segment_size)

        maxnamelen = max(len(w.name) for w in self.trace)
        maxtracelen = max(len(v) for v in self.trace.values())
        if segment_size is None:
            segment_size = maxtracelen
        spaces = ' '*(maxnamelen+1)
        ticks = [tick_segment(n) for n in xrange(0, maxtracelen, segment_size)]
        print spaces + segment_delim.join(ticks).encode('utf-8')

        # now all the traces
        for w in sorted(self.trace, key=trace_sort_key):
            if extra_line:
                print
            print formatted_trace_line(w, self.trace[w]).encode('utf-8')
        if extra_line:
            print


#-----------------------------------------------------------------
#        ___  __  ___  __   __   __               ___
#  \  / |__  /  `  |  /  \ |__) /__`   -|-  |\/| |__   |\/|
#   \/  |___ \__,  |  \__/ |  \ .__/        |  | |___  |  |
#

class WireVector(object):
    def __init__(self, bitwidth=None, name=None):
        # now figure out a name
        if name is None:
            name = ParseState.next_tempvar_name()
        if name.lower() in ['clk', 'clock']:
            raise PyrtlError(
                'Clock signals should never be explicitly instantiated')
        self.name = name
        # now handle the bitwidth
        if bitwidth is not None:
            assert isinstance(bitwidth, int)
            assert bitwidth > 0
        self.bitwidth = bitwidth
        ParseState.current_block.add_wirevector(self)

    def __repr__(self):
        return ''.join([
            type(self).__name__,
            ':',
            self.name,
            '/',
            str(self.bitwidth)
            ])

    def __ilshift__(self, other):
        if not isinstance(other, WireVector):
            other = Const(other)
        if self.bitwidth is None:
            self.bitwidth = len(other)
        else:
            assert len(self) == len(other)

        net = LogicNet(
            op=None,
            op_param=None,
            args=(other,),
            dests=(self,))
        ParseState.current_block.add_net(net)
        return self

    def logicop(self, other, op):
        a, b = self, other
        # convert constants if necessary
        if not isinstance(b, WireVector):
            b = Const(b)
        # check size of operands
        if len(a) < len(b):
            a = a.sign_extended(len(b))
        elif len(b) < len(a):
            b = b.sign_extended(len(a))
        # if len(a) != len(b):
        #    raise PyrtlError(
        #       'error, cannot apply op "%s" to wirevectors'
        #       ' of different length' % op)
        s = WireVector(bitwidth=len(a))  # both are same length now
        net = LogicNet(
            op=op,
            op_param=None,
            args=(a, b),
            dests=(s,))
        ParseState.current_block.add_net(net)
        return s

    def __and__(self, other):
        return self.logicop(other, '&')

    def __or__(self, other):
        return self.logicop(other, '|')

    def __xor__(self, other):
        return self.logicop(other, '^')

    def __add__(self, other):
        return self.logicop(other, '+')

    def __sub__(self, other):
        return self.logicop(other, '-')

    def __getitem__(self, item):
        assert self.bitwidth is not None
        allindex = [i for i in range(self.bitwidth)]
        if isinstance(item, int):
            selectednums = [allindex[item]]
        else:
            selectednums = allindex[item]  # slice
        outwire = WireVector(bitwidth=len(selectednums))
        net = LogicNet(
            op='s',
            op_param=tuple(selectednums),
            args=(self,),
            dests=(outwire,))
        ParseState.current_block.add_net(net)
        return outwire

    def __len__(self):
        return self.bitwidth

    def sign_extended(self, bitwidth):
        """ return a sign extended wirevector derived from self """
        return self._extended(bitwidth, self[-1])

    def zero_extended(self, bitwidth):
        """ return a zero extended wirevector derived from self """
        return self._extended(bitwidth, Const(0, bitwidth=1))

    def _extended(self, bitwidth, extbit):
        numext = bitwidth - self.bitwidth
        if numext == 0:
            return self
        elif numext < 0:
            raise PyrtlError(
                'error, zero_extended cannot reduce the number of bits')
        else:
            extvector = WireVector(bitwidth=numext)
            net = LogicNet(
                op='s',
                op_param=(0,)*numext,
                args=(extbit,),
                dests=(extvector,))
            ParseState.current_block.add_net(net)
            return concat(extvector, self)


class Input(WireVector):
    def __init__(self, bitwidth=None, name=None):
        WireVector.__init__(self, bitwidth, name)

    def __ilshift__(self, _):
        raise PyrtlError(
            'Input, such as "%s", cannot have values generated internally'
            % str(self.name))


class Output(WireVector):
    def __init__(self, bitwidth=None, name=None):
        WireVector.__init__(self, bitwidth, name)
    # todo: check that we can't read from this vector


class Const(WireVector):
    def __init__(self, val, bitwidth=None):
        self.name = ParseState.next_constvar_name(val)
        if bitwidth is None:
            self.bitwidth = len(bin(val))-2
        else:
            self.bitwidth = bitwidth
        self.val = val
        assert (self.val >> self.bitwidth) == 0
        ParseState.current_block.add_wirevector(self)

    def __ilshift__(self, other):
        raise PyrtlError(
            'ConstWires, such as "%s", should never be assigned to with <<='
            % str(self.name))


class Register(WireVector):
    def __init__(self, bitwidth, name=None):
        WireVector.__init__(self, bitwidth=bitwidth, name=name)
        self.reg_in = None

    def _makereg(self):
        if self.reg_in is None:
            n = WireVector(bitwidth=self.bitwidth, name=self.name+"'")
            net = LogicNet(
                op='r',
                op_param=None,
                args=(n,),
                dests=(self,))
            ParseState.current_block.add_net(net)
            self.reg_in = n
        return self.reg_in

    def __ilshift__(self, other):
        raise PyrtlError(
            'Registers, such as "%s", should never be assigned to with <<='
            % str(self.name))

    @property
    def next(self):
        return self._makereg()

    @next.setter
    def next(self, value):
        # The .next feild can be set with either "<<=" or "=", and
        # they do the same thing.
        if self.reg_in == value:
            return
        if self.reg_in is not None:
            raise PyrtlError
        if len(self) != len(value):
            raise PyrtlError
        n = self._makereg()
        n <<= value


class MemBlock(object):
    # data = memory[addr]  (infer read port)
    # memory[addr] = data  (infer write port)
    # Not currently implemented:  memory[addr] <<= data (infer write port)
    def __init__(self,  bitwidth, addrwidth, name=None):
        if bitwidth <= 0:
            raise PyrtlError
        if addrwidth <= 0:
            raise PyrtlError
        if name is None:
            name = ParseState.next_tempvar_name()

        self.bitwidth = bitwidth
        self.name = name
        self.addrwidth = addrwidth
        self.stored_net = None
        self.id = ParseState.next_memid()
        self.read_addr = []  # arg
        self.read_data = []  # dest
        self.write_addr = []  # arg
        self.write_data = []  # arg

    def __getitem__(self, item):
        if not isinstance(item, WireVector):
            raise PyrtlError
        if len(item) != self.addrwidth:
            raise PyrtlError

        data = WireVector(bitwidth=self.bitwidth)
        self.read_data.append(data)
        self.read_addr.append(item)
        self._update_net()
        return data

    def _update_net(self):
        if self.stored_net:
            ParseState.current_block.logic.remove(self.stored_net)
        assert len(self.write_addr) == len(self.write_data)
        net = LogicNet(
            op='m',
            op_param=(self.id, len(self.read_addr), len(self.write_addr)),
            args=tuple(self.read_addr + self.write_addr + self.write_data),
            dests=tuple(self.read_data))
        ParseState.current_block.add_net(net)
        self.stored_net = net

    def __setitem__(self, item, val):
        if not isinstance(item, WireVector):
            raise PyrtlError
        if len(item) != self.addrwidth:
            raise PyrtlError
        if not isinstance(val, WireVector):
            raise PyrtlError
        if len(val) != self.bitwidth:
            raise PyrtlError
        self.write_data.append(val)
        self.write_addr.append(item)
        self._update_net()


#-----------------------------------------------------------------
#        ___       __   ___  __   __
#  |__| |__  |    |__) |__  |__) /__`
#  |  | |___ |___ |    |___ |  \ .__/
#

def as_wires(val):
    if isinstance(val, int):
        return Const(val)
    else:
        assert isinstance(val, WireVector)
        return val


def concat(*args):
    assert len(args) > 0
    if len(args) == 1:
        return args[0]
    else:
        final_width = sum([len(arg) for arg in args])
        outwire = WireVector(bitwidth=final_width)
        net = LogicNet(
            op='c',
            op_param=None,
            args=tuple(args),
            dests=(outwire,))
        ParseState.current_block.add_net(net)
        return outwire


class PyrtlError(Exception):
    pass  # raised on any user-facing error in this module


class PyrtlInternalError(Exception):
    pass  # raised on any internal failure


#-----------------------------------------------------------------
#   __        __   __   ___     __  ___      ___  ___
#  |__)  /\  |__) /__` |__     /__`  |   /\   |  |__
#  |    /~~\ |  \ .__/ |___    .__/  |  /~~\  |  |___
#

class ParseState(object):
    current_block = Block()
    _tempvar_count = 1
    _memid_count = 0

    @classmethod
    def print_trivial_graph(cls, file=sys.stdout):
        tgf = TrivalGraphExporter()
        tgf.import_from_block(cls.current_block)
        tgf.dump(file)

    @classmethod
    def next_tempvar_name(cls):
        wire_name = ''.join(['tmp', str(cls._tempvar_count)])
        cls._tempvar_count += 1
        return wire_name

    @classmethod
    def next_constvar_name(cls, val):
        wire_name = ''.join(['const', str(cls._tempvar_count), '_', str(val)])
        cls._tempvar_count += 1
        return wire_name

    @classmethod
    def next_memid(cls):
        cls._memid_count += 1
        return cls._memid_count


#-----------------------------------------------------------------
#   ___      __   __   __  ___
#  |__  \_/ |__) /  \ |__)  |
#  |___ / \ |    \__/ |  \  |
#

class TrivalGraphExporter(object):
    def __init__(self):
        self.uid = 1
        self.nodes = {}
        self.edges = set([])
        self.edge_names = {}
        self._block = None

    def producer(self, wire):
        assert isinstance(wire, WireVector)
        for net in self._block.logic:
            for dest in net.dests:
                if dest == wire:
                    return net
        self.add_node(wire, '???')
        return wire

    def consumer(self, wire):
        assert isinstance(wire, WireVector)
        for net in self._block.logic:
            for arg in net.args:
                if arg == wire:
                    return net
        self.add_node(wire, '???')
        return wire

    def add_node(self, x, label):
        self.nodes[x] = (self.uid, label)
        self.uid += 1

    def add_edge(self, frm, to):
        if hasattr(frm, 'name') and not frm.name.startswith('tmp'):
            edge_label = frm.name
        else:
            edge_label = ''
        if frm not in self.nodes:
            frm = self.producer(frm)
        if to not in self.nodes:
            to = self.consumer(to)
        (frm_id, _) = self.nodes[frm]
        (to_id, _) = self.nodes[to]
        self.edges.add((frm_id, to_id))
        if edge_label:
            self.edge_names[(frm_id, to_id)] = edge_label

    def import_from_block(self, block):
        self._block = block
        # build edge and node sets
        for net in self._block.logic:
            label = str(net.op)
            label += str(net.op_param) if net.op_param is not None else ''
            self.add_node(net, label)
        for input in self._block.wirevector_subset(Input):
            label = 'in' if input.name is None else input.name
            self.add_node(input, label)
        for output in self._block.wirevector_subset(Output):
            label = 'out' if output.name is None else output.name
            self.add_node(output, label)
        for const in self._block.wirevector_subset(Const):
            label = str(const.val)
            self.add_node(const, label)
        for net in self._block.logic:
            for arg in net.args:
                self.add_edge(arg, net)
            for dest in net.dests:
                self.add_edge(net, dest)

    def dump(self, file=sys.stdout):
        for (id, label) in self.nodes.values():
            print >> file, id, label
        print >> file, '#'
        for (frm, to) in self.edges:
            print >> file, frm, to, self.edge_names.get((frm, to), '')
