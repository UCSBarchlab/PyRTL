
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
        try:
            return self._pipeline_register_map[self._current_stage_num][name]
        except KeyError:
            raise PyrtlError('error, no pipeline register "%s" defined for stage %d'
                             % (name, self._current_stage_num))

    def __setattr__(self, name, value):
        if name.startswith('_'):
            # do not do anything tricky with variables starting with '_'
            object.__setattr__(self, name, value)
        else:
            rtype = appropriate_register_type(value)
            next_stage = self._current_stage_num + 1
            pipereg_id = str(self._current_stage_num) + 'to' + str(next_stage)
            rname = 'pipereg_' + pipereg_id + '_' + name
            if next_stage not in self._pipeline_register_map:
                self._pipeline_register_map[next_stage] = {}
            if name not in self._pipeline_register_map[next_stage]:
                new_pipereg = rtype(bitwidth=len(value), name=rname)
                self._pipeline_register_map[next_stage][name] = new_pipereg
                new_pipereg.next <<= value
            else:
                self._pipeline_register_map[next_stage][name].next <<= value

    def route_future_pipeline_reg(self, stage, bitwidth, name, rtype=Register):
        next_stage = stage + 1

        if next_stage not in self._pipeline_register_map:
            self._pipeline_register_map[next_stage] = {}

        pipereg_id = str(stage) + 'to' + str(next_stage)
        rname = 'pipereg_' + pipereg_id + '_' + name
        new_pipereg = rtype(bitwidth=bitwidth, name=rname)
        self._pipeline_register_map[next_stage][name] = new_pipereg
        return new_pipereg


def switch(ctrl, logic_dict):
    """ switch finds the matching key in logic_dict and returns the value.

    The case "0" specifies the default value to return when there is no
    match.  The logic will be a simple linear mux tree of comparisons between
    the key and the ctrl, selecting the appropriate value
    """

    working_result = logic_dict[0]
    for case_value in logic_dict:
        working_result = mux(
            ctrl == case_value,
            falsecase=working_result,
            truecase=logic_dict[case_value])
    return working_result


class TrivialPipelineExample(Pipeline):
    """ A very simple pipeline to show how registers are inferred. """

    def __init__(self):
        self._loopback = WireVector(1, 'loopback')
        super(TrivialPipelineExample, self).__init__()

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
    """ Simple 5 Stage Mips Pipeline """
    def __init__(self, addrwidth=5):
        """ all of the cross-pipeline signals are declared here """
        self._addrwidth = addrwidth  # a compile time constant
        self._pcsrc = WireVector(1, 'pcsrc')
        self._computed_address = WireVector(self._addrwidth, 'computed_address')
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
        opcode = self.opcode
        regdest, alusrc = self.ex_ctrl(opcode)
        alu_op_1 = self.regread1
        alu_op_2 = mux(alusrc, self.regread2, self.immed)
        alu_ctrl = self.alu_ctrl(self.opcode, self.immed)

        self._computed_address <<= self.pc_incr + (self.immed * 4)
        self._write_register <<= mux(regdest, self.rt, self.rd)
        self.alu_result, self.zero = self.alu(alu_ctrl, alu_op_1, alu_op_2)
        self.regread2 = self.regread2
        self.opcode = opcode

    def stage3_memory(self):
        """ access dmem for loads and stores """
        opcode = self.opcode
        branch, memwrite = self.mem_ctrl(opcode)

        dmem = MemBlock(32, self._addrwidth, 'dmem')
        EW = MemBlock.EnabledWrite

        address = self.alu_result[0:self._addrwidth]
        dmem[address] = EW(self.regread2, enable=memwrite)

        self._pcsrc <<= branch & self.zero
        self.read_data = dmem[address]
        self.alu_result = self.alu_result
        self.opcode = opcode

    def stage4_writeback(self):
        """ select the data to write back to registers """
        self._regwrite <<= self.wb_ctrl(self.opcode)
        self._write_data <<= mux(self._regwrite, self.alu_result, self.read_data)

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

    def ex_ctrl(self, opcode):
        #                       EXECUTE CONTROL
        #          O O O O O O  R A A A
        #          P P P P P P  E L L L
        #          C C C C C C  G U U U
        #          O O O O O O  D O O S
        #          D D D D D D  S P P R
        #  Inst    E E E E E E  T 1 0 C
        #          5 4 3 2 1 0         
        # -----------------------------
        # R-format 0 0 0 0 0 0  1 1 0 0
        # lw       1 0 0 0 1 1  0 0 0 1
        # sw       1 0 1 0 1 1  X 0 0 1
        # beq      0 0 1 1 0 0  X 0 1 0
        # addi     0 0 1 0 0 0  0 0 0 1
        oc = opcode
        # aluop0 = ~oc[5] & ~oc[4] & oc[3] & oc[2] & ~oc[1] & ~oc[0]
        # aluop1 = ~oc[5] & ~oc[4] & ~oc[3] & ~oc[2] & ~oc[1] & ~oc[0]
        alusrc = (~oc[5] & ~oc[4] & oc[3] & ~oc[2] & ~oc[1] & ~oc[0]) | (oc[5] & ~oc[4] & ~oc[2] & oc[1] & oc[0])
        regdest = ~oc[5] & ~oc[4] & ~oc[3] & ~oc[2] & ~oc[1] & ~oc[0]

        return regdest, alusrc

    def mem_ctrl(self, opcode):
        #                       MEM CONTROL
        #          O O O O O O  B    
        #          P P P P P P  R M M
        #          C C C C C C  A E E
        #          O O O O O O  B M M
        #          D D D D D D  C R W
        #  Inst    E E E E E E  H D R
        #          5 4 3 2 1 0       
        # ---------------------------
        # R-format 0 0 0 0 0 0  0 0 0
        # lw       1 0 0 0 1 1  0 1 0
        # sw       1 0 1 0 1 1  0 0 1
        # beq      0 0 1 1 0 0  1 0 0
        oc = opcode
        branch = ~oc[5] & ~oc[4] & oc[3] & oc[2] & ~oc[1] & ~oc[0]
        # memread = oc[5] & ~oc[4] & ~oc[3] & ~oc[2] & oc[1] & oc[0]
        memwrite = oc[5] & ~oc[4] & oc[3] & ~oc[2] & oc[1] & oc[0]

        return branch, memwrite

    def wb_ctrl(self, opcode):
        #                       WRITEBACK CONTROL
        #          O O O O O O  M
        #          P P P P P P  E
        #          C C C C C C  M
        #          O O O O O O  R
        #          D D D D D D  E
        #  Inst    E E E E E E  G
        #          5 4 3 2 1 0   
        # -----------------------
        # R-format 0 0 0 0 0 0  0
        # lw       1 0 0 0 1 1  1
        # sw       1 0 1 0 1 1  X
        # beq      0 0 1 1 0 0  X
        oc = opcode
        regwrite = oc[5] & ~oc[4] & ~oc[3] & ~oc[2] & oc[1] & oc[0]

        return regwrite

    def alu(self, ctrl, op1, op2):
        retval = switch(ctrl, {
            "3'b000": op1 & op2,
            "3'b001": op1 | op2,
            "3'b010": op1 + op2,
            "3'b110": op1 - op2,
            "3'b111": op1 < op2,
            0: 0,
            })
        return retval[0:32], retval[32]

# testcore = TrivialPipelineExample()
testcore = MipsCore(addrwidth=32)

# Simulation of the core
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    sim.step({})
sim_trace.render_trace()
