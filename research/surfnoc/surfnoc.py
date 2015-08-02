from pyrtl import *
from collections import namedtuple

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



# =========== Testing ====================================================

def test_surfnoc_single_buffer():

    buffer_addrwidth = 2
    buffer_bitwidth = 8
    write_enable = Input(1,'write_enable')
    read_enable = Input(1,'read_enable')
    data_in = Input(buffer_bitwidth,'data_in')
    data_out = Output(buffer_bitwidth,'data_out')
    valid = Output(1,'valid')
    full = Output(1,'full')

    read_output, valid_output, full_output = surfnoc_single_buffer(buffer_bitwidth, buffer_addrwidth, data_in, write_enable, read_enable)
    data_out <<= read_output
    valid <<= valid_output
    full <<= full_output

    simvals = {
	    write_enable: "111111110000111100000001111",
	    data_in:      "123456780000678900000001234",
	    read_enable:  "000000001111000001111111111"
	}
    	
    sim_trace=SimulationTrace()
    sim=Simulation(tracer=sim_trace)
    for cycle in range(len(simvals[write_enable])):
        sim.step({k: int(v[cycle]) for k,v in simvals.items()})
    sim_trace.render_trace()

test_surfnoc_single_buffer()
