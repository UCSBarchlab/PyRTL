import sys
from pprint import *
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

class SwitchDefaultType(object):
    # __slots__ = () if you want to save a few bytes
    def __init__(self, val=None):
        self._value = val
        super(SwitchDefaultType, self).__init__()

    def __repr__(self):
        return 'SwitchDefault'

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        return self.__repr__() == self.__repr__()

    def __call__(self, val=None):
        if val is not None:
            self._value = val
            return SwitchDefaultType(val)
        else:
            return self._value

SwitchDefault = SwitchDefaultType()

def switch(ctrl, logic_dict):
    """ switch finds the matching key in logic_dict and returns the value.

    The case SwitchDefault specifies the default value to return when there is no
    match.  The logic will be a simple linear mux tree of comparisons between
    the key and the ctrl, selecting the appropriate value
    """

    working_result = logic_dict[SwitchDefault]
    for case_value in sorted(logic_dict):
        true_case = logic_dict[case_value]

        if isinstance(case_value, SwitchDefaultType):
            case_value = case_value()
            true_case = logic_dict[SwitchDefault]

            if case_value is None:
                continue

        working_result = mux(
            ctrl == case_value,
            falsecase=working_result,
            truecase=true_case)
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
        self._write_data = WireVector(32, 'write_data')
        self._alu_result = WireVector(32, 'alu_result')
        self._zero = WireVector(1, 'zero')
        self._regfile = MemBlock(32, 5, 'regfile')

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
        immed = instr[0:16].sign_extended(32)
        opcode = instr[26:]

        control_signals = self.main_decoder(opcode)

        self.fwd_op_1, self.fwd_op_2 = self.decoder_forwarding_unit(rs, rt)
        self.write_register = mux(control_signals["regdest"], rt, rd)

        # target = instr[0:26]
        # shamt = instr[6:11]
        funct = instr[0:6]

        self.aluop = concat(control_signals["aluop1"], control_signals["aluop0"])
        self.funct = funct
        self.alusrc = control_signals["alusrc"]
        self.branch = control_signals["branch"]
        self.immed = immed
        self.memwrite = control_signals["memwrite"]
        self.regread2 = self._regfile[rt]
        self.regwrite = control_signals["regwrite"]
        self.rs = rs
        self.rt = rt
        self.pc_incr = self.pc_incr
        self.opcode = opcode

    def stage2_execute(self):
        """ perform the alu operations """
        # fwd_op_1, fwd_op_2 = self.execution_forwarding_unit()

        # alu_op_1 = fwd_op_1
        # alu_op_2 = mux(self.alusrc, fwd_op_2, self.immed)

        fwd_op_1, fwd_op_2 = self.fwd_op_1, self.fwd_op_2

        alu_op_1 = fwd_op_1
        alu_op_2 = mux(self.alusrc, fwd_op_2, self.immed)

        alu_ctrl = self.alu_ctrl(self.aluop, self.immed)

        immed_shifted = concat(self.immed, Const(0, bitwidth=2))[:32]

        # needed for next stage and sw
        # check that regread2 is correct
        self.regread2 = self.regread2

        self._computed_address <<= self.pc_incr + immed_shifted
        alu_result, zero = self.alu(alu_ctrl, alu_op_1, alu_op_2)
        self._alu_result <<= alu_result
        self._zero <<= zero
        self.branch = self.branch
        self.memwrite = self.memwrite
        self.alu_result, self.zero = self._alu_result, self._zero
        self.regwrite = self.regwrite
        self.write_register = self.write_register

    def stage3_memory(self):
        """ access dmem for loads and stores """
        dmem = MemBlock(32, self._addrwidth, 'dmem')
        EW = MemBlock.EnabledWrite

        address = self.alu_result[0:self._addrwidth]
        dmem[address] = EW(self.regread2, enable=self.memwrite)  # TODO: check if regread2 is correct
        read_data = dmem[address]

        self._pcsrc <<= self.branch & self.zero
        self.write_register = self.write_register
        self.write_data = mux(self.regwrite, read_data, self.alu_result)
        self.read_data = read_data
        self.alu_result = self.alu_result
        self.regwrite = self.regwrite

    def stage4_writeback(self):
        """ select the data to write back to registers """
        self._write_data <<= mux(self.regwrite, self.read_data, self.alu_result)

        EW = MemBlock.EnabledWrite
        writable_register = (self.regwrite == 1) & (self.write_register != 0)
        self._regfile[self.write_register] = EW(self._write_data, enable=writable_register)

    def main_decoder(self, opcode):
        #                       SIGNALS
        #          O O O O O O  A A A B J M M R R
        #          P P P P P P  L L L R U E E E E
        #          C C C C C C  U U U A M M M G G
        #          O O O O O O  O O S N P T W D W
        #          D D D D D D  P P R C   R R S R
        #  Inst    E E E E E E  1 0 C H   G I T I
        #          5 4 3 2 1 0
        # ---------------------------------------
        # R-format 0 0 0 0 0 0  1 0 0 0 0 0 0 1 1
        # lw       1 0 0 0 1 1  0 0 1 0 0 1 0 0 1
        # sw       1 0 1 0 1 1  0 0 1 0 0 X 1 X 0
        # beq      0 0 0 1 0 0  0 1 0 1 0 X 0 X 0
        # j        0 0 0 0 1 0  0 0 X 0 1 X 0 X 0
        # addi     0 0 1 0 0 0  0 0 1 0 0 0 0 0 1

        r_format_inst = opcode == "6'b000000"
        lw_inst       = opcode == "6'b100011"
        sw_inst       = opcode == "6'b101011"
        j_inst        = opcode == "6'b000010"
        beq_inst      = opcode == "6'b000100"
        addi_inst     = opcode == "6'b001000"

        control_signals = {}

        control_signals["aluop0"]   = beq_inst
        control_signals["aluop1"]   = r_format_inst

        control_signals["alusrc"]   = lw_inst | sw_inst | addi_inst

        control_signals["branch"]   = beq_inst
        control_signals["jump"]     = j_inst

        control_signals["memtoreg"] = lw_inst
        control_signals["memwrite"] = sw_inst

        control_signals["regdest"]  = r_format_inst
        control_signals["regwrite"] = r_format_inst | lw_inst | addi_inst

        return control_signals

    def alu_ctrl(self, aluop, immed):
        # A A
        # L L
        # U U  F F F F F F  O
        # 1 0  5 4 3 2 1 0  P  OPERATION
        # ------------------------------
        # 0 0  X X X X X X 010 lw/sw
        # X 1  X X X X X X 110 beq
        # 1 X  X X 0 0 0 0 010 add
        # 1 X  X X 0 0 1 0 110 sub
        # 1 X  X X 0 1 0 0 000 and
        # 1 X  X X 0 1 0 1 001 or
        # 1 X  X X 1 0 1 0 111 slt

        f = immed[:6]
        op0 = aluop[1] & (f[0] | f[3])
        op1 = ~aluop[1] | ~f[2]
        op2 = aluop[0] | (aluop[1] & f[1])

        return concat(op2, op1, op0)

    def alu(self, ctrl, op1, op2):
        retval = switch(ctrl, {
            "3'b000": op1 & op2,
            "3'b001": op1 | op2,
            "3'b010": op1 + op2,
            "3'b110": op1 - op2,
            "3'b111": op1 < op2,
            SwitchDefault: op1,
            })
        return retval[0:32], retval[32]

    def decoder_forward_ctrl(self, fwd_id, fwd_ex, fwd_mem):
        fwd_ctrl = switch(concat(fwd_id, fwd_ex, fwd_mem), {
            SwitchDefault("3'b000"): "3'b000",
            "3'b100": "3'b100",
            "3'b010": "3'b010",
            "3'b001": "3'b001",
            })
        return fwd_ctrl

    def decoder_forward_op(self, fwd_ctrl, register, id_ex_alu_result, ex_mem_alu_result, mem_wb_alu_result):
        fwd_op = switch(fwd_ctrl, {
            SwitchDefault("3'b000"): self._regfile[register],
            "3'b001": mem_wb_alu_result,
            "3'b010": ex_mem_alu_result,
            "3'b100": id_ex_alu_result,
            })
        return fwd_op

    def decoder_forwarding_unit(self, rs, rt):
        # get a reference to some pipeline registers that don't exist yet
        id_ex_alu_result = self._alu_result
        id_ex_regwrite = self.route_future_pipeline_reg(1, bitwidth=1, name="regwrite")
        id_ex_write_register = self.route_future_pipeline_reg(1, bitwidth=5, name="write_register")

        ex_mem_alu_result = self.route_future_pipeline_reg(2, bitwidth=32, name="alu_result")
        ex_mem_regwrite = self.route_future_pipeline_reg(2, bitwidth=1, name="regwrite")
        ex_mem_write_register = self.route_future_pipeline_reg(2, bitwidth=5, name="write_register")

        mem_wb_write_data = self._write_data
        mem_wb_regwrite = self.route_future_pipeline_reg(3, bitwidth=1, name="regwrite")
        mem_wb_write_register = self.route_future_pipeline_reg(3, bitwidth=5, name="write_register")

        # tests for id_ex
        id_ex_regwrite_enabled = id_ex_regwrite == 1
        id_ex_write_register_is_nonzero = id_ex_write_register != 0

        id_ex_write_register_eq_rs = id_ex_write_register == rs
        id_ex_write_register_eq_rt = id_ex_write_register == rt

        # tests for ex_mem
        ex_mem_regwrite_enabled = ex_mem_regwrite == 1
        ex_mem_write_register_is_nonzero = ex_mem_write_register != 0

        ex_mem_write_register_eq_rs = ex_mem_write_register == rs
        ex_mem_write_register_eq_rt = ex_mem_write_register == rt

        # tests for mem_wb registers
        mem_wb_regwrite_enabled = mem_wb_regwrite == 1
        mem_wb_write_register_is_nonzero = mem_wb_write_register != 0

        mem_wb_write_register_eq_rs = mem_wb_write_register == rs
        mem_wb_write_register_eq_rt = mem_wb_write_register == rt

        # forward id
        fwd_ab_id = id_ex_regwrite_enabled & id_ex_write_register_is_nonzero
        fwd_a_id = fwd_ab_id & id_ex_write_register_eq_rs
        fwd_b_id = fwd_ab_id & id_ex_write_register_eq_rt

        # forward ex
        fwd_ab_ex = ex_mem_regwrite_enabled & ex_mem_write_register_is_nonzero
        fwd_a_ex = fwd_ab_ex & ~fwd_a_id & ex_mem_write_register_eq_rs
        fwd_b_ex = fwd_ab_ex & ~fwd_b_id & ex_mem_write_register_eq_rt

        # forward mem
        fwd_ab_mem = mem_wb_regwrite_enabled & mem_wb_write_register_is_nonzero
        fwd_a_mem = fwd_ab_mem & ~fwd_a_id & ~fwd_a_ex & mem_wb_write_register_eq_rs
        fwd_b_mem = fwd_ab_mem & ~fwd_b_id & ~fwd_b_ex & mem_wb_write_register_eq_rt

        # get the appropriate forwarding control for the forwarding selection
        forward_a = self.decoder_forward_ctrl(fwd_a_id, fwd_a_ex, fwd_a_mem)
        forward_b = self.decoder_forward_ctrl(fwd_b_id, fwd_b_ex, fwd_b_mem)

        # get the operand from the correct place based on the control
        fwd_op_1 = self.decoder_forward_op(forward_a, rs, id_ex_alu_result, ex_mem_alu_result, mem_wb_write_data)
        fwd_op_2 = self.decoder_forward_op(forward_b, rt, id_ex_alu_result, ex_mem_alu_result, mem_wb_write_data)

        return fwd_op_1, fwd_op_2

    # def execution_forward_ctrl(self, fwd_ex, fwd_mem):
    #     fwd_ctrl = switch(concat(fwd_ex, fwd_mem), {
    #         SwitchDefault("2'b00"): "2'b00",
    #         "2'b10": "2'b10",
    #         "2'b11": "2'b10",
    #         "2'b01": "2'b01",
    #         })
    #     return fwd_ctrl

    # def execution_forward_op(self, fwd_ctrl, register, ex_mem_alu_result, mem_wb_alu_result):
    #     fwd_op = switch(fwd_ctrl, {
    #         SwitchDefault("2'b00"): self._regfile[register],
    #         "2'b01": mem_wb_alu_result,
    #         "2'b10": ex_mem_alu_result,
    #         })
    #     return fwd_op

    # def execution_forwarding_unit(self):
    #     # get a reference to some pipeline registers that don't exist yet
    #     ex_mem_alu_result = self.route_future_pipeline_reg(2, bitwidth=32, name="alu_result")
    #     ex_mem_regwrite = self.route_future_pipeline_reg(2, bitwidth=1, name="regwrite")
    #     ex_mem_write_register = self.route_future_pipeline_reg(2, bitwidth=5, name="write_register")

    #     mem_wb_alu_result = self.route_future_pipeline_reg(3, bitwidth=32, name="alu_result")
    #     mem_wb_regwrite = self.route_future_pipeline_reg(3, bitwidth=1, name="regwrite")
    #     mem_wb_write_register = self.route_future_pipeline_reg(3, bitwidth=5, name="write_register")

    #     # tests for ex_mem registers
    #     ex_mem_regwrite_enabled = ex_mem_regwrite == 1
    #     ex_mem_write_register_is_nonzero = ex_mem_write_register != 0

    #     ex_mem_write_register_eq_rs = ex_mem_write_register == self.rs
    #     ex_mem_write_register_eq_rt = ex_mem_write_register == self.rt

    #     # tests for mem_wb registers
    #     mem_wb_regwrite_enabled = mem_wb_regwrite == 1
    #     mem_wb_write_register_is_nonzero = mem_wb_write_register != 0

    #     mem_wb_write_register_eq_rs = mem_wb_write_register == self.rs
    #     mem_wb_write_register_eq_rt = mem_wb_write_register == self.rt

    #     # forward ex when regwrite for that stage is used, won't be written to $r0, and is one of the operands
    #     fwd_a_ex = ex_mem_regwrite_enabled & ex_mem_write_register_is_nonzero & ex_mem_write_register_eq_rs
    #     fwd_b_ex = ex_mem_regwrite_enabled & ex_mem_write_register_is_nonzero & ex_mem_write_register_eq_rt

    #     # forward mem when regwrite for that stage is used, won't br written to $r0, isn't already being forwarded from ex, and is one of the operands
    #     fwd_a_mem = mem_wb_regwrite_enabled & mem_wb_write_register_is_nonzero & ~ex_mem_write_register_eq_rs & mem_wb_write_register_eq_rs
    #     fwd_b_mem = mem_wb_regwrite_enabled & mem_wb_write_register_is_nonzero & ~ex_mem_write_register_eq_rt & mem_wb_write_register_eq_rt

    #     # get the appropriate forwarding control for the forwarding selection
    #     forward_a = self.execution_forward_ctrl(fwd_a_ex, fwd_a_mem)
    #     forward_b = self.execution_forward_ctrl(fwd_b_ex, fwd_b_mem)

    #     # get the operand from the correct place based on the control
    #     fwd_op_1 = self.execution_forward_op(forward_a, self.rs, ex_mem_alu_result, mem_wb_alu_result)
    #     fwd_op_2 = self.execution_forward_op(forward_b, self.rt, ex_mem_alu_result, mem_wb_alu_result)

    #     return fwd_op_1, fwd_op_2

# testcore = TrivialPipelineExample()
testcore = MipsCore(addrwidth=24)

# Simulation of the core
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)

sim.memvalue = {
    (2, 0): 0x20020001,
    (2, 4): 0x20030002,
    (2, 8): 0x00431820,
    (2, 12): 0x00621020,
    (2, 16): 0x00421820,
    (2, 20): 0x00431822,
    (2, 24): 0x20630005,
}

for i in xrange(25):
    sim.step({})

sim_trace.render_trace()
# sim_trace.print_vcd(open("pipelines.vcd", "w"))
# output_to_verilog(open("pipelines.v", "w"))

pprint(sim.memvalue)

# print working_block()
# synthesize()
# optimize()
# print working_block()
