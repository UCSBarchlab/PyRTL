#----------------------------------------------------------
import random
import pyrtl as rtl

def one_bit_add(a,b,cin):
    """ Generates a one-bit full adder, returning type of signals """
    assert len(a) == len(b) == len(cin) == 1
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum,cout

def add( a, b, cin=rtl.Const(0,bitwidth=1) ):
    """ Generates a arbitrary bitwidth ripple-carry adder """
    assert len(a) == len(b)

    if len(a)==1:
        sumbits, cout = one_bit_add(a,b,cin)
    else:
        lsbit, ripplecarry = one_bit_add( a[0], b[0], cin )
        msbits, cout = add( a[1:], b[1:], ripplecarry )
        sumbits = rtl.concat(msbits,lsbit)
    return sumbits, cout

def run_adder():
    # create a 3-bit incrementer connected to a 3-bit register 
    bitwidth = 3
    r = rtl.Register(bitwidth=bitwidth,name='r')
    r.next, cout = add(r, rtl.Const(1).zero_extended(bitwidth) )

    sim_trace = rtl.SimulationTrace()
    on_reset = {} # signal states to be set when reset is asserted

    # build the actual simulation environment
    sim = rtl.Simulation( register_value_map=on_reset, default_value=0, tracer=sim_trace )

    # step through 15 cycles
    for i in xrange(15):  
        sim.step( {} )
        
    #sim_trace.render_trace()
    return sim_trace
