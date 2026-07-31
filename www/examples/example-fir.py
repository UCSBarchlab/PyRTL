import pyrtl


def fir(x: pyrtl.WireVector, bs: list[int]):
    rwidth = x.bitwidth  # Bitwidth of the registers.
    ntaps = len(bs)  # Number of coefficients.

    zs = [x] + [pyrtl.Register(rwidth) for _ in range(ntaps - 1)]
    for i in range(1, ntaps):
        zs[i].next <<= zs[i - 1]

    # Produce the final sum of products.
    return sum(z * b for z, b in zip(zs, bs, strict=True))


x = pyrtl.Input(name="x", bitwidth=8)
y = pyrtl.Output(name="y", bitwidth=8)
y <<= fir(x, bs=[0, 1])

sim = pyrtl.Simulation()
sim.step_multiple({"x": [0, 9, 18, 8, 17, 7, 16, 6, 15, 5]})
sim.tracer.render_trace()
