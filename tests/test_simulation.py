import unittest
import io

from .helperfunctions import *


class TestRTLSimulationTraceWithBasicOperations(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.r = pyrtl.Register(bitwidth=self.bitwidth, name='r')

    def tearDown(self):
        pass

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), correct_string)

    def test_not_simulation(self):
        self.r.next <<= ~ self.r
        self.check_trace('r 07070707\n')

    def test_and_simulation(self):
        self.r.next <<= (~ self.r) & pyrtl.Const(6, bitwidth=self.bitwidth)
        self.check_trace('r 06060606\n')

    def test_nand_simulation(self):
        self.r.next <<= self.r.nand(pyrtl.Const(6, bitwidth=self.bitwidth))
        self.check_trace('r 07171717\n')

    def test_or_simulation(self):
        result = self.r | pyrtl.Const(4, bitwidth=self.bitwidth)
        self.r.next <<= result
        self.assertEqual(len(result), self.bitwidth)
        self.check_trace('r 04444444\n')

    def test_xor_simulation(self):
        self.r.next <<= self.r ^ pyrtl.Const(4, bitwidth=self.bitwidth)
        self.check_trace('r 04040404\n')

    def test_plus_simulation(self):
        self.r.next <<= self.r + pyrtl.Const(2, bitwidth=self.bitwidth)
        self.check_trace('r 02460246\n')

    def test_minus_simulation(self):
        self.r.next <<= self.r - pyrtl.Const(1, bitwidth=self.bitwidth)
        self.check_trace('r 07654321\n')

    def test_multiply_simulation(self):
        self.r.next <<= self.r * pyrtl.Const(2, bitwidth=self.bitwidth) + \
            pyrtl.Const(1, bitwidth=self.bitwidth)
        self.check_trace('r 01377777\n')

    def test_const_nobitwidth_simulation(self):
        self.r.next <<= self.r - pyrtl.Const(1)
        self.check_trace('r 07654321\n')

    def test_const_rawint_simulation(self):
        self.r.next <<= self.r - 1
        self.check_trace('r 07654321\n')

    def test_const_verilogsmall_simulation(self):
        self.r.next <<= self.r - "1'b1"
        self.check_trace('r 07654321\n')

    def test_const_verilogbig_simulation(self):
        self.r.next <<= self.r - "3'b1"
        self.check_trace('r 07654321\n')

    def test_const_veriloghuge_simulation(self):
        self.r.next <<= self.r - "64'b1"
        self.check_trace('r 07654321\n')

    def test_const_veriloghuge2_simulation(self):
        self.r.next <<= self.r + "64'b1"
        self.check_trace('r 01234567\n')

    def test_const_associativity_string_simulation(self):
        self.r.next <<= "64'b1" + self.r
        self.check_trace('r 01234567\n')

    def test_const_associativity_int_simulation(self):
        self.r.next <<= 1 + self.r
        self.check_trace('r 01234567\n')

    def test_bitslice_and_concat_simulation(self):
        left = self.r[0:-1]
        right = pyrtl.Const(1, bitwidth=1)
        self.r.next <<= pyrtl.concat(left, right)
        self.check_trace('r 01377777\n')

    def test_bitslice2_and_concat_simulation(self):
        left = self.r[:-1]
        right = pyrtl.Const(1, bitwidth=1)
        self.r.next <<= pyrtl.concat(left, right)
        self.check_trace('r 01377777\n')

    def test_reg_to_reg_simulation(self):
        self.r2 = pyrtl.Register(bitwidth=self.bitwidth, name='r2')
        self.r.next <<= self.r2
        self.r2.next <<= self.r + pyrtl.Const(2, bitwidth=self.bitwidth)
        self.check_trace(' r 00224466\nr2 02244660\n')


class TestRTLSimulationInputValidation(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_input_out_of_bitwidth(self):
        counter = pyrtl.Register(bitwidth=3, name='counter')
        i = pyrtl.Input(bitwidth=2, name='i')
        counter.next <<= counter + i

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(4):
            sim.step({i: cycle})
        with self.assertRaises(pyrtl.PyrtlError):
            sim.step({i: 5})


class TestRTLSimulationTraceWithAdder(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        bitwidth = 3
        self.r = pyrtl.Register(bitwidth=bitwidth, name='r')
        self.sum, self.cout = generate_full_adder(self.r, pyrtl.Const(1).zero_extended(bitwidth))
        self.r.next <<= self.sum

    def tearDown(self):
        pass

    def test_adder_simulation(self):
        sim_trace = pyrtl.SimulationTrace()
        on_reset = {}  # signal states to be set when reset is asserted
        # build the actual simulation environment
        sim = pyrtl.Simulation(register_value_map=on_reset, default_value=0, tracer=sim_trace)

        # step through 15 cycles
        for i in range(15):
            sim.step({})

        output = io.StringIO()
        sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), 'r 012345670123456\n')


VCD_OUTPUT = """$timescale 1ns $end
$scope module logic $end
$var wire 3 r r $end
$upscope $end
$enddefinitions $end
$dumpvars
b0 r
$end
#0
b0 r
#1
b1 r
#2
b10 r
#3
b11 r
#4
b100 r
#5
b101 r
#6
b110 r
#7
b111 r
#8
b0 r
#9
b1 r
#10
b10 r
#11
b11 r
#12
b100 r
#13
b101 r
#14
b110 r
#15
"""


class TestRTLSimulationTraceVCDWithAdder(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        bitwidth = 3
        self.r = pyrtl.Register(bitwidth=bitwidth, name='r')
        self.sum, self.cout = generate_full_adder(self.r, pyrtl.Const(1).zero_extended(bitwidth))
        self.r.next <<= self.sum

    def tearDown(self):
        pass

    def test_vcd_output(self):
        sim_trace = pyrtl.SimulationTrace()
        on_reset = {}  # signal states to be set when reset is asserted
        # build the actual simulation environment
        sim = pyrtl.Simulation(register_value_map=on_reset, default_value=0, tracer=sim_trace)

        # step through 15 cycles
        for i in range(15):
            sim.step({})

        test_output = io.StringIO()
        sim_trace.print_vcd(test_output)
        self.assertEqual(VCD_OUTPUT, test_output.getvalue())


class TestRTLSimulationTraceWithMux(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        bitwidth = 3
        self.a = pyrtl.Input(bitwidth=bitwidth)
        self.b = pyrtl.Input(bitwidth=bitwidth)
        self.sel = pyrtl.Input(bitwidth=1)
        self.muxout = pyrtl.Output(bitwidth=bitwidth, name='muxout')
        self.muxout <<= generate_full_mux(self.a, self.b, self.sel)

        # build the actual simulation environment
        self.sim_trace = pyrtl.SimulationTrace()
        self.sim = pyrtl.Simulation(tracer=self.sim_trace)

    def tearDown(self):
        pass

    def test_adder_simulation(self):
        input_signals = {0: {self.a: 0, self.b: 1, self.sel: 1},
                         1: {self.a: 0, self.b: 2, self.sel: 1},
                         2: {self.a: 0, self.b: 0, self.sel: 1},
                         3: {self.a: 1, self.b: 1, self.sel: 0},
                         4: {self.a: 2, self.b: 1, self.sel: 0},
                         5: {self.a: 0, self.b: 1, self.sel: 0}}
        for i in range(6):
            self.sim.step(input_signals[i])

        output = io.StringIO()
        self.sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), 'muxout 120120\n')


class TestRTLMemBlockSimulation(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.addrwidth = 4
        self.output1 = pyrtl.Output(self.bitwidth, "o1")
        self.output2 = pyrtl.Output(self.bitwidth, "o2")
        self.read_addr1 = pyrtl.Input(self.addrwidth)
        self.read_addr2 = pyrtl.Input(self.addrwidth)
        self.write_addr = pyrtl.Input(self.addrwidth)
        self.write_data = pyrtl.Input(self.bitwidth)
        self.rom = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                                  name='rom')
        self.output1 <<= self.rom[self.read_addr1]
        self.output2 <<= self.rom[self.read_addr2]
        self.rom[self.write_addr] <<= self.write_data

        # build the actual simulation environment
        self.sim_trace = pyrtl.SimulationTrace()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_simple_memblock(self):
        self.sim = pyrtl.Simulation(tracer=self.sim_trace)

        input_signals = [[0, 1, 4, 5],
                         [4, 1, 0, 5],
                         [0, 4, 1, 6],
                         [1, 1, 0, 0],
                         [6, 0, 6, 7]]
        for signals in input_signals:
            self.sim.step({self.read_addr1: signals[0], self.read_addr2: signals[1],
                           self.write_addr: signals[2], self.write_data: signals[3]})

        output = io.StringIO()
        self.sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), 'o1 05560\no2 00560\n')

    def test_simple2_memblock(self):
        self.sim = pyrtl.Simulation(tracer=self.sim_trace)
        input_signals = [
            {self.read_addr1: 0, self.read_addr2: 1, self.write_addr: 0, self.write_data: 0x7},
            {self.read_addr1: 1, self.read_addr2: 2, self.write_addr: 1, self.write_data: 0x6},
            {self.read_addr1: 0, self.read_addr2: 0, self.write_addr: 2, self.write_data: 0x5},
            {self.read_addr1: 0, self.read_addr2: 1, self.write_addr: 0, self.write_data: 0x4},
            {self.read_addr1: 1, self.read_addr2: 0, self.write_addr: 1, self.write_data: 0x3},
            {self.read_addr1: 2, self.read_addr2: 2, self.write_addr: 2, self.write_data: 0x2},
            {self.read_addr1: 1, self.read_addr2: 2, self.write_addr: 0, self.write_data: 0x1},
            {self.read_addr1: 0, self.read_addr2: 1, self.write_addr: 1, self.write_data: 0x0},
            {self.read_addr1: 1, self.read_addr2: 0, self.write_addr: 2, self.write_data: 0x7},
            {self.read_addr1: 2, self.read_addr2: 1, self.write_addr: 0, self.write_data: 0x6}]

        for signal in input_signals:
            self.sim.step(signal)

        output = io.StringIO()
        self.sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), 'o1 0077653107\no2 0076452310\n')

    def test_synth_simple_memblock(self):
        pyrtl.synthesize()
        pyrtl.optimize()
        self.sim_trace = pyrtl.SimulationTrace()
        self.sim = pyrtl.Simulation(tracer=self.sim_trace)
        input_signals = [[0, 1, 4, 5],
                         [4, 1, 0, 5],
                         [0, 4, 1, 6],
                         [1, 1, 0, 0],
                         [6, 0, 6, 7]]
        for signals in input_signals:
            self.sim.step({self.read_addr1: signals[0], self.read_addr2: signals[1],
                           self.write_addr: signals[2], self.write_data: signals[3]})

        output = io.StringIO()
        self.sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), 'o1 05560\no2 00560\n')


class TestRTLRomBlockSimulation(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def generate_expected_output(self, data_tuples, length):
        """dataTuple is in a series of tuples in  (name, function) format
            the function takes in a single argument, length
           length is the number of steps in the length """

        out_string = ""
        for tuple in data_tuples:
            out_string = out_string + tuple[0] + " "
            for time in range(0, length - 1):
                out_string += str(tuple[1](time))
            out_string += '\n'
        return out_string

    def compareIO(self, sim_trace_a, expected_output):
        output = io.StringIO()
        sim_trace_a.print_trace(output)
        self.assertEqual(output.getvalue(), expected_output)

    def test_function_RomBlock(self):

        def rom_data_function(add):
            return int((add + 5)/2)

        pyrtl.reset_working_block()
        self.bitwidth = 4
        self.addrwidth = 4
        self.output1 = pyrtl.Output(self.bitwidth, "o1")
        self.output2 = pyrtl.Output(self.bitwidth, "o2")
        self.read_addr1 = pyrtl.Input(self.addrwidth)
        self.read_addr2 = pyrtl.Input(self.addrwidth)
        self.rom = pyrtl.RomBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                                  name='rom', romdata=rom_data_function)
        self.output1 <<= self.rom[self.read_addr1]
        self.output2 <<= self.rom[self.read_addr2]
        # build the actual simulation environment
        self.sim_trace = pyrtl.SimulationTrace()
        self.sim = pyrtl.Simulation(tracer=self.sim_trace)

        input_signals = {}
        for i in range(0, 5):
            input_signals[i] = {self.read_addr1: i, self.read_addr2: 2*i}
            self.sim.step(input_signals[i])

        exp_out = self.generate_expected_output((("o1", lambda x: rom_data_function(x)),
                                                ("o2", lambda x: rom_data_function(2*x))), 6)
        self.compareIO(self.sim_trace, exp_out)

    def test_function_RomBlock_with_optimization(self):

        def rom_data_function(add):
            return int((add + 5)/2)

        pyrtl.reset_working_block()
        self.bitwidth = 4
        self.addrwidth = 4
        self.output1 = pyrtl.Output(self.bitwidth, "o1")
        self.output2 = pyrtl.Output(self.bitwidth, "o2")
        # self.output3 = pyrtl.Output(self.bitwidth, "o3")
        # self.read_out = pyrtl.WireVector(self.bitwidth)
        self.read_addr1 = pyrtl.Input(self.addrwidth)
        self.read_addr2 = pyrtl.Input(self.addrwidth)
        self.rom = pyrtl.RomBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                                  name='rom', romdata=rom_data_function)
        # self.read_out <<= self.rom[self.read_addr1]
        # self.output1 <<= self.read_out - 1
        self.output1 <<= self.rom[self.read_addr1]
        self.output2 <<= self.rom[self.read_addr2]

        pyrtl.synthesize()
        pyrtl.optimize()
        # build the actual simulation environment
        self.sim_trace = pyrtl.SimulationTrace()
        self.sim = pyrtl.Simulation(tracer=self.sim_trace)

        input_signals = {}
        for i in range(0, 5):
            input_signals[i] = {self.read_addr1: i, self.read_addr2: 2*i}
            input_signals[i] = {self.read_addr1: i, self.read_addr2: 2*i}
            self.sim.step(input_signals[i])

        # exp_out = self.generate_expected_output((("o1", lambda x: rom_data_function(x) - 1),
        exp_out = self.generate_expected_output((("o1", lambda x: rom_data_function(x)),
                                                 ("o2", lambda x: rom_data_function(2*x))), 6)
        self.compareIO(self.sim_trace, exp_out)

    def test_rom_error(self):
        rom_data_array = [15, 13, 11, 9, 7, 5, 3, 1]
        rom1 = pyrtl.RomBlock(bitwidth=4, addrwidth=3, romdata=rom_data_array)
        rom_add_1 = pyrtl.Input(3, "rom_in")
        rom_out_1 = pyrtl.Output(4, "rom_out_1")
        rom_out_1 <<= rom1[rom_add_1]

        with self.assertRaises(pyrtl.PyrtlError):
            simvals = {
                rom_add_1: "392081",
            }
            sim_trace = pyrtl.SimulationTrace()
            sim = pyrtl.Simulation(tracer=sim_trace)
            for cycle in range(len(simvals[rom_add_1])):
                sim.step({k: int(v[cycle]) for k, v in list(simvals.items())})
            sim_trace.render_trace()


if __name__ == '__main__':
    unittest.main()
