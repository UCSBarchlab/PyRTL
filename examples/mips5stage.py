import sys
sys.path.append("..")  # needed only if not installed
from pyrtl import *

class Pipeline(object):
    def __init__(self):
        pipeline_register = {}
        current_state = 0
    def __getattr__(self, name):
        return pipeline_register[current_state][name]
    def __setattr__(self, name, value):
        new_pipe_reg = Register(bitwidth=len(value))
        pipeline_register[current_state+1][name] = new_pipe_reg
        new_pipe_reg.next <<= value


# implementation of: http://i.stack.imgur.com/Pc9Vh.png
class MipsCore(Pipeline):
    def out_of_pipeline(self):
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
        opcode = instr[26:]
        rs = instr[21:26]
        rt = instr[16:21]
        rd = instr[11:16]
        shamt = instr[6:11]
        funct = instr[0:6]
        immed = instr[0:16]
        target = instr[0:26]

        regfile = MemBlock(bitwidth, 5, 'regfile')
        EW = MemBlock.EnabledWrite
        regfile[self.write_register] = EW(self.write_data, enable=self.regwrite)

        self.immed = immed.sign_extended()
        self.rt = rt
        self.rd = rd
        self.regread1 = regfile[rs]
        self.regread2 = regfile[rt]
        self.pc_incr = self.pc_incr 
        
    def stage2_execute(self):
        alu_op_1 = self.regread1
        alu_op_2 = mux(self.alusrc, self.regread2, self.immed)

        self.pc_cmp = self.pc_incr + (self.immed << 2)
        self.alu_result, self.zero = alu(?,alu_op_1, alu_op_2)
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


# Simulation of the core
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    sim.step({})
sim_trace.render_trace()
