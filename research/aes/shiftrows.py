# shiftrows.py

import sys
sys.path.append('../..')
import pyrtl

def aes_shift_rows(in_vector):
    """ ShiftRows round of AES.
    
    Input: A single wirevector of width 128.
    Output: A single wirevector of width 128.
    """
    
    a00 = in_vector[120:128]
    a01 = in_vector[112:120]
    a02 = in_vector[104:112]
    a03 = in_vector[96:104]
    a10 = in_vector[88:96]
    a11 = in_vector[80:88]
    a12 = in_vector[72:80]
    a13 = in_vector[64:72]
    a20 = in_vector[56:64]
    a21 = in_vector[48:56]
    a22 = in_vector[40:48]
    a23 = in_vector[32:40]
    a30 = in_vector[24:32]
    a31 = in_vector[16:24]
    a32 = in_vector[8:16]
    a33 = in_vector[0:8]
    
    out_vector = pyrtl.concat(a00, a01, a02, a03,
                      a11, a12, a13, a10,
                      a22, a23, a20, a21,
                      a33, a30, a31, a32)
    return out_vector

# Hardware build.
aes_input = pyrtl.Input(bitwidth=128, name='aes_input')
aes_output = pyrtl.Output(bitwidth=128, name='aes_output')
aes_output <<= aes_shift_rows(aes_input)

print pyrtl.working_block()
print

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

for cycle in range(1):
    sim.step({aes_input: 35})

sim_trace.render_trace(symbol_len=5, segment_size=5)
