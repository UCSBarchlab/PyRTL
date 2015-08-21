import sys
sys.path.append('../..')
import math
import pyrtl
from pyrtl import *

set_debug_mode()

def cache(word_address, datain, size, read_enable, write_enable, associativity=1, blocksize=1):
    """ Generate a cache.
    word_address is wirevector
    read_enable is wirevector of len 1
    write_enable is wirevector of len 1
    datain is wirevector of length of 1 word
    size is total number of words in the cache
    associativity is 1, 2, or 4
    blocksize is number of words in a block
    """
    # add assertions!

    word_size = len(datain)
    num_of_lines = size / blocksize
    index_size = int(math.log(num_of_lines, 2))  # fixme: add pyrtl log2 function
    end_of_blockoffset = int(math.log(blocksize, 2))
    end_of_index = end_of_blockoffset + index_size

    blockoffset = word_address[0:end_of_blockoffset]
    index = word_address[end_of_blockoffset:end_of_index]
    tag = word_address[end_of_index:]

	tag_block = MemBlock(bitwidth=len(tag)+1, addrwidth=index_size)
	data_block = MemBlock(bitwidth=word_size*blocksize, addrwidth=index_size)
	
    tag_line = tag_block[index]
    # valid bit is the msb of the tag_line
	hit = pyrtl.concat(1,tag) == tag_line
	
	data_line = data_block[index]
    data_list = [data_line[i*word_size:(i+1)*word_size] for i in range(blocksize)]
	dataout = pyrtl.mux(blockoffset, *data_list)
	
    return dataout, hit

def old_cache(tag, index, blockselect, byteselect, associativity, datain):
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
