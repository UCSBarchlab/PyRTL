import sys
sys.path.append("..")  # needed only if not installed
import random
from pyrtl import *

a, b, c = [Input(1, signame) for signame in ['a', 'b', 'c']]
x, y = [Output(1, signame) for signame in ['x', 'y']]
r = Register(1, 'r')


u = ConditionalUpdate()
with u.when(a):
    r.next = b
with u.otherwise():
    r.next = c
x <<= r
y <<= r


sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    # here we actually generate random booleans for the inputs
    sim.step({
             a: random.choice([0, 1]),
             b: random.choice([0, 1]),
             c: random.choice([0, 1])
             })
sim_trace.render_trace(symbol_len=5, segment_size=5)
