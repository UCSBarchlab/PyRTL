import pyrtl

# ------------------------------------------------------
# example hardware generators, useful for testing

def generate_one_bit_adder(a, b, cin):
    """ Generates a one-bit full adder, returning type of signals """
    assert len(a) == len(b) == len(cin) == 1
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum, cout


def generate_full_adder(a, b, cin=None):
    """ Generates a arbitrary bitwidth ripple-carry adder """
    assert len(a) == len(b)
    if cin is None:
        cin = pyrtl.Const(0, bitwidth=1)
    if len(a) == 1:
        sumbits, cout = generate_one_bit_adder(a, b, cin)
    else:
        lsbit, ripplecarry = generate_one_bit_adder(a[0], b[0], cin)
        msbits, cout = generate_full_adder(a[1:], b[1:], ripplecarry)
        sumbits = pyrtl.concat(msbits, lsbit)
    return sumbits, cout

