import unittest
import random
import pyrtl
import StringIO

from helperfunctions import *

class TestRTLSimulationTraceWithAdder(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
        bitwidth = 3
        self.r = pyrtl.Register(bitwidth=bitwidth, name='r')
        self.r.next, self.cout = generate_full_adder(self.r, pyrtl.Const(1).zero_extended(bitwidth) )
    
    def tearDown(self):
        pass
        
    def test_adder_simulation(self):
        print pyrtl.working_block()
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






