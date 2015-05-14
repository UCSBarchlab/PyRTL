__author__ = 'Deeksha'

# Notes:
# Carry save adds the partial sum to the shift carry 
# partial_sum = a ^ b ^ c
# shift_carry = (a|b) & (a|c) & (b|c)

import sys
sys.path.append("..")
import random
import pyrtl
from pyrtl import *
from rtllib import adders


def main():
    test()

# Perform 1-bit addition first
def one_bit_add(a, b, cin):
    assert len(a) == len(b) == 1
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum, cout


# Implement ripple-carry adder 
def ripple_add(a, b, cin):
    assert len(a) == len(b)
    if len(a) == 1:
        sumbits, cout = one_bit_add(a, b, cin)
    else:
        lsbit, ripplecarry = one_bit_add(a[0], b[0], cin)
        msbits, cout = ripple_add(a[1:], b[1:], ripplecarry)
        sumbits = pyrtl.concat(msbits, lsbit)
    return sumbits, cout


# Implement carry-save design where last stage of addition is done using a ripple-carry adder
def carrysave_adder(a, b, c):
    assert len(a) == len(b)
    partial_sum = a ^ b ^ c
    partial_shift = pyrtl.concat(0, partial_sum)
    shift_carry = (a | b) & (a | c) & (b | c)
    shift_carry_1 = pyrtl.concat(shift_carry, 0)
    sum_1, c_out = ripple_add(partial_shift, shift_carry_1, 0)
    sum = pyrtl.concat(c_out, sum_1)
    return sum


def test():

        pyrtl.reset_working_block()
        a, b, c = pyrtl.Input(32, "a"), pyrtl.Input(32, "b"), pyrtl.Input(32, "c") 
        sum = pyrtl.Output(34, "sum")
        sum <<= carrysave_adder(a, b, c)  

        # x = [int(random.uniform(0, 2**32-1)) for i in range(20)]
        # y = [int(random.uniform(0, 2**32-1)) for i in range(20)]

        x = [3759516320L, 973033565, 4120989505L, 199451263, 3625363122L, 1115190551, 2207055453L, 2946555493L,
             760932817, 1072117699, 3456362420L, 2369715268L, 341973812, 1822482086, 1000917448, 3736696910L,
             1952403941, 766232820, 3355093416L, 3068692689L]
        y = [637240484, 2996140373L, 4171443642L, 500315891, 2908097029L, 3899747324L, 1198363687, 2707178015L,
             1873950916, 1166457082, 321919507, 1480307297, 2704513799L, 1502918399,
             895718745, 1215430802, 3917621196L, 3157183468L, 14334859, 1254750152]
        z = [637240484, 2996140373L, 4171443642L, 500315891, 2908097029L, 3899747324L, 1198363687, 2707178015L,
             1873950916, 1166457082, 321919507, 1480307297, 2704513799L, 1502918399,
             895718745, 1215430802, 3917621196L, 3157183468L, 14334859, 1254750152]

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)

        for cycle in xrange(len(x)):
                sim.step({
                    a: x[cycle],
                    b: y[cycle],
                    c: z[cycle],
                    })
        true_result = [a + b + c for a, b, c in zip(x, y, z)]
        adder_result = sim_trace.trace[sum]
        sim_trace.render_trace()
        assert (adder_result == true_result)
        print "Test passed"

def test_ripple():

        pyrtl.reset_working_block() 
        a, b = pyrtl.Input(32, "a"), pyrtl.Input(32, "b") 
        sum = pyrtl.Output(34, "sum")
        psum, cout= ripple_add(a, b, pyrtl.Const(0)) 
        sum <<= pyrtl.concat(cout, psum)

        # x = [int(random.uniform(0, 2**32-1)) for i in range(20)]
        # y = [int(random.uniform(0, 2**32-1)) for i in range(20)]

        x = [3759516320L, 973033565, 4120989505L, 199451263, 3625363122L, 1115190551, 2207055453L, 2946555493L,
             760932817, 1072117699, 3456362420L, 2369715268L, 341973812, 1822482086, 1000917448, 3736696910L,
             1952403941, 766232820, 3355093416L, 3068692689L]
        y = [637240484, 2996140373L, 4171443642L, 500315891, 2908097029L, 3899747324L, 1198363687, 2707178015L,
             1873950916, 1166457082, 321919507, 1480307297, 2704513799L, 1502918399,
             895718745, 1215430802, 3917621196L, 3157183468L, 14334859, 1254750152]
        z = [637240484, 2996140373L, 4171443642L, 500315891, 2908097029L, 3899747324L, 1198363687, 2707178015L,
             1873950916, 1166457082, 321919507, 1480307297, 2704513799L, 1502918399,
             895718745, 1215430802, 3917621196L, 3157183468L, 14334859, 1254750152]

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)

        for cycle in xrange(len(x)):
                sim.step({
                    a: x[cycle],
                    b: y[cycle],
                    })
        true_result = [a + b for a, b in zip(x, y)]
        adder_result = sim_trace.trace[sum]
        sim_trace.render_trace()
        assert (adder_result == true_result)
        print "Test passed"


if __name__ == "__main__":
    main()