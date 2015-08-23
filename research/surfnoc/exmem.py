import pyrtl

def surfnoc_buffer(bitwidth, addrwidth, data, write_enable, read_enable):
    """ """

    buffer_memory = pyrtl.MemBlock(bitwidth=bitwidth, addrwidth=addrwidth)

    head = pyrtl.Register(addrwidth) # write pointer into the circular buffer
    tail = pyrtl.Register(addrwidth) # read pointer into the circular buffer
    count = pyrtl.Register(addrwidth+1)  # number of elements currently stored in buffer
    
    full = pyrtl.mux(count >= 2**addrwidth, truecase=1, falsecase=0)
    do_write = pyrtl.mux(full, truecase=0, falsecase=write_enable)
    empty = (~do_write) & (count==0)
    do_read = pyrtl.mux(empty, truecase=0, falsecase=read_enable)

    buffer_memory[head] <<= pyrtl.MemBlock._EnabledWrite(data, do_write)

    head.next <<= pyrtl.mux(do_write, truecase=head+1, falsecase=head)
    tail.next <<= pyrtl.mux(do_read, truecase=tail+1, falsecase=tail)
    count.next <<= count + do_write - do_read

    read_output = pyrtl.mux(do_read & do_write & (head==tail), truecase=data, falsecase=buffer_memory[tail])
    return (read_output, do_read, full)


def test_buffer():

    buffer_addrwidth = 2
    buffer_bitwidth = 8
    write_enable = pyrtl.Input(1,'write_enable')
    read_enable = pyrtl.Input(1,'read_enable')
    data_in = pyrtl.Input(buffer_bitwidth,'data_in')
    data_out = pyrtl.Output(buffer_bitwidth,'data_out')
    valid = pyrtl.Output(1,'valid')
    full = pyrtl.Output(1,'full')

    read_output, valid_output, full_output = surfnoc_buffer(buffer_bitwidth, buffer_addrwidth, data_in, write_enable, read_enable)
    data_out <<= read_output
    valid <<= valid_output
    full <<= full_output

    simvals = {
	    write_enable: "111111110000111100000001111",
	    data_in:      "123456780000678900000001234",
	    read_enable:  "000000001111000001111111111"
	}
	
    sim_trace=pyrtl.SimulationTrace()
    sim=pyrtl.Simulation(tracer=sim_trace)
    for cycle in range(len(simvals[write_enable])):
        sim.step({k: int(v[cycle]) for k,v in simvals.items()})
    sim_trace.render_trace()

test_buffer()
