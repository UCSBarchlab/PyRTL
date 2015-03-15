from pyrtl import *


def main():
    # test_simple_mult()
    test_wallace_tree()


def simple_mult(A, B, start, done):
    """Build a slow, small multiplier using the simple shift-and-add algorithm. Requires very small
    area (it uses only a single adder), but has long delay (worst case is len(a) cycles).
    a and b are arbitrary-length inputs; start is a one-bit input to indicate inputs are ready.
    done is a one-bit signal output raised when the multiplication is finished, at which point the
    product will be on the result line (returned by the function)."""
    alen = len(A)
    blen = len(B)
    areg = Register(alen)
    breg = Register(blen+alen)
    accum = Register(blen+alen)
    aiszero = areg == 0

    # Multiplication is finished when a becomes 0
    done <<= aiszero

    # During multiplication, shift a right every cycle, b left every cycle
    with ConditionalUpdate() as condition:
        with condition(start):  # initialization
            areg.next |= A
            breg.next |= B
            accum.next |= 0
        with condition(~aiszero):  # don't run when there's no work to do
            areg.next |= areg[1:]  # right shift
            breg.next |= concat(breg, "1'b0")  # left shift

            # "Multply" shifted breg by LSB of areg by conditionally adding
            with condition(areg[0]):
                accum.next |= accum + breg  # adds to accum only when LSB of areg is 1

    return accum


def test_simple_mult():

    a, b, start = Input(8, "a"), Input(8, "b"), Input(1, "start")
    done, product = Output(1, "done"), Output(16, "product")

    product <<= simple_mult(a, b, start, done)

    aval, bval = 12, 19
    trueval = Output(16, "Answer")
    trueval <<= aval * bval

    sim_trace = SimulationTrace()
    sim = Simulation(tracer=sim_trace)
    sim.step({a: aval, b: bval, start: 1})
    for cycle in range(14):
        sim.step({a: 0, b: 0, start: 0})

    sim_trace.render_trace()


def wallace_tree(A, B):
    """Build an unclocked multiplier for inputs A and B using a Wallace Tree.
    Delay is order NlogN, while area is order N^2.
    (Actually, the way I wrote this, I think it's a Dadda multiplier).
    """

    # AND every bit of A with every bit of B (N^2 results) and store by "weight" (bit-position)
    bits = {weight: [] for weight in range(len(A) + len(B))}
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            bits[i+j].append(a & b)

    # Add together wires of the same weight. Sum keeps that weight; cout goes to the next bit up.
    result = bits[0][0]  # Start with bit 0, we'll add concatenate bits to the left
    for i in range(1, len(A) + len(B)):  # Start with low weights and move up
        while len(bits[i]) >= 3:  # Reduce with Full Adders until < 3 wires
            a, b, cin = bits[i].pop(0), bits[i].pop(0), bits[i].pop(0)
            bits[i].append(a ^ b ^ cin)  # sum bit keeps this weight
            bits[i+1].append((a & b) | (b & cin) | (a & cin))  # cout goes up one weight
        if len(bits[i]) == 2:  # Reduce with a Half Adder if exactly 2 wires
            a, b = bits[i].pop(0), bits[i].pop(0)
            bits[i].append(a ^ b)  # sum bit keeps this weight
            bits[i+1].append(a & b)  # cout goes up one weight
        if len(bits[i]) == 1:  # Remaining wire is the answer for this bit
            result = concat(bits[i][0], result)
    return result


def test_wallace_tree():

    a, b = Input(8, "a"), Input(8, "b")
    product = Output(16, "product")

    product <<= wallace_tree(a, b)

    aval, bval = 12, 19
    trueval = Output(16, "Answer")
    trueval <<= aval * bval

    sim_trace = SimulationTrace()
    sim = Simulation(tracer=sim_trace)
    sim.step({a: aval, b: bval})
    for cycle in range(14):
        sim.step({a: 0, b: 0})

    sim_trace.render_trace()


if __name__ == "__main__":
    main()
