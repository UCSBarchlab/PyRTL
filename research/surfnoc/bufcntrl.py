import pyrtl 

data = pyrtl.Input(16,'data')
head_ptr = pyrtl.Input(1,'head_ptr')
tail_ptr = pyrtl.Input(1,'tail_ptr')
#router_id = pyrtl.Input(4,'router_id')
#data_in = pyrtl.Output(8,'data_out')
#dmn_read = pyrtl.Output(2,'dmn_read')
dmn_wrt = pyrtl.Output(2,'dmn_wrt')
source_id = pyrtl.Output(4,'source_id')
dest_id = pyrtl.Output(4,'dest_id')
surf_sch = pyrtl.Input(1,'surf_sch')
vc_id = pyrtl.Input(1,'vc_id')

#vc_id = vc_id+1    For swapping
d0=surf_sch+1
head = pyrtl.mux(head_ptr, truecase=data[:8],falsecase=0)
source_id <<= pyrtl.mux(head_ptr, truecase=head[:4], falsecase=0)
dest_id <<= pyrtl.mux(head_ptr, truecase=head[4:8], falsecase=0)
dmn_wrt <<= pyrtl.concat(surf_sch,vc_id)
#dmn_read = pyrtl.concat(d0,)
simvals ={
	data: [43981, 52735],
	head_ptr: [1, 0],
	tail_ptr: [0, 0],
	surf_sch: [0, 1],
	vc_id: [1, 1]
}
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in xrange(len(simvals[data])):
    sim.step({k: v[cycle] for k,v in simvals.items()	})
sim_trace.render_trace(symbol_len=7)
