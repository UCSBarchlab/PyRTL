from .core import set_working_block, LogicNet, working_block
from .wire import Const, Input, Output, WireVector, Register


def net_transform(transform_func, block=None):
    """
    :param transform_func:
        Function signature: func(orig_net (logicnet)) -> keep_orig_net (bool)
    :return:
    """
    block = working_block(block)
    with set_working_block(block, True):
        for net in block.logic.copy():
            keep_orig_net = transform_func(net)
            if not keep_orig_net:
                block.logic.remove(net)


def wire_transform(transform_func, select_types=WireVector,
                   exclude_types=(Input, Output, Register, Const), block=None):
    """
    Maps Wires to new sets of nets and wires accrding to a custom function

    :param transform_func:
        Function signature: func(orig_wire (logicnet)) -> src_wire, dst_wire
        src_wire is the src for the stuff you made in the transform func
        and dst_wire is the sink

        to indicate that the wire has not been changed, make src_wire and dst_wire both
        the original wire
    :param select_types: Type or Tuple of types of WireVectors to replace
    :param exclude_types: Type or Tuple of types of WireVectors to exclude from replacement
    :param block: The Block to replace wires on
    """
    block = working_block(block)
    for orig_wire in block.wirevector_subset(select_types, exclude_types):
        new_src, new_dst = transform_func(orig_wire)
        replace_wire(orig_wire, new_src, new_dst, block)


def replace_wire(orig_wire, new_src, new_dst, block=None):
    block = working_block(block)
    if new_src is not orig_wire:
        # don't need to add the new_src and new_dst because they were made added at creation
        for net in block.logic:
            for wire in net.dests:  # problem is that tuples use the == operator when using 'in'
                if wire is orig_wire:
                    new_net = LogicNet(
                        op=net.op, op_param=net.op_param, args=net.args,
                        dests=tuple(new_src if w is orig_wire else w for w in net.dests))
                    block.add_net(new_net)
                    block.logic.remove(net)
                    break

    if new_dst is not orig_wire:
        for net in block.logic:
            for wire in set(net.args):
                if wire is orig_wire:
                    new_net = LogicNet(
                        op=net.op, op_param=net.op_param, dests=net.dests,
                        args=tuple(new_src if w is orig_wire else w for w in net.args))
                    block.add_net(new_net)
                    block.logic.remove(net)

    if new_dst is not orig_wire and new_src is not orig_wire:
        block.remove_wirevector(orig_wire)


def replace_wires(wire_map, block=None):
    """
    Quickly replace all wires in a block

    :param {old_wire, new_wire} wire_map: mapping of old wires to
      new wires
    """
    block = working_block(block)
    src_nets, dst_nets = block.net_connections(include_virtual_nodes=False)
    for old_w, new_w in wire_map.items():
        replace_wire_fast(old_w, new_w, new_w, src_nets, dst_nets, block)


def replace_wire_fast(orig_wire, new_src, new_dst, src_nets, dst_nets, block=None):
    def remove_net(net_):
        for arg in set(net_.args):
            dst_nets[arg].remove(net_)
            if not len(dst_nets[arg]):
                del dst_nets[arg]
        if len(net_.dests) == 1:
            del src_nets[net_.dests[0]]
        block.logic.remove(net_)

    def add_net(net_):
        for arg in set(net_.args):
            if arg not in dst_nets:
                dst_nets[arg] = [net_]
            else:
                dst_nets[arg].append(net_)
        if len(net_.dests) == 1:
            src_nets[net_.dests[0]] = net_
        block.add_net(new_net)

    # src and dst in this function are all relative to wires
    block = working_block(block)
    if new_src is not orig_wire and orig_wire in src_nets:
        # don't need to add the new_src and new_dst because they were made added at creation
        net = src_nets[orig_wire]
        new_net = LogicNet(
            op=net.op, op_param=net.op_param, args=net.args,
            dests=tuple(new_src if w is orig_wire else w for w in net.dests))
        remove_net(net)
        add_net(new_net)

    if new_dst is not orig_wire and orig_wire in dst_nets:
        for net in dst_nets[orig_wire]:
            new_net = LogicNet(
                op=net.op, op_param=net.op_param, dests=net.dests,
                args=tuple(new_dst if w is orig_wire else w for w in net.args))
            remove_net(net)
            add_net(new_net)

    if new_dst is not orig_wire and new_src is not orig_wire:
        block.remove_wirevector(orig_wire)


def clone_wire(old_wire, name=None):
    if isinstance(old_wire, Const):
        return Const(old_wire.val, old_wire.bitwidth)
    else:
        if name is None:
            return old_wire.__class__(old_wire.bitwidth, name=old_wire.name)
        return old_wire.__class__(old_wire.bitwidth, name=name)


def copy_block(block=None, update_working_block=True):
    """
    Makes a copy of an existing block
    :param block: The block to clone.
    :return: The resulting block
    """
    block_in = working_block(block)
    block_out, temp_wv_map = _synth_base(block_in)
    mems = {}
    for net in block_in.logic:
        _copy_net(block_out, net, temp_wv_map, mems)

    if update_working_block:
        set_working_block(block_out)
    return block_out


def _synth_base(block_in):
    """
    This is a generic function to copy the wirevectors for another round of
    synthesis This does not split a wirevector with multiple wires.

    :param block_in: The block to change
    :param synth_name: a name to prepend to all new copies of a wire
    :return: the resulting block and a wirevector map
    """
    block_in.sanity_check()  # make sure that everything is valid
    block_out = block_in.__class__()
    temp_wv_map = {}
    with set_working_block(block_out, no_sanity_check=True):
        for wirevector in block_in.wirevector_subset():
            new_wv = clone_wire(wirevector)
            temp_wv_map[wirevector] = new_wv

    return block_out, temp_wv_map


def _copy_net(block_out, net, temp_wv_net, mem_map):
    """This function makes a copy of all nets passed to it for synth uses
    """
    new_args = tuple(temp_wv_net[a_arg] for a_arg in net.args)
    new_dests = tuple(temp_wv_net[a_dest] for a_dest in net.dests)
    if net.op in "m@":  # special stuff for copying memories
        new_param = _get_new_block_mem_instance(net.op_param, mem_map, block_out)
    else:
        new_param = net.op_param

    new_net = LogicNet(net.op, new_param, args=new_args, dests=new_dests)
    block_out.add_net(new_net)


def _get_new_block_mem_instance(op_param, mem_map, block_out):
    """ gets the instance of the memory in the new block that is
    associated with a memory in a old block
    """
    memid, old_mem = op_param
    if old_mem not in mem_map:
        new_mem = old_mem._make_copy(block_out)
        new_mem.id = old_mem.id
        mem_map[old_mem] = new_mem
    return memid, mem_map[old_mem]
