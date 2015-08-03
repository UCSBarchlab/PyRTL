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

def surfnoc_single_buffer(bitwidth, addrwidth, data_in, write_enable, read_enable):
    """ Create a buffer of size 2**addrwidth.

    bitwidth -- the data width of the buffer
    addrwidth -- the size of the address needed to index the buffer
    data_in -- a wirevector of width bitwidth to be input to the buffer
    write_enable -- 1-bit wirevector, if high data_in is valid and ready
    read_enable -- 1-bit wirevector, if high requesting a read of data_out 

    returns tuple (data_out, valid, full)
    data_out -- wirevector for data being read, only valid if "valid" is high
    valid -- 1-bit wirevector, see above
    full -- 1-bit wirevector, high if buffer cannot be written this cycle
    """
    assert len(write_enable) == len(read_enable) == 1

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


def surfnoc_big_buffer(bitwidth, addrwidth, data_in, dmn_vc_wrt, vc_read_req):
    """ Create a large buffer combining multiple virtual channels and domains.

    bitwidth -- the data width of the buffer
    addrwidth -- the size of the index of the smaller buffers
    data_in -- a wirevector of width bitwidth to be input to the buffer
    dmn_vc_wrt -- ?
    vc_read_req -- ?
    """

    data_out = WireVector(bitwidth)
    valid, full = WireVector(1), WireVector(1)

    we = [dmn_vc_wrt == i for i in range(4)]
    re = [vc_read_req == i  for i in range(4)]
    bufout = [surfnoc_single_buffer(8, 2, data_in, we[i], re[i]) for i in range(4)]
    d, v, f = zip(*bufout)

    data_out = mux(vc_read_req, *d)
    valid = mux(vc_read_req, *v)
    full = mux(vc_read_req, *f)

    return data_out, valid, full



# =========== Testing ====================================================


def test_block(name, func, param, retnames):
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
    for cycle in range(trace_len):
        sim.step({w: int(param['/'.join([w.name,str(w.bitwidth)])][cycle]) for w in vector_param.values()})    
    sim_trace.render_trace()

def test_surfnoc_single_buffer():
    param = {
        'bitwidth': 8,
        'addrwidth': 2,
	    'write_enable/1': '111111110000111100000001111',
	    'data_in/8':      '123456780000678900000001234',
	    'read_enable/1':  '000000001111000001111111111'
	}
    retnames = ('read_output', 'do_read', 'full')
    test_block('single buffer', surfnoc_single_buffer, param, retnames)

def test_surfnoc_big_buffer():
    reset_working_block()
    print_banner('big buffer')

    buffer_addrwidth = 2
    buffer_bitwidth = 8
    data_in = Input(buffer_bitwidth, 'data_in')
    dmn_vc_wrt = Input(2, 'dmn_vc_wrt')
    vc_read_req = Input(3, 'vc_read_req') # first bit valid 2 bit for domain and VC
    full = Output(1,'full')
    valid = Output(1,'valid')
    data_out = Output(buffer_bitwidth, 'data_out')

    d, v, f = surfnoc_big_buffer(buffer_bitwidth, buffer_addrwidth, data_in, dmn_vc_wrt, vc_read_req)
    data_out <<= d
    valid <<= v
    full <<= f

    simvals = {
       dmn_vc_wrt:  "021302130213",
	   vc_read_req: "203120312031",
	   data_in:     "123456789012"		
    }

    sim_trace=SimulationTrace()
    sim=Simulation(tracer=sim_trace)
    for cycle in range(len(simvals[dmn_vc_wrt])):
        sim.step({k: int(v[cycle]) for k,v in simvals.items()})
    sim_trace.render_trace()

test_surfnoc_single_buffer()
Xtest_surfnoc_single_buffer()
#test_surfnoc_big_buffer()
