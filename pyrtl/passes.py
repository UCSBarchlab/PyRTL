
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

    block = working_block(block)
    t_count = 0

    net in block.logic:
        max_arg_width = max([len(arg) for arg in net.args])
        max_dest_width = max([len(dest) for dest in net.dests])
        max_width = max(max_arg_width, max_dest_width)
        if net.op in '&|':
            t_count += max_width * 3
        elif net.op in '^=x':
            t_count += max_width * 5
        elif net.op in '+-<>':
            t_count += max_width * max_width
        elif net.op in '*':
            t_count += max_width * max_width * 5
        elif net.op in 'r':
            t_count += max_width * 10
        elif net.op in 'm':
            t_count += max_width * 10

