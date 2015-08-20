import sys
sys.path.append('../..')
import pyrtl
from pyrtl import *


def cache(tag, index, blockselect, byteselect, associativity, datain):
	# blocksize = 1 + len(tag) + len(blockselect) + len(byteselect) + len(datain)
	# indexlen = len(index)
	blocksize = 1 + 4 + 16 + 1 + 1
	indexlen = 8
	memory1 = MemBlock(bitwidth=blocksize, addrwidth=indexlen, name='memory1')
	# tag = Input(len(tag), 'tag')
	# index = Input(len(index), 'index')
	# blockselect = Input(len(blockselect), 'blockselect')
	# datain = Input(len(datain), 'datain')
	# byteselect = Input(len(byteselect), 'byteselect')
	tag = pyrtl.Register(tag)
	index = pyrtl.Register(index)
	# blockselect = pyrtl.Register(blockselect)
	# byteselect = pyrtl.Register(byteselect)
	# datain = pyrtl.Register(datain)
	blockselect = pyrtl.Register(4)
	byteselect = pyrtl.Register(1)
	datain = pyrtl.Register(16)
	lineselected = Output(blocksize, 'lineselected')
	lineselected <<= memory1[index]
	return (lineselected)
	# do this for update:
	# buffer_memory[head] <<= pyrtl.MemBlock.EnabledWrite(data, do_write)

def testcache():
	testtag = 4
	testindex = 5
	blockselect = Input(4, 'blockselect')
	datain = Input(16, 'datain')
	byteselect = Input(1, 'byteselect')
	associativity = Input(1, 'associativity')
	lineselected = cache(testtag, testindex, blockselect, byteselect, associativity, datain)
	
	simvals = {
		# tag: [15, 12],
		# index: [4, 0],
		blockselect: [0, 0],
		byteselect: [0, 1],
		associativity: [1, 1],
		datain: [77, 88]
	}
	sim_trace = pyrtl.SimulationTrace()
	sim = pyrtl.Simulation(tracer=sim_trace)
	for cycle in xrange(len(simvals[tag])):
		sim.step({k: v[cycle] for k,v in simvals.items()	})
	sim_trace.render_trace(symbol_len=7)

testcache()
