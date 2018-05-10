import pyrtl

counter = pyrtl.Register(bitwidth=3, name='counter')
zero = pyrtl.Input(1, 'zero')
counter_output = pyrtl.Output(3, 'counter_output')
counter = pyrtl.Register(3, 'counter')
counter.next <<= pyrtl.mux(zero, counter + 1, 0)
counter_output <<= counter

print(pyrtl.working_block())