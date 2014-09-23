import sys
sys.path.append("..")  # needed only if not installed
import random
import pyrtl
from pyrtl import Input, Output, WireVector, Const, Register, concat


a, b, c = Input(1, 'a'), Input(1, 'b'), Input(1, 'c')
sum, cout = Output(1, 'sum'), Output(1, 'cout')

sum <<= a ^ b ^ c
cout <<= a & b | a & c | b & c


# output the hardware as verilog
pyrtl.output_to_verilog(sys.stdout)

# now simulate the logic with some random inputs
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for i in xrange(15):
    # here we actually generate random booleans for the inputs
    sim.step({
        a: random.choice([0, 1]),
        b: random.choice([0, 1]),
        c: random.choice([0, 1])
        })
sim_trace.render_trace(symbol_len=5, segment_size=5)
