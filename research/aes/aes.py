import sys
sys.path.append('../..')
import pyrtl


def aes_shift_rows(in_vector):
    """ Shift Rows rounds of AES.
    
    Input: A single wirevector of width 128.
    Output: A single wirevector of width 128.
    """
    
    a00 = in_vector[120:128]
    a01 = in_vector[112:120] # not sure about these?
    # ..
    
    out_vector = cat( a00, a01, a02, a03,
                      a11, a12, a13, a10,
                      # ...
    return out_vector

# now actually build the AES hardware
aes_input = pyrtl.Input(width=128, name='aes_input')
aes_output = pyrtl.Output(width=128, name='aes_output')
aes_output <<= aes_shift_rows(aes_input)

print pyrtl.working_block()
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

for cycle in range(1):
    sim.step({aes_input: 35})
