from pyrtl import *
from collections import namedtuple, Iterable

#  Numbering scheme for links is as follows
#  Each horizontal link (dir = 0):
#     is indexed by the same cordinates as the router to its left
#     if numbered 0 if it goes to the right
#     if numbered 1 if it goes to the left
#  Each vertical link (dir = 1):
#     is indexed by the same cordinates as the router underneath it
#     if numbered 0 if it goes up
#     if numbered 1 if it goes down
#  Each local link (dir = 2, not shown):
#     is indexed by the same cordinates as the router it connects to
#     if numbered 0 if to goes into the router (from the processor node)
#     if numbered 1 if it goes out of the router (into the processor node)
#
#  Full link "address" is (x, y, dir, number)
#
#                A   |
#       x,y,1,0  |   | x,y,1,1
#                |   |
#                |   V
#              *********
#      ------> *       * -------> x,y,0,0
#              *  x,y  * 
#      <------ *       * <------- x,y,0,1
#              *********
#                A   |
#     x,y-1,1,0  |   | x,y-1,1,1
#                |   |
#                |   V


class SurfNocPort():
    """ A class building the set of WireVectors needed for one router link. """
    def __init__(self):
        self.valid = WireVector(1)
        self.domain = WireVector(1)
        self.head = WireVector(16)
        self.data = WireVector(128)
        # note that credit should flow counter to the rest
        self.credit = WireVector(3)

def surfnoc_torus(width, height):
    """ Create a width x height tourus of surfnoc routers. """
    link = [[[[SurfNocPort() for n in (0,1)] for d in (0,1,2)] for y in range(height)] for x in range(width)]

    for x in range(width):
        for y in range(height):
            north = link[x][y][1]
            south = link[x][(y - 1) % height][1]
            east = link[x][y][0]
            west = link[(x - 1) % width][y][0]
            local = link[x][y][2]
            surfnoc_router(north=north, south=south, east=east, west=west, local=local)

def surfnoc_router(north, south, east, west, local):
    """ Create a SurfNOC Router Pipeline from the set of surrounding links. """
    # create the list of SurfNocPorts in and out bound of the router
    inbound = [north[1], south[0], east[1], west[0], local[0]]
    outbound = [north[0], south[1], east[0], west[1], local[1]]

    #for p in inbound:
    #    print p.valid

def surfnoc_single_buffer(addrwidth, data_in, read_enable, write_enable):
    """ Create a buffer of size 2**addrwidth.

    addrwidth -- the size of the address needed to index the buffer
    data_in -- a wirevector of width bitwidth to be input to the buffer
    read_enable -- 1-bit wirevector, if high requesting a read of data_out 
    write_enable -- 1-bit wirevector, if high data_in is valid and ready

    returns tuple (data_out, valid, full)
    data_out -- wirevector for data being read, only valid if "valid" is high
    valid -- 1-bit wirevector, see above
    full -- 1-bit wirevector, high if buffer cannot be written this cycle
    """
    assert len(write_enable) == len(read_enable) == 1

    bitwidth = len(data_in) # infer the bitwidth from the size of the data_in
    buffer_memory = MemBlock(bitwidth=bitwidth, addrwidth=addrwidth)

    head = Register(addrwidth) # write pointer into the circular buffer
    tail = Register(addrwidth) # read pointer into the circular buffer
    count = Register(addrwidth+1)  # number of elements currently stored in buffer

    # calculate status bits
    full = count >= 2**addrwidth
    do_write = mux(full, truecase=0, falsecase=write_enable)
    empty = (~do_write) & (count==0)
    do_read = mux(empty, truecase=0, falsecase=read_enable)

    # handle writes 
    buffer_memory[head] <<= MemBlock.EnabledWrite(data_in, do_write)

    # handle reads (including pass-through case of empty/full buffer)
    read_output = mux(do_read & do_write & (head==tail), 
                      truecase=data_in, 
                      falsecase=buffer_memory[tail])

    # update the state of the buffer
    head.next <<= mux(do_write, truecase=head+1, falsecase=head)
    tail.next <<= mux(do_read, truecase=tail+1, falsecase=tail)
    count.next <<= count + do_write - do_read

    return (read_output, do_read, full)


def surfnoc_multi_buffer(addrwidth, data_in, read_buffer_select, write_buffer_select, read_enable, write_enable):
    """ Create a large buffer combining multiple virtual channels and domains.
    addrwidth -- the size of the index of the smaller buffers
    data_in -- a wirevector of width bitwidth to be input to the buffer
    read_buffer_select -- a wirevector used to select the simple buffer for read
    write_buffer_select -- a wirevector used to select the simple buffer for write
    read_enable -- 1-bit wirevector, if high requesting a read of data_out 
    write_enable -- 1-bit wirevector, if high data_in is valid and ready

    returns tuple (data_out, valid, full)
    data_out -- wirevector for data being read, only valid if "valid" is high
    valid -- 1-bit wirevector, see above
    full -- 1-bit wirevector, high if buffer cannot be written this cycle
    """
    assert len(write_enable) == len(read_enable) == 1
    assert len(read_buffer_select) == len(write_buffer_select)

    num_buffer = 2**len(read_buffer_select)
    we = [write_enable & (write_buffer_select==i) for i in range(num_buffer)]
    re = [read_enable & (read_buffer_select==i) for i in range(num_buffer)]
    bufout = [surfnoc_single_buffer(addrwidth, data_in, re[i], we[i]) for i in range(num_buffer)]
    d, v, f = zip(*bufout)  # split out the list of tuples into three seperate arrays

    for n, i in enumerate(v):
        probe(i, 'v[%d]' % n)

    data_out = mux(read_buffer_select, *d)
    valid = mux(read_buffer_select, *v)
    full = mux(write_buffer_select, *f)

    return data_out, valid, full



# =========== Testing ====================================================


def test_block(name, func, param, retnames):
    """ Simulate and print the trace for a pyrtl block generating function.
    name -- string of the name of the function
    func -- function generating the block, args described below
    param -- dictionary of function arguments to trace values
    retnames -- tuple or list of names to be given wirevector return values of the function
    """
    reset_working_block()
    print
    print '===== {:=<65}'.format(name+' ')
    print

    # part of the dictionary (with non iterable values) are just passed along
    fixed_param = {k: v for k, v in param.iteritems() if not isinstance(v, Iterable)}
    # for the part of the dictionary specifying a trace (i.e. it is iterable) we 
    # allocate a wirevector.  The name given should be something like 'name/bitwidth'
    # so we need to split it up and allocate the wirevector appropriately 
    vector_param = {}
    for k, v in param.iteritems():
        if isinstance(v, Iterable):
            assert '/' in k
            name = k.split('/')[0]
            bitwidth = int(k.split('/')[1])
            vector_param[name] = Input(bitwidth, name)

    # put the dictionaries together and actually build the hardware block
    final_param = {}
    final_param.update(fixed_param)
    final_param.update(vector_param)
    out = func(**final_param)
    
    # okay, now we need to link the result to some Output that we can render
    assert len(retnames) == len(out)
    for i in range(len(retnames)):
        o = Output(len(out[i]), retnames[i]) 
        o <<= out[i]

    trace_len = min([len(v) for v in param.values() if isinstance(v, Iterable)])
    sim_trace=SimulationTrace()
    sim=Simulation(tracer=sim_trace)
    def val(w, cycle):
        name_in_dict = w.name + '/' + str(w.bitwidth)
        char_in_trace = param[name_in_dict][cycle]
        if char_in_trace == '-':
            return 1
        elif char_in_trace == '_':
            return 0
        else:
            return int(char_in_trace)

    for cycle in range(trace_len):
        sim.step({w: val(w, cycle) for w in vector_param.values()})    
    sim_trace.render_trace()

def test_surfnoc_single_buffer():
    param = {
        'addrwidth': 2,
	    'data_in/8':      '123456780000678900000001234',
	    'write_enable/1': '--------____----_______----',
	    'read_enable/1':  '________----_____----------'
	}
    retnames = ('read_output', 'valid', 'full')
    test_block('single buffer', surfnoc_single_buffer, param, retnames)

def test_surfnoc_multi_buffer():
    param = {
        'addrwidth': 2,
        'read_buffer_select/2':  '021302130213',
	    'write_buffer_select/2': '203120312031',
        'read_enable/1':         '--___--_-_--',
        'write_enable/1':        '____---__-_-',
	    'data_in/8':             '123456789012'		
	}
    retnames = ('read_output', 'valid', 'full')
    test_block('multi buffer', surfnoc_multi_buffer, param, retnames)

test_surfnoc_single_buffer()
test_surfnoc_multi_buffer()
