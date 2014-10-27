import unittest
import random
import pyrtl
import StringIO
import os
import subprocess

from helperfunctions import *

class TestRTLSimulationTraceWithBasicOperations(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.r = pyrtl.Register(bitwidth=self.bitwidth, name='r')
    
    def tearDown(self):
        pass

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation( tracer=sim_trace )
        for i in xrange(8):
            sim.step( {} )
        output = StringIO.StringIO()
        sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), correct_string)
        
    def test_not_simulation(self):
        self.r.next <<= ~ self.r
        self.check_trace('r 07070707\n')

    def test_and_simulation(self):
        self.r.next <<= (~ self.r) & pyrtl.Const(6,bitwidth=self.bitwidth)
        self.check_trace('r 06060606\n')

    def test_or_simulation(self):
        self.r.next <<= self.r | pyrtl.Const(4,bitwidth=self.bitwidth)
        self.check_trace('r 04444444\n')

    def test_xor_simulation(self):
        self.r.next <<= self.r ^ pyrtl.Const(4,bitwidth=self.bitwidth)
        self.check_trace('r 04040404\n')

    def test_plus_simulation(self):
        self.r.next <<= self.r + pyrtl.Const(2,bitwidth=self.bitwidth)
        self.check_trace('r 02460246\n')

    def test_minus_simulation(self):
        self.r.next <<= self.r - pyrtl.Const(1,bitwidth=self.bitwidth)
        self.check_trace('r 07654321\n')

    def test_multiply_simulation(self):
        self.r.next <<= self.r * pyrtl.Const(2,bitwidth=self.bitwidth) + pyrtl.Const(1,bitwidth=self.bitwidth)
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


class TestRTLSimulationTraceWithAdder(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
        bitwidth = 3
        self.r = pyrtl.Register(bitwidth=bitwidth, name='r')
        self.sum, self.cout = generate_full_adder(self.r, pyrtl.Const(1).zero_extended(bitwidth) )
        self.r.next <<= self.sum
    
    def tearDown(self):
        pass
        
    def test_adder_simulation(self):
        sim_trace = pyrtl.SimulationTrace()
        on_reset = {} # signal states to be set when reset is asserted
        # build the actual simulation environment
        sim = pyrtl.Simulation( register_value_map=on_reset, default_value=0, tracer=sim_trace )

        # step through 15 cycles
        for i in xrange(15):  
            sim.step( {} )

        output = StringIO.StringIO()
        sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), 'r 012345670123456\n')

class TestRTLSimulationTraceVCDWithAdder(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
        bitwidth = 3
        self.r = pyrtl.Register(bitwidth=bitwidth, name='r')
        self.sum, self.cout = generate_full_adder(self.r, pyrtl.Const(1).zero_extended(bitwidth) )
        self.r.next <<= self.sum
    
    def tearDown(self):
        pass
        
    def test_adder_simulation(self):
        sim_trace = pyrtl.SimulationTrace()
        on_reset = {} # signal states to be set when reset is asserted
        # build the actual simulation environment
        sim = pyrtl.Simulation( register_value_map=on_reset, default_value=0, tracer=sim_trace )

        # step through 15 cycles
        for i in xrange(15):  
            sim.step( {} )
            
        current_dir = os.path.dirname(os.path.realpath(__file__))
        # generate output from this test case
        with open(os.path.join(current_dir, "TestRTLSimulationTraceVCDWithAdder_1.vcd"), "w") as fd:
            sim_trace.print_vcd(fd)
        
        # TODO: Remove this Java!
        #with open(os.path.join(current_dir, "TestRTLSimulationTraceVCDWithAdder_comparevcd_log.txt"), "w") as fd:
        #    compare_result = subprocess.call(["java", "-jar", os.path.join(current_dir, "comparevcd.jar"), 
        #        os.path.join(current_dir, "TestRTLSimulationTraceVCDWithAdder.vcd"), 
        #        os.path.join(current_dir, "TestRTLSimulationTraceVCDWithAdder_1.vcd")], stdout=fd)
        #self.assertEqual(compare_result, 0)

        # generate initial vcd output
        #with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"TestRTLSimulationTraceWithAdder.vcd"), "w") as fd:
        #    sim_trace.print_vcd(fd)

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
        self.sim = pyrtl.Simulation( tracer=self.sim_trace )
        
    def tearDown(self):
        pass
        
    def test_adder_simulation(self):
        input_signals = {}
        input_signals[0] = {self.a:0, self.b:1, self.sel:1}
        input_signals[1] = {self.a:0, self.b:2, self.sel:1}
        input_signals[2] = {self.a:0, self.b:0, self.sel:1}
        input_signals[3] = {self.a:1, self.b:1, self.sel:0}
        input_signals[4] = {self.a:2, self.b:1, self.sel:0}
        input_signals[5] = {self.a:0, self.b:1, self.sel:0}
        for i in xrange(6):  
            self.sim.step( input_signals[i] )

        output = StringIO.StringIO()
        self.sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), 'muxout 120120\n')

class TestRTLMemBlockSimulation(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.addrwidth = 4
        self.output1 = pyrtl.Output(self.bitwidth,"o1")
        self.output2 = pyrtl.Output(self.bitwidth,"o2")
        self.read_addr1 = pyrtl.Input(self.addrwidth)
        self.read_addr2 = pyrtl.Input(self.addrwidth)
        self.write_addr = pyrtl.Input(self.addrwidth)
        self.write_data = pyrtl.Input(self.bitwidth)
        self.memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth, name='memory')
        self.output1 <<= self.memory[self.read_addr1]
        self.output2 <<= self.memory[self.read_addr2]
        self.memory[self.write_addr] = self.write_data

        # build the actual simulation environment
        self.sim_trace = pyrtl.SimulationTrace()
        self.sim = pyrtl.Simulation( tracer=self.sim_trace )

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_simple_memblock(self):
        input_signals = {}
        input_signals[0] = {self.read_addr1:0, self.read_addr2:1, self.write_addr:4, self.write_data:5}
        input_signals[1] = {self.read_addr1:4, self.read_addr2:1, self.write_addr:0, self.write_data:5}
        input_signals[2] = {self.read_addr1:0, self.read_addr2:4, self.write_addr:1, self.write_data:6}
        input_signals[3] = {self.read_addr1:1, self.read_addr2:1, self.write_addr:0, self.write_data:0}
        input_signals[4] = {self.read_addr1:6, self.read_addr2:0, self.write_addr:6, self.write_data:7}
        for i in xrange(5):  
            self.sim.step( input_signals[i] )

        output = StringIO.StringIO()
        self.sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), 'o1 05567\no2 00560\n')


if __name__ == '__main__':
  unittest.main()






