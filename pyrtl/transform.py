import copy

from .core import PostSynthBlock, set_working_block, LogicNet, working_block
from .pyrtlexceptions import PyrtlError
from .wire import Const, Input, Output, WireVector, Register
from .helperfuncs import get_block


def net_transform(transform_func, block=None):
    """
    :param transform_func:
        Function signature: func(orig_net (logicnet)) -> keep_orig_net (bool)
    :return:
    """
    block = working_block(block)
    for net in block.logic.copy():
        keep_orig_net = transform_func(net)
        if not keep_orig_net:
            block.logic.remove(net)


def wire_transform(transform_func, select_types=WireVector,
                   exclude_types=(Input, Output, Register, Const), block=None):
    """

    :param transform_func:
        Function signature: func(orig_wire (logicnet)) -> src_wire, dst_wire
        src_wire is the src for the stuff you made in the transform func
        and dst_wire is the sink

        to indicate that the wire has not been changed, make src_wire and dst_wire
    :param block:
    :return:
    """
    block = working_block(block)
    for orig_wire in block.wirevector_subset(select_types, exclude_types):
        new_src, new_dst = transform_func(orig_wire)
        replace_wire(orig_wire, new_src, new_dst, block)


def replace_wire(orig_wire, new_src, new_dst, block=None):
    if not block:
        block = get_block(orig_wire, new_src, new_dst)
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
            for wire in net.args:
                if wire is orig_wire:
                    new_net = LogicNet(
                        op=net.op, op_param=net.op_param, dests=net.dests,
                        args=tuple(new_src if w is orig_wire else w for w in net.args))
                    block.add_net(new_net)
                    block.logic.remove(net)

    if new_dst is not orig_wire and new_src is not orig_wire:
        block.remove_wirevector(orig_wire)


def clone_wire(old_wire, block=None):
    if not block:
        block = old_wire.block
    if isinstance(old_wire, Const):
        return Const(old_wire.val, old_wire.bitwidth, block)
    else:
        return old_wire.__class__(old_wire.bitwidth, block=block)


def copy_block(block=None, update_working_block=True):
    """
    Makes a copy of an existing block
    :param block: The block to clone.
    :return: The resulting block
    """
    block_in = working_block(block)
    block_out, temp_wv_map = _synth_base(block_in, "_")
    mems = {}
    for net in block_in:
        _copy_net(block_out, net, temp_wv_map, mems)

    if update_working_block:
        set_working_block(block_out)
    return block_out


def _synth_base(block_in, synth_name="synth"):
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
    temp_io_map = {}
    for wirevector in block_in.wirevector_subset():
        new_name = '_'.join([synth_name, str(wirevector)])
        new_wv = clone_wire(wirevector, block_out)
        temp_wv_map[wirevector] = new_wv
        if isinstance(wirevector, (Input, Output)):
            temp_io_map[wirevector] = new_wv

    block_out.io_map = _create_io_map(block_in, temp_io_map)
    return block_out, temp_wv_map


def _create_io_map(block_in, temp_io_map):
    try:
        return {orig_wire: temp_io_map[v] for (orig_wire, v) in block_in.io_map.viewitems()}
    except AttributeError:
        return temp_io_map


def _copy_net(block_out, net, temp_wv_net, mem_map):
    """This function makes a copy of all nets passed to it for synth uses
    """
    new_args = tuple(temp_wv_net[a_arg] for a_arg in net.args)
    new_dests = tuple(temp_wv_net[a_dest] for a_dest in net.dests)
    if net.op in "m@":  # special stuff for copying memories
        new_param = _get_new_block_mem_instance(net.op_param, mem_map, block_out)
    else:
        new_param = copy.copy(net.op_param)

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
