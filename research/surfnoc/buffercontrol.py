import pyrtl

#       -------------------------------------------------------
#       |VC|HEAD|TAIL|SOURCE_ID|DEST_ID|PAYLOAD               |
#       |1 |1   |1   |4        |4      |136                   |
#       -------------------------------------------------------

#       The above shows a Head or a tail flit. Each flit is 147 bits wide. Payload is 136bits if
#       Head flit, the rest will have a payload of 144bits. Tail indicates the end of packet.
#       For testing purpose 63 bit is used

flit = pyrtl.Input(63,'flit')   #Input flit
port = pyrtl.Input(4,'port')
full_N = pyrtl.Input(1,'full_N')
full_S = pyrtl.Input(1,'full_S')
full_E = pyrtl.Input(1,'full_E')
full_W = pyrtl.Input(1,'full_W')
full_L = pyrtl.Input(1,'full_L')    #signal from the downstream buffer
full = pyrtl.WireVector(1,'full')
buffer_write_sel = pyrtl.Output(2,'buffer_write_sel') 
source_id = pyrtl.Output(4,'source_id') 
dest_id = pyrtl.Output(4,'dest_id') #destination id
VC = pyrtl.WireVector(1,'vc') #virtual channel 
head = pyrtl.WireVector(1,'head') 
tail = pyrtl.WireVector(1,'tail')
surf_sch = pyrtl.Input(1,'surf_sch')
read_enable = pyrtl.Output(1,'read_enable')
check = pyrtl.Input(1,'check') # from Switch allocator, if check ==1 dont read the buffer
VC <<= flit[62]
head <<= flit[61]
tail <<= flit[60]
with pyrtl.ConditionalUpdate() as condition:
    with condition(port==15):
	full |= full_L
    with condition(port==8):
	full |= full_N
    with condition(port==4):
	full |= full_S
    with condition(port==2):
	full |= full_E
    with condition(port==1):
	full |= full_W
    with condition.fallthrough:
	full |= 0
read_enable <<=pyrtl.mux(((full|check)),truecase=0,falsecase=1)
source_id <<= pyrtl.mux(head, truecase=flit[56:60],falsecase=0)
dest_id <<= pyrtl.mux(head, truecase= flit[52:56],falsecase=0)
buffer_write_sel <<= pyrtl.concat(surf_sch+1,VC)

simvals ={
        flit: [7692148163548807167, 7845270550879404031,5539427541665710079,3233584532452016127],
        surf_sch: [0,1,0,1],
        check: [0, 0, 0, 1],
	port: [8,4,2,1],
        full_N:[1,0,0,1],
	full_S:[0,1,0,0],
	full_E:[1,0,1,1],
	full_W:[0,0,1,1],
	full_L:[1,1,1,1]
}
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in xrange(len(simvals[flit])):
    sim.step({k: v[cycle] for k,v in simvals.items()    })
sim_trace.render_trace(symbol_len=16)

