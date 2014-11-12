import sys
sys.path.append("..")  # needed only if not installed

"add verilog stuff"

import pyrtl
pyrtl.set_debug_mode(True)
output = pyrtl.Output(bitwidth=3, name='output')
counter = pyrtl.Register(bitwidth=3, name='counter')
counter.next <<= counter + 1
output <<= counter


def run(steps):
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)
    for i in xrange(15):
        sim.step({})
    sim_trace.render_trace()

print '\nBefore Synthesis:'
print pyrtl.working_block()
run(15)

pyrtl.synthesize()
pyrtl.optimize()

print '\nAfter Synthesis:'
print pyrtl.working_block()
run(15)
