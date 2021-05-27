"""
Transform contains structures helpful for writing analysis and
transformation passes over blocks.

Most of the functions in this module are for advanced users only.
However, the following functions are prebuilt transformations
that everyone can use:
(As of 7/1/16 there are none in this folder).

Other user accessible transforms that are based on these function
can be found in the passes module.


PyRTL makes it easy to make your own transformation. However
in order to make your first transform, some knowledge about the
structure of PyRTL Internal Representation (IR) of the circuit
is necessary. Specifically, one must know what Block, LogicNet,
and WireVector are as well as how Blocks store the latter two
structures (through Block.logic, block.Wirevector_set, etc).
"""
import functools
from pyrtl.pyrtlexceptions import PyrtlError

from .core import set_working_block, LogicNet, working_block
from .wire import Const, Input, Output, WireVector, Register


def net_transform(transform_func, block=None, **kwargs):
    """ Maps nets to new sets of nets according to a custom function.

    :param transform_func:
        Function signature: func(orig_net (logicnet)) -> keep_orig_net (bool)
    :param block: optional block to work on (defaults to working block)
    :return:

    If transform_func does not return True, the original net is removed from
    the block's logic set. The net's argument wire/destination wires are not removed.
    """
    block = working_block(block)
    with set_working_block(block, True):
        for net in block.logic.copy():
            keep_orig_net = transform_func(net, **kwargs)
            if not keep_orig_net:
                block.logic.remove(net)


def all_nets(transform_func):
    """ Decorator that wraps a net transform function. """
    @functools.wraps(transform_func)
    def t_res(**kwargs):
        net_transform(transform_func, **kwargs)
    return t_res


def wire_transform(transform_func, select_types=WireVector,
                   exclude_types=(Input, Output, Register, Const), block=None):
    """ Maps Wires to new sets of nets and wires according to a custom function.

    :param transform_func: The function you want to run on all wires.
        Function signature: func(orig_wire (WireVector)) -> src_wire, dst_wire
        src_wire is the src for the stuff you made in the transform func
        and dst_wire is the sink. To indicate that the wire has not been changed,
        make src_wire and dst_wire both the original wire.
    :param select_types: Type or Tuple of types of WireVectors to replace
    :param exclude_types: Type or Tuple of types of WireVectors to exclude from replacement
    :param block: The Block to replace wires on

    Note that if both new_src and new_dst don't equal orig_wire, orig_wire will
    be removed from the block entirely.
    """
    block = working_block(block)
    src_nets, dst_nets = block.net_connections(include_virtual_nodes=False)
    for orig_wire in block.wirevector_subset(select_types, exclude_types):
        new_src, new_dst = transform_func(orig_wire)
        replace_wire_fast(orig_wire, new_src, new_dst, src_nets, dst_nets, block)


def all_wires(transform_func):
    """ Decorator that wraps a wire transform function. """
    @functools.wraps(transform_func)
    def t_res(**kwargs):
        wire_transform(transform_func, **kwargs)
    return t_res


def replace_wires(wire_map, block=None):
    """ Replace all wires in a block.

    :param {old_wire: new_wire} wire_map: mapping of old wires to new wires
    :param block: block to operate over (defaults to working block)
    """
    block = working_block(block)
    src_nets, dst_nets = block.net_connections(include_virtual_nodes=False)
    for old_w, new_w in wire_map.items():
        replace_wire_fast(old_w, new_w, new_w, src_nets, dst_nets, block)


def replace_wire_fast(orig_wire, new_src, new_dst, src_nets, dst_nets, block=None):
    """ Replace orig_wire with new_src and/or new_dst.

    :param WireVector orig_wire: Wire to be replaced
    :param WireVector new_src: Wire to replace orig_wire, anywhere orig_wire is the
        destination of a net. Ignored if orig_wire equals new_src.
    :param WireVector new_dst: Wire to replace orig_wire, anywhere orig_wire is an
        argument of a net. Ignored if orig_wire equals new_dst.
    :param {WireVector: LogicNet} src_nets: Maps a wire to the net where it is a dest
    :param {WireVector: List[LogicNet]} dst_nets: Maps a wire to list of nets where it is an arg
    :param Block block: The block on which to operate (defaults to working block)

    The net that orig_wire originates from (its source net) will use new_src as its
    destination wire. The nets that orig_wire went to (its destination nets) will now
    have new_dst as one of their argument wires instead.

    This removes and/or adds nets to the block's logic set. This also *updates* the
    src_nets and dst_nets maps that are passed in, such that the following hold:

    ```
        old_src_net = src_nets[orig_wire]
        src_nets[new_src] = old_src_net (where old_src_net.dests = (new_src,))
    ``` 
    and
    ```
        old_dst_nets = dst_nets[orig_wire]
        dst_nets[new_dst] = [old_dst_net (where old_dst_net.args replaces orig_wire with new_dst) foreach old_dst_net]  # noqa
    ```

    For example, given the graph on left, `replace_wire_fast(w1, w4, w1, ...)` produces on right:

    ```
      a b c d                   a b    c d
      | | | |                   | |    | |
      net net                   net    net
        | |                      |      |
       w1 w2  ==> produces  ==>  w4 w1 w2
        | |                          | |
        net                          net
         |                            |
         w3                           w3
    ```

    And given the graph on the left, `replace_wire_fast(w1, w1, w4, ...)` produces on the right:
    ```
      a b c d                   a b    c d
      | | | |                   | |    | |
      net net                   net    net
        | |                      |      |
       w1 w2  ==> produces  ==>  w1 w4 w2
        | |                          | |
        net                          net
         |                            |
         w3                           w3
    ```

    Calling `replace_wire_fast(w1, w4, w4, ...)`, then, fully replaces w1 with w3 in both
    its argument and dest positions:

    ```
      a b c d                   a b c d
      | | | |                   | | | |
      net net                   net net
        | |                      |   |
       w1 w2  ==> produces  ==>  w4 w2
        | |                       | |
        net                       net
         |                         |
         w3                        w3
    ```
    """
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
        block.add_net(net_)

    # src and dst in this function are all relative to wires
    block = working_block(block)
    if new_src is not orig_wire and orig_wire in src_nets:
        # don't need to add the new_src and new_dst because they were made at creation
        net = src_nets[orig_wire]
        new_net = LogicNet(
            op=net.op, op_param=net.op_param, args=net.args,
            dests=tuple(new_src if w is orig_wire else w for w in net.dests))
        remove_net(net)
        add_net(new_net)

    if new_dst is not orig_wire and orig_wire in dst_nets:
        old_nets = tuple(dst_nets[orig_wire])  # need a copy bc the original will be modified
        for net in old_nets:
            new_net = LogicNet(
                op=net.op, op_param=net.op_param, dests=net.dests,
                args=tuple(new_dst if w is orig_wire else w for w in net.args))
            remove_net(net)
            add_net(new_net)

    if new_dst is not orig_wire and new_src is not orig_wire:
        block.remove_wirevector(orig_wire)


def clone_wire(old_wire, name=None):
    """ Makes a copy of any existing wire.

    :param old_wire: The wire to clone
    :param name: A name for the new wire (required if the old wire
        and newly cloned wire are part of the same block)

    This function is mainly intended to be used when the two wires are from different
    blocks. Making two wires with the same name in the same block is not allowed.
    """
    if name is None:
        if working_block() is old_wire._block:
            raise PyrtlError("Must provide a name for the newly cloned wire "
                             "when cloning within the same block.")
        name = old_wire.name

    if name in working_block().wirevector_by_name:
        raise PyrtlError("Cannot give a newly cloned wire the same name "
                         "as an existing wire.")

    if isinstance(old_wire, Const):
        return Const(old_wire.val, old_wire.bitwidth, name=name)
    else:
        return old_wire.__class__(old_wire.bitwidth, name=name)


def copy_block(block=None, update_working_block=True):
    """ Makes a copy of an existing block.

    :param block: The block to clone (defaults to the working block).
    :return: The resulting block
    """
    block_in = working_block(block)
    block_out, temp_wv_map = _clone_block_and_wires(block_in)
    mems = {}
    for net in block_in.logic:
        _copy_net(block_out, net, temp_wv_map, mems)
    block_out.mem_map = mems
    block_out.io_map = {io: w for io, w in temp_wv_map.items() if isinstance(io, (Input, Output))}
    block_out.reg_map = {r: w for r, w, in temp_wv_map.items() if isinstance(r, Register)}

    if update_working_block:
        set_working_block(block_out)
    return block_out


def _clone_block_and_wires(block_in):
    """ This is a generic function to copy the WireVectors for another round of
    synthesis. This does not split a WireVector with multiple wires.

    :param block_in: The block to change
    :param synth_name: a name to prepend to all new copies of a wire
    :return: the resulting block and a WireVector map
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
    """ This function makes a copy of all nets passed to it for synth uses.
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
    """ Gets the instance of the memory in the new block that is
    associated with a memory in a old block.
    """
    memid, old_mem = op_param
    if old_mem not in mem_map:
        new_mem = old_mem._make_copy(block_out)
        new_mem.id = old_mem.id
        mem_map[old_mem] = new_mem
    return memid, mem_map[old_mem]
