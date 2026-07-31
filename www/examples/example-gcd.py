import pyrtl


def gcd(
    a: pyrtl.WireVector, b: pyrtl.WireVector, begin: pyrtl.WireVector
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    x = pyrtl.Register(bitwidth=a.bitwidth)
    y = pyrtl.Register(bitwidth=b.bitwidth)
    done = pyrtl.WireVector(bitwidth=1)

    with pyrtl.conditional_assignment:
        with begin:
            x.next |= a
            y.next |= b
        with x > y:
            x.next |= x - y
        with y > x:
            y.next |= y - x
        with pyrtl.otherwise:
            done |= True
    return x, done


a = pyrtl.Input(name="a", bitwidth=8)
b = pyrtl.Input(name="b", bitwidth=8)
begin = pyrtl.Input(name="begin", bitwidth=1)

x = pyrtl.Output(name="x", bitwidth=8)
done = pyrtl.Output(name="done", bitwidth=1)

x_, done_ = gcd(a, b, begin)
x <<= x_
done <<= done_

sim = pyrtl.Simulation()
sim.step({"a": 12, "b": 9, "begin": True})
while not sim.inspect("done"):
    sim.step({"a": 0, "b": 0, "begin": False})
sim.tracer.render_trace()
