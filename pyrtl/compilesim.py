from __future__ import print_function, unicode_literals

import ctypes
import subprocess
import tempfile
import traceback
import shutil
import os
from os import path

from .core import working_block
from .wire import Input, Output, Const, WireVector
from .memory import RomBlock
from .pyrtlexceptions import PyrtlError
from .simulation import SimulationTrace


class CompiledSimulation(object):
    """Simulate a block, compiling to C for efficiency.

    THIS IS AN EXPERIMENTAL SIMULATION CLASS. NO SUPPORT WILL BE GIVEN
    TO PEOPLE WHO CANNOT GET IT TO RUN. EXPECT THE API TO CHANGE IN THE FUTURE

    This module provides significant speed improvements for people who are looking
    for high performance simulation. It is not built to be a debugging tool, though
    it may help with debugging. Generally this will do better than fastsim for
    simulations requiring over 1000 iterations.

    In order to use this, you must have:
      clang compiler
      linker (install visual studio compiler on Windows)
      64 bit version of python running

    KNOWN ISSUES:
    Not compatible with a design with any wires where wires.bitwidth > 128
    compatible but very slow with a design with any wires where 64 < wires.bitwidth <= 128
    Temporary files might not be cleaned up properly
    """

    def __init__(
            self, tracer=None, register_value_map={}, memory_value_map={},
            default_value=0, block=None):
        self.block = working_block(block)
        self.block.sanity_check()

        if tracer is None:
            tracer = SimulationTrace()
        self.tracer = tracer
        self.default_value = default_value

        try:
            self._create_and_compile_code(register_value_map, memory_value_map)
            self._setup_dll()
        except EnvironmentError:
            traceback.print_exc()
            self._create_and_compile_code(register_value_map, memory_value_map)
            self._setup_dll()

    def _create_and_compile_code(self, register_value_map, memory_value_map):
        self._dir = tempfile.mkdtemp()
        code = self._create_code(register_value_map, memory_value_map)
        with open(path.join(self._dir, 'pyrtlsim.c'), 'w') as f:
            f.write(code)
        subprocess.check_call([
            'clang', '-O0', '-march=native', '-std=c99',
            '-shared', '-fPIC', '-mcmodel=medium',
            path.join(self._dir, 'pyrtlsim.c'), '-o', path.join(self._dir, 'pyrtlsim.so')])

    def _setup_dll(self):
        inputbuf_type = ctypes.c_uint64*(2*len(self._inputorder))
        outputbuf_type = ctypes.c_uint64*(2*len(self._outputorder))
        self._inputbuf = inputbuf_type()
        self._outputbuf = outputbuf_type()

        self._dll = ctypes.CDLL(path.join(self._dir, 'pyrtlsim.so'))

        self._cstep = self._dll.sim_run_step
        self._cstep.argtypes = [inputbuf_type, outputbuf_type]
        self._cstep.restype = None

        self._crun = self._dll.sim_run_all
        self._crun.restype = None  # argtypes later

        self._cgetmem = self._dll.sim_get_mem
        self._cgetmem.argtypes = [ctypes.c_uint64]
        self._cgetmem.restype = ctypes.POINTER(ctypes.c_uint64)

    def _create_code(self, regmap, memmap):
        code = ['#include <stdint.h>']
        windows = os.name == 'nt'
        highest_bw = max(w.bitwidth for w in self.block.wirevector_set)
        if highest_bw > 128:
            raise PyrtlError('CompiledSimulation does not yet support large WireVectors')  # TODO
        self._use128 = use128 = highest_bw > 64
        usewidth = 128 if use128 else 64
        if use128:
            code.append('typedef unsigned int uint128_t __attribute__((mode(TI)));')
        self.varname = {}
        uid = 0
        for w in self.block.wirevector_set:
            self.varname[w] = vn = 'w{}_{}'.format(
                str(uid), ''.join(c for c in w.name if c.isalnum()))
            code.append('static{mod} uint{width}_t {name} = {val};'.format(
                mod=' const' if isinstance(w, Const) else '',
                width=usewidth, name=vn,
                val=w.val if isinstance(w, Const) else regmap.get(w, self.default_value)))
            uid += 1
        uid = 0
        mems = {net.op_param[1] for net in self.block.logic_subset('m@')}
        self.memid = {}
        for mem in mems:
            self.varname[mem] = vn = 'm{}_{}'.format(
                str(uid), ''.join(c for c in mem.name if c.isalnum()))
            if isinstance(mem, RomBlock):
                romval = [mem._get_read_data(n) for n in range(1 << mem.addrwidth)]
                code.append('static const uint{width}_t {name}[] = {{'.format(
                    name=vn, width=usewidth))
                for rv in romval:
                    code.append(str(rv)+',')
                code.append('};')
            else:
                if mem in memmap:
                    memval = [mem.get(n, 0) for n in range(1 << mem.addrwidth)]
                    code.append('static uint{width}_t {name}[] = {{'.format(
                        name=vn, width=usewidth))
                    for mv in memval:
                        code.append(str(mv)+',')
                    code.append('};')
                else:
                    code.append('static uint{width}_t {name}[{size}];'.format(
                        name=vn, size=1 << mem.addrwidth, width=usewidth))
            self.memid[mem] = uid
            uid += 1
        if windows:
            code.append('__declspec(dllexport)')
        code.append('const uint{}_t* sim_get_mem(uint64_t memnum) {{'.format(usewidth))
        code.append('switch (memnum) {')
        for mem in mems:
            code.append('case {num}: return {mem};'.format(
                num=self.memid[mem], mem=self.varname[mem]))
        code.append('default: return (uint{}_t*)(0);'.format(usewidth))
        code.append('}}')
        if windows:
            code.append('__declspec(dllexport)')
        code.append('void sim_run_step(uint64_t inputs[], uint64_t outputs[]) {')
        # memory writes
        for net in self.block.logic_subset('@'):
            code.append('if ({enable}) {mem}[{addr}] = {val};'.format(
                enable=self.varname[net.args[2]],
                mem=self.varname[net.op_param[1]],
                addr=self.varname[net.args[0]],
                val=self.varname[net.args[1]]))
        # register updates
        regnets = list(self.block.logic_subset('r'))
        for uid, net in enumerate(regnets):
            code.append('uint{width}_t regtmp{uid} = {vn};'.format(
                uid=uid, vn=self.varname[net.args[0]], width=usewidth))
        for uid, net in enumerate(regnets):
            code.append('{} = regtmp{};'.format(self.varname[net.dests[0]], uid))
        # inputs
        inputs = list(self.block.wirevector_subset(Input))
        self._inputorder = {w.name: n for n, w in enumerate(inputs)}
        for n, w in enumerate(inputs):
            if use128:
                code.append('{} = (((uint128_t)inputs[{}])<<64)|inputs[{}];'.format(
                    self.varname[w], 2*n, 2*n+1))
            else:
                code.append('{} = inputs[{}];'.format(self.varname[w], n))
        # combinational logic
        simple_ops = {
            'w': '{0}',
            '~': '~{0}',
            '&': '{0}&{1}',
            '|': '{0}|{1}',
            '^': '{0}^{1}',
            'n': '~({0}&{1})',
            '+': '{0}+{1}',
            '-': '{0}-{1}',
            '*': '{0}*{1}',
            '<': '{0}<{1}',
            '>': '{0}>{1}',
            '=': '{0}=={1}',
            'x': '{0}?{2}:{1}',  # note order of args
        }

        def bw_max(net):
            return max(len(x) for x in net.args)

        def bw_sum(net):
            return sum(len(x) for x in net.args)

        op_bitwidths = {
            'w': bw_max,
            '~': None,
            '&': bw_max,
            '|': bw_max,
            '^': bw_max,
            'n': None,
            '+': lambda net: bw_max(net) + 1,
            '-': lambda net: bw_max(net) + 1,
            '*': bw_sum,
            '<': lambda net: 1,
            '>': lambda net: 1,
            '=': lambda net: 1,
            'x': bw_max,
            'c': bw_sum,
            's': lambda net: len(net.op_param),
            'm': lambda net: net.op_param[1].bitwidth
        }
        bw_good_count = 0
        bw_mask_count = 0
        for net in self.block:  # topo order
            if net.op in 'r@':
                continue  # skip synchronized nets
            code.append('// {}'.format(net))
            if net.op in simple_ops:
                expr = simple_ops[net.op].format(*(self.varname[x] for x in net.args))
            elif net.op == 'c':
                expr = []
                for n, a in enumerate(net.args):
                    shift = sum(len(x) for x in net.args[n+1:])
                    expr.append('({} << {})'.format(self.varname[a], shift))
                expr = '|'.join(expr)
            elif net.op == 's':
                expr = []
                source = self.varname[net.args[0]]
                for n, bit in enumerate(net.op_param):
                    expr.append('((({source} >> {bit}) & 1) << {n})'.format(
                        source=source, bit=bit, n=n))
                expr = '|'.join(expr)
            elif net.op == 'm':
                expr = '{mem}[{addr}]'.format(
                    mem=self.varname[net.op_param[1]], addr=self.varname[net.args[0]])
            if (op_bitwidths[net.op] is not None and
                    op_bitwidths[net.op](net) <= net.dests[0].bitwidth):
                code.append('{dest} = {expr};'.format(
                    dest=self.varname[net.dests[0]], expr=expr))
            else:
                code.append('{dest} = {mask} & ({expr});'.format(
                    dest=self.varname[net.dests[0]],
                    mask=hex(net.dests[0].bitmask),
                    expr=expr))
        # outputs
        outputs = list(self.block.wirevector_subset(Output))
        self._outputorder = {w.name: n for n, w in enumerate(outputs)}
        for n, w in enumerate(outputs):
            if use128:
                code.append('outputs[{}] = {}>>64;'.format(2*n, self.varname[w]))
                code.append('outputs[{}] = {};'.format(2*n+1, self.varname[w]))
            else:
                code.append('outputs[{}] = {};'.format(n, self.varname[w]))
        code.append('}')
        # multiple steps
        if windows:
            code.append('__declspec(dllexport)')
        code.append('void sim_run_all(uint64_t stepcount, uint64_t inputs[], uint64_t outputs[]) {')
        code.append('uint64_t input_pos = 0, output_pos = 0;')
        code.append('for (uint64_t stepnum = 0; stepnum < stepcount; stepnum++) {')
        code.append('sim_run_step(inputs+input_pos, outputs+output_pos);')
        code.append('input_pos += {};'.format((use128+1)*len(inputs)))
        code.append('output_pos += {};'.format((use128+1)*len(outputs)))
        code.append('}}')
        return '\n'.join(code)

    def step(self, inputs):
        """Runs one step of the simulation.

        The argument is a mapping from input names to the values for the step.
        """
        for inp in inputs:
            if isinstance(inp, WireVector):
                name = inp.name
            else:
                name = inp
            if self._use128:
                self._inputbuf[2*self._inputorder[name]] = inputs[inp] >> 64
                self._inputbuf[2*self._inputorder[name]+1] = inputs[inp] & ((1 << 64)-1)
            else:
                self._inputbuf[self._inputorder[name]] = inputs[inp]
        self._cstep(self._inputbuf, self._outputbuf)
        if self._use128:
            values = {w: (
                self._outputbuf[2*self._outputorder[w]] << 64) |
                self._outputbuf[2*self._outputorder[w]+1] for w in self._outputorder}
        else:
            values = {w: self._outputbuf[self._outputorder[w]] for w in self._outputorder}
        self.tracer.add_step_named(values)

    def run(self, inputs):
        """Run many steps of the simulation.

        The argument is a list of input mappings for each step,
        and its length is the number of steps to be executed.
        """
        steps = len(inputs)
        ilen = len(self._inputorder)
        olen = len(self._outputorder)
        ibuf_type = ctypes.c_uint64*(steps*ilen*(self._use128+1))
        obuf_type = ctypes.c_uint64*(steps*olen*(self._use128+1))
        ibuf = ibuf_type()
        obuf = obuf_type()
        self._crun.argtypes = [ctypes.c_uint64, ibuf_type, obuf_type]
        for n, inmap in enumerate(inputs):
            for w in inmap:
                if isinstance(w, WireVector):
                    name = w.name
                else:
                    name = w
                if self._use128:
                    ibuf[2*(n*ilen+self._inputorder[name])] = inmap[w] >> 64
                    ibuf[2*(n*ilen+self._inputorder[name])+1] = inmap[w] & ((1 << 64)-1)
                else:
                    ibuf[n*ilen+self._inputorder[name]] = inmap[w]
        self._crun(steps, ibuf, obuf)
        for w in self.tracer.trace:
            if self._use128:
                values = (
                    (obuf[2*(n*olen+self._outputorder[w])] << 64) |
                    obuf[2*(n*olen+self._outputorder[w])+1] for n in range(steps))
            else:
                values = (obuf[n*olen+self._outputorder[w]] for n in range(steps))
            self.tracer.trace[w].extend(values)

    def unload_dll(self):
        # from http://stackoverflow.com/questions/19547084/can-i-explicitly-close-a-ctypes-cdll
        handle = self._dll._handle
        if os.name == 'nt':
            # needed to make sure that the handle is properly converted to a windows
            # sized pointer
            # http://stackoverflow.com/questions/23522055/error-when-unload-a-
            # 64bit-dll-using-ctypes-windll?rq=1
            from ctypes import wintypes
            ctypes.windll.kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]

            ctypes.windll.kernel32.FreeLibrary(handle)
        else:
            # don't know if this works
            ctypes.cdll.LoadLibrary(path.join(self._dir, 'pyrtlsim.so')).dlclose(handle)

    def inspect_mem(self, mem):
        ptr = self._cgetmem(self.memid[mem])
        if ptr is None:
            raise PyrtlError('Specified memory not in simulated block')
        buf = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint64*(1 << mem.addrwidth))).contents
        return {n: v for n, v in enumerate(buf)}

    def __del__(self):
        # cannot call this in Windows, as the library is still bound to, and therefore
        # the directory is still in use in Windows
        self.unload_dll()
        shutil.rmtree(self._dir)  # clean up temporary directory
