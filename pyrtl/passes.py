
"""
passes contains structures helpful for writing analysis and
transformation passes over blocks.
"""

import copy
import core
import wire
import helperfuncs

# --------------------------------------------------------------------
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


# --------------------------------------------------------------------
#   ___                 __        /\                     __      __
#    |  |  |\/| | |\ | /  `      /~~\ |\ |  /\  |  \_/  /__` |  /__`
#    |  |  |  | | | \| \__>     /    \| \| /~~\ |_  |   .__/ |  .__/
#

def quick_timing_analysis(block, print_total_length=True):
    cleared = block.wirevector_subset(wire.Input).union(block.wirevector_subset(wire.Register))
    remaining = block.logic.copy()
    num_prev_remaining = len(remaining)+1
    timing_map = {}
    time = 0
    while len(remaining) > num_prev_remaining:
        num_prev_remaining = len(remaining)
        time += 1
        for gate in remaining:  # loop over logicnets not yet returned
            if all([arg in cleared for arg in gate.args]):  # if all args ready
                timing_map[gate] = time
                cleared.update(set(gate.dests))  # add dests to set of ready wires
                remaining.remove(gate)  # remove gate from set of to return

    if len(remaining) > 0:
        raise core.PyrtlError("Cannot do static timing analysis due to nonregister "
                              "loops in the code")

    if print_total_length:
        print "The estimated total block timing delay is " + time
    return timing_map


def advanced_timing_analysis(block):

    def find_blocks(wires_to_check, all_wires):
        return set([aBlock for aBlock in block.logic if
                    set(aBlock.args).intersection(wires_to_check) is not None
                    and set(aBlock.args).intersection(all_wires) is set(aBlock.args)])

    raise NotImplementedError


def print_analysis(block, wirevector_timing_map, ):
    raise NotImplementedError

# --------------------------------------------------------------------
#   __   __  ___           __      ___    __
#  /  \ |__)  |  |  |\/| |  /  /\   |  | /  \ |\ |
#  \__/ |     |  |  |  | | /_ /~~\  |  | \__/ | \|
#


def _remove_wire_nets(block):
    """ Remove all wire nodes from the block. """

    def find_producer(x):
        # trace back to the root producer of x
        if x in immediate_producer:
            return find_producer(immediate_producer[x])
        else:
            return x

    immediate_producer = {}  # map from wirevector to its direct producer wirevector
    wire_removal_set = set()  # set of all wirevectors to be removed

    # one pass to build the map of value producers and
    # all of the nets and wires to be removed
    for net in block.logic:
        if net.op == 'w':
            immediate_producer[net.dests[0]] = net.args[0]
            if not isinstance(net.dests[0], wire.Output):
                wire_removal_set.add(net.dests[0])

    # second full pass to create the new logic without the wire nets
    new_logic = set()
    for net in block.logic:
        if net.op != 'w' or isinstance(net.dests[0], wire.Output):
            new_args = tuple(find_producer(x) for x in net.args)
            new_net = core.LogicNet(net.op, net.op_param, new_args, net.dests)
            new_logic.add(new_net)

    # now update the block with the new logic and remove wirevectors
    block.logic = new_logic
    for dead_wirevector in wire_removal_set:
        del block.wirevector_by_name[dead_wirevector.name]
        block.wirevector_set.remove(dead_wirevector)

    block.sanity_check()


def optimize(update_working_block=True, block=None):
    """ Return an optimized version of a synthesized hardware block. """
    block = core.working_block(block)
    for net in block.logic:
        if net.op not in set('r|&~^w'):
            raise core.PyrtlError('error, optimization only works on post-synthesis blocks')
    if not update_working_block:
        block = copy.deepcopy(block)

    if core.debug_mode:
        block.sanity_check()
        _remove_wire_nets(block)
        block.sanity_check()
        constant_propagation(block)
        block.sanity_check()
        remove_unlistened_nets(block)
    else:
        _remove_wire_nets(block)
        constant_propagation(block)
        remove_unlistened_nets(block)
    return block


def constant_propagation(block):
    """
    Removes excess constants in the block

    Note on resulting block:
    The output of the block can have wirevectors that are driven but not
    listened to. This is to be expected. These are to be removed by the
    remove_unlistened_nets function
    """

    current_nets = 0
    while len(block.logic) != current_nets:
        current_nets = len(block.logic)
        constant_prop_pass(block)


def constant_prop_pass(block):
    """ Does one constant propagation pass """

    def constant_prop_check(net_checking):

        def replace_net(new_net):
            nets_to_remove.add(net_checking)
            nets_to_add.add(new_net)
            # for arg_wire in net_checking.args:
            #     if arg_wire not in new_net.args:
            #         wire_removal_set.add(arg_wire)

        def replace_net_with_const(const_val):
            new_const_wire = wire.Const(bitwidth=1, val=const_val, block=block)
            wire_add_set.add(new_const_wire)
            replace_net_with_wire(new_const_wire)

        def replace_net_with_wire(new_wire):
            if isinstance(net_checking.dests[0], wire.Output):
                # if isinstance(new_wire,wire.Input) or isinstance(new_wire,wire.Const):
                replace_net(core.LogicNet('w', None, args=(new_wire,),
                                          dests=net_checking.dests))
            else:
                nets_to_remove.add(net_checking)
                replacement_wires[net_checking.dests[0]] = new_wire
                # wire_removal_set.add(net_checking.dests)

        one_var_ops = {
            '~': lambda x: 1-x,
            'r': lambda x: x   # This is only valid for constant folding purposes
        }
        two_var_ops = {
            '&': lambda l, r: l & r,
            '|': lambda l, r: l | r,
            '^': lambda l, r: l ^ r,
        }
        num_constants = 0
        for arg_wires in net_checking.args:
            if isinstance(arg_wires, wire.Const):
                num_constants += 1

        if num_constants is 0 or net_checking.op == 'w':
            return None

        if (net_checking.op in two_var_ops) & num_constants is 1:
            # special case
            arg1, arg2 = net_checking.args
            if isinstance(arg1, wire.Const):
                const_wire = arg1
                other_wire = arg2
            else:
                const_wire = arg2
                other_wire = arg1

            outputs = [two_var_ops[net_checking.op](const_wire.val, other_val)
                       for other_val in range(0, 2)]

            if outputs[0] == outputs[1]:
                replace_net_with_const(outputs[0])
            elif outputs[0] == 0:
                replace_net_with_wire(other_wire)
            else:
                replace_net(core.LogicNet('~', None, args=(other_wire,),
                                          dests=net_checking.dests))

        else:
            if net_checking.op in two_var_ops:
                output = two_var_ops[net_checking.op](net_checking.args[0].val,
                                                      net_checking.args[1].val)
            elif net_checking.op in one_var_ops:
                output = one_var_ops[net_checking.op](net_checking.args[0].val)
            else:
                raise core.PyrtlInternalError('net with invalid op code, '
                                              + net_checking.op + ' found')

            replace_net_with_const(output)

    def find_producer(x):
        # trace back to the root producer of x
        if x in replacement_wires:
            return find_producer(replacement_wires[x])
        else:
            return x

    replacement_wires = {}  # map from wire to its producer
    wire_add_set = set()
    nets_to_add = set()
    nets_to_remove = set()

    for a_net in block.logic:
        constant_prop_check(a_net)
    # second full pass to cleanup

    new_logic = set()
    for net in block.logic:
        if net not in nets_to_remove:
            new_args = tuple(find_producer(x) for x in net.args)
            new_net = core.LogicNet(net.op, net.op_param, new_args, net.dests)
            new_logic.add(new_net)
    # now update the block with the new logic and remove wirevectors

    new_logic = new_logic.union(nets_to_add)
    block.logic = new_logic
    for new_wirevector in wire_add_set:
        block.add_wirevector(new_wirevector)

    remove_unused_wires(block, "constant folding")


def remove_unlistened_nets(block):
    """
    Removes all nets that are not connected to an output wirevector
    """

    listened_nets = set()
    listened_wires_cur = set()
    prev_listened_net_count = 0

    for a_net in block.logic:
        if isinstance(a_net.dests[0], wire.Output):
            listened_nets.add(a_net)
            for arg_wire in a_net.args:
                listened_wires_cur.add(arg_wire)

    while len(listened_nets) > prev_listened_net_count:
        prev_listened_net_count = len(listened_nets)
        listened_wires_prev = listened_wires_cur

        for net in block.logic:
            if (net.dests[0] in listened_wires_prev) and net not in listened_nets:
                listened_nets.add(net)
                for arg_wire in net.args:
                    listened_wires_cur.add(arg_wire)

    block.logic = listened_nets
    remove_unused_wires(block, "unlistened net removal")


def remove_unused_wires(block, parent_process_name):
    """ Removes all unconnected wires from a block"""
    all_wire_vectors = set()
    for logic_net in block.logic:
        for arg_wire in logic_net.args:
            all_wire_vectors.add(arg_wire)
        for dest_wire in logic_net.dests:
            all_wire_vectors.add(dest_wire)

    wire_removal_set = block.wirevector_set.difference(all_wire_vectors)
    for removed_wire in wire_removal_set:
        if isinstance(removed_wire, wire.Input):
            print "Input Wire, " + removed_wire.name + " was removed by " + parent_process_name
        if isinstance(removed_wire, wire.Output):
            core.PyrtlInternalError("Output wire, " + removed_wire.name +
                                    "was disconnected by" + parent_process_name)

    block.wirevector_set = all_wire_vectors

# --------------------------------------------------------------------
#    __           ___       ___  __     __
#   /__` \ / |\ |  |  |__| |__  /__` | /__`
#   .__/  |  | \|  |  |  | |___ .__/ | .__/
#


def synthesize(update_working_block=True, block=None):
    """ Lower the design to just single-bit "and", "or", and "not" gates.

    Takes as input a block (default to working block) and creates a new
    block which is identical in function but uses only single bit gates
    and excludes many of the more complicated primitives.  The new block
    should only consist of the combination elements of w, &, |, ^, and ~.
    and sequential elements of registers (which are one bit as well).
    Because memories cannot be broken down to bit-level operations they
    are extracted from the design and made into new input/output interfaces.
    """

    block_in = core.working_block(block)
    block_out = core.Block()
    # resulting block should only have one of a restricted set of net ops
    block_out.legal_ops = set('~&|^rw')
    wirevector_map = {}  # map from (vector,index) -> new_wire
    uid = 0  # used for unique names

    # First step, create all of the new wires for the new block
    # from the original wires and store them in the wirevector_map
    # for reference.
    for wirevector in block_in.wirevector_subset():
        for i in range(len(wirevector)):
            new_name = '_'.join(['synth', wirevector.name, str(i), str(uid)])
            uid += 1
            if isinstance(wirevector, wire.Const):
                new_val = (wirevector.val >> i) & 0x1
                new_wirevector = wire.Const(bitwidth=1, val=new_val, block=block_out)
            else:
                # build the appropriately typed wire (maintaining input/output)
                wirevector_type = type(wirevector)
                new_wirevector = wirevector_type(name=new_name, bitwidth=1, block=block_out)
            wirevector_map[(wirevector, i)] = new_wirevector

    # Now that we have all the wires built and mapped, walk all the blocks
    # and map the logic to the equivalent set of primitives in the system
    for net in block_in.logic:
        _decompose(net, wirevector_map, block_out)

    block_in.wirevector_map = wirevector_map
    if update_working_block:
        core.set_working_block(block_out)
    return block_out


def _decompose(net, wv_map, block_out):
    """ Add the wires and logicnets to block_out and wv_map to decompose net """

    def arg(x, i):
        # return the mapped wire vector for argument x, wire number i
        return wv_map[(net.args[x], i)]

    def destlen():
        # return the length of the destination in bits
        return range(len(net.dests[0]))

    def assign_dest(i, v):
        # assign v to the wiremap for dest[0], wire i
        wv_map[(net.dests[0], i)] <<= v

    if net.op == 'w':
        for i in destlen():
            assign_dest(i, arg(0, i))
    elif net.op == '~':
        for i in destlen():
            assign_dest(i, ~arg(0, i))
    elif net.op == '&':
        for i in destlen():
            assign_dest(i, arg(0, i) & arg(1, i))
    elif net.op == '|':
        for i in destlen():
            assign_dest(i, arg(0, i) | arg(1, i))
    elif net.op == '^':
        for i in destlen():
            assign_dest(i, arg(0, i) ^ arg(1, i))
    elif net.op == '=':
        # The == operator is implemented with a nor of xors.
        temp_result = arg(0, 0) ^ arg(1, 0)
        for i in range(1, len(net.args[0])):
            temp_result = temp_result | (arg(0, i) ^ arg(1, i))
        assign_dest(0, ~temp_result)
    elif net.op == 'x':
        for i in destlen():
            muxed_bit = ~arg(0, 0) & arg(1, i) | arg(0, 0) & arg(2, i)
            assign_dest(i, muxed_bit)
    elif net.op == 's':
        for i in destlen():
            selected_bit = arg(0, net.op_param[i])
            assign_dest(i, selected_bit)
    elif net.op == 'c':
        arg_wirelist = []
        # generate list of wires for vectors being concatenated
        for arg_vector in net.args:
            arg_vector_as_list = [wv_map[(arg_vector, i)] for i in range(len(arg_vector))]
            arg_wirelist = arg_vector_as_list + arg_wirelist
        for i in destlen():
            assign_dest(i, arg_wirelist[i])
    elif net.op == 'r':
        for i in destlen():
            args = (arg(0, i),)
            dests = (wv_map[(net.dests[0], i)],)
            new_net = core.LogicNet('r', None, args=args, dests=dests)
            block_out.add_net(new_net)
    elif net.op == '+':
        arg0list = [arg(0, i) for i in range(len(net.args[0]))]
        arg1list = [arg(1, i) for i in range(len(net.args[1]))]
        cin = wire.Const(0, bitwidth=1, block=block_out)
        sumbits, cout = _generate_add(arg0list, arg1list, cin)
        destlist = sumbits + [cout]
        for i in destlen():
            assign_dest(i, destlist[i])
    elif net.op == '-':
        arg0list = [arg(0, i) for i in range(len(net.args[0]))]
        arg1list = [~arg(1, i) for i in range(len(net.args[1]))]
        cin = wire.Const(1, bitwidth=1, block=block_out)
        sumbits, cout = _generate_add(arg0list, arg1list, cin)
        destlist = sumbits + [cout]
        for i in destlen():
            assign_dest(i, destlist[i])
    else:
        raise core.PyrtlInternalError('Unable to synthesize the following net '
                                      'due to unimplemented op :\n%s' % str(net))
    return

def _generate_one_bit_add(a, b, cin):
    """ Generates hardware for a 1-bit full adder.
        Input: 3 1-bit wire vectors
        Output: a list of wire vectors (the sum), and a single 1-bit wirevector cout
    """
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return [sum], cout


def _generate_add(a, b, cin):
    """ a and b are lists of wirevectors (all len 1)
        cin is a wirevector (also len 1)
        returns sum as list of wirevectors (all len 1)
        and a carry out wirevector (also len 1)
    """
    if len(a) == 1:
        sumbits, cout = _generate_one_bit_add(a[0], b[0], cin)
    else:
        lsbit, ripplecarry = _generate_one_bit_add(a[0], b[0], cin)
        msbits, cout = _generate_add(a[1:], b[1:], ripplecarry)
        sumbits = lsbit + msbits  # append to lsb to the lowest bits
    return sumbits, cout
