from functools import reduce

import pyrtl


def max_n(*inputs):
    def max_2(x, y):
        return pyrtl.select(x > y, x, y)

    return reduce(max_2, inputs)


a = pyrtl.Input(name="a", bitwidth=8)
b = pyrtl.Input(name="b", bitwidth=8)
c = pyrtl.Input(name="c", bitwidth=8)
max = pyrtl.Output(name="max", bitwidth=8)

max <<= max_n(a, b, c)

sim = pyrtl.Simulation()
sim.step_multiple({"a": [1, 5, 9], "b": [2, 6, 7], "c": [3, 4, 8]})
sim.tracer.render_trace()
