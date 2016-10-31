from __future__ import print_function, unicode_literals

import ctypes
import _ctypes
import subprocess
import tempfile
import traceback
import shutil
import collections
from os import path
import platform

from .core import working_block
from .wire import Input, Output, Const, WireVector, Register
from .memory import RomBlock
from .pyrtlexceptions import PyrtlError
from .simulation import SimulationTrace


class DllMemInspector(collections.Mapping):
    def __init__(self, sim, mem):
        self._aw = mem.addrwidth
        bw = mem.bitwidth
        self._limbs = limbs = (bw+63)//64
        self._vn = vn = sim.varname[mem]
        if bw <= 8:
            scalar = ctypes.c_uint8
        elif bw <= 16:
            scalar = ctypes.c_uint16
        elif bw <= 32:
            scalar = ctypes.c_uint32
        else:
            scalar = ctypes.c_uint64
        array_type = scalar*(len(self)*limbs)
        self._buf = array_type.in_dll(sim._dll, vn)
        self._sim = sim  # keep reference to avoid freeing dll

    def __getitem__(self, ind):
        val = 0
        limbs = self._limbs
        for n in reversed(range(ind*limbs, (ind+1)*limbs)):
            val <<= 64
            val |= self._buf[n]
        return val

    def __iter__(self):
        return iter(range(len(self)))

    def __len__(self):
        return 1 << self._aw

    def __eq__(self, other):
        if isinstance(other, DllMemInspector):
            return self._sim is other._sim and self._vn == other._vn
        return all(self[x] == other.get(x, 0) for x in self)


class CompiledSimulation(object):
    """Simulate a block, compiling to C for efficiency.

    THIS IS AN EXPERIMENTAL SIMULATION CLASS. NO SUPPORT WILL BE GIVEN
    TO PEOPLE WHO CANNOT GET IT TO RUN. EXPECT THE API TO CHANGE IN THE FUTURE

    This module provides significant speed improvements for people who are looking
    for high performance simulation. It is not built to be a debugging tool, though
    it may help with debugging. Generally this will do better than fastsim for
    simulations requiring over 1000 iterations.

    In order to use this, you need:
        - A 64-bit processor (currently only x86-64 supported for multiplication)
        - GCC (tested on version 4.8.4)
        - A 64-bit build of Python
    """

    def __init__(
            self, tracer=None, register_value_map={}, memory_value_map={},
            default_value=0, block=None):
        self._dll = self._dir = None
        self.block = working_block(block)
        self.block.sanity_check()

        if tracer is None:
            tracer = SimulationTrace()
        self.tracer = tracer
        self._remove_untraceable()

        self.default_value = default_value

        self._create_dll(register_value_map, memory_value_map)

    def _remove_untraceable(self):
        wvs = [wv for wv in self.tracer.wires_to_track if isinstance(wv, (Input, Output))]
        self.tracer.wires_to_track = wvs
        self.tracer._wires = {wv.name: wv for wv in wvs}
        self.tracer.trace.__init__(wvs)

    def _create_dll(self, register_value_map, memory_value_map):
        self._dir = tempfile.mkdtemp()
        code = self._create_code(register_value_map, memory_value_map)
        with open(path.join(self._dir, 'pyrtlsim.c'), 'w') as f:
            f.write(code)
        subprocess.check_call([
            'gcc', '-O0', '-march=native', '-std=c99', '-m64',
            '-shared', '-fPIC', '-mcmodel=medium',
            path.join(self._dir, 'pyrtlsim.c'), '-o', path.join(self._dir, 'pyrtlsim.so')],
            shell=(platform.system() == 'Windows'))
        self._dll = ctypes.CDLL(path.join(self._dir, 'pyrtlsim.so'))
        self._crun = self._dll.sim_run_all
        self._crun.restype = None  # argtypes set on use

    def _create_code(self, regmap, memmap):
        def limbs(w):
            return (w.bitwidth+63)//64

        def makeini(w, v):
            pieces = []
            for n in range(limbs(w)):
                pieces.append(hex(v & ((1 << 64)-1)))
                v >>= 64
            return ','.join(pieces).join('{}')

        def memwidth(m):
            if m.bitwidth <= 8:
                return 8
            if m.bitwidth <= 16:
                return 16
            if m.bitwidth <= 32:
                return 32
            return 64

        def makemask(dest, res, pos):
            if (res is None or dest.bitwidth < res) and 0 < (dest.bitwidth - 64*pos) < 64:
                return '&0x{:X}'.format((1 << (dest.bitwidth % 64))-1)
            return ''

        def getarglimb(arg, n):
            return '{vn}[{n}]'.format(vn=self.varname[arg], n=n) if arg.bitwidth > 64*n else '0'

        code = ['#include <stdint.h>']
        machine = platform.machine().lower()
        if machine in ('x86_64', 'amd64'):
            code.append(
                '#define mul128(t0, t1, pl, ph) __asm__('
                '"mulq %q3":"=a"(pl),"=d"(ph):"%0"(t0),"r"(t1):"cc")')
        # variable declarations
        self.varname = {}
        uid = 0
        for w in self.block.wirevector_set:
            self.varname[w] = vn = 'w{}_{}'.format(
                str(uid), ''.join(c for c in w.name if c.isalnum()))
            if isinstance(w, Const):
                code.append('static const uint64_t {name}[{limbs}] = {val};'.format(
                    limbs=limbs(w), name=vn, val=makeini(w, w.val)))
            elif isinstance(w, Register) and regmap.get(w, self.default_value):
                code.append('static uint64_t {name}[{limbs}] = {val};'.format(
                    limbs=limbs(w), name=vn, val=makeini(w, regmap.get(w, self.default_value))))
            else:
                code.append('static uint64_t {name}[{limbs}];'.format(
                    limbs=limbs(w), name=vn))
            uid += 1
        mems = {net.op_param[1] for net in self.block.logic_subset('m@')}
        for key in memmap:
            if key not in mems:
                raise PyrtlError('unrecognized MemBlock in map')
            if isinstance(key, RomBlock):
                raise PyrtlError('error, one or more of the memories in the map is a RomBlock')
        for mem in mems:
            self.varname[mem] = vn = 'm{}_{}'.format(
                str(uid), ''.join(c for c in mem.name if c.isalnum()))
            if isinstance(mem, RomBlock):
                romval = [mem._get_read_data(n) for n in range(1 << mem.addrwidth)]
                code.append('static const uint{width}_t {name}[][{limbs}] = {{'.format(
                    name=vn, width=memwidth(mem), limbs=limbs(mem)))
                for rv in romval:
                    code.append(makeini(mem, rv)+',')
                code.append('};')
            else:
                if platform.system() == 'Windows':
                    code.append('__declspec(dllexport)')
                if mem in memmap:
                    memval = [
                        memmap[mem].get(n, 0) for n in
                        range(min(1 << mem.addrwidth, max(memmap[mem])+1))]
                    code.append('uint{width}_t {name}[{size}][{limbs}] = {{'.format(
                        name=vn, width=memwidth(mem), size=1 << mem.addrwidth, limbs=limbs(mem)))
                    for mv in memval:
                        code.append(makeini(mem, mv)+',')
                    code.append('};')
                else:
                    code.append('uint{width}_t {name}[{size}][{limbs}] = {{{{0}}}};'.format(
                        name=vn, width=memwidth(mem), size=1 << mem.addrwidth, limbs=limbs(mem)))
            uid += 1
        # single step
        code.append('static void sim_run_step(uint64_t inputs[], uint64_t outputs[]) {')
        code.append('uint64_t tmp, carry, tmphi, tmplo;')
        # register updates
        regnets = list(self.block.logic_subset('r'))
        for uid, net in enumerate(regnets):
            rin = net.args[0]
            code.append('uint64_t regtmp{uid}[{limbs}];'.format(
                uid=uid, limbs=limbs(rin)))
            for n in range(limbs(rin)):
                code.append('regtmp{uid}[{n}] = {vn}[{n}];'.format(
                    uid=uid, vn=self.varname[rin], n=n))
        for uid, net in enumerate(regnets):
            rout = net.dests[0]
            for n in range(limbs(rout)):
                code.append('{vn}[{n}] = regtmp{uid}[{n}];'.format(
                    vn=self.varname[rout], uid=uid, n=n))
        # inputs
        inputs = list(self.block.wirevector_subset(Input))
        self._inputpos = {}
        self._inputbw = {}
        ipos = 0
        for w in inputs:
            self._inputpos[w.name] = ipos, limbs(w)
            self._inputbw[w.name] = w.bitwidth
            for n in range(limbs(w)):
                code.append('{vn}[{n}] = inputs[{pos}];'.format(
                    vn=self.varname[w], n=n, pos=ipos))
                ipos += 1
        self._ibufsz = ipos
        # combinational logic
        for net in self.block:  # topo order
            if net.op in 'r@':
                continue  # skip synchronized nets
            op, param, args, dest = net.op, net.op_param, net.args, net.dests[0]
            code.append('// net {op} : {args} -> {dest}'.format(
                op=op, args=', '.join(self.varname[x] for x in args), dest=self.varname[dest]))
            if net.op == 'm':
                mem = param[1]
                for n in range(limbs(dest)):
                    code.append('{dest}[{n}] = {mem}[{addr}[0]][{n}]{mask};'.format(
                        dest=self.varname[dest], n=n, mem=self.varname[mem],
                        addr=self.varname[args[0]], mask=makemask(dest, mem.bitwidth, n)))
            elif net.op == 'w':
                for n in range(limbs(dest)):
                    code.append('{dest}[{n}] = {arg}[{n}]{mask};'.format(
                        dest=self.varname[dest], n=n, arg=self.varname[args[0]],
                        mask=makemask(dest, args[0].bitwidth, n)))
            elif net.op == '~':
                for n in range(limbs(dest)):
                    code.append('{dest}[{n}] = (~{arg}[{n}]){mask};'.format(
                        dest=self.varname[dest], n=n, arg=self.varname[args[0]],
                        mask=makemask(dest, None, n)))
            elif net.op in '&|^':
                for n in range(limbs(dest)):
                    arg0 = getarglimb(args[0], n)
                    arg1 = getarglimb(args[1], n)
                    code.append('{dest}[{n}] = ({arg0}{op}{arg1}){mask};'.format(
                        dest=self.varname[dest], n=n, arg0=arg0, arg1=arg1, op=net.op,
                        mask=makemask(dest, max(args[0].bitwidth, args[1].bitwidth), n)))
            elif net.op == 'n':
                for n in range(limbs(dest)):
                    arg0 = getarglimb(args[0], n)
                    arg1 = getarglimb(args[1], n)
                    code.append('{dest}[{n}] = (~({arg0}&{arg1})){mask};'.format(
                        dest=self.varname[dest], n=n, arg0=arg0, arg1=arg1,
                        mask=makemask(dest, None, n)))
            elif net.op == '=':
                cond = []
                for n in range(max(limbs(args[0]), limbs(args[1]))):
                    arg0 = getarglimb(args[0], n)
                    arg1 = getarglimb(args[1], n)
                    cond.append('({arg0}=={arg1})'.format(arg0=arg0, arg1=arg1))
                code.append('{dest}[0] = {cond};'.format(
                    dest=self.varname[dest], cond='&&'.join(cond)))
            elif net.op in '<>':
                cond = None
                for n in range(max(limbs(args[0]), limbs(args[1]))):
                    arg0 = getarglimb(args[0], n)
                    arg1 = getarglimb(args[1], n)
                    c = '({arg0}{op}{arg1})'.format(arg0=arg0, op=net.op, arg1=arg1)
                    if cond is None:
                        cond = c
                    else:
                        cond = '({c}||(({arg0}=={arg1})&&{inner}))'.format(
                            c=c, arg0=arg0, arg1=arg1, inner=cond)
                code.append('{dest}[0] = {cond};'.format(dest=self.varname[dest], cond=cond))
            elif net.op == 'x':
                code.append('if ({mux}[0]) {{'.format(mux=self.varname[args[0]]))
                for n in range(limbs(dest)):
                    code.append('{dest}[{n}] = {arg}[{n}]{mask};'.format(
                        dest=self.varname[dest], n=n, arg=self.varname[args[2]],
                        mask=makemask(dest, args[2].bitwidth, n)))
                code.append('} else {')
                for n in range(limbs(dest)):
                    code.append('{dest}[{n}] = {arg}[{n}]{mask};'.format(
                        dest=self.varname[dest], n=n, arg=self.varname[args[1]],
                        mask=makemask(dest, args[1].bitwidth, n)))
                code.append('}')
            elif net.op == '+':
                code.append('carry = 0;')
                for n in range(limbs(dest)):
                    arg0 = getarglimb(args[0], n)
                    arg1 = getarglimb(args[1], n)
                    code.append('tmp = {arg0}+{arg1};'.format(arg0=arg0, arg1=arg1))
                    code.append('{dest}[{n}] = (tmp + carry){mask};'.format(
                        dest=self.varname[dest], n=n,
                        mask=makemask(dest, max(args[0].bitwidth, args[1].bitwidth)+1, n)))
                    code.append('carry = (tmp < {arg0})|({dest}[{n}] < tmp);'.format(
                        arg0=arg0, dest=self.varname[dest], n=n))
            elif net.op == '-':
                code.append('carry = 0;')
                for n in range(limbs(dest)):
                    arg0 = getarglimb(args[0], n)
                    arg1 = getarglimb(args[1], n)
                    code.append('tmp = {arg0}-{arg1};'.format(arg0=arg0, arg1=arg1))
                    code.append('{dest}[{n}] = (tmp - carry){mask};'.format(
                        dest=self.varname[dest], n=n, mask=makemask(dest, None, n)))
                    code.append('carry = (tmp > {arg0})|({dest}[{n}] > tmp);'.format(
                        arg0=arg0, dest=self.varname[dest], n=n))
            elif net.op == '*':
                for n in range(limbs(dest)):
                    code.append('{dest}[{n}] = 0;'.format(dest=self.varname[dest], n=n))
                for p0 in range(limbs(args[0])):
                    code.append('carry = 0;')
                    arg0 = getarglimb(args[0], p0)
                    for p1 in range(limbs(args[1])):
                        if limbs(dest) <= p0+p1:
                            break
                        arg1 = getarglimb(args[1], p1)
                        code.append('mul128({arg0}, {arg1}, tmplo, tmphi);'.format(
                            arg0=arg0, arg1=arg1))
                        code.append('tmp = {dest}[{p}];'.format(dest=self.varname[dest], p=p0+p1))
                        code.append('tmplo += carry; carry = tmplo < carry; tmplo += tmp;')
                        code.append('tmphi += carry + (tmplo < tmp); carry = tmphi;')
                        code.append('{dest}[{p}] = tmplo{mask};'.format(
                            dest=self.varname[dest], p=p0+p1,
                            mask=makemask(dest, args[0].bitwidth+args[1].bitwidth, p0+p1)))
                    if limbs(dest) > p0+limbs(args[1]):
                        code.append('{dest}[{p}] = carry{mask};'.format(
                            dest=self.varname[dest], p=p0+limbs(args[1]),
                            mask=makemask(
                                dest, args[0].bitwidth+args[1].bitwidth, p0+limbs(args[1]))))
            elif net.op == 'c':
                cattotal = sum(x.bitwidth for x in args)
                pieces = (
                    (self.varname[a], l, 0, min(64, a.bitwidth-64*l))
                    for a in reversed(args) for l in range(limbs(a)))
                curr = next(pieces)
                for n in range(limbs(dest)):
                    res = []
                    dpos = 0
                    while True:
                        arg, alimb, astart, asize = curr
                        res.append('(({arg}[{limb}]>>{start})<<{pos})'.format(
                            arg=arg, limb=alimb, start=astart, pos=dpos))
                        dpos += asize
                        if dpos >= dest.bitwidth-64*n:
                            break
                        if dpos > 64:
                            curr = (arg, alimb, 64-(dpos-asize), dpos-64)
                            break
                        curr = next(pieces)
                        if dpos == 64:
                            break
                    code.append('{dest}[{n}] = ({res}){mask};'.format(
                        dest=self.varname[dest], n=n, res='|'.join(res),
                        mask=makemask(dest, cattotal, n)))
            elif net.op == 's':
                for n in range(limbs(dest)):
                    bits = [
                        '((1&({src}[{limb}]>>{sb}))<<{db})'.format(
                            src=self.varname[args[0]], sb=(b % 64), limb=(b//64), db=en)
                        for en, b in enumerate(param[64*n:min(dest.bitwidth, 64*(n+1))])]
                    code.append('{dest}[{n}] = {bits};'.format(
                        dest=self.varname[dest], n=n, bits='|'.join(bits)))
        # memory writes
        for net in self.block.logic_subset('@'):
            mem = net.op_param[1]
            code.append('if ({enable}[0]) {{'.format(enable=self.varname[net.args[2]]))
            for n in range(limbs(mem)):
                code.append('{mem}[{addr}[0]][{n}] = {vn}[{n}];'.format(
                    mem=self.varname[mem],
                    addr=self.varname[net.args[0]],
                    vn=self.varname[net.args[1]],
                    n=n))
            code.append('}')
        # outputs
        outputs = list(self.block.wirevector_subset(Output))
        self._outputpos = {}
        opos = 0
        for w in outputs:
            self._outputpos[w.name] = opos, limbs(w)
            for n in range(limbs(w)):
                code.append('outputs[{pos}] = {vn}[{n}];'.format(
                    pos=opos, vn=self.varname[w], n=n))
                opos += 1
        self._obufsz = opos
        code.append('}')
        # entry point
        if platform.system() == 'Windows':
            code.append('__declspec(dllexport)')
        code.append('void sim_run_all(uint64_t stepcount, uint64_t inputs[], uint64_t outputs[]) {')
        code.append('uint64_t input_pos = 0, output_pos = 0;')
        code.append('for (uint64_t stepnum = 0; stepnum < stepcount; stepnum++) {')
        code.append('sim_run_step(inputs+input_pos, outputs+output_pos);')
        code.append('input_pos += {};'.format(self._ibufsz))
        code.append('output_pos += {};'.format(self._obufsz))
        code.append('}}')
        return '\n'.join(code)

    def step(self, inputs):
        """Runs one step of the simulation.

        The argument is a mapping from input names to the values for the step.
        """
        self.run([inputs])

    def run(self, inputs):
        """Run many steps of the simulation.

        The argument is a list of input mappings for each step,
        and its length is the number of steps to be executed.
        """
        steps = len(inputs)
        ibuf_type = ctypes.c_uint64*(steps*self._ibufsz)
        obuf_type = ctypes.c_uint64*(steps*self._obufsz)
        ibuf = ibuf_type()
        obuf = obuf_type()
        self._crun.argtypes = [ctypes.c_uint64, ibuf_type, obuf_type]
        for n, inmap in enumerate(inputs):
            for w in inmap:
                if isinstance(w, WireVector):
                    name = w.name
                else:
                    name = w
                start, count = self._inputpos[name]
                start += n*self._ibufsz
                val = inmap[w]
                if val >= 1 << self._inputbw[name]:
                    raise PyrtlError(
                        'Wire {} has value {} which cannot be represented '
                        'using its bitwidth'.format(name, val))
                for pos in range(start, start+count):
                    ibuf[pos] = val & ((1 << 64)-1)
                    val >>= 64
        self._crun(steps, ibuf, obuf)
        for name in self.tracer.trace:
            if name in self._outputpos:
                start, count = self._outputpos[name]
                buf, sz = obuf, self._obufsz
            elif name in self._inputpos:
                start, count = self._inputpos[name]
                buf, sz = ibuf, self._ibufsz
            else:
                continue  # or raise error?
            res = []
            for n in range(steps):
                val = 0
                for pos in reversed(range(start, start+count)):
                    val <<= 64
                    val |= buf[pos]
                res.append(val)
                start += sz
            self.tracer.trace[name].extend(res)

    def __del__(self):
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

    def inspect_mem(self, mem):
        return DllMemInspector(self, mem)

    def inspect(self, w):
        raise PyrtlError('CompiledSimulation does not support inspecting WireVectors')
