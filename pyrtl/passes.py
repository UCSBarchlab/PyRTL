
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


def _decompose(net):


def synthesis(update_working_block=True, block=None):
    """ Lower the design to just single-bit "and", "or", and "not" gates.

    Takes as input a block (default to working block) and creates a new
    block which is identical in fucntion but uses only single bit gates
    and excludes many of the more complicated primitives.  The new block
    should only consist of the combination elements of &, |, and ~ (and
    the functionless wire "None") and sequential elements of registers
    (which are one bit as well).  Because memories cannot be broken
    down to bit-level operations they extracted from the design and made
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
            if type(wirevector == SignedConst):
                new_wirevector = Const(ADDME, block=block_out):
            elif type(wirevector == Const):
                new_wirevector = Const(ADDME, block=block_out):
            else:
                new_wirevector = type(wirevector)(name=new_name, block=block_out)
            wirevector_map[(wirevector,i)] = new_wirevector

    for net in block.logic:
        new_nets = _decompose(net, wirevector_map)
        for n in new_nets:
            block_out.add_net(n)

    if update_working_block:
        set_working_block(block_out)
    return block_out
