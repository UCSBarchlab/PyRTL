import pyrtl


def one_bit_add(
    a: pyrtl.WireVector, b: pyrtl.WireVector, carry_in: pyrtl.WireVector | int
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    assert len(a) == len(b) == 1  # `len` returns the bitwidth.
    sum = a ^ b ^ carry_in  # WireVector operators build the hardware.
    carry_out = a & b | a & carry_in | b & carry_in
    return sum, carry_out


def ripple_add(
    a: pyrtl.WireVector, b: pyrtl.WireVector, carry_in: pyrtl.WireVector | int = 0
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    a, b = pyrtl.match_bitwidth(a, b)
    if len(a) == 1:
        sumbits, carry_out = one_bit_add(a, b, carry_in)
    else:
        lsbit, ripplecarry = one_bit_add(a[0], b[0], carry_in)
        msbits, carry_out = ripple_add(a[1:], b[1:], ripplecarry)
        sumbits = pyrtl.concat(msbits, lsbit)
    return sumbits, carry_out


# Use the adder in a 3-bit counter.
counter = pyrtl.Register(bitwidth=3, name="counter")
sum, _carry_out = ripple_add(counter, pyrtl.Const(1))
counter.next <<= sum

# Simulate the instantiated design for 12 cycles.
sim = pyrtl.Simulation()
sim.step_multiple(nsteps=12)
sim.tracer.render_trace()
