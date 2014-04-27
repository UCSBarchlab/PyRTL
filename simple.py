#----------------------------------------------------------
import random
import pyrtl.pyrtl as rtl
from pyrtl.export import *
from pyrtl.simulation import *

def one_bit_add(a,b,cin):
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum,cout

# set up inputs and outputs to the block
a = rtl.Input(1,'a')
b = rtl.Input(1,'b')
c = rtl.Input(1,'c')
out_sum = rtl.Output(1,'sum')
out_cout = rtl.Output(1,'cout')
y = rtl.Output(3,'y')

x = rtl.Const(0x3,3)
x1 = rtl.WireVector(1,'x1')
x2 = rtl.WireVector(1,'x2')
x3 = rtl.WireVector(1,'x3')
sum,cout = one_bit_add(a,b,c)

# the <<= operator lets you do assignment
# to nets that already exist (like outputs)
out_sum <<= sum
out_cout <<= cout
x1 <<= x[0]
x2 <<= x[1]
x3 <<= x[2]
y <<= rtl.concat(x3,x2,x1)

#-----------------------------------------------------

sim_trace = SimulationTrace()
on_reset = {}
sim = Simulation( register_value_map=on_reset, default_value=0, tracer=sim_trace )

# each input (a,b,c) is given a random value (0,1) each cycle
for i in xrange(15):  
    sim.step( {a:random.choice([0,1]), b:random.choice([0,1]), c:random.choice([0,1])} )

sim_trace.render_trace(symbol_len=5, segment_size=5)
