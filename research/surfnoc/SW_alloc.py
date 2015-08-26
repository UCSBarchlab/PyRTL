import pyrtl
#self
#	
#	____________
#	|	   |
#  N--->|	   |
#  S--->|	   |
#  E--->|	   |--->Local
#  W--->|	   |
#  L--->|	   |
#	|__________|
#
#
north_in=pyrtl.Input(9,'north_in')	#Input request from VC 
south_in=pyrtl.Input(9,'south_in')
east_in=pyrtl.Input(9,'east_in')
west_in=pyrtl.Input(9,'west_in')
self_in=pyrtl.Input(9,'self_in')
surf_sch = pyrtl.Input(1,'surf_sch')
sel_read_buffer = pyrtl.Output(2,'sel_read_buffer')	
vc = pyrtl.WireVector(2,'vc')
out_port = pyrtl.Output(4,'out_port')
port_north = pyrtl.mux((north_in[4:8]==15),truecase=north_in[4:8],falsecase=0)	#checking if local is requested by the input signals
port_south = pyrtl.mux((south_in[4:8]==15),truecase=south_in[4:8],falsecase=0)
port_east = pyrtl.mux((east_in[4:8]==15),truecase=east_in[4:8],falsecase=0)
port_west = pyrtl.mux((west_in[4:8]==15),truecase=west_in[4:8],falsecase=0)
port_self = pyrtl.mux((self_in[4:8]==15),truecase=self_in[4:8],falsecase=0)
with pyrtl.ConditionalUpdate() as condition:	#taking out the VC and port from the request
    with condition((self_in[8]==1)&(port_self!=0)):
	vc |= self_in[4]
	out_port |= self_in[4:8]
    with condition((north_in[8]==1)&(port_north!=0)):
	vc |= north_in[4]
	out_port |= north_in[4:8]
    with condition((south_in[8]==1)&(port_south!=0)):
	vc |= south_in[4]
	out_port |= south_in[4:8]
    with condition((east_in[8]==1)&(port_east!=0)):
	vc |= east_in[4]
	out_port |= east_in[4:8]
    with condition((west_in[8]==1)&(port_west!=0)):
	vc |= west_in[4]
	out_port |= west_in[4:8]
    with condition.fallthrough:
	vc |= 3
	out_port |= 0


check = pyrtl.mux((vc!=3),truecase=0,falsecase=1)
check.name = ('check')
sel_read_buffer <<= pyrtl.concat(surf_sch,vc[0])
simvals ={
        north_in:[496,264,266],
        south_in:[312,319,316],
        east_in:[292,292,351],
        west_in:[280,280,280],
        self_in:[295,295,295],
        surf_sch:[1,0,1]
}
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in xrange(len(simvals[north_in])):
    sim.step({k: v[cycle] for k,v in simvals.items()    })
sim_trace.render_trace(symbol_len=7)

