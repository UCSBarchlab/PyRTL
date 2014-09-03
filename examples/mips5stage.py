import sys
sys.path.append("..")  # needed only if not installed
from pyrtl import *

class Pipeline(object):
    """ Pipeline constructor with auto generation of pipeline registers. """

    def __init__(self):
        self._pipeline_register = {}
        self._interstage_signals = {}
        self._current_stage_num = 0

        self._processing_stages = False
        self.interstage()
        
        self._processing_stages = True
        stage_list = sorted([method for
            method in dir(self)
            if method.startswith('stage')])
        for stage in stage_list:
            self._pipeline_register[self._current_stage_num] = {}
            stage_method = getattr(self,stage)
            stage_method()
            self._current_stage_num += 1

    def __getattr__(self, name):
        if name in self._interstage_signals:
            return self._interstage_signals[name]
        else:
            return self._pipeline_register[self._current_state_num][name]

    def __setattr__(self, name, value):
        if self._processing_stages:
            rtype = appropriate_register_type(value)
            rname = '_'.join(['stage', str(self._current_stage_num), name])
            new_pipe_reg = rtype(bitwidth=len(value), name=rname)
            self._pipeline_register[self._current_stage_num + 1][name] = new_pipe_reg
            new_pipe_reg.next <<= value
        else:
            self._interstage_signals[name] = value

# implementation of: http://i.stack.imgur.com/Pc9Vh.png
class MipsCore(Pipeline):
    def interstage(self):
        self.pcsrc = WireVector(1,'pcsrc')
        self.computed_address = WireVector(1,'computed_address')
        self.regwrite = WireVector(1,'regwrite')
        self.write_register = WireVector(5,'write_register')
        self.write_data = WireVector(bitwidth,'write_data')

    def stage0_fetch(self):
        pc = Register(addrwidth, 'pc')
        imem = MemBlock(bitwidth, addrwidth, 'imem')
        instr = imem[pc]
        pc_incr = pc + 4
        pc.next <<= mux(self.pcsrc, pc_incr, self.computed_address)

        self.pc_incr = pc_incr
        self.instr = instr

    def stage1_decode(self):
        instr = self.instr
        rs = instr[21:26]
        rt = instr[16:21]
        rd = instr[11:16]
        immed = instr[0:16]
        opcode = instr[26:]

        # target = instr[0:26]
        # shamt = instr[6:11]
        # funct = instr[0:6]

        regfile = MemBlock(bitwidth, 5, 'regfile')
        EW = MemBlock.EnabledWrite
        regfile[self.write_register] = EW(self.write_data, enable=self.regwrite)

        self.immed = immed.sign_extended()
        self.rt = rt
        self.rd = rd
        self.regread1 = regfile[rs]
        self.regread2 = regfile[rt]
        self.pc_incr = self.pc_incr 
        self.opcode = opcode
        
    def stage2_execute(self):
        alu_op_1 = self.regread1
        alu_op_2 = mux(self.alusrc, self.regread2, self.immed)
        alu_ctrl = self.alu_ctrl(self.opcode, self.immed)

        self.pc_cmp = self.pc_incr + (self.immed << 2)
        self.alu_result, self.zero = alu(alu_ctrl, alu_op_1, alu_op_2)
        self.regread2 = self.regread2
        self.dest = mux(self.regdest, rt, rd)

    def stage3_memory(self):
        dmem = MemBlock(bitwidth, addrwidth, 'dmem')
        EW = MemBlock.EnabledWrite
        dmem[self.alu_result] = EW(self.regread2, enable=self.memwrite)

        self.read_data = dmem[self.alu_result]
        self.alu_result = self.alu_result
        self.pc_src = self.branch & self.zero

    def stage4_writeback(self):
        self.write_data = mux(self.mem_to_reg, self.alu_result, self.read_data)

    def alu_ctrl(self, opcode, immed)
        # A A
        # L L
        # U U  F F F F F F  O
        # 1 0  5 4 3 2 1 0  P
        # --------------------
        # 0 0  X X X X X X 010
        # X 1  X X X X X X 110
        # 1 X  X X 0 0 0 0 010
        # 1 X  X X 0 0 1 0 110
        # 1 X  X X 0 1 0 0 000
        # 1 X  X X 0 1 0 1 001
        # 1 X  X X 1 0 1 0 111

        aluop = opcode[:2]
        f = immed[:6]
        op0 = aluop[1] & (f[0] | f[3])
        op1 = ~aluop[0] | ~f[2]
        op2 = aluop[0] | (aluop[1] & f[1])
        return concat(op0, op1, op2)

    def alu(self, ctrl, op1, op2)
        retval = mux( (ctrl)
        
        op1 & op2
        op1 | op2
        op1 + op2
        op1 - op2
000 AND
001 OR
010 add
110 subtract
111 set-on-less-than




# Simulation of the core
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    sim.step({})
sim_trace.render_trace()
