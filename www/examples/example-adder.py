import pyrtl


def fa(
    x: pyrtl.WireVector, y: pyrtl.WireVector, cin: pyrtl.WireVector
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    """Full adder."""
    sum = x ^ y ^ cin
    cout = x & y | y & cin | x & cin
    return sum, cout


def adder(
    a: pyrtl.WireVector, b: pyrtl.WireVector, cin: pyrtl.WireVector
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    """n-bit ripple carry adder with carry in and carry out."""
    a, b = pyrtl.match_bitwidth(a, b)

    sum = [None] * a.bitwidth
    for i in range(a.bitwidth):
        sum[i], cout = fa(a[i], b[i], cin)
        cin = cout

    full_sum = pyrtl.concat_list(sum)
    return full_sum, cout


a = pyrtl.Input(name="a", bitwidth=4)
b = pyrtl.Input(name="b", bitwidth=4)
sum = pyrtl.Output(name="sum", bitwidth=8)

sum_, cout_ = adder(a, b, pyrtl.Const(0))
sum <<= sum_

sim = pyrtl.Simulation()
sim.step_multiple({"a": [1, 2, 3], "b": [2, 3, 4]})
sim.tracer.render_trace()
