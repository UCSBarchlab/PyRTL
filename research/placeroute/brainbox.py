import sys
sys.path.append("../..")
import pyrtl

def enumerate_states(n, name):
    """ Return a register and the Consts for the different states. """
    statewidth = n.bit_length()
    retlist = [pyrtl.Register(bitwidth=statewidth, name=name)]
    retlist.extend([pyrtl.Const(i, bitwidth=statewidth) for i in range(n)])
    return retlist

def wirevectorlist(type=pyrtl.WireVector, bitwidth=None, name=None):
    return [type(bitwidth=bitwidth, name=x) for x in name.split()]

def updown(data, ctl):
    """ Return data added to one of {0,1,-1} as selected by ctl. """
    result = pyrtl.WireVector(bitwidth=len(data))
    term = pyrtl.WireVector(bitwidth=len(data))

    with ConditionalUpdate() as condition:
        with condition(ctl==0):
            term |= 0
        with condtion(ctl==1):
            term |= 1
        with condtion.default:
            # this seems clunky -- it should sign extend by default
            term |= Const(-1, bitwidth=len(data))
    result <<= data + term


datawidth = 8  # width of one one data cell in the brainfuck machine
addrwidth = 16  # width of address pointers (log2 of the memory size)

# control register for the program counter, data pointer, and depth counter
pc, dptr, depthcount = wirevectorlist(
    pyrtl.Register, bitwidth=addrwidth, name='pc dptr depthcount')

# two main memories define the brainfuck machine, one for instructions and one for data
instr_mem = pyrtl.MemBlock(bitwidth=datawidth, addrwidth=addrwidth, name='instr_mem')
instr = pyrtl.WireVector(name='instr')
instr <<= instr_mem[pc]

data_mem = pyrtl.MemBlock(bitwidth=datawidth, addrwidth=addrwidth, name='data_mem')
data = pyrtl.WireVector(bitwidth=datawidth, name='data')
data <<= data_mem[dptr]

# a set of control signals orchestrate the data flow of the machine
pc_ctl, dptr_ctl, depth_ctl, dmem_ctl = wirevectorlist(
    pyrtl.WireVector, bitwidth=2, name='pc_ctl dptr_ctl depth_ctl dmem_ctl')
write_ctl

# blocking I/O ports, with valid bit to sync 
input_data = pyrtl.Input(bitwidth=datawidth, name='input_data')
input_valid = pyrtl.Input(bitwidth=1, name='input_valid')
input_ack = pyrtl.Output(bitwidth=1, name='input_ack')
output_data = pyrtl.Output(bitwidth=datawidth, name='output_data')
output_valid = pyrtl.Output(bitwidth=1, name='output_valid')
output_ack = pyrtl.Input(bitwidth=1, name='output_ack')


# the updown units do most of the computation, it is just a matter of controlling them
pc.next <<= updown(pc, pc_ctl)
dptr.next <<= updown(dptr, dptr_ctl)
depth.next <<= updown(depth, depth_ctl)

write_data = pyrtl.mux( input_ctl, falsecase=update(data, dmem_ctl), truecase=input_data)
data_mem[dptr] <<= pyrtl.MemBlock._EnabledWrite(write_data, enable=write_ctl)


# core state machine for the machine
state, EXE, FSEEK, BSEEK = enumerate_states(3, 'state')
with pyrtl.ConditionalUpdate() as condition:

    # in EXE state we are reading instruction and executing it
    with condition(state==EXE):
        pc.next |= pc + 1
        with condition(instr==ord('>')):
            dptr.next |= dptr + 1
        with condition(instr==ord('<')):
            dptr.next |= dptr - 1
        with condition(instr==ord('+')):
            increment_data |= True
        with condition(instr==ord('-')):
            decrement_data |= True
        with condition(instr==ord('[')):
            with condition(read_data == 0):
                depthcount.next |= 0
                state.next |= FSEEK
        with condition(instr==ord(']')):
            with condition(read_data != 0):
                depthcount.next |= 0
                state.next |= BSEEK
        with condition(instr==ord('.')):
            output_data |= read_data
            output_valid |= True
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

    # in BSEEK state we are scaning for the matching "["
    with condition(state==BSEEK):
        with condition(instr==ord(']')):
            pc.next |= pc - 1
            depthcount.next |= depthcount + 1            
        with condition(instr==ord('[')):
            depthcount.next |= depthcount - 1
            with condition(depthcount==0):
                pc.next |= pc + 1
                state.next |= EXE
        with condition.default:
            pc.next |= pc - 1    


hello_world_program = '++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++'\
                      '..+++.>>.<-.<.+++.------.--------.>>+.>++.'
program_dict = {k:ord(v) for k,v in enumerate(hello_world_program)}
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map={instr_mem:program_dict})
for cycle in range(30):
    sim.step({input_data:0, input_valid:0})
sim_trace.render_trace()
