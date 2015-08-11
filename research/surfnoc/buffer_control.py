import pyrtl
#INCOMPLETE!!!!!!
#	-------------------------------------------------------
#	|VC|HEAD|TAIL|SOURCE_ID|DEST_ID|PAYLOAD		      |
#	|1 |1   |1   |4	       |4      |136	              |
#	-------------------------------------------------------

#	The above shows a Head or a tail flit. Each flit is 147 bits wide. Payload is 136bits if
#	Head flit, the rest will have a payload of 144bits. Tail indicates the end of packet.
#	For testing purpose 63 bit is used

flit = pyrtl.Input(63,'flit')
buffer_read_sel = pyrtl.Output(2,'buffer_read_sel')
buffer_write_sel = pyrtl.Output(2,'buffer_write_sel')
source_id = pyrtl.Output(4,'source_id')
dest_id = pyrtl.Output(4,'dest_id')
VC = pyrtl.WireVector(1,'vc')
head = pyrtl.WireVector(1,'head')
tail = pyrtl.WireVector(1,'tail')
surf_sch = pyrtl.Input(1,'surf_sch')
VC <<= flit[62]
head <<= flit[61]
tail <<= flit[60]
source_id <<= pyrtl.mux(head, truecase=flit[56:60],falsecase=0)
dest_id <<= pyrtl.mux(head, truecase= flit[52:56],falsecase=0)
buffer_write_sel <<= pyrtl.concat(surf_sch+1,VC)
buffer_read_sel <<= pyrtl.concat(surf_sch,VC)
simvals ={
        flit: [7692148163548807167, 7845270550879404031,5539427541665710079,3233584532452016127],
        surf_sch: [0,1,0,1]
}
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in xrange(len(simvals[flit])):
    sim.step({k: v[cycle] for k,v in simvals.items()    })
sim_trace.render_trace(symbol_len=16)

