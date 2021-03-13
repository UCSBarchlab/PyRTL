import pyrtl

# "pin" input/outputs
a = pyrtl.Input(8, 'a')
b = pyrtl.Input(8, 'b')
q = pyrtl.Output(8, 'q')
gt5 = pyrtl.Output(1, 'gt5')

sum = a + b  # makes an 8-bit adder
q <<= sum  # assigns output of adder to out pin
gt5 <<= sum > 5  # does a comparison, assigns that to different pin

# the simulation and waveform output
sim = pyrtl.Simulation()
sim.step_multiple({'a': [0, 1, 2, 3, 4], 'b': [2, 2, 3, 3, 4]})
sim.tracer.render_trace()
