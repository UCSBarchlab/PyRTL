from pyrtl import *

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


