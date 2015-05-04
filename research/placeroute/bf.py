import sys
sys.path.append("..")
import pyrtl

def enumerate_states(n, name):
    """ return a register and the Consts for the different states. """
    statewidth = n.bit_length()
    retlist = [pyrtl.Register(bitwidth=statewidth, name=name)]
    retlist.extend([pyrtl.Const(i, bitwidth=statewidth) for i in range(n)])
    return retlist

datawidth = 8  # width of one one data cell in the brainfuck machine
addrwidth = 8  # width of address pointers (log2 of the memory size)

# two main memories define the brainfuck machine, one for instructions and one for data
instr_mem = pyrtl.MemBlock(bitwidth=datawidth, addrwidth=addrwidth, name='instr_mem')
data_mem = pyrtl.MemBlock(bitwidth=datawidth, addrwidth=addrwidth, name='data_mem')

# control register for the program counter, data pointer, and depth counter
pc = pyrtl.Register(bitwidth=addrwidth, name='pc')
dptr = pyrtl.Register(bitwidth=addrwidth, name='dptr')
depthcount = pyrtl.Register(bitwidth=addrwidth, name='depthcount')
state, EXE, FSEEK, BSEEK = enumerate_states(3, 'state')

# blocking I/O ports, with valid bit to sync 
input_data = pyrtl.Input(bitwidth=datawidth, name='input_data')
input_valid = pyrtl.Input(bitwidth=1, name='input_valid')
output_data = pyrtl.Input(bitwidth=datawidth, name='output_data')
output_valid = pyrtl.Input(bitwidth=1, name='output_valid')

# instr memory hooked up to the PC
instr = pyrtl.WireVector(name='instr')
instr <<= instr_mem[pc]

# data memory hooked up to the dptr
read_data = pyrtl.WireVector(bitwidth=datawidth, name='read_data')
read_data <<= data_mem[dptr]

pc.next <<= mux(

# PC update logic
with pyrtl.ConditionalUpdate() as condition:
    with condition(pc_backwards):
        pc |= pc - 1
    with condition.fallthrough:
        pc |= pc + 1

# DepthCount update logic
with pyrtl.ConditionalUpdate() as condition:
    with condition(dc_zero):
        pc |= pc - 1
    with condition.fallthrough:
        pc |= pc + 1


with pyrtl.ConditionalUpdate() as condition:

    # the EXE state is the normal "execute command" state
    with condition(state==EXE):
        pc.next |= pc + 1
        with condition(instr==ord('>')):
            dptr.next |= dptr + 1
        with condition(instr==ord('<')):
            dptr.next |= dptr - 1
        with condition( (instr==ord('+')) | (instr==ord('-')) ):
            with condition(instr==ord('+')):
                new_data |= data + 1
            with condition(instr==ord('-')):
                new_data |= data - 1
            data_mem[dptr] |= new_data
        with condition(instr==ord('[')):
            with condition(data == 0):
                depthcount.next |= 0
                state.next |= FSEEK
        with condition(instr==ord(']')):
            with condition(data != 0):
                depthcount.next |= 0
                state.next |= BSEEK
        with condition(instr==ord('.')):
            pass
        with condition(instr==ord(',')):
            pass

    # in FSEEK state we are scaning for the matching "]"
    with condition(state==FSEEK):
        pc.next |= pc + 1
        with condition(instr==ord('[')):
            depthcount.next |= depthcount + 1            
        with condition(instr==ord(']')):
            depthcount.next |= depthcount - 1
            with condition(depthcount==0):
                state.next |= EXE

    with condition(state==BSEEK):
        with condition(instr==ord('[')):
            pc.next |= pc - 1
            depthcount.next |= depthcount - 1            
        with condition(instr==ord(']')):
            depthcount.next |= depthcount + 1
            with condition(depthcount==0):
                pc.next |= pc + 1
                state.next |= EXE
            with condition.fallthrough:
                pc.next |= pc - 1    

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in range(10):
    sim.step({})
sim_trace.render_trace()

