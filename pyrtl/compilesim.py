from __future__ import print_function, unicode_literals

import ctypes
import subprocess
import tempfile
import shutil
import collections
from os import path
import platform
import sys
import _ctypes

from .core import working_block
from .wire import Input, Output, Const, WireVector, Register
from .memory import MemBlock, RomBlock
from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .simulation import SimulationTrace, _trace_sort_key


__all__ = ['CompiledSimulation']


class DllMemInspector(collections.Mapping):
    """ Dictionary-like access to a hashmap in a CompiledSimulation. """

    def __init__(self, sim, mem):
        self._aw = mem.addrwidth
        self._limbs = sim._limbs(mem)
        self._vn = vn = sim.varname[mem]
        self._mem = ctypes.c_void_p.in_dll(sim._dll, vn)
        self._sim = sim  # keep reference to avoid freeing dll

    def __getitem__(self, ind):
        arr = self._sim._mem_lookup(self._mem, ind)
        val = 0
        for n in reversed(range(self._limbs)):
            val <<= 64
            val |= arr[n]
        return val

    def __iter__(self):
        return iter(range(len(self)))

    def __len__(self):
        return 1 << self._aw

    def __eq__(self, other):
        if isinstance(other, DllMemInspector):
            if self._sim is other._sim and self._vn == other._vn:
                return True
        return all(self[x] == other.get(x, 0) for x in self)


class CompiledSimulation(object):
    """Simulate a block, compiling to C for efficiency.

    This module provides significant speed improvements over FastSimulation,
    at the cost of somewhat longer setup time.
    Generally this will do better than FastSimulation for simulations requiring over 1000 steps.
    It is not built to be a debugging tool, though it may help with debugging.
    Note that only Input and Output wires can be traced using CompiledSimulation.  This code
    is still experimental, but has been used on designs of significant scale to good effect.

    In order to use this, you need:
        - A 64-bit processor
        - GCC (tested on version 4.8.4)
        - A 64-bit build of Python
    If using the multiplication operand, only some architectures are supported:
        - x86-64 / amd64
        - arm64 / aarch64 (untested)
        - mips64 (untested)

    default_value is currently only implemented for registers, not memories.
    """

    def __init__(
            self, tracer=True, register_value_map={}, memory_value_map={},
            default_value=0, block=None):
        self._dll = self._dir = None
        self.block = working_block(block)
        self.block.sanity_check()

        if tracer is True:
            tracer = SimulationTrace()
        self.tracer = tracer
        self._remove_untraceable()

        self.default_value = default_value
        self._regmap, self._memmap = register_value_map, memory_value_map
        self._uid_counter = 0
        self.varname = {}  # mapping from wires and memories to C variables

        # Passing the dictionary objects themselves since they aren't updated anywhere.
        # If that's ever not the case, will need to pass in deep copies of them like done
        # for the normal Simulation so we retain the initial values that had.
        self.tracer._set_initial_values(default_value, register_value_map, memory_value_map)

        self._create_dll()
        self._initialize_mems()

    def inspect_mem(self, mem):
        """Get a view into the contents of a MemBlock."""
        return DllMemInspector(self, mem)

    def inspect(self, w):
        """Get the latest value of the wire given, if possible."""
        if isinstance(w, WireVector):
            w = w.name
        try:
            vals = self.tracer.trace[w]
        except KeyError:
            pass
        else:
            if not vals:
                raise PyrtlError('No context available. Please run a simulation step')
            return vals[-1]
        raise PyrtlError('CompiledSimulation does not support inspecting internal WireVectors')

    def step(self, inputs):
        """Run one step of the simulation.

        The argument is a mapping from input names to the values for the step.
        """
        self.run([inputs])

    def step_multiple(self, provided_inputs={}, expected_outputs={}, nsteps=None,
                      file=sys.stdout, stop_after_first_error=False):
        """ Take the simulation forward N cycles, where N is the number of values
         for each provided input.

        :param provided_inputs: a dictionary mapping wirevectors to their values for N steps
        :param expected_outputs: a dictionary mapping wirevectors to their expected values
            for N steps
        :param nsteps: number of steps to take (defaults to None, meaning step for each
            supplied input value)
        :param file: where to write the output (if there are unexpected outputs detected)
        :param stop_after_first_error: a boolean flag indicating whether to stop the simulation
            after the step where the first errors are encountered (defaults to False)

        All input wires must be in the provided_inputs in order for the simulation
        to accept these values. Additionally, the length of the array of provided values for each
        input must be the same.

        When 'nsteps' is specified, then it must be *less than or equal* to the number of values
        supplied for each input when 'provided_inputs' is non-empty. When 'provided_inputs' is
        empty (which may be a legitimate case for a design that takes no inputs), then 'nsteps'
        will be used.  When 'nsteps' is not specified, then the simulation will take the number
        of steps equal to the number of values supplied for each input.

        Example: if we have inputs named 'a' and 'b' and output 'o', we can call:
        sim.step_multiple({'a': [0,1], 'b': [23,32]}, {'o': [42, 43]}) to simulate 2 cycles,
        where in the first cycle 'a' and 'b' take on 0 and 23, respectively, and 'o' is expected to
        have the value 42, and in the second cycle 'a' and 'b' take on 1 and 32, respectively, and
        'o' is expected to have the value 43.

        If your values are all single digit, you can also specify them in a single string, e.g.
        sim.step_multiple({'a': '01', 'b': '01'}) will simulate 2 cycles, with 'a' and 'b' taking on
        0 and 0, respectively, on the first cycle and '1' and '1', respectively, on the second
        cycle.

        Example: if the design had no inputs, like so:

            a = pyrtl.Register(8)
            b = pyrtl.Output(8, 'b')

            a.next <<= a + 1
            b <<= a

            sim = pyrtl.Simulation()
            sim.step_multiple(nsteps=3)

        Using sim.step_multiple(nsteps=3) simulates 3 cycles, after which we would expect the value
        of 'b' to be 2.

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

        if list(filter(lambda l: len(l) < nsteps, provided_inputs.values())):
            raise PyrtlError(
                "must supply a value for each provided wire "
                "for each step of simulation")

        if list(filter(lambda l: len(l) < nsteps, expected_outputs.values())):
            raise PyrtlError(
                "any expected outputs must have a supplied value "
                "each step of simulation")

        failed = []
        for i in range(nsteps):
            self.step({w: int(v[i]) for w, v in provided_inputs.items()})

            for expvar in expected_outputs.keys():
                expected = int(expected_outputs[expvar][i])
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

    def run(self, inputs):
        """ Run many steps of the simulation.

        :param inputs: A list of input mappings for each step;
            its length is the number of steps to be executed.
        """
        steps = len(inputs)
        # create i/o arrays of the appropriate length
        ibuf_type = ctypes.c_uint64 * (steps * self._ibufsz)
        obuf_type = ctypes.c_uint64 * (steps * self._obufsz)
        ibuf = ibuf_type()
        obuf = obuf_type()
        # these array will be passed to _crun
        self._crun.argtypes = [ctypes.c_uint64, ibuf_type, obuf_type]

        # build the input array
        for n, inmap in enumerate(inputs):
            for w in inmap:
                if isinstance(w, WireVector):
                    name = w.name
                else:
                    name = w
                start, count = self._inputpos[name]
                start += n * self._ibufsz
                val = inmap[w]
                if val >= 1 << self._inputbw[name]:
                    raise PyrtlError(
                        'Wire {} has value {} which cannot be represented '
                        'using its bitwidth'.format(name, val))
                # pack input
                for pos in range(start, start + count):
                    ibuf[pos] = val & ((1 << 64) - 1)
                    val >>= 64

        # run the simulation
        self._crun(steps, ibuf, obuf)

        # save traced wires
        for name in self.tracer.trace:
            rname = self._probe_mapping.get(name, name)
            if rname in self._outputpos:
                start, count = self._outputpos[rname]
                buf, sz = obuf, self._obufsz
            elif rname in self._inputpos:
                start, count = self._inputpos[rname]
                buf, sz = ibuf, self._ibufsz
            else:
                raise PyrtlInternalError('Untraceable wire in tracer')
            res = []
            for n in range(steps):
                val = 0
                # unpack output
                for pos in reversed(range(start, start + count)):
                    val <<= 64
                    val |= buf[pos]
                res.append(val)
                start += sz
            self.tracer.trace[name].extend(res)

    def _traceable(self, wv):
        """ Check if wv is able to be traced.

        If it is traceable due to a probe, record that probe in _probe_mapping.
        """
        if isinstance(wv, (Input, Output)):
            return True
        for net in self.block.logic:
            if net.op == 'w' and net.args[0].name == wv.name and isinstance(net.dests[0], Output):
                self._probe_mapping[wv.name] = net.dests[0].name
                return True
        return False

    def _remove_untraceable(self):
        """ Remove from the tracer those wires that CompiledSimulation cannot track.

        Create _probe_mapping for wires only traceable via probes.
        """
        self._probe_mapping = {}
        wvs = {wv for wv in self.tracer.wires_to_track if self._traceable(wv)}
        self.tracer.wires_to_track = wvs
        self.tracer._wires = {wv.name: wv for wv in wvs}
        self.tracer.trace.__init__(wvs)

    def _create_dll(self):
        """ Create a dynamically-linked library implementing the simulation logic. """
        self._dir = tempfile.mkdtemp()
        with open(path.join(self._dir, 'pyrtlsim.c'), 'w') as f:
            self._create_code(lambda s: f.write(s + '\n'))
        if platform.system() == 'Darwin':
            shared = '-dynamiclib'
        else:
            shared = '-shared'
        subprocess.check_call(['gcc', '-O0', '-march=native', '-std=c99', '-m64',
                               shared, '-fPIC',
                               path.join(self._dir, 'pyrtlsim.c'),
                               '-o', path.join(self._dir, 'pyrtlsim.so'), ],
                              shell=(platform.system() == 'Windows'))
        self._dll = ctypes.CDLL(path.join(self._dir, 'pyrtlsim.so'))
        self._crun = self._dll.sim_run_all
        self._crun.restype = None  # argtypes set on use
        self._initialize_mems = self._dll.initialize_mems
        self._initialize_mems.restype = None
        self._mem_lookup = self._dll.lookup
        self._mem_lookup.restype = ctypes.POINTER(ctypes.c_uint64)

    def _limbs(self, w):
        """ Number of 64-bit words needed to store value of wire. """
        return (w.bitwidth + 63) // 64

    def _makeini(self, w, v):
        """ C initializer string for a wire with a given value. """
        pieces = []
        for _ in range(self._limbs(w)):
            pieces.append(hex(v & ((1 << 64) - 1)))
            v >>= 64
        return ','.join(pieces).join('{}')

    def _romwidth(self, m):
        """ Bitwidth of integer type sufficient to hold rom entry.

        On large memories, returns 64; an array will be needed.
        """
        if m.bitwidth <= 8:
            return 8
        if m.bitwidth <= 16:
            return 16
        if m.bitwidth <= 32:
            return 32
        return 64

    def _makemask(self, dest, res, pos):
        """Create a bitmask.

        The value being masked is of width `res`.
        Limb number `pos` of `dest` is being assigned to.
        """
        if (res is None or dest.bitwidth < res) and 0 < (dest.bitwidth - 64 * pos) < 64:
            return '&0x{:X}'.format((1 << (dest.bitwidth % 64)) - 1)
        return ''

    def _getarglimb(self, arg, n):
        """ Get the nth limb of the given wire.

        Returns '0' when the wire does not have sufficient limbs.
        """
        return '{vn}[{n}]'.format(vn=self.varname[arg], n=n) if arg.bitwidth > 64 * n else '0'

    def _clean_name(self, prefix, obj):
        """ Create a C variable name with the given prefix based on the name of obj. """
        return '{}{}_{}'.format(prefix, self._uid(), ''.join(c for c in obj.name if c.isalnum()))

    def _uid(self):
        """ Get an auto-incrementing number suitable for use as a unique identifier. """
        x = self._uid_counter
        self._uid_counter += 1
        return x

    def _declare_roms(self, write, roms):
        for mem in roms:
            self.varname[mem] = vn = self._clean_name('m', mem)
            # extract data from mem
            romval = [mem._get_read_data(n) for n in range(1 << mem.addrwidth)]
            write('static const uint{width}_t {name}[][{limbs}] = {{'.format(
                name=vn, width=self._romwidth(mem), limbs=self._limbs(mem)))
            for rv in romval:
                write(self._makeini(mem, rv) + ',')
            write('};')

    def _declare_mems(self, write, mems):
        for mem in mems:
            self.varname[mem] = vn = self._clean_name('m', mem)
            write('EXPORT')
            write('hashmap_t *{name};'.format(name=vn))

        next_tmp = 0
        write('EXPORT')
        write('void initialize_mems() {')
        for mem in mems:
            # Create hashmap
            write('{name} = create_hash_map(256, {limbs});'.format(
                name=self.varname[mem], limbs=self._limbs(mem)
            ))
            if mem in self._memmap:
                # Insert default values
                for k, v in self._memmap[mem].items():
                    write('val_t t{n}[] = {val};'.format(
                        n=next_tmp, val=self._makeini(mem, v)))
                    write('insert({name}, {key}, t{n});'.format(
                        name=self.varname[mem], key=k, n=next_tmp
                    ))
                    next_tmp += 1
        write('}')

    def _declare_wv(self, write, w):
        self.varname[w] = vn = self._clean_name('w', w)
        if isinstance(w, Const):
            write('const uint64_t {name}[{limbs}] = {val};'.format(
                limbs=self._limbs(w), name=vn, val=self._makeini(w, w.val)))
        elif isinstance(w, Register):
            write('static uint64_t {name}[{limbs}] = {val};'.format(
                limbs=self._limbs(w), name=vn,
                val=self._makeini(w, self._regmap.get(w, self.default_value))))
        else:
            write('uint64_t {name}[{limbs}];'.format(limbs=self._limbs(w), name=vn))

    def _build_memread(self, write, op, param, args, dest):
        mem = param[1]
        for n in range(self._limbs(dest)):
            if isinstance(mem, RomBlock):
                write('{dest}[{n}] = {mem}[{addr}[0]][{n}]{mask};'.format(
                    dest=self.varname[dest], n=n, mem=self.varname[mem],
                    addr=self.varname[args[0]], mask=self._makemask(dest, mem.bitwidth, n)))
            else:
                write('{dest}[{n}] = lookup({mem}, {addr}[0])[{n}]{mask};'.format(
                    dest=self.varname[dest], n=n, mem=self.varname[mem],
                    addr=self.varname[args[0]], mask=self._makemask(dest, mem.bitwidth, n)))

    def _build_wire(self, write, op, param, args, dest):
        for n in range(self._limbs(dest)):
            write('{dest}[{n}] = {arg}[{n}]{mask};'.format(
                dest=self.varname[dest], n=n, arg=self.varname[args[0]],
                mask=self._makemask(dest, args[0].bitwidth, n)))

    def _build_not(self, write, op, param, args, dest):
        for n in range(self._limbs(dest)):
            write('{dest}[{n}] = (~{arg}[{n}]){mask};'.format(
                dest=self.varname[dest], n=n, arg=self.varname[args[0]],
                mask=self._makemask(dest, None, n)))

    def _build_bitwise(self, write, op, param, args, dest):  # &, |, ^ only
        for n in range(self._limbs(dest)):
            arg0 = self._getarglimb(args[0], n)
            arg1 = self._getarglimb(args[1], n)
            write('{dest}[{n}] = ({arg0}{op}{arg1}){mask};'.format(
                dest=self.varname[dest], n=n, arg0=arg0, arg1=arg1, op=op,
                mask=self._makemask(dest, max(args[0].bitwidth, args[1].bitwidth), n)))

    def _build_nand(self, write, op, param, args, dest):
        for n in range(self._limbs(dest)):
            arg0 = self._getarglimb(args[0], n)
            arg1 = self._getarglimb(args[1], n)
            write('{dest}[{n}] = (~({arg0}&{arg1})){mask};'.format(
                dest=self.varname[dest], n=n, arg0=arg0, arg1=arg1,
                mask=self._makemask(dest, None, n)))

    def _build_eq(self, write, op, param, args, dest):
        cond = []
        for n in range(max(self._limbs(args[0]), self._limbs(args[1]))):
            arg0 = self._getarglimb(args[0], n)
            arg1 = self._getarglimb(args[1], n)
            cond.append('({arg0}=={arg1})'.format(arg0=arg0, arg1=arg1))
        write('{dest}[0] = {cond};'.format(dest=self.varname[dest], cond='&&'.join(cond)))

    def _build_cmp(self, write, op, param, args, dest):  # <, > only
        cond = None
        for n in range(max(self._limbs(args[0]), self._limbs(args[1]))):
            arg0 = self._getarglimb(args[0], n)
            arg1 = self._getarglimb(args[1], n)
            c = '({arg0}{op}{arg1})'.format(arg0=arg0, op=op, arg1=arg1)
            if cond is None:
                cond = c
            else:
                cond = '({c}||(({arg0}=={arg1})&&{inner}))'.format(
                    c=c, arg0=arg0, arg1=arg1, inner=cond)
        write('{dest}[0] = {cond};'.format(dest=self.varname[dest], cond=cond))

    def _build_mux(self, write, op, param, args, dest):
        write('if ({mux}[0]) {{'.format(mux=self.varname[args[0]]))
        for n in range(self._limbs(dest)):
            write('{dest}[{n}] = {arg}[{n}]{mask};'.format(
                dest=self.varname[dest], n=n, arg=self.varname[args[2]],
                mask=self._makemask(dest, args[2].bitwidth, n)))
        write('} else {')
        for n in range(self._limbs(dest)):
            write('{dest}[{n}] = {arg}[{n}]{mask};'.format(
                dest=self.varname[dest], n=n, arg=self.varname[args[1]],
                mask=self._makemask(dest, args[1].bitwidth, n)))
        write('}')

    def _build_add(self, write, op, param, args, dest):
        write('carry = 0;')
        for n in range(self._limbs(dest)):
            arg0 = self._getarglimb(args[0], n)
            arg1 = self._getarglimb(args[1], n)
            write('tmp = {arg0}+{arg1};'.format(arg0=arg0, arg1=arg1))
            write('{dest}[{n}] = (tmp + carry){mask};'.format(
                dest=self.varname[dest], n=n,
                mask=self._makemask(dest, max(args[0].bitwidth, args[1].bitwidth) + 1, n)))
            write('carry = (tmp < {arg0})|({dest}[{n}] < tmp);'.format(
                arg0=arg0, dest=self.varname[dest], n=n))

    def _build_sub(self, write, op, param, args, dest):
        write('carry = 0;')
        for n in range(self._limbs(dest)):
            arg0 = self._getarglimb(args[0], n)
            arg1 = self._getarglimb(args[1], n)
            write('tmp = {arg0}-{arg1};'.format(arg0=arg0, arg1=arg1))
            write('{dest}[{n}] = (tmp - carry){mask};'.format(
                dest=self.varname[dest], n=n, mask=self._makemask(dest, None, n)))
            write('carry = (tmp > {arg0})|({dest}[{n}] > tmp);'.format(
                arg0=arg0, dest=self.varname[dest], n=n))

    def _build_mul(self, write, op, param, args, dest):
        for n in range(self._limbs(dest)):
            write('{dest}[{n}] = 0;'.format(dest=self.varname[dest], n=n))
        for p0 in range(self._limbs(args[0])):
            write('carry = 0;')
            arg0 = self._getarglimb(args[0], p0)
            for p1 in range(self._limbs(args[1])):
                if self._limbs(dest) <= p0 + p1:
                    break
                arg1 = self._getarglimb(args[1], p1)
                write('mul128({arg0}, {arg1}, tmplo, tmphi);'.format(arg0=arg0, arg1=arg1))
                write('tmp = {dest}[{p}];'.format(dest=self.varname[dest], p=p0 + p1))
                write('tmplo += carry; carry = tmplo < carry; tmplo += tmp;')
                write('tmphi += carry + (tmplo < tmp); carry = tmphi;')
                write('{dest}[{p}] = tmplo{mask};'.format(
                    dest=self.varname[dest], p=p0 + p1,
                    mask=self._makemask(dest, args[0].bitwidth + args[1].bitwidth, p0 + p1)))
            if self._limbs(dest) > p0 + self._limbs(args[1]):
                write('{dest}[{p}] = carry{mask};'.format(
                    dest=self.varname[dest], p=p0 + self._limbs(args[1]),
                    mask=self._makemask(
                        dest, args[0].bitwidth + args[1].bitwidth, p0 + self._limbs(args[1]))))

    def _build_concat(self, write, op, param, args, dest):
        cattotal = sum(x.bitwidth for x in args)
        pieces = (
            (self.varname[a], lx, 0, min(64, a.bitwidth - 64 * lx))
            for a in reversed(args) for lx in range(self._limbs(a)))
        curr = next(pieces)
        for n in range(self._limbs(dest)):
            res = []
            dpos = 0
            while True:
                arg, alimb, astart, asize = curr
                res.append('(({arg}[{limb}]>>{start})<<{pos})'.format(
                    arg=arg, limb=alimb, start=astart, pos=dpos))
                dpos += asize
                if dpos >= dest.bitwidth - 64 * n:
                    break
                if dpos > 64:
                    curr = (arg, alimb, 64 - (dpos - asize), dpos - 64)
                    break
                curr = next(pieces)
                if dpos == 64:
                    break
            write('{dest}[{n}] = ({res}){mask};'.format(
                dest=self.varname[dest], n=n, res='|'.join(res),
                mask=self._makemask(dest, cattotal, n)))

    def _build_select(self, write, op, param, args, dest):
        for n in range(self._limbs(dest)):
            bits = [
                '((1&({src}[{limb}]>>{sb}))<<{db})'.format(
                    src=self.varname[args[0]], sb=(b % 64), limb=(b // 64), db=en)
                for en, b in enumerate(param[64 * n:min(dest.bitwidth, 64 * (n + 1))])]
            write('{dest}[{n}] = {bits};'.format(
                dest=self.varname[dest], n=n, bits='|'.join(bits)))

    def _declare_mem_helpers(self, write):
        helpers = '''
            typedef uint64_t val_t;

            typedef struct node
            {
                uint64_t key;
                val_t *val;
                struct node *next;
            } node_t;

            typedef struct hashmap
            {
                int size;
                int val_limbs;
                val_t *default_value;
                node_t **list;
            } hashmap_t;

            hashmap_t *create_hash_map(int size, int val_limbs)
            {
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

            int hash_code(hashmap_t *h, uint64_t key)
            {
                return key % h->size;
            }

            void insert(hashmap_t *h, uint64_t key, val_t val[])
            {
                int pos = hash_code(h, key);
                struct node *list = h->list[pos];
                struct node *new_node = (node_t *) malloc(sizeof(node_t));
                struct node *temp = list;
                while (temp)
                {
                    if (temp->key == key)
                    {
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
            val_t* lookup(hashmap_t *h, uint64_t key)
            {
                int pos = hash_code(h, key);
                node_t *list = h->list[pos];
                node_t *temp = list;
                while (temp)
                {
                    if (temp->key == key)
                    {
                        return temp->val;
                    }
                    temp = temp->next;
                }
                return h->default_value;
            }
        '''
        write(helpers)

    def _create_code(self, write):
        write('#include <stdint.h>')
        write('#include <stdlib.h>')
        write('#include <string.h>')

        # windows dllexport needed to make symbols visible
        if platform.system() == 'Windows':
            write('#define EXPORT __declspec(dllexport)')
        else:
            write('#define EXPORT')

        # multiplication macro
        #  for efficient 64x64 -> 128 bit multiplication without uint128_t
        #  as -O0 optimization does not handle uint128_t well
        machine_alias = {'amd64': 'x86_64', 'aarch64': 'arm64', 'aarch64_be': 'arm64'}
        machine = platform.machine().lower()
        machine = machine_alias.get(machine, machine)
        mulinstr = {
            'x86_64': '"mulq %q3":"=a"(pl),"=d"(ph):"%0"(t0),"r"(t1):"cc"',
            'arm64': '"mul %0, %2, %3\n\tumulh %1, %2, %3":'
                     '"=&r"(*pl),"=r"(*ph):"r"(t0),"r"(t1):"cc"',
            'mips64': '"dmultu %2, %3\n\tmflo %0\n\tmfhi %1":'
                      '"=r"(*pl),"=r"(*ph):"r"(t0),"r"(t1)',
        }
        if machine in mulinstr:
            write('#define mul128(t0, t1, pl, ph) __asm__({})'.format(mulinstr[machine]))

        # declare memories
        mems = {net.op_param[1] for net in self.block.logic_subset('m@')}
        for key in self._memmap:
            if key not in mems:
                raise PyrtlError('unrecognized MemBlock in memory_value_map')
            if isinstance(key, RomBlock):
                raise PyrtlError('RomBlock in memory_value_map')
        self._declare_mem_helpers(write)
        roms = {mem for mem in mems if isinstance(mem, RomBlock)}
        self._declare_roms(write, roms)
        mems = {mem for mem in mems if isinstance(mem, MemBlock) and not isinstance(mem, RomBlock)}
        self._declare_mems(write, mems)

        # single step function
        write('static void sim_run_step(uint64_t inputs[], uint64_t outputs[]) {')
        write('uint64_t tmp, carry, tmphi, tmplo;')  # temporary variables

        # declare wire vectors
        for w in self.block.wirevector_set:
            self._declare_wv(write, w)

        # inputs copied in
        inputs = list(self.block.wirevector_subset(Input))
        self._inputpos = {}  # for each input wire, start and number of elements in input array
        self._inputbw = {}  # bitwidth of each input wire
        ipos = 0
        for w in inputs:
            self._inputpos[w.name] = ipos, self._limbs(w)
            self._inputbw[w.name] = w.bitwidth
            for n in range(self._limbs(w)):
                write('{vn}[{n}] = inputs[{pos}];'.format(vn=self.varname[w], n=n, pos=ipos))
                ipos += 1
        self._ibufsz = ipos  # total length of input array

        # combinational logic
        op_builders = {
            'm': self._build_memread,
            'w': self._build_wire,
            '~': self._build_not,
            '&': self._build_bitwise,
            '|': self._build_bitwise,
            '^': self._build_bitwise,
            'n': self._build_nand,
            '=': self._build_eq,
            '<': self._build_cmp,
            '>': self._build_cmp,
            'x': self._build_mux,
            '+': self._build_add,
            '-': self._build_sub,
            '*': self._build_mul,
            'c': self._build_concat,
            's': self._build_select,
        }
        for net in self.block:  # topological order
            if net.op in 'r@':
                continue  # skip synchronized nets
            op, param, args, dest = net.op, net.op_param, net.args, net.dests[0]
            write('// net {op} : {args} -> {dest}'.format(
                op=op, args=', '.join(self.varname[x] for x in args), dest=self.varname[dest]))
            op_builders[op](write, op, param, args, dest)

        # memory writes
        for net in self.block.logic_subset('@'):
            mem = net.op_param[1]
            write('if ({enable}[0]) {{'.format(enable=self.varname[net.args[2]]))
            write('insert({mem}, {addr}[0], {vn});'.format(
                mem=self.varname[mem],
                addr=self.varname[net.args[0]],
                vn=self.varname[net.args[1]]
            ))
            write('}')

        # register updates
        regnets = list(self.block.logic_subset('r'))
        for x, net in enumerate(regnets):
            rin = net.args[0]
            write('uint64_t regtmp{x}[{limbs}];'.format(x=x, limbs=self._limbs(rin)))
            for n in range(self._limbs(rin)):
                write('regtmp{x}[{n}] = {vn}[{n}];'.format(x=x, vn=self.varname[rin], n=n))
        # double loop to ensure register-to-register chains update correctly
        for x, net in enumerate(regnets):
            rout = net.dests[0]
            for n in range(self._limbs(rout)):
                write('{vn}[{n}] = regtmp{x}[{n}];'.format(vn=self.varname[rout], x=x, n=n))

        # output copied out
        outputs = list(self.block.wirevector_subset(Output))
        self._outputpos = {}  # for each output wire, start and number of elements in output array
        opos = 0
        for w in outputs:
            self._outputpos[w.name] = opos, self._limbs(w)
            for n in range(self._limbs(w)):
                write('outputs[{pos}] = {vn}[{n}];'.format(pos=opos, vn=self.varname[w], n=n))
                opos += 1
        self._obufsz = opos  # total length of output array
        write('}')

        # entry point
        write('EXPORT')
        write('void sim_run_all(uint64_t stepcount, uint64_t inputs[], uint64_t outputs[]) {')
        write('uint64_t input_pos = 0, output_pos = 0;')
        write('for (uint64_t stepnum = 0; stepnum < stepcount; stepnum++) {')
        write('sim_run_step(inputs+input_pos, outputs+output_pos);')
        write('input_pos += {};'.format(self._ibufsz))
        write('output_pos += {};'.format(self._obufsz))
        write('}}')

    def __del__(self):
        """Handle removal of the DLL when the simulator is deleted."""
        if self._dll is not None:
            handle = self._dll._handle
            if platform.system() == 'Windows':
                _ctypes.FreeLibrary(handle)  # pylint: disable=no-member
            else:
                _ctypes.dlclose(handle)  # pylint: disable=no-member
            self._dll = None
        if self._dir is not None:
            shutil.rmtree(self._dir)
            self._dir = None
