# Issues:
# Need to input status_carry, shift_carry, barrel_shift_carry, status_bits_carry
# fulladder_out, fulladder_cout
# out_flags needs to be displayed as an output

import sys
sys.path.append('../..')
import pyrtl

# def alu(a_in, b_in, swap_sel, not_sel, cin_sel, cout_sel):
''' Arithmetic Logic Unit for a 32-bit RISC machine
    Input:  a_in, b_in              : 32 bits
            shift_carry             : 1 bit
            status_carry            : 1 bit
    Output: out                     : 32 bits
            out_flags               : 4 bits
'''

# Declarations: 
a_in = pyrtl.Input(32, 'a_in')
b_in = pyrtl.Input(32, 'b_in')
a = pyrtl.WireVector(32, 'a')
b = pyrtl.WireVector(32, 'b')
swap_sel = pyrtl.Input(1, 'swap_sel')
not_sel = pyrtl.Input(1, 'not_sel')
cin_sel = pyrtl.Input(2, 'cin_sel')
cout_sel = pyrtl.Input(1, 'cout_sel')
shift_carry = pyrtl.Input(1, 'shift_carry')
status_carry = pyrtl.Input(1, 'status_carry')
out = pyrtl.Output(32, 'out')
#out_flags = pyrtl.Output(4, 'out_flags')
out_sel = pyrtl.Input(4, 'out_sel')
barrel_shift_carry = pyrtl.Input(1, 'barrel_shift_carry')
status_bits_carry = pyrtl.Input(1, 'status_bit_carry')

# Swap if (swap_sel):
with pyrtl.ConditionalUpdate() as condition:
    with condition(swap_sel):
        a |= b_in
        b |= a_in
    with condition.fallthrough:
        a |= a_in
        b |= b_in
        
not_b = pyrtl.WireVector(32, 'not_b')
# Reverse Subtract if (not_sel)
with pyrtl.ConditionalUpdate() as condition:
    with condition(not_sel):
        not_b |= ~b
    with condition(~not_sel):
        not_b |= b
        
# Cin Selection:
carry_in = pyrtl.WireVector(1, 'carry_in')
carry_out = pyrtl.WireVector(1, 'carry_out')
with pyrtl.ConditionalUpdate() as condition:
    with condition(cin_sel == 00):
        carry_in |= 0
    with condition(cin_sel == 11):
        carry_in |= 1
    with condition.fallthrough:
        carry_in |= status_bits_carry
        
# Cout Selection:
# overflow_out = pyrtl.WireVector(1, 'overflow_out')
# fulladder_cout = pyrtl.WireVector(1, 'fulladder_cout')
with pyrtl.ConditionalUpdate() as condition:
    with condition(cout_sel == 0):
        carry_out |= 0 #fulladder_cout
    with condition(cout_sel):
        carry_out |= barrel_shift_carry

# Overflow out:
# (Only assert when using the adder)
# over_out = out_sel == 1111 & >>> UNDERSTAND THIS PART

and_out = pyrtl.WireVector(32, 'and_out')
or_out = pyrtl.WireVector(32, 'or_out')
xor_out = pyrtl.WireVector(32, 'xor_out')
signext8 = pyrtl.WireVector(32, 'signext8')
signext16 = pyrtl.WireVector(32, 'signext16')
zeroext8 = pyrtl.WireVector(32, 'zeroext8')
zeroext16 = pyrtl.WireVector(32, 'zeroext16')
# fulladder_out = pyrtl.WireVector(33, 'fulladder_out')

and_out <<= a & b
or_out <<= a | b
xor_out <<= a ^ b
filler = pyrtl.Const(0)
notb_8 = pyrtl.WireVector(8, 'notb_8')
notb_8 <<= not_b[0:7]
zeroext8 <<= pyrtl.concat(filler, notb_8)
notb_16 = pyrtl.WireVector(16, 'notb_16')
notb_16 <<= not_b[0:15]
zeroext16 <<= pyrtl.concat(filler, notb_16)
sign_b8 = pyrtl.WireVector(1, 'sign_b')
sign_b8 <<= not_b[7]
signext8 <<= pyrtl.concat(sign_b8, notb_8)
sign_b16 = pyrtl.WireVector(1, 'sign_b16')
sign_b16 <<= not_b[15]
signext16 <<= pyrtl.concat(sign_b16, notb_16) 

with pyrtl.ConditionalUpdate() as condition:
    with condition(out_sel == 0000):
        out |= not_b
    with condition(out_sel == 0001):
        out |= 0 #fulladder_out[0:31]
    with condition(out_sel == 0010):
        out |= zeroext16
    with condition(out_sel == 0011):
        out |= zeroext8
    with condition(out_sel == 0100):
        out |= signext16
    with condition(out_sel == 0101):
        out |= signext8
    with condition(out_sel == 0110):
        out |= xor_out
    with condition(out_sel == 0111):
        out |= or_out
    with condition.fallthrough:
        out |= and_out
# out_flags = pyrtl.concat(out[31], 0, carry_out, overflow_out)# FILL THIS UP

print '---------------------------SIMULATION----------------------------------'
print pyrtl.working_block()
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

for cycle in range(15):
    sim.step({
    a_in : 1001,
    b_in : 1000,
    swap_sel : 0,
    cout_sel : 0,
    cin_sel : 00,
    not_sel : 0,
    out_sel : 0000,
    shift_carry : 0,
    status_carry : 0,
    status_bits_carry : 0,
    barrel_shift_carry : 0})
    
sim_trace.render_trace(symbol_len=32, segment_size=5)
print out
exit(0)
    
             

