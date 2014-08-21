import sys
sys.path.append("..")  # needed only if not installed
import pyrtl
from pyrtl import Const, Register, concat


def one_bit_add(a, b, cin):
    """ Generates hardware for a 1-bit full adder. """
    assert len(a) == len(b) == len(cin) == 1
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum, cout


def add(a, b, cin=Const(0)):
    """ Recursively generates hardware for ripple carry adder. """
    assert len(a) == len(b)
    if len(a) == 1:
        sumbits, cout = one_bit_add(a, b, cin)
    else:
        lsbit, ripplecarry = one_bit_add(a[0], b[0], cin)
        msbits, cout = add(a[1:], b[1:], ripplecarry)
        sumbits = concat(msbits, lsbit)
    return sumbits, cout


counter = Register(bitwidth=3, name='counter')
sum, cout = add(counter, Const("3'b001"))
counter.next <<= sum

# Actually simulate the adder here
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for i in xrange(15):
    sim.step({})
sim_trace.render_trace()
