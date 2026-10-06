import pyrtl

# # ROM-based multiplier example.


def mul(x: pyrtl.WireVector, y: pyrtl.WireVector) -> pyrtl.WireVector:
    assert x.bitwidth == 4
    assert y.bitwidth == 4

    def romdata(addr: int) -> int:
        return (addr >> 4) * (addr & 0xF)

    tbl = pyrtl.RomBlock(bitwidth=8, addrwidth=8, romdata=romdata)
    return tbl[pyrtl.concat(x, y)]


a = pyrtl.Input(name="a", bitwidth=4)
b = pyrtl.Input(name="b", bitwidth=4)
product = pyrtl.Output(name="product", bitwidth=8)

product <<= mul(a, b)

# Simulate the design.
sim = pyrtl.Simulation()
sim.step_multiple({"a": [1, 2, 3], "b": [2, 3, 4]})
sim.tracer.render_trace()
