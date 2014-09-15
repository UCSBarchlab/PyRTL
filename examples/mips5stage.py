
import sys
sys.path.append("..")  # needed only if not installed
from pyrtl import *


class Pipeline(object):
    """ Pipeline constructor with auto generation of pipeline registers. """

    def __init__(self):
        self._pipeline_register_map = {}
        self._current_stage_num = 0

        stage_list = sorted(
            [method for
             method in dir(self)
             if method.startswith('stage')])
        for stage in stage_list:
            stage_method = getattr(self, stage)
            stage_method()
            self._current_stage_num += 1

    def __getattr__(self, name):
            return self._pipeline_register_map[self._current_stage_num][name]

    def __setattr__(self, name, value):
        if name.startswith('_'):
            # do not do anything tricky with variables starting with '_'
            object.__setattr__(self, name, value)
        else:
            rtype = appropriate_register_type(value)
            next_stage = self._current_stage_num + 1
            pipereg_id = str(self._current_stage_num) + 'to' + str(next_stage)
            rname = 'pipereg_' + pipereg_id + '_' + name
            new_pipereg = rtype(bitwidth=len(value), name=rname)
            if next_stage not in self._pipeline_register_map:
                self._pipeline_register_map[next_stage] = {}
            self._pipeline_register_map[next_stage][name] = new_pipereg
            t = WireVector(1)
            t <<= value
            new_pipereg.next <<= t
            #new_pipereg.next <<= value


def switch(ctrl, logic_dict):
    working_result = logic_dict[None]
    for case_value in logic_dict:
        working_result = mux(
            ctrl == case_value,
            falsecase=working_result,
            truecase=logic_dict[case_value])
    return working_result


class StupidPipeline(Pipeline):
    def __init__(self):
        self._loopback = WireVector(1, 'loopback')
        super(StupidPipeline, self).__init__()
    def stage0(self):
        self.n = ~ self._loopback
    def stage1(self):
        self.n = self.n
    def stage2(self):
        self.n = self.n
    def stage3(self):
        self.n = self.n
    def stage4(self):
        self._loopback <<= self.n


# implementation of: http://i.stack.imgur.com/Pc9Vh.png
class MipsCore(Pipeline):
    """ Variable bitwidth 5 Stage Mips Pipeline """
    def __init__(self, addrwidth=5):
        """ all of the cross-pipeline signals are declared here """
        self._addrwidth = addrwidth  # a compile time constant
        self._pcsrc = WireVector(1, 'pcsrc')
        self._computed_address = WireVector(1, 'computed_address')
        self._regwrite = WireVector(1, 'regwrite')  # CHECK
        self._write_register = WireVector(5, 'write_register')  # CHECK
        self._write_data = WireVector(32, 'write_data')
        super(MipsCore, self).__init__()

    def stage0_fetch(self):
        """ update the PC, grab the instruction from imem """
        pc = Register(self._addrwidth, 'pc')
        imem = MemBlock(32, self._addrwidth, 'imem')
        instr = imem[pc]
        pc_incr = pc + 4
        pc.next <<= mux(self._pcsrc, pc_incr, self._computed_address)

        self.pc_incr = pc_incr
        self.instr = instr

    def stage1_decode(self):
        """ break instruction into fields and access registers """
        instr = self.instr
        rs = instr[21:26]
        rt = instr[16:21]
        rd = instr[11:16]
        immed = instr[0:16]
        opcode = instr[26:]

        # target = instr[0:26]
        # shamt = instr[6:11]
        # funct = instr[0:6]

        regfile = MemBlock(32, 5, 'regfile')
        EW = MemBlock.EnabledWrite
        regfile[self._write_register] = EW(self._write_data, enable=self._regwrite)

        self.immed = immed.sign_extended(32)
        self.rt = rt
        self.rd = rd
        self.regread1 = regfile[rs]
        self.regread2 = regfile[rt]
        self.pc_incr = self.pc_incr
        self.opcode = opcode

    def stage2_execute(self):
        """ perform the alu operations """
        alu_op_1 = self.regread1
        alu_op_2 = mux(self.alusrc, self.regread2, self.immed)
        alu_ctrl = self.alu_ctrl(self.opcode, self.immed)

        self.pc_cmp = self.pc_incr + (self.immed << 2)
        self.alu_result, self.zero = alu(alu_ctrl, alu_op_1, alu_op_2)
        self.regread2 = self.regread2
        self.dest = mux(self.regdest, rt, rd)

    def stage3_memory(self):
        """ access dmem for loads and stores """
        dmem = MemBlock(32, self._addrwidth, 'dmem')
        EW = MemBlock.EnabledWrite
        dmem[self.alu_result] = EW(self.regread2, enable=self.memwrite)

        self.read_data = dmem[self.alu_result]
        self.alu_result = self.alu_result
        self.pc_src = self.branch & self.zero

    def stage4_writeback(self):
        """ select the data to write back to registers """
        self._write_data = mux(self.mem_to_reg, self.alu_result, self.read_data)

    def alu_ctrl(self, opcode, immed):
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

    def alu(self, ctrl, op1, op2):
        retval = switch(ctrl, {
            "3'000": op1 & op2,
            "3'001": op1 | op2,
            "3'010": op1 + op2,
            "3'110": op1 - op2,
            "3'111": op1 < op2,
            None: 0,
            })


#testcore = MipsCore(addrwidth=5)
testcore = StupidPipeline()
print working_block()

# Simulation of the core
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    sim.step({})
sim_trace.render_trace()
