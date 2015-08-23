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

bitwidth=8
addrwidth=2
data_in = pyrtl.Input(8,'data_in')
#we = pyrtl.Input(1,'we')
#re = pyrtl.Input(1,'re')
#router_id = pyrtl.Input(4,'router_id')
dmn_vc_wrt = pyrtl.Input(2,'dmn_vc_wrt')
#dmn_vc_read = pyrtl.Input(2,'dmn_vc_read')
#head_ptr = pyrtl.Input(1,'head_ptr')
#tail_ptr = pyrtl.Input(1,'tail_ptr')
full = pyrtl.Output(1,'full')
valid = pyrtl.Output(1,'valid')
data_out = pyrtl.Output(144,'data_out')
#credit = pyrtl.Output(5,'credit')   # 1 bit says if its valid, 2 bit for domain and VC and other 2 bit indicates free bits in that buffer
vc_read_req = pyrtl.Input(3,'vc_read_req') # first bit valid 2 bit for domain and VC
#head = pyrtl.Register(8,'head')

#head <<= mux(head_ptr, truecase=)
we0,we1,we2,we3 = pyrtl.WireVector(1,'we0'), pyrtl.WireVector(1,'we1'), pyrtl.WireVector(1,'we2'), pyrtl.WireVector(1,'we3') 
re0, re1, re2 ,re3 = pyrtl.WireVector(1,'re0'), pyrtl.WireVector(1,'re1'), pyrtl.WireVector(1,'re2'), pyrtl.WireVector(1,'re3')
we0<<=(dmn_vc_wrt==00)
we1<<=(dmn_vc_wrt==01)
we2<<=(dmn_vc_wrt==02)
we3<<=(dmn_vc_wrt==03)
re0<<=(vc_read_req==00)
re1<<=(vc_read_req==01)
re2<<=(vc_read_req==02)
re3<<=(vc_read_req==03)
#d0,d1,d2,d3 = pyrtl.WireVector(8,'d0'), pyrtl.WireVector(8,'d1'), pyrtl.WireVector(8,'d2'), pyrtl.WireVector(8,'d3')
#v0,v1,v2,v3 = pyrtl.WireVector(1,'v0'), pyrtl.WireVector(1,'v1'), pyrtl.WireVector(1,'v2'), pyrtl.WireVector(1,'v3')
#f0,f1,f2,f3 = pyrtl.WireVector(1,'f0'), pyrtl.WireVector(1,'f1'), pyrtl.WireVector(1,'f2'), pyrtl.WireVector(1,'f3')
d0,v0,f0 = surfnoc_buffer(8,2,data_in,we0,re0)
d1,v1,f1 = surfnoc_buffer(8,2,data_in,we1,re1)
d2,v2,f2 = surfnoc_buffer(8,2,data_in,we2,re2)
d3,v3,f3 = surfnoc_buffer(8,2,data_in,we3,re3)

data_out <<=pyrtl.mux(re0, truecase=d0, falsecase=pyrtl.mux(re1, truecase=d1, falsecase=pyrtl.mux(re2, truecase=d2, falsecase= pyrtl.mux(re3, truecase=d3, falsecase=0))))
valid <<=pyrtl.mux(re0, truecase=v0, falsecase=pyrtl.mux(re1, truecase=v1, falsecase=pyrtl.mux(re2, truecase=v2, falsecase= pyrtl.mux(re3, truecase=v3, falsecase=0))))
full <<= pyrtl.mux(re0, truecase=f0, falsecase=pyrtl.mux(re1, truecase=f1, falsecase=pyrtl.mux(re2, truecase=f2, falsecase= pyrtl.mux(re3, truecase=f3, falsecase=0))))
#data_out <<= pyrtl.mux(re0,truecase=d0, falsecase=0)
simvals = {
           dmn_vc_wrt: "021302130213",
	   vc_read_req: "203120312031",
	   data_in: "123456789012"		
       }
        
sim_trace=pyrtl.SimulationTrace()
sim=pyrtl.Simulation(tracer=sim_trace)
for cycle in range(len(simvals[dmn_vc_wrt])):
        sim.step({k: int(v[cycle]) for k,v in simvals.items()})
sim_trace.render_trace()

