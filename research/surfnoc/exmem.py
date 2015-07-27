import pyrtl
from pyrtl import *

memory = MemBlock(bitwidth=8, addrwidth=2)
head=Register(2,'head')
tail=Register(2,'tail')
read=Output(8,'read')
data=Input(8,'data')
we=Input(1,'we')
rd=Input(1,'rd')
we1=pyrtl.WireVector(1,'we1')
rd1=pyrtl.WireVector(1,'rd1')
valid=Output(1,'valid')
cmp1=WireVector(1,'cmp')
cnt=Register(3,'cnt')
#empty=Output(1,'empty')
e=WireVector(1,'e')
full=WireVector(1,'full')
we1<<=mux(full,falsecase=we,truecase=0)
WE=MemBlock.EnabledWrite
memory[head]<<=WE(data,we1)
head.next<<=mux(we1, falsecase=head, truecase=head+1)
cnt.next<<=cnt+we1-rd1
#rd1<<=mux(we1,falsecase=rd, truecase=0)
read<<=mux((rd1 & we1 & cmp1),falsecase=memory[tail],truecase=data)
tail.next<<=mux(rd1,falsecase=tail,truecase=tail+1)
valid<<=rd1
cmp1<<=head==tail
full<<=mux(cnt>=4,0,1)
e<<=(cnt==0)
rd1<<=mux(((cmp1 & ~we1) & e),rd,0)
#mux((cmp & ~rd1 ==1),0,1)
#empty<<=~full
#cnt.next<<=mux(cnt==3,falsecase=cnt, truecase=0)

simvals = {
	we: "111111110000111100000001111",
	data:"123456780000678900000001234",
	rd: "000000001111000001111111111"
	}
sim_trace=pyrtl.SimulationTrace()
sim=pyrtl.Simulation(tracer=sim_trace)
for cycle in range(len(simvals[we])):
    sim.step({k: int(v[cycle]) for k,v in simvals.items()})
sim_trace.render_trace()
