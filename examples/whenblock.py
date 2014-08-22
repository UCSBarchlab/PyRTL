import sys
sys.path.append("..")  # needed only if not installed
import random
from pyrtl import *

a, b, c, d = [Input(1, signame) for signame in 'abcd']

r = Register(1, 'r')
r2 = Register(3, 'r2')

# Example of how to use ConditionalUpdate to set
# registers only when the conditions are true.  
condition = ConditionalUpdate()
with condition(a):
    r.next <<= 1  # when a is true
    with condition(d):
        r2.next <<= 2  # when a and d are true
    with condition():
        r2.next <<= 3  # when a is true and d is false
with condition(b & c):
    r.next <<= 0  # when a is not true and b & c is true


# print working_block()
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    # here we actually generate random booleans for the inputs
    sim.step({
             a: random.choice([0, 0, 1]),
             b: random.choice([0, 0, 1]),
             c: random.choice([0, 1]),
             d: random.choice([0, 1]),
             })
sim_trace.render_trace(symbol_len=5, segment_size=5)
