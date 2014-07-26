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
        self.muxout = generate_full_mux(self.a, self.b, self.sel)
     
    def tearDown(self):
        pass
        
    def test_adder_simulation(self):
        sim_trace = pyrtl.SimulationTrace()
        # build the actual simulation environment
        sim = pyrtl.Simulation( tracer=sim_trace )

        # step through 15 cycles
        input_signals = {}
        input_signals[0] = {self.a:0, self.b:1, self.sel:1}
        for i in xrange(15):  
            sim.step( input_signals[0] )

        output = StringIO.StringIO()
        sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), '\n')

if __name__ == '__main__':
  unittest.main()
