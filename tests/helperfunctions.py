
import pyrtl

# ------------------------------------------------------

def testmissing():
    """ called when a test is just stubbed in """
    #raise NotImplementedError
    pass

# ------------------------------------------------------
# example hardware generators, useful for testing

def generate_one_bit_adder(a,b,cin):
    """ Generates a one-bit full adder, returning type of signals """
    assert len(a) == len(b) == len(cin) == 1
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum,cout

def generate_full_adder( a, b, cin=None ):
    """ Generates a arbitrary bitwidth ripple-carry adder """
    assert len(a) == len(b)
    if cin is None:
        cin = pyrtl.Const(0,bitwidth=1)
    if len(a)==1:
        sumbits, cout = generate_one_bit_adder(a,b,cin)
    else:
        lsbit, ripplecarry = generate_one_bit_adder( a[0], b[0], cin )
        msbits, cout = generate_full_adder( a[1:], b[1:], ripplecarry )
        sumbits = pyrtl.concat(msbits,lsbit)
    return sumbits, cout

def generate_one_bit_mux(a,b,sel):
    """Generates a one-bit multiplexor"""
    assert len(a) == len(b) == len(sel) == 1
    out = ( b & sel ) | ( a & ~sel)
    return out

def generate_full_mux(a,b,sel):
    """Generates a multiplexor
       b is the one selected when sel is high"""
    assert len(a) ==  len(b)
    if len(a) == 1:
        out = generate_one_bit_mux(a,b,sel)
    else:
        lsbit = generate_one_bit_mux(a[0],b[0],sel)
        msbits = generate_full_mux(a[1:],b[1:],sel)
        out = pyrtl.concat(msbits,lsbit)
    return out
