import pyrtl
#INCOMPLETE
router_id = pyrtl.Input(4,'router_id')
#source_id = pyrtl.Input(4,'source_id')
dest_id = pyrtl.Input(4,'dest_id')

# 	-----------------------
#	|G|N|S|E|W|port3bit|VC|		9bits
#	-----------------------

#	0000	0001	0010	0011
#	0100	0101	0110	0111
#	1000	1001	1010	1011
#	1100	1101	1110	1111



#	router_id[3:2] == dest_id[3:2] & router_id[1:0] < dest_id[1:0]
#	router_id[3:2] == dest_id[3:2] & router_id[1:0] > dest_id[1:0]
#	router_id[3:2] > dest_id[3:2] & router_id[1:0] == 2'b11 //use west port
#	router_id[3:2] > dest_id[3:2] & router_id[1:0] < 2'b11 
#	router_id[3:2] > dest_id[3:2] & router_id[3:2] == 2'b11
#	router_id[3:2] < dest_id[3:2] & router_id[1:0] == 2'b00
#	router_id[3:2] < dest_id[3:2] & router_id[3:2] == 2'b00
#	router_id[3:2] < dest_id[3:2] & router_id[1:0] < 2'b11


#	NORTH	if[3:2] == 00 wraparound 
#	SOUTH	if[3:2] == 11 wraparound
#	WEST	if[1:0] == 00 wraparound
#	EAST	if[1:0] == 11 wraparound

#	if go_x = 1, give west port || if go_x = 0, give east port
#	if go_y = 1, give south port || if go_y = 0, give north port
#
port = pyrtl.Input(3,'port')

go_x=pyrtl.Output(9,'go_x')
go_y=pyrtl.Output(9,'go_y')
x=pyrtl.WireVector(2,'x')
y=pyrtl.WireVector(2,'y')
vc = pyrtl.Input(1,'vc')

x<<=pyrtl.mux((router_id[0:2]>dest_id[0:2]),truecase=router_id[0:2]-dest_id[0:2],falsecase=dest_id[0:2]-router_id[0:2])
y<<=pyrtl.mux((router_id[2:4]>dest_id[2:4]),truecase=router_id[2:4]-dest_id[2:4],falsecase=dest_id[2:4]-router_id[2:4])
x1 = pyrtl.mux(((x==3)|(dest_id[0:2]>router_id[0:2])),truecase=18,falsecase=pyrtl.mux(router_id[0:2]>dest_id[0:2],truecase=17,falsecase=pyrtl.mux(((x==0)&(y==0)),truecase=31, falsecase=00000)))
y1 = pyrtl.mux(((y==3)|(dest_id[2:4]>router_id[2:4])),truecase=24,falsecase=pyrtl.mux(router_id[2:4]>dest_id[2:4],truecase=20,falsecase=pyrtl.mux(((y==0)&(x==0)),truecase=31,falsecase=00000)))

x1.name= ('x1')

go_x <<= pyrtl.concat(x1,port,vc)
go_y <<= pyrtl.concat(y1,port,vc)

simvals ={
        router_id:[3,9,15,15,2,0,0],
	dest_id:[3,3,0,4,0,1,4],
	port:[0,1,2,3,4,2,1],
	vc: [0,1,0,1,0,1,1] 
}
sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)
for cycle in xrange(len(simvals[dest_id])):
    sim.step({k: v[cycle] for k,v in simvals.items()    })
sim_trace.render_trace(symbol_len=7)

