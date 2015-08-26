import pyrtl

router_id = pyrtl.Input(4,'router_id')
dest_id = pyrtl.Input(4,'dest_id')

# 	-------------------------
#	|G|port3bits|VC|N||S|E|W|		9bits
#	-------------------------
#	port N = 0 | S = 0 | E = 0 | W= 0 | Self = 0 |
#
port = pyrtl.Input(3,'port')	#port which is giving Input signals

go_x=pyrtl.Output(9,'go_x')	#the X co-ordinate Request	##select X or Y request || X first then Y
go_y=pyrtl.Output(9,'go_y')	#the Y co-ordinate Request
x=pyrtl.WireVector(2,'x')	#X co-ordinate of the route
y=pyrtl.WireVector(2,'y')	#Y co-ordinate of the route
vc = pyrtl.Input(1,'vc')	# Virtual channel

x<<=pyrtl.mux((router_id[0:2]>dest_id[0:2]),truecase=router_id[0:2]-dest_id[0:2],falsecase=dest_id[0:2]-router_id[0:2])
y<<=pyrtl.mux((router_id[2:4]>dest_id[2:4]),truecase=router_id[2:4]-dest_id[2:4],falsecase=dest_id[2:4]-router_id[2:4])
x1 = pyrtl.mux(((x==3)|(dest_id[0:2]>router_id[0:2])),truecase=18,falsecase=pyrtl.mux(router_id[0:2]>dest_id[0:2],truecase=17,falsecase=pyrtl.mux(((x==0)&(y==0)),truecase=31, falsecase=00000)))
y1 = pyrtl.mux(((y==3)|(dest_id[2:4]>router_id[2:4])),truecase=24,falsecase=pyrtl.mux(router_id[2:4]>dest_id[2:4],truecase=20,falsecase=pyrtl.mux(((y==0)&(x==0)),truecase=31,falsecase=00000)))


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

