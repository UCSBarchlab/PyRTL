import unittest
import random
import io
import pyrtl
from pyrtl import verilog

verilog_output_small = """\
// Generated automatically via PyRTL
// As one initial test of synthesis, map to FPGA with:
//   yosys -p "synth_xilinx -top toplevel" thisfile.v

module toplevel(clk, o);
    input clk;
    output[12:0] o;

    wire[3:0] const_0_12;
    wire[2:0] const_1_3;
    wire[5:0] k;
    wire[12:0] tmp0;

    // Combinational
    assign const_0_12 = 12;
    assign const_1_3 = 3;
    assign k = 38;
    assign o = tmp0;
    assign tmp0 = {const_0_12, const_1_3, k};

endmodule

"""


verilog_output_large = """\
// Generated automatically via PyRTL
// As one initial test of synthesis, map to FPGA with:
//   yosys -p "synth_xilinx -top toplevel" thisfile.v

module toplevel(clk, a, o);
    input clk;
    input[3:0] a;
    output[5:0] o;

    reg[3:0] mem_0[3:0]; //z
    reg[3:0] mem_1[3:0]; //tmp2
    reg[3:0] mem_2[3:0]; //tmp3
    reg[3:0] mem_3[3:0]; //tmp4
    reg[3:0] mem_4[3:0]; //tmp5
    reg[3:0] mem_5[3:0]; //tmp6
    reg[3:0] mem_6[3:0]; //tmp7
    reg[3:0] mem_7[3:0]; //tmp8
    reg[3:0] mem_8[3:0]; //tmp9
    reg[3:0] mem_9[3:0]; //tmp10
    reg[3:0] mem_10[3:0]; //tmp11
    reg[3:0] mem_11[3:0]; //tmp12
    reg[3:0] mem_12[3:0]; //tmp13
    reg[3:0] tmp0;
    reg[3:0] tmp1;

    wire[1:0] const_0_0;
    wire[1:0] const_1_0;
    wire const_2_1;
    wire[1:0] const_3_1;
    wire const_4_1;
    wire const_5_0;
    wire[1:0] const_6_1;
    wire const_7_1;
    wire[1:0] const_8_0;
    wire[1:0] const_9_0;
    wire const_10_1;
    wire[1:0] const_11_1;
    wire const_12_1;
    wire const_13_0;
    wire[1:0] const_14_1;
    wire const_15_1;
    wire[1:0] const_16_0;
    wire[1:0] const_17_0;
    wire const_18_1;
    wire[1:0] const_19_1;
    wire const_20_1;
    wire const_21_0;
    wire[1:0] const_22_1;
    wire const_23_1;
    wire[1:0] const_24_0;
    wire[1:0] const_25_0;
    wire const_26_1;
    wire[1:0] const_27_1;
    wire const_28_1;
    wire const_29_0;
    wire[1:0] const_30_1;
    wire const_31_1;
    wire[1:0] const_32_0;
    wire[1:0] const_33_0;
    wire const_34_1;
    wire[1:0] const_35_1;
    wire const_36_1;
    wire const_37_0;
    wire[1:0] const_38_1;
    wire const_39_1;
    wire[1:0] const_40_0;
    wire[1:0] const_41_0;
    wire const_42_1;
    wire[1:0] const_43_1;
    wire const_44_1;
    wire const_45_0;
    wire[1:0] const_46_1;
    wire const_47_1;
    wire[1:0] const_48_0;
    wire[1:0] const_49_0;
    wire const_50_1;
    wire[1:0] const_51_1;
    wire const_52_1;
    wire const_53_0;
    wire[1:0] const_54_1;
    wire const_55_1;
    wire[1:0] const_56_0;
    wire[1:0] const_57_0;
    wire const_58_1;
    wire[1:0] const_59_1;
    wire const_60_1;
    wire const_61_0;
    wire[1:0] const_62_1;
    wire const_63_1;
    wire[1:0] const_64_0;
    wire[1:0] const_65_0;
    wire const_66_1;
    wire[1:0] const_67_1;
    wire const_68_1;
    wire const_69_0;
    wire[1:0] const_70_1;
    wire const_71_1;
    wire[1:0] const_72_0;
    wire[1:0] const_73_0;
    wire const_74_1;
    wire[1:0] const_75_1;
    wire const_76_1;
    wire const_77_0;
    wire[1:0] const_78_1;
    wire const_79_1;
    wire[1:0] const_80_0;
    wire[1:0] const_81_0;
    wire const_82_1;
    wire[1:0] const_83_1;
    wire const_84_1;
    wire const_85_0;
    wire[1:0] const_86_1;
    wire const_87_1;
    wire[1:0] const_88_0;
    wire[1:0] const_89_0;
    wire const_90_1;
    wire[1:0] const_91_1;
    wire const_92_1;
    wire const_93_0;
    wire[1:0] const_94_1;
    wire const_95_1;
    wire const_96_1;
    wire const_97_0;
    wire const_98_0;
    wire const_99_1;
    wire const_100_0;
    wire[1:0] const_101_0;
    wire[1:0] const_102_0;
    wire const_103_1;
    wire[3:0] const_104_9;
    wire[1:0] const_105_0;
    wire const_106_0;
    wire[1:0] const_107_0;
    wire const_108_0;
    wire[2:0] tmp14;
    wire[3:0] tmp15;
    wire[4:0] tmp16;
    wire[3:0] tmp17;
    wire[2:0] tmp18;
    wire[3:0] tmp19;
    wire[4:0] tmp20;
    wire[3:0] tmp21;
    wire[2:0] tmp22;
    wire[3:0] tmp23;
    wire[4:0] tmp24;
    wire[3:0] tmp25;
    wire[2:0] tmp26;
    wire[3:0] tmp27;
    wire[4:0] tmp28;
    wire[3:0] tmp29;
    wire[2:0] tmp30;
    wire[3:0] tmp31;
    wire[4:0] tmp32;
    wire[3:0] tmp33;
    wire[2:0] tmp34;
    wire[3:0] tmp35;
    wire[4:0] tmp36;
    wire[3:0] tmp37;
    wire[2:0] tmp38;
    wire[3:0] tmp39;
    wire[4:0] tmp40;
    wire[3:0] tmp41;
    wire[2:0] tmp42;
    wire[3:0] tmp43;
    wire[4:0] tmp44;
    wire[3:0] tmp45;
    wire[2:0] tmp46;
    wire[3:0] tmp47;
    wire[4:0] tmp48;
    wire[3:0] tmp49;
    wire[2:0] tmp50;
    wire[3:0] tmp51;
    wire[4:0] tmp52;
    wire[3:0] tmp53;
    wire[2:0] tmp54;
    wire[3:0] tmp55;
    wire[4:0] tmp56;
    wire[3:0] tmp57;
    wire[2:0] tmp58;
    wire[3:0] tmp59;
    wire[4:0] tmp60;
    wire[3:0] tmp61;
    wire[4:0] tmp62;
    wire[3:0] tmp63;
    wire[4:0] tmp64;
    wire[5:0] tmp65;
    wire[1:0] tmp66;
    wire[5:0] tmp67;
    wire[6:0] tmp68;
    wire[3:0] tmp69;
    wire[2:0] tmp70;
    wire[3:0] tmp71;
    wire[4:0] tmp72;
    wire[3:0] tmp73;
    wire[3:0] tmp74;
    wire tmp75;
    wire[4:0] tmp76;
    wire[5:0] tmp77;
    wire[3:0] tmp78;
    wire[1:0] tmp79;
    wire[5:0] tmp80;
    wire[6:0] tmp81;
    wire[5:0] tmp82;

    // Combinational
    assign const_0_0 = 0;
    assign const_1_0 = 0;
    assign const_2_1 = 1;
    assign const_3_1 = 1;
    assign const_4_1 = 1;
    assign const_5_0 = 0;
    assign const_6_1 = 1;
    assign const_7_1 = 1;
    assign const_8_0 = 0;
    assign const_9_0 = 0;
    assign const_10_1 = 1;
    assign const_11_1 = 1;
    assign const_12_1 = 1;
    assign const_13_0 = 0;
    assign const_14_1 = 1;
    assign const_15_1 = 1;
    assign const_16_0 = 0;
    assign const_17_0 = 0;
    assign const_18_1 = 1;
    assign const_19_1 = 1;
    assign const_20_1 = 1;
    assign const_21_0 = 0;
    assign const_22_1 = 1;
    assign const_23_1 = 1;
    assign const_24_0 = 0;
    assign const_25_0 = 0;
    assign const_26_1 = 1;
    assign const_27_1 = 1;
    assign const_28_1 = 1;
    assign const_29_0 = 0;
    assign const_30_1 = 1;
    assign const_31_1 = 1;
    assign const_32_0 = 0;
    assign const_33_0 = 0;
    assign const_34_1 = 1;
    assign const_35_1 = 1;
    assign const_36_1 = 1;
    assign const_37_0 = 0;
    assign const_38_1 = 1;
    assign const_39_1 = 1;
    assign const_40_0 = 0;
    assign const_41_0 = 0;
    assign const_42_1 = 1;
    assign const_43_1 = 1;
    assign const_44_1 = 1;
    assign const_45_0 = 0;
    assign const_46_1 = 1;
    assign const_47_1 = 1;
    assign const_48_0 = 0;
    assign const_49_0 = 0;
    assign const_50_1 = 1;
    assign const_51_1 = 1;
    assign const_52_1 = 1;
    assign const_53_0 = 0;
    assign const_54_1 = 1;
    assign const_55_1 = 1;
    assign const_56_0 = 0;
    assign const_57_0 = 0;
    assign const_58_1 = 1;
    assign const_59_1 = 1;
    assign const_60_1 = 1;
    assign const_61_0 = 0;
    assign const_62_1 = 1;
    assign const_63_1 = 1;
    assign const_64_0 = 0;
    assign const_65_0 = 0;
    assign const_66_1 = 1;
    assign const_67_1 = 1;
    assign const_68_1 = 1;
    assign const_69_0 = 0;
    assign const_70_1 = 1;
    assign const_71_1 = 1;
    assign const_72_0 = 0;
    assign const_73_0 = 0;
    assign const_74_1 = 1;
    assign const_75_1 = 1;
    assign const_76_1 = 1;
    assign const_77_0 = 0;
    assign const_78_1 = 1;
    assign const_79_1 = 1;
    assign const_80_0 = 0;
    assign const_81_0 = 0;
    assign const_82_1 = 1;
    assign const_83_1 = 1;
    assign const_84_1 = 1;
    assign const_85_0 = 0;
    assign const_86_1 = 1;
    assign const_87_1 = 1;
    assign const_88_0 = 0;
    assign const_89_0 = 0;
    assign const_90_1 = 1;
    assign const_91_1 = 1;
    assign const_92_1 = 1;
    assign const_93_0 = 0;
    assign const_94_1 = 1;
    assign const_95_1 = 1;
    assign const_96_1 = 1;
    assign const_97_0 = 0;
    assign const_98_0 = 0;
    assign const_99_1 = 1;
    assign const_100_0 = 0;
    assign const_101_0 = 0;
    assign const_102_0 = 0;
    assign const_103_1 = 1;
    assign const_104_9 = 9;
    assign const_105_0 = 0;
    assign const_106_0 = 0;
    assign const_107_0 = 0;
    assign const_108_0 = 0;
    assign o = tmp82;
    assign tmp14 = {const_5_0, const_5_0, const_5_0};
    assign tmp15 = {tmp14, const_4_1};
    assign tmp16 = tmp0 + tmp15;
    assign tmp17 = {tmp16[3], tmp16[2], tmp16[1], tmp16[0]};
    assign tmp18 = {const_13_0, const_13_0, const_13_0};
    assign tmp19 = {tmp18, const_12_1};
    assign tmp20 = tmp0 + tmp19;
    assign tmp21 = {tmp20[3], tmp20[2], tmp20[1], tmp20[0]};
    assign tmp22 = {const_21_0, const_21_0, const_21_0};
    assign tmp23 = {tmp22, const_20_1};
    assign tmp24 = tmp0 + tmp23;
    assign tmp25 = {tmp24[3], tmp24[2], tmp24[1], tmp24[0]};
    assign tmp26 = {const_29_0, const_29_0, const_29_0};
    assign tmp27 = {tmp26, const_28_1};
    assign tmp28 = tmp0 + tmp27;
    assign tmp29 = {tmp28[3], tmp28[2], tmp28[1], tmp28[0]};
    assign tmp30 = {const_37_0, const_37_0, const_37_0};
    assign tmp31 = {tmp30, const_36_1};
    assign tmp32 = tmp0 + tmp31;
    assign tmp33 = {tmp32[3], tmp32[2], tmp32[1], tmp32[0]};
    assign tmp34 = {const_45_0, const_45_0, const_45_0};
    assign tmp35 = {tmp34, const_44_1};
    assign tmp36 = tmp0 + tmp35;
    assign tmp37 = {tmp36[3], tmp36[2], tmp36[1], tmp36[0]};
    assign tmp38 = {const_53_0, const_53_0, const_53_0};
    assign tmp39 = {tmp38, const_52_1};
    assign tmp40 = tmp0 + tmp39;
    assign tmp41 = {tmp40[3], tmp40[2], tmp40[1], tmp40[0]};
    assign tmp42 = {const_61_0, const_61_0, const_61_0};
    assign tmp43 = {tmp42, const_60_1};
    assign tmp44 = tmp0 + tmp43;
    assign tmp45 = {tmp44[3], tmp44[2], tmp44[1], tmp44[0]};
    assign tmp46 = {const_69_0, const_69_0, const_69_0};
    assign tmp47 = {tmp46, const_68_1};
    assign tmp48 = tmp0 + tmp47;
    assign tmp49 = {tmp48[3], tmp48[2], tmp48[1], tmp48[0]};
    assign tmp50 = {const_77_0, const_77_0, const_77_0};
    assign tmp51 = {tmp50, const_76_1};
    assign tmp52 = tmp0 + tmp51;
    assign tmp53 = {tmp52[3], tmp52[2], tmp52[1], tmp52[0]};
    assign tmp54 = {const_85_0, const_85_0, const_85_0};
    assign tmp55 = {tmp54, const_84_1};
    assign tmp56 = tmp0 + tmp55;
    assign tmp57 = {tmp56[3], tmp56[2], tmp56[1], tmp56[0]};
    assign tmp58 = {const_93_0, const_93_0, const_93_0};
    assign tmp59 = {tmp58, const_92_1};
    assign tmp60 = tmp0 + tmp59;
    assign tmp61 = {tmp60[3], tmp60[2], tmp60[1], tmp60[0]};
    assign tmp62 = a + tmp0;
    assign tmp63 = {const_97_0, const_97_0, const_97_0, const_97_0};
    assign tmp64 = {tmp63, const_96_1};
    assign tmp65 = tmp62 + tmp64;
    assign tmp66 = {const_98_0, const_98_0};
    assign tmp67 = {tmp66, tmp1};
    assign tmp68 = tmp65 - tmp67;
    assign tmp69 = {tmp68[3], tmp68[2], tmp68[1], tmp68[0]};
    assign tmp70 = {const_100_0, const_100_0, const_100_0};
    assign tmp71 = {tmp70, const_99_1};
    assign tmp72 = a - tmp71;
    assign tmp73 = {tmp72[3], tmp72[2], tmp72[1], tmp72[0]};
    assign tmp75 = {const_106_0};
    assign tmp76 = {tmp75, tmp74};
    assign tmp77 = tmp62 + tmp76;
    assign tmp79 = {const_108_0, const_108_0};
    assign tmp80 = {tmp79, tmp78};
    assign tmp81 = tmp77 + tmp80;
    assign tmp82 = {tmp81[5], tmp81[4], tmp81[3], tmp81[2], tmp81[1], tmp81[0]};

    // Registers
    always @( posedge clk )
    begin
        tmp0 <= tmp69;
        tmp1 <= tmp73;
    end

    // Memory mem_0: z
    always @( posedge clk )
    begin
        if (const_103_1) begin
                mem_0[const_102_0] <= const_104_9;
        end
    end

    // Memory mem_1: tmp2
    always @( posedge clk )
    begin
        if (const_2_1) begin
                mem_1[const_1_0] <= a;
        end
        if (const_7_1) begin
                mem_1[const_6_1] <= tmp17;
        end
    end
    assign tmp74 = mem_1[const_105_0];

    // Memory mem_2: tmp3
    always @( posedge clk )
    begin
        if (const_10_1) begin
                mem_2[const_9_0] <= a;
        end
        if (const_15_1) begin
                mem_2[const_14_1] <= tmp21;
        end
    end
    assign tmp78 = mem_2[const_107_0];

    // Memory mem_3: tmp4
    always @( posedge clk )
    begin
        if (const_18_1) begin
                mem_3[const_17_0] <= a;
        end
        if (const_23_1) begin
                mem_3[const_22_1] <= tmp25;
        end
    end

    // Memory mem_4: tmp5
    always @( posedge clk )
    begin
        if (const_26_1) begin
                mem_4[const_25_0] <= a;
        end
        if (const_31_1) begin
                mem_4[const_30_1] <= tmp29;
        end
    end

    // Memory mem_5: tmp6
    always @( posedge clk )
    begin
        if (const_34_1) begin
                mem_5[const_33_0] <= a;
        end
        if (const_39_1) begin
                mem_5[const_38_1] <= tmp33;
        end
    end

    // Memory mem_6: tmp7
    always @( posedge clk )
    begin
        if (const_42_1) begin
                mem_6[const_41_0] <= a;
        end
        if (const_47_1) begin
                mem_6[const_46_1] <= tmp37;
        end
    end

    // Memory mem_7: tmp8
    always @( posedge clk )
    begin
        if (const_50_1) begin
                mem_7[const_49_0] <= a;
        end
        if (const_55_1) begin
                mem_7[const_54_1] <= tmp41;
        end
    end

    // Memory mem_8: tmp9
    always @( posedge clk )
    begin
        if (const_58_1) begin
                mem_8[const_57_0] <= a;
        end
        if (const_63_1) begin
                mem_8[const_62_1] <= tmp45;
        end
    end

    // Memory mem_9: tmp10
    always @( posedge clk )
    begin
        if (const_66_1) begin
                mem_9[const_65_0] <= a;
        end
        if (const_71_1) begin
                mem_9[const_70_1] <= tmp49;
        end
    end

    // Memory mem_10: tmp11
    always @( posedge clk )
    begin
        if (const_74_1) begin
                mem_10[const_73_0] <= a;
        end
        if (const_79_1) begin
                mem_10[const_78_1] <= tmp53;
        end
    end

    // Memory mem_11: tmp12
    always @( posedge clk )
    begin
        if (const_82_1) begin
                mem_11[const_81_0] <= a;
        end
        if (const_87_1) begin
                mem_11[const_86_1] <= tmp57;
        end
    end

    // Memory mem_12: tmp13
    always @( posedge clk )
    begin
        if (const_90_1) begin
                mem_12[const_89_0] <= a;
        end
        if (const_95_1) begin
                mem_12[const_94_1] <= tmp61;
        end
    end

endmodule

"""


class TestOutputTestbench(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_verilog_testbench_does_not_throw_error(self):
        zero = pyrtl.Input(1, 'zero')
        counter_output = pyrtl.Output(3, 'counter_output')
        counter = pyrtl.Register(3, 'counter')
        counter.next <<= pyrtl.mux(zero, counter + 1, 0)
        counter_output <<= counter
        sim_trace = pyrtl.SimulationTrace([counter_output, zero])
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(15):
            sim.step({zero: random.choice([0, 0, 0, 1])})
        with io.StringIO() as tbfile:
            pyrtl.output_verilog_testbench(tbfile, sim_trace)


class TestVerilogNames(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.vnames = verilog._VerilogSanitizer("_sani_test")

    def checkname(self, name):
        self.assertEqual(self.vnames.make_valid_string(name), name)

    def assert_invalid_name(self, name):
        self.assertNotEqual(self.vnames.make_valid_string(name), name)

    def test_verilog_check_valid_name_good(self):
        self.checkname('abc')
        self.checkname('a')
        self.checkname('BC')
        self.checkname('Kabc')
        self.checkname('B_ac')
        self.checkname('_asdvqa')
        self.checkname('_Bs_')
        self.checkname('fd$oeoe')
        self.checkname('_B$$s')
        self.checkname('B')

    def test_verilog_check_valid_name_bad(self):
        self.assert_invalid_name('carne asda')
        self.assert_invalid_name('')
        self.assert_invalid_name('asd%kask')
        self.assert_invalid_name("flipin'")
        self.assert_invalid_name(' jklol')
        self.assert_invalid_name('a' * 2000)


class TestVerilog(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        # To compare textual consistency, need to make
        # sure we're starting at the same index for all
        # automatically created names.
        pyrtl.wire._reset_wire_indexers()
        pyrtl.memory._reset_memory_indexer()

    def test_romblock_does_not_throw_error(self):
        from pyrtl.corecircuits import _basic_add
        a = pyrtl.Input(bitwidth=3, name='a')
        b = pyrtl.Input(bitwidth=3, name='b')
        o = pyrtl.Output(bitwidth=3, name='o')
        res = _basic_add(a, b)
        rdat = {0: 1, 1: 2, 2: 5, 5: 0}
        mixtable = pyrtl.RomBlock(addrwidth=3, bitwidth=3, pad_with_zeros=True, romdata=rdat)
        o <<= mixtable[res[:-1]]
        with io.StringIO() as testbuffer:
            pyrtl.output_to_verilog(testbuffer)

    def test_textual_consistency_small(self):
        i = pyrtl.Const(0b1100)
        j = pyrtl.Const(0b011, bitwidth=3)
        k = pyrtl.Const(0b100110, name='k')
        o = pyrtl.Output(13, 'o')
        o <<= pyrtl.concat(i, j, k)

        buffer = io.StringIO()
        pyrtl.output_to_verilog(buffer)

        self.assertEqual(buffer.getvalue(), verilog_output_small)

    def test_textual_consistency_large(self):
        # The following is a non-sensical program created to test
        # that the Verilog that is created is deterministic
        # in the order in which it presents the wire, register,
        # and memory declarations and the combinational and
        # sequential logic. Hence it creates many memories, and
        # makes sure at least two lines of code are created in
        # the always @ blocks associated with them (so we have
        # many different wire names to deal with and test against).
        a = pyrtl.Input(4, 'a')
        r = pyrtl.Register(4)
        s = pyrtl.Register(4)
        # This will have mem id 0, so prints first despite actual name
        mt = pyrtl.MemBlock(4, 2, name='z')
        m = [pyrtl.MemBlock(4, 2, max_write_ports=2) for _ in range(12)]
        for mem in m:
            mem[0] <<= a
            mem[1] <<= (r + 1).truncate(4)
        b = a + r
        r.next <<= b + 1 - s
        s.next <<= a - 1
        mt[0] <<= 9
        o = pyrtl.Output(6, 'o')
        o <<= b + m[0][0] + m[1][0]

        buffer = io.StringIO()
        pyrtl.output_to_verilog(buffer)

        self.assertEqual(buffer.getvalue(), verilog_output_large)


if __name__ == "__main__":
    unittest.main()
