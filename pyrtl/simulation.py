
import sys
import re
import time
import core
import wire
import memory

# ----------------------------------------------------------------
#    __                         ___    __
#   /__` |  |\/| |  | |     /\   |  | /  \ |\ |
#   .__/ |  |  | \__/ |___ /~~\  |  | \__/ | \|
#


class Simulation(object):
    """A class for simulating blocks of logic step by step."""

    def __init__(
            self, register_value_map=None, memory_value_map=None,
            default_value=0, tracer=None, use_postsynth_map_if_available=True, block=None):
        """ Creates object and initializes it with self.initialize.

        register_value_map, memory_value_map, and default_value are passed on to initialize.
        tracer is an instance of SimulationTrace used to store execution results.
        use_postsynth_map_if_available will map the I/O to the block from the
        pre-synthesis block so the names and outputs can be used or generated respectively.
        block is the hardware block to be traced (which might be of type PostSynthesisBlock).
        """

        block = core.working_block(block)
        block.sanity_check()  # check that this is a good hw block

        self.value = {}   # map from signal->value
        self.memvalue = {}  # map from (memid,address)->value
        self.block = block
        self.default_value = default_value
        self.tracer = tracer
        self.initialize(register_value_map, memory_value_map)
        self.max_iter = 1000
        self.use_postsynth_map = use_postsynth_map_if_available

    def initialize(self, register_value_map=None, memory_value_map=None, default_value=None):
        """ Sets the wire, register, and memory values to default or as specified.

        register_value_map is a map of {Register: value}.
        memory_value_map is a map of maps {Memory: {address: Value}}.
        default_value is the value that all unspecified registers and memories will default to.
        if no default_value is specified, it will use the value stored in the object (default to 0)
        """

        self.value = {}
        if default_value is None:
            default_value = self.default_value

        # set registers to their values
        reg_set = self.block.wirevector_subset(wire.Register)
        if register_value_map is not None:
            for r in reg_set:
                if r in register_value_map:
                    self.value[r] = register_value_map[r]
                else:
                    self.value[r] = default_value

        # set constants to their set values
        for w in self.block.wirevector_subset(wire.Const):
            self.value[w] = w.val
            assert isinstance(w.val, int)  # for now

        # set memories to their passed values
        if memory_value_map is not None:
            for (mem, mem_map) in memory_value_map.items():
                if isinstance(self.block, core.PostSynthBlock):
                    mem = self.block.mem_map[mem]  # pylint: disable=maybe-no-member
                for (addr, val) in mem_map.items():
                    if addr < 0 or addr >= 2**mem.addrwidth:
                        raise core.PyrtlError('error, address outside of bounds')
                    self.memvalue[(mem.id, addr)] = val
                    # TODO: warn if value larger than fits in bitwidth

        defined_roms = []
        # set ROMs to their default values
        for romNet in self.block.logic_subset('m'):
            rom = romNet.op_param[1]
            if isinstance(rom, memory.RomBlock) and rom not in defined_roms:
                for address in range(0, 2**rom.addrwidth):
                    self.memvalue[(rom.id, address)] = rom._get_read_data(address)

        # set all other variables to default value
        for w in self.block.wirevector_set:
            if w not in self.value:
                self.value[w] = default_value

    def step(self, provided_inputs):
        """ Take the simulation forward one cycle """

        # To avoid weird loops, we need a copy of the old values which
        # we can then use to make our updates from
        prior_value = self.value.copy()

        # Check that all Input have a corresponding provided_input
        input_set = self.block.wirevector_subset(wire.Input)
        supplied_inputs = set()
        for i in provided_inputs:
            sim_wire = i
            if isinstance(self.block, core.PostSynthBlock) and self.use_postsynth_map:
                sim_wire = self.block.io_map[sim_wire]  # pylint: disable=maybe-no-member
            if sim_wire not in input_set:
                raise core.PyrtlError(
                    'step provided a value for input for "%s" which is '
                    'not a known input ' % i.name)
            if not isinstance(provided_inputs[i], (int, long)) or provided_inputs[i] < 0:
                raise core.PyrtlError(
                    'step provided an input "%s" which is not a valid '
                    'positive integer' % provided_inputs[i])
            if len(bin(provided_inputs[i]))-2 > sim_wire.bitwidth:
                raise core.PyrtlError(
                    'the bitwidth for "%s" is %d, but the provided input '
                    '%d requires %d bits to represent'
                    % (sim_wire.name, sim_wire.bitwidth,
                       provided_inputs[i], len(bin(provided_inputs[i]))-2))

            self.value[sim_wire] = provided_inputs[i]
            supplied_inputs.add(sim_wire)

        # Check that only inputs are specified, and set the values
        if input_set != supplied_inputs:
            for i in input_set.difference(supplied_inputs):
                raise core.PyrtlError(
                    'Input "%s" has no input value specified' % i.name)

        # Do all of the clock-edge triggered operations based off of the priors
        for net in self.block.logic:
            self._edge_update(net, prior_value)

        # propagate inputs to outputs
        # wires  which are defined at the start are inputs and registers
        const_set = self.block.wirevector_subset(wire.Const)
        reg_set = self.block.wirevector_subset(wire.Register)
        defined_set = reg_set | const_set | input_set
        logic_left = self.block.logic.copy()

        for _ in xrange(self.max_iter):
            logic_left = set(
                net
                for net in logic_left
                if not self._try_execute(defined_set, net)
                )
            if len(logic_left) == 0:
                break
        else:  # no break
            raise core.PyrtlInternalError(
                'error, the set of logic "%s" appears to be waiting for value never produced'
                % str(logic_left))

        # at the end of the step, record the values to the trace
        # print self.value # Helpful Debug Print
        if self.tracer is not None:
            self.tracer.add_step(self.value)

    def _sanitize(self, val, wirevector):
        """Return a modified version of val that would fit in wirevector.

        This function should be applied to every primitive call, and it's
        default behavior is to mask the upper bits of value and return that
        new value.
        """
        return val & ((1 << len(wirevector))-1)

    def execute(self, net):
        """Handle the combinational logic update rules for the given net.

        This function, along with execute, defined the semantics
        of the primitive ops.  Function updates self.value accordingly.
        """
        simple_func = {  # OPS
            'w': lambda x: x,
            '~': lambda x: ~x,
            '&': lambda l, r: l & r,
            '|': lambda l, r: l | r,
            '^': lambda l, r: l ^ r,
            '+': lambda l, r: l + r,
            '-': lambda l, r: l - r,
            '*': lambda l, r: l * r,
            '<': lambda l, r: int(l < r),
            '>': lambda l, r: int(l > r),
            '=': lambda l, r: int(l == r)
            }
        if net.op in simple_func:
            argvals = [self.value[arg] for arg in net.args]
            result = simple_func[net.op](*argvals)
            self.value[net.dests[0]] = self._sanitize(result, net.dests[0])
        elif net.op == 'x':
            select = self.value[net.args[0]]
            a = self.value[net.args[1]]
            b = self.value[net.args[2]]
            if select == 0:
                result = a
            else:
                result = b
            self.value[net.dests[0]] = self._sanitize(result, net.dests[0])
        elif net.op == 'c':
            result = 0
            for arg in net.args:
                result = result << len(arg)
                result = result | self.value[arg]
            self.value[net.dests[0]] = self._sanitize(result, net.dests[0])
        elif net.op == 's':
            result = 0
            source = self.value[net.args[0]]
            for b in net.op_param[::-1]:
                result = (result << 1) | (0x1 & (source >> b))
            self.value[net.dests[0]] = self._sanitize(result, net.dests[0])
        elif net.op == 'm':
            # memories act async for reads
            memid = net.op_param[0]
            read_addr = self.value[net.args[0]]
            index = (memid, read_addr)
            mem_lookup_result = self.memvalue.get(index, self.default_value)
            self.value[net.dests[0]] = mem_lookup_result
        elif net.op == 'r' or net.op == '@':
            pass  # registers and memory write ports have no logic function
        else:
            raise core.PyrtlInternalError('error, unknown op type')

    def _edge_update(self, net, prior_value):
        """Handle the posedge event for the simulation of the given net.

        Combinational logic should have no posedge behavior, but registers and
        memory should.  This function, along with execute, defined the
        semantics of the primitive ops.  Function updates self.value and
        self.memvalue accordingly (using prior_value)
        """
        if net.op in 'w~&|^+-*<>=xcsm':
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
                    self.memvalue[(memid, write_addr)] = write_val
            else:
                raise core.PyrtlInternalError

    def _try_execute(self, defined_set, net):
        """ Try to Execute net but return False if not ready.

        Ready inputs will be fined in "defined_set" and if any
        inputs are not yet in this set, we know the we need to execute
        the preceding ops first.  If the net is successfully executed
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

    def _print_values(self):
        print ' '.join([str(v) for _, v in sorted(self.value.iteritems())])


# ----------------------------------------------------------------
#    ___       __  ___     __
#   |__   /\  /__`  |     /__` |  |\/|
#   |    /~~\ .__/  |     .__/ |  |  |
#

class FastSimulation(object):
    """A class for simulating blocks of logic step by step."""

    def __init__(
            self, register_value_map=None, memory_value_map=None,
            default_value=0, tracer=None, block=None):

        block = core.working_block(block)
        block.sanity_check()  # check that this is a good hw block

        self.block = block
        self.default_value = default_value
        self.tracer = tracer
        self.context = {}
        self.initialize(register_value_map, memory_value_map)

    def initialize(self, register_value_map=None, memory_value_map=None, default_value=None):

        if default_value is None:
            default_value = self.default_value

        # set registers to their values
        reg_set = self.block.wirevector_subset(wire.Register)
        if register_value_map is not None:
            for r in reg_set:
                if r in register_value_map:
                    self.context[self.varname(r)] = register_value_map[r]
                else:
                    self.context[self.varname(r)] = default_value

        # set constants to their set values
        for w in self.block.wirevector_subset(wire.Const):
            self.context[self.varname(w)] = w.val
            assert isinstance(w.val, int)  # for now

        # set memories to their passed values
        if memory_value_map is not None:
            for (mem, mem_map) in memory_value_map.items():
                self.context[self.varname(mem)] = mem_map

        # set all other variables to default value
        for w in self.block.wirevector_set:
            if w not in self.context:
                self.context[self.varname(w)] = default_value

        s = self.compiled()
        print s
        self.logic_function = compile(s, '<string>', 'exec')

    def step(self, provided_inputs):
        # update inputs
        for k, v in provided_inputs.items():
            self.context[self.varname(k)] = v

        # update register values
        if '__next' in self.context:
            next = self.context['__next']
            self.context['__next'] = None
            self.context.update(next)

        # propagate through logic
        # print
        # print '-----------------------------------'
        # for w in self.block.wirevector_subset():
        #     print w.name + ":  " + str(self.context[self.varname(w)])
        exec self.logic_function in self.context

        if self.tracer is not None:
            self.tracer.add_fast_step(self)

    def varname(self, val):
        # TODO check if w.name is a legal python identifier
        if isinstance(val, memory.MemBlock):
            return 'fs_mem' + str(val.id)
        else:
            return val.name

    def compiled(self):
        """Return a string of the self.block compiled to python. """
        prog = ''

        simple_func = {  # OPS
            'w': lambda x: x,
            '~': lambda x: '(~' + x + ')',
            '&': lambda l, r: '(' + l + '&' + r + ')',
            '|': lambda l, r: '(' + l + '|' + r + ')',
            '^': lambda l, r: '(' + l + '^' + r + ')',
            '+': lambda l, r: '(' + l + '+' + r + ')',
            '-': lambda l, r: '(' + l + '-' + r + ')',
            '*': lambda l, r: '(' + l + '*' + r + ')',
            '<': lambda l, r: 'int(' + l + '<' + r + ')',
            '>': lambda l, r: 'int(' + l + '>' + r + ')',
            '=': lambda l, r: 'int(' + l + '==' + r + ')'
            }

        for net in self.block:
            if net.op in simple_func:
                argvals = [self.varname(arg) for arg in net.args]
                result = simple_func[net.op](*argvals)
                mask = str((1 << len(net.dests[0])) - 1)
                prog += self.varname(net.dests[0]) + ' = ' + mask + ' & ' + result + '\n'
            elif net.op == 'x':
                select = self.varname(net.args[0])
                a = self.varname(net.args[1])
                b = self.varname(net.args[2])
                mask = str((1 << len(net.dests[0])) - 1)
                result = self.varname(net.dests[0])
                prog += '%s = %s & ((%s) if (%s==0) else (%s))\n' %\
                        (result, mask, a, select, b)
            elif net.op == 'c':
                result = self.varname(net.dests[0])
                mask = str((1 << len(net.dests[0])) - 1)
                expr = ''
                for i in range(len(net.args)):
                    if expr is not '':
                        expr += ' | '
                    shiftby = str(sum(len(net.args[j]) for j in range(i+1, len(net.args))))
                    expr += '(%s << %s)' % (self.varname(net.args[i]), shiftby)
                prog += '%s = %s & (%s)\n' % (result, mask, expr)
            elif net.op == 's':
                source = self.varname(net.args[0])
                result = self.varname(net.dests[0])
                mask = str((1 << len(net.dests[0])) - 1)
                expr = ''
                i = 0
                for b in net.op_param:
                    if expr is not '':
                        expr += ' | '
                    bit = '(0x1 & (%s >> %d))' % (source, b)
                    expr += '(%s << %d)' % (bit, i)
                    i += 1
                prog += '%s = %s & (%s)\n' % (result, mask, expr)

            elif net.op == 'm':
                # memories act async for reads
                memid = net.op_param[0]
                read_addr = self.varname(net.args[0])
                index = '(%d, %s)' % (memid, read_addr)
                result = self.varname(net.dests[0])
                mask = str((1 << len(net.dests[0])) - 1)
                expr = 'fs_mem%d.get(%s, %s)' % (memid, index, self.default_value)
                prog += '%s = %s & (%s)\n' % (result, mask, expr)
                
            elif net.op == 'r' or net.op == '@':
                pass  # registers and memory write ports have no logic function
            else:
                raise core.PyrtlError('FastSimulation cannot handle primitive "%s"' % net.op)

        return prog


# ----------------------------------------------------------------
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


def _trace_sort_key(w):
    def tryint(s):
        try:
            return int(s)
        except ValueError:
            return s
    return [tryint(c) for c in re.split('([0-9]+)', w.name)]


class SimulationTrace(object):
    """ Storage and presentation of simulation waveforms. """

    def __init__(self, wirevector_subset=None, block=None):
        block = core.working_block(block)

        def is_internal_name(name):
            if (
               name.startswith('tmp')
               or name.startswith('const')
               # or name.startswith('synth_')
               or name.endswith("'")
               ):
                return True
            else:
                return False

        if wirevector_subset is None:
            self.trace = {
                w: []
                for w in block.wirevector_set
                if not is_internal_name(w.name)
                }
        else:
            self.trace = {w: [] for w in wirevector_subset}

    def __len__(self):
        """ Return the current length of the trace in cycles. """
        if len(self.trace) == 0:
            raise core.PyrtlError('error, length of trace undefined if no signals tracked')
        # return the length of the list of some element in the dictionary (all should be the same)
        wire, value_list = next(x for x in self.trace.items())
        return len(value_list)

    def add_step(self, value_map):
        """ Add the values in value_map to the end of the trace. """
        if len(self.trace) == 0:
            raise core.PyrtlError('error, simulation trace needs at least 1 signal '
                                  'to track (try passing name to WireVector)')
        for w in self.trace:
            self.trace[w].append(value_map[w])

    def add_fast_step(self, fastsim):
        """ Add the fastsim context to the trace. """
        for w in self.trace:
            self.trace[w].append(fastsim.context[fastsim.varname(w)])

    def print_trace(self, file=sys.stdout):
        if len(self.trace) == 0:
            raise core.PyrtlError('error, cannot print an empty trace')
        maxlen = max([len(w.name) for w in self.trace])
        for w in sorted(self.trace, key=_trace_sort_key):
            file.write(" ".join([w.name.rjust(maxlen),
                       ''.join(str(x) for x in self.trace[w])+"\n"]))
            file.flush()

    def print_vcd(self, file=sys.stdout):
        """ Print the trace out as a VCD File for use in other tools. """
        # dump header info
        # file_timestamp = time.strftime("%a, %d %b %Y %H:%M:%S (UTC/GMT)", time.gmtime())
        # print >>file, " ".join(["$date", file_timestamp, "$end"])
        print >>file, " ".join(["$timescale", "1ns", "$end"])
        print >>file, " ".join(["$scope", "module logic", "$end"])

        # dump variables
        for w in sorted(self.trace, key=_trace_sort_key):
            print >>file, " ".join(["$var", "wire", str(w.bitwidth), w.name, w.name, "$end"])
        print >>file, " ".join(["$upscope", "$end"])
        print >>file, " ".join(["$enddefinitions", "$end"])
        print >>file, " ".join(["$dumpvars"])
        for w in sorted(self.trace, key=_trace_sort_key):
            if w.bitwidth > 1:
                print >>file, " ".join([str(bin(self.trace[w][0]))[1:], w.name])
            else:
                print >>file, "".join([str(self.trace[w][0]), w.name])
        print >>file, " ".join(["$end"])

        # dump values
        endtime = max([len(self.trace[w]) for w in self.trace])
        for timestamp in range(endtime):
            print >>file, "".join(["#", str(timestamp)])
            for w in sorted(self.trace, key=_trace_sort_key):
                if w.bitwidth > 1:
                    print >>file, " ".join([str(bin(self.trace[w][timestamp]))[1:], w.name])
                else:
                    print >>file, "".join([str(self.trace[w][timestamp]), w.name])
        print >>file, "".join(["#", str(endtime)])
        file.flush()

    def render_trace(
            self, trace_list=None, file=sys.stdout, renderer=wave_trace_render,
            symbol_len=5, segment_size=5, segment_delim=' ', extra_line=True):
        """ Render the trace to a file using unicode and ASCII escape sequences.

        The resulting output can be viewed directly on the terminal or looked
        at with "more" or "less -R" which both should handle the ASCII escape
        sequences used in rendering. render_trace takes the following optional
        arguments.
        trace_list: A list of signals to be output in the specified order.
        file: The place to write output, default to stdout.
        renderer: A function that translates traces into output bytes.
        symbol_len: The "length" of each rendered cycle in characters.
        segment_size: Traces are broken in the segments of this number of cycles.
        segment_delim: The character to be output between segments.
        extra_line: A Boolean to determin if we should print a blank line between signals.
        """

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

        # default to printing all signals in sorted order
        if trace_list is None:
            trace_list = sorted(self.trace, key=_trace_sort_key)

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
        print >>file, spaces + segment_delim.join(ticks).encode('utf-8')

        # now all the traces
        for w in trace_list:
            if extra_line:
                print >>file
            print >>file, formatted_trace_line(w, self.trace[w]).encode('utf-8')
        if extra_line:
            print >>file
