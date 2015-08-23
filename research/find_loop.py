__author__ = 'johnw'

def _find_loop(wires, throwError=True, block=None):
    """
    Finds a loop in the wires given a set of wires that are all at or after where the loop
    occurs. This function will only find a single loop, and will not gaurentee that
    the same loop is found each time.

    :param iterable<Wirevector> wires: a set of wires that are all after the
    :return: a set of logicnets that form a loop
    """
    pass
    # Not working yet
    block = core.working_block(block)
    wire_set = frozenset(wire)
    start_wire = next(iter(wire_set))  # "random" element from the set
    net_dict = {dest_w: net for net in block.logic for dest_w in net.dest}
    # this is not proper logic!!!!!
    # previous line done for perfomance

    checking_lists = [((start_wire,), tuple())]

