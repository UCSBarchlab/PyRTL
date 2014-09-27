
"""
passes contains structures helpful for writing analysis and
transformation passes over blocks.
"""

from block import *
from wirevector import *
from helperfuncs import *


#---------------------------------------------------------------------
#         __   ___          ___  __  ___              ___    __
#    /\  |__) |__   /\     |__  /__`  |  |  |\/|  /\   |  | /  \ |\ |
#   /~~\ |  \ |___ /~~\    |___ .__/  |  |  |  | /~~\  |  | \__/ | \|
#


def area_estimation(tech_in_nm, block=None):
    """ Returns a single number estimating the total area of the block.

    The tech_in_nm is the size of the circuit technology to be estimated,
    with 65 being 65nm and 250 being 0.25um for example.  The area returned
    is in the units of square mm.  The estimates are VERY simple
    """
    raise NotImplementedError



#---------------------------------------------------------------------
#    __           ___       ___  __     __
#   /__` \ / |\ |  |  |__| |__  /__` | /__`
#   .__/  |  | \|  |  |  | |___ .__/ | .__/
#

def _generate_one_bit_add(a, b, cin):
    """ Generates hardware for a 1-bit full adder. """
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum, cout


def _generate_add(a, b, cin):
    """ a and b are lists of wirevectors (all len 1)
        cin is a wirevector (also len 1) 
        returns sum as list of wirevectors (all len 1)
        and a carry out wirevector (also len 1)
    """
    if len(a) == 1:
        sumbits, cout = _generate_one_bit_add(a, b, cin)
    else:
        lsbit, ripplecarry = _generate_one_bit_add(a[0], b[0], cin)
        msbits, cout = add(a[1:], b[1:], ripplecarry)
        sumbits = [lsbit] + msbits  # append to lsb to the lowest bits
    return sumbits, cout


def _decompose(net, wv_map, block_out):
    def arg(x,i):
        return wirevector_map[(net.args[x],i)] 
    if net.op is None:
        for i in range(len(net.dests[0])):
            wv_map[(net.dests[0],i)] <<= arg(0,i) 
    if net.op == '~':
        for i in range(len(net.dests[0])):
            wv_map[(net.dests[0],i)] <<= ~ arg(0,i) 
    if net.op == '&':
        for i in range(len(net.dests[0])):
            wv_map[(net.dests[0],i)] <<= arg(0,i) & arg(1,i)
    if net.op == '|':
        for i in range(len(net.dests[0])):
            wv_map[(net.dests[0],i)] <<= arg(0,i) | arg(1,i)
    if net.op == '^':
        for i in range(len(net.dests[0])):
            wv_map[(net.dests[0],i)] <<= arg(0,i) ^ arg(1,i)            
    elif net.op == '=':
        result = arg(0,i) ^ arg(1,i)
        for i in range(1,len(net.args[0])):
            result = result | (arg(0,i) ^ arg(1,i))            
        wv_map[(net.dests[0],0)] <<= ~ result
    elif net.op == 'm':
        for i in range(len(net.dests[0])):
            wv_map[(net.dests[0],i)] <<= (~arg(0,0) & arg(1,i)) | (arg(0,0) & arg(2,i))
    elif net.op == '+':
        arg0list = [arg(0,i) for i in range(len(net.args[0]))]
        arg1list = [arg(1,i) for i in range(len(net.args[0]))]
        cin = Const(0, bitwidth=1, block=block_out)
        sumbits, cout = _generate_add(arg0list, arg1list, cin)
        destlist = sumbits + [cout]
        for i in range(len(net.dests[0])):
            wv_map[(net.dests[0],i)] <<= destlist[i]
    else:
        raise PyrtlInternalError 
    return new_nets

def synthesis(update_working_block=True, block=None):
    """ Lower the design to just single-bit "and", "or", and "not" gates.

    Takes as input a block (default to working block) and creates a new
    block which is identical in fucntion but uses only single bit gates
    and excludes many of the more complicated primitives.  The new block
    should only consist of the combination elements of &, |, and ~ (and
    the functionless wire "None") and sequential elements of registers
    (which are one bit as well).  Because memories cannot be broken
    down to bit-level operations they are extracted from the design and made
    into new input/output interfaces.
    """

    block_in = working_block(block)
    block_out = Block()
    wirevector_map = {}  # map from (vector,index) -> new_wire
    uid = 0

    # first step, create all of the new wires for the new block
    # from the original wires and store them in the wirevector_map
    # for reference.
    for wirevector in block_in.wirevector_subset():
        for i in len(wirevector):
            new_name = 'synth' + str(uid)  # FIXME: better name needed
            uid += 1
            if isinstance(wirevector, Const):
                new_val = (wirevector.val >> i) & 0x1
                new_wirevector = Const(bitwidth=1, val=new_val, block=block_out):
            else:
                new_wirevector = WireVector(name=new_name, block=block_out)
            wirevector_map[(wirevector,i)] = new_wirevector

    # Now walk all the blocks and map the logic to the equivelent set of 
    # primitives in the system
    for net in block.logic:
        new_nets = _decompose(net, wirevector_map, block_out)
        for n in new_nets:
            block_out.add_net(n)

    if update_working_block:
        set_working_block(block_out)
    return block_out
