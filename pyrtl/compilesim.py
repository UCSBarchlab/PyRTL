from __future__ import print_function, unicode_literals

import ctypes
import subprocess
import tempfile
import shutil
from os import path

from .core import working_block
from .wire import Input, Output, Const, WireVector
from .memory import RomBlock


class CompiledSimulation(object):
    """Simulate a block, compiling to C for efficiency."""
    
    def __init__(
            self, tracer=None, register_value_map={}, memory_value_map={},
            default_value=0, block=None):
        self.block = working_block(block)
        self.block.sanity_check()
        self.tracer = tracer
        self.default_value = default_value
        self._dir = tempfile.mkdtemp()
        code = self._create_code(register_value_map, memory_value_map)
        with open(path.join(self._dir, 'pyrtlsim.c'), 'w') as f:
            f.write(code)
        subprocess.check_call([
            'gcc', '-O0', '-march=native', '-std=c99', '-shared', '-fPIC', '-s',
            path.join(self._dir, 'pyrtlsim.c'), '-o', path.join(self._dir, 'pyrtlsim.so')])
        inputbuf_type = ctypes.c_uint64*len(self._inputorder)
        outputbuf_type = ctypes.c_uint64*len(self._outputorder)
        self._inputbuf = inputbuf_type()
        self._outputbuf = outputbuf_type()
        self._dll = ctypes.CDLL(path.join(self._dir, 'pyrtlsim.so'))
        self._cstep = self._dll.sim_run_step
        self._cstep.argtypes = [inputbuf_type, outputbuf_type]
        self._cstep.restype = None
        self._crun = self._dll.sim_run_all
        self._crun.restype = None  # argtypes later

    def _create_code(self, regmap, memmap):
        code = ['#include <stdint.h>']
        self.varname = {}
        uid = 0
        for w in self.block.wirevector_set:
            self.varname[w] = vn = 'w{}_{}'.format(
                str(uid), ''.join(c for c in w.name if c.isalnum()))
            assert(w.bitwidth <= 64)  # TODO bigint support
            code.append('static{mod} uint64_t {name} = {val};'.format(
                mod=' const' if isinstance(w, Const) else '',
                name=vn,
                val=w.val if isinstance(w, Const) else regmap.get(w, self.default_value)))
            uid += 1
        uid = 0
        mems = {net.op_param[1] for net in self.block.logic_subset('m@')}
        for mem in mems:
            self.varname[mem] = vn = 'm{}_{}'.format(
                str(uid), ''.join(c for c in mem.name if c.isalnum()))
            if isinstance(mem, RomBlock):
                romval = [mem._get_read_data(n) for n in range(1 << mem.addrwidth)]
                code.append('static const uint64_t {name}[] = {{'.format(name=vn))
                for rv in romval:
                    code.append(str(rv)+',')
                code.append('};')
            else:
                if mem in memmap:
                    assert(len(memmap[mem]) == (1 << mem.addrwidth))
                    memval = [memmap[mem][n] for n in range(1 << mem.addrwidth)]
                    code.append('static uint64_t {name}[] = {{'.format(name=vn))
                    for mv in memval:
                        code.append(str(mv)+',')
                    code.append('};')
                else:
                    code.append('static uint64_t {name}[{size}];'.format(
                        name=vn, size=1 << mem.addrwidth))
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
            code.append('uint64_t regtmp{} = {};'.format(uid, self.varname[net.args[0]]))
        for uid, net in enumerate(regnets):
            code.append('{} = regtmp{};'.format(self.varname[net.dests[0]], uid))
        # inputs
        inputs = list(self.block.wirevector_subset(Input))
        self._inputorder = {w.name: n for n, w in enumerate(inputs)}
        for n, w in enumerate(inputs):
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
            code.append('{dest} = {mask} & {expr};'.format(
                dest=self.varname[net.dests[0]],
                mask=hex(net.dests[0].bitmask),
                expr=expr))
        # outputs
        outputs = list(self.block.wirevector_subset(Output))
        self._outputorder = {w.name: n for n, w in enumerate(outputs)}
        for n, w in enumerate(outputs):
            code.append('outputs[{}] = {};'.format(n, self.varname[w]))
        code.append('}')
        # multiple steps
        code.append('void sim_run_all(uint64_t stepcount, uint64_t inputs[], uint64_t outputs[]) {')
        code.append('uint64_t input_pos = 0, output_pos = 0;')
        code.append('for (uint64_t stepnum = 0; stepnum < stepcount; stepnum++) {')
        code.append('sim_run_step(inputs+input_pos, outputs+output_pos);')
        code.append('input_pos += {};'.format(len(inputs)))
        code.append('output_pos += {};'.format(len(outputs)))
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
            self._inputbuf[self._inputorder[name]] = inputs[inp]
        self._cstep(self._inputbuf, self._outputbuf)
        if self.tracer is not None:
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
        ibuf_type = ctypes.c_uint64*(steps*ilen)
        obuf_type = ctypes.c_uint64*(steps*olen)
        ibuf = ibuf_type()
        obuf = obuf_type()
        self._crun.argtypes = [ctypes.c_uint64, ibuf_type, obuf_type]
        for n, inmap in enumerate(inputs):
            for w in inmap:
                if isinstance(w, WireVector):
                    name = w.name
                else:
                    name = w
                ibuf[n*ilen+self._inputorder[name]] = inmap[w]
        self._crun(steps, ibuf, obuf)
        if self.tracer is None:
            return
        for w in self.tracer.trace:
            self.tracer.trace[w].extend(obuf[n*olen+self._outputorder[w]] for n in range(steps))

    #def inspect(self, w):
    #    """Get the current value of a wirevector."""
    #    return ctypes.c_uint64.in_dll(self._dll, self.varname[w]).value

    #def inspect_mem(self, mem):
    #    """Get the current contents of a memory.
    #    
    #    The dictionary returned is a copy: modifying it will not affect the simulation.
    #    """
    #    arr = (ctypes.c_uint64*(1 << mem.addrwidth)).in_dll(self._dll, self.varname[mem])
    #    return {n: v for n, v in enumerate(arr)}

    def __del__(self):
        shutil.rmtree(self._dir)  # clean up temporary directory
