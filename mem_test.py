#----------------------------------------------------------

# debugging tools
#import pdb
#pdb.set_trace()
#end debugging tools

import pyrtl.pyrtl as rtl
from pyrtl.export import *
from pyrtl.simulation import *

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

def one_bit_mux(a,b,sel):
    """Generates a one-bit multiplexor"""
    assert len(a) == len(b) == len(sel) == 1
    out = ( b & sel ) | ( a & ~sel)
    return out

def mux(a,b,sel):
    """Generates a multiplexor
       b is the one selected when sel is high"""
    assert len(a) ==  len(b)
    if len(a) == 1:
	out = one_bit_mux(a,b,sel)
    else:
	lsbit = one_bit_mux(a[0],b[0],sel)
	msbits = mux(a[1:],b[1:],sel)
	out = rtl.concat(msbits,lsbit)
    return out


def memUnit(address,readWire,writeSelect,bitwidth):
    """generates a functioning memory unit"""
    #write select wire is high when you want to write an low when reading
    


inDataIncrement = rtl.Input(3,"InDataIncrement")
addressIncrement = rtl.Input(3,"addressIncrement")
outAddressIncrement = rtl.Input(3,"outAddressIncrement")

output = rtl.Output(3,"Output")


bitwidth = 3
memInData = rtl.Register(bitwidth=bitwidth,name='memInData')
memInData.next, cout = add(memInData, inDataIncrement )

memAddress =rtl.Register(bitwidth=bitwidth,name='memAddress')
memAddress.next, cout = add(memAddress, addressIncrement )

memOutAddress =rtl.Register(bitwidth=bitwidth,name='memOutAddress')
memOutAddress.next, cout = add(memOutAddress, outAddressIncrement )
   
adderMem = rtl.MemBlock(bitwidth = bitwidth,addrwidth = bitwidth,name ='adderMem')
output <<= adderMem[memOutAddress]
adderMem[memAddress] = memInData

  
#-----------------------------------------------------

sim_trace = SimulationTrace()
on_reset = {} # signal states to be set when reset is asserted
#  build the actual simulation environment
sim = Simulation( register_value_map=on_reset, default_value=0, tracer=sim_trace )

#  step through 15 cycles
for i in xrange(8):  
   sim.step( {inDataIncrement:0x3,addressIncrement:0x5,outAddressIncrement:0x1} )

for i in xrange(8):  
   sim.step( {inDataIncrement:3,addressIncrement:3,outAddressIncrement:0x1} )
   #sim_trace.render_trace()

sim_trace.print_vcd()
sim_trace.render_trace(symbol_len = 10, segment_size = 4)

