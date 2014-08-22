import sys
sys.path.append("..")  # needed only if not installed
import random
from pyrtl import *

a, b, c = [Input(1, signame) for signame in ['a', 'b', 'c']]
x, y, z, w = [Input(1, signame) for signame in ['x', 'y', 'z', 'w']]
trash = Output(1,'trash')

r = Register(1, 'r')
r2 = Register(1, 'r2')

"""
condition = ConditionalUpdate()
with condition(a):
    x.next <<= ~ x
with condition():
    with condition(b&c):
        y.next <<= ~ y
"""

condition = ConditionalUpdate()
with condition(a):
    # updates with a is true
    r.next <<= ~ r 
    with condition(b):
        # updates when a and b are true
        r2.next <<= y  
with condition(b):
    # updates when a is false and b and c are true
    r.next <<= z  
#    r2.next <<= z 
#with condition(c):
#    # updates when a is false and b and c are true
#    r.next <<= w

#    with condition(b < c):
#        r.next <<= c
#with condition(b):
#    r.next <<= b
#with condition():
#    r.next <<= c

trash <<= a | b | c | x | y | z | w


print working_block()
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    # here we actually generate random booleans for the inputs
    sim.step({
             a: random.choice([0, 1]),
             b: random.choice([0, 1]),
             c: random.choice([0, 1]),
             x: random.choice([0, 1]),
             y: random.choice([0, 1]),
             z: random.choice([0, 1]),
             w: random.choice([0, 1])
             })
sim_trace.render_trace(symbol_len=5, segment_size=5)
