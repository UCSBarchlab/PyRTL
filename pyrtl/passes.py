"""
Passes contains prebuilt transformantion passes to do optimization, lowering of the
design to single wire gates (synthesis), along with other ways to change a block.
"""

import collections

from pyrtl import transform  # transform.all_nets looks better than all_nets
from pyrtl.core import (
    Block,
    LogicNet,
    PostSynthBlock,
    _get_debug_mode,
    set_working_block,
    working_block,
)
from pyrtl.corecircuits import (
    _basic_add,
    _basic_eq,
    _basic_gt,
    _basic_lt,
    _basic_mult,
    _basic_select,
    _basic_sub,
    as_wires,
    concat,
    concat_list,
)
from pyrtl.helperfuncs import _NetCount
from pyrtl.memory import MemBlock
from pyrtl.pyrtlexceptions import PyrtlError, PyrtlInternalError
from pyrtl.transform import (
    _get_new_block_mem_instance,
    copy_block,
    net_transform,
    replace_wires,
)
from pyrtl.wire import Const, Input, Output, Register, WireVector

# --------------------------------------------------------------------
#   __   __  ___           __      ___    __
#  /  \ |__)  |  |  |\/| |  /  /\   |  | /  \ |\ |
#  \__/ |     |  |  |  | | /_ /~~\  |  | \__/ | \|
#


def optimize(
    update_working_block: bool = True,
    block: Block = None,
    skip_sanity_check: bool = False,
):
    """Return an optimized version of a synthesized hardware block.

    ``optimize`` works on all hardware designs, both synthesized and non synthesized.

    :param update_working_block: Don't copy the block and optimize the new block
        (defaults to ``True``).
    :param block: The block to optimize (defaults to :ref:`working_block`).
    :param skip_sanity_check: Don't perform :meth:`~Block.sanity_check` on the ``block``
        before, during, and after the optimization passes (defaults to ``False``).
        :meth:`~Block.sanity_check` will always be performed in debug mode
        (:func:`set_debug_mode`).
    """
    block = working_block(block)
    if not update_working_block:
        block = copy_block(block)

    with set_working_block(block, no_sanity_check=True):
        if (not skip_sanity_check) or _get_debug_mode():
            block.sanity_check()
        _remove_wire_nets(block, skip_sanity_check)
        _remove_slice_nets(block, skip_sanity_check)
        constant_propagation(block, True)
        _remove_unlistened_nets(block)
        common_subexp_elimination(block)
        _optimize_inverter_chains(block, skip_sanity_check)
        if (not skip_sanity_check) or _get_debug_mode():
            block.sanity_check()
    return block


def _get_inverter_chains(wire_creator, wire_users):
    """Returns all inverter chains in the block.

    The function returns a list of inverter chains in the block. Each inverter chain is
    represented as a list of the WireVectors in the chain.

    Consider the following circuit, for example::

        A -~-> B -~-> C -w-> X
        D -~-> E -w-> Y

    If the function is called on this circuit, it will return::

        [[A, B, C], [D, E]].
    """

    # Build a list of inverter chains. Each inverter chain is a list of WireVectors,
    # from source to destination.
    inverter_chains = []
    for current_dest, current_creator in wire_creator.items():
        if current_creator.op != "~":
            # Skip non-inverters.
            continue

        # The current inverter connects current_arg (a WireVector) to current_dest (also
        # a WireVector).
        current_arg = current_creator.args[0]
        # current_users is the number of LogicNets that use current_dest.
        current_users = len(wire_users[current_dest])

        # Add the current inverter to the end of this inverter chain.
        append_to = None
        # Add the current inverter to the beginning of this inverter chain.
        prepend_to = None
        next_inverter_chains = []
        for inverter_chain in inverter_chains:
            chain_arg = inverter_chain[0]
            chain_dest = inverter_chain[-1]
            chain_users = len(wire_users[chain_dest])

            if chain_dest is current_arg and chain_users == 1:
                # This chain's only destination is the current inverter. Append the
                # current inverter to the chain.
                append_to = inverter_chain
            elif chain_arg is current_dest and current_users == 1:
                # This chain's only argument is the current inverter. Add the current
                # inverter to the beginning of the chain.
                prepend_to = inverter_chain
            else:
                # The current inverter is not connected to the inverter chain, so we
                # pass the inverter chain through to next_inverter_chains
                next_inverter_chains.append(inverter_chain)

        if append_to and prepend_to:
            # The current inverter joins two existing inverter chains.
            next_inverter_chains.append(append_to + prepend_to)
        elif append_to:
            # Add the current inverter after 'append_to'.
            next_inverter_chains.append([*append_to, current_dest])
        elif prepend_to:
            # Add the current inverter before 'prepend_to'.
            next_inverter_chains.append([current_arg, *prepend_to])
        else:
            # The current inverter is not connected to any inverter chain, so we start a
            # new inverter chain with it
            next_inverter_chains.append([current_arg, current_dest])

        inverter_chains = next_inverter_chains
    return inverter_chains


def _optimize_inverter_chains(block, skip_sanity_check=False):
    """Optimizes inverter chains in the block.

    An inverter chain means two or more inverters directly connected to each other.
    Inverter chains are redundant and can be removed. For example, ``A -~-> B -~-> C
    -w-> X`` can be reduced to ``A -w-> X``.

    After optimization, a chain of an even number of inverters will be reduced a direct
    connection, and a chain of an odd number of inverters will be reduced to one
    inverter.

    If an inverter chain has intermediate users it won't be removed. For example, the
    inverter chain in the following circuit won't be removed::

        A -~-> B -~-> C -w-> X
        B -w-> Y
    """

    # wire_creator maps from WireVector to the LogicNet that defines its value.
    # wire_users maps from WireVector to a list of LogicNets that use its value.
    wire_creator, wire_users = block.net_connections()

    new_logic = set()
    net_removal_set = set()
    wire_removal_set = set()

    # This ProducerList maps the end wire of an inverter chain to its beginning wire. We
    # need this because when removing an inverter chain its end wire gets removed, so we
    # need to replace the source of LogicNets using the end wire of the inverter chain
    # with the chain's beginning wire.
    #
    # We need a ProducerList, rather than a simple dict, because if an inverter chain of
    # more than two inverters has intermediate users, we may have to query the dict
    # multiple times to get the replacement for the inverter chain's last wire. Consider
    # the following circuit, for example:
    #
    # A -~-> B -~-> C -w-> X
    # C -~-> D -~-> E -w-> Y
    #
    # This is the optimized version of the circuit:
    #
    # A -w-> X
    # A -w-> Y
    #
    # The inverter chains found will be A-B-C and C-D-E (two separate chains will be
    # found instead of A-B-C-D-E because C has an intermediate user). In the dict, C
    # will be mapped to A and E will be mapped to C. Hence, when finding the replacement
    # of E, we have to first query the dict to get C, and then query the dict again on C
    # to get A.
    wire_src_dict = _ProducerList()

    for inverter_chain in _get_inverter_chains(wire_creator, wire_users):
        # If len(inverter_chain) = n, there are n-1 inverters in the chain. We only
        # remove inverters if there are at least two inverters in a chain.
        if len(inverter_chain) > 2:
            if (
                len(inverter_chain) % 2 == 1
            ):  # There is an even number of inverters in a chain.
                start_idx = 1
            else:  # There is an odd number of inverters in a chain.
                start_idx = 2
            # Remove wires used in the inverter chain.
            wires_to_remove = inverter_chain[start_idx:]
            wire_removal_set.update(wires_to_remove)
            # Remove inverters used in the chain.
            inverters_to_remove = {wire_creator[wire] for wire in wires_to_remove}
            net_removal_set.update(inverters_to_remove)
            # Map the end wire of the inverter chain to the beginning wire.
            wire_src_dict[inverter_chain[-1]] = inverter_chain[start_idx - 1]

    # This loop recreates the block with inverter chains removed. It adds each LogicNet
    # in the original block to the new block if it is not marked for removal, and
    # replaces the source of the LogicNet if its source was the end wire of a removed
    # inverter chain.
    for net in block.logic:
        if net not in net_removal_set:
            new_logic.add(
                LogicNet(
                    net.op,
                    net.op_param,
                    args=tuple(wire_src_dict.find_producer(x) for x in net.args),
                    dests=net.dests,
                )
            )

    block.logic = new_logic
    for dead_wirevector in wire_removal_set:
        block.remove_wirevector(dead_wirevector)

    if (not skip_sanity_check) or _get_debug_mode():
        block.sanity_check()


class _ProducerList:
    """Maps from wire to its immediate producer and finds ultimate producers."""

    def __init__(self):
        self.dict = {}  # map from wirevector to its direct producer wirevector

    def __getitem__(self, item):
        msg = "You usually don't want the immediate producer"
        raise PyrtlError(msg)

    def __setitem__(self, key, item):
        self.dict[key] = item

    def find_producer(self, item):
        while item in self.dict:
            item = self.dict[item]
        return item


def _remove_wire_nets(block, skip_sanity_check=False):
    """Remove all wire nodes from the block."""

    wire_src_dict = _ProducerList()
    wire_removal_set = set()  # set of all wirevectors to be removed

    # one pass to build the map of value producers and all of the nets and wires to be
    # removed
    for net in block.logic:
        if net.op == "w":
            wire_src_dict[net.dests[0]] = net.args[0]
            if not isinstance(net.dests[0], Output):
                wire_removal_set.add(net.dests[0])

    # second full pass to create the new logic without the wire nets
    new_logic = set()
    for net in block.logic:
        if net.op != "w" or isinstance(net.dests[0], Output):
            new_args = tuple(wire_src_dict.find_producer(x) for x in net.args)
            new_net = LogicNet(net.op, net.op_param, new_args, net.dests)
            new_logic.add(new_net)

    # now update the block with the new logic and remove wirevectors
    block.logic = new_logic
    for dead_wirevector in wire_removal_set:
        block.remove_wirevector(dead_wirevector)

    if (not skip_sanity_check) or _get_debug_mode():
        block.sanity_check()


def _remove_slice_nets(block, skip_sanity_check=False):
    """Remove all unneeded slice nodes from the block.

    Unneeded here means that the source and destination wires of a slice net are exactly
    the same, because the slice takes all the bits, in order, from the source.
    """
    # Turns a net of form on the left into the one on the right:
    #
    #  w1
    #   |
    # [3:0]
    #   |
    # [3:0]     ===>  w1
    #   |             |
    # [3:0] w2      [3:0] w2
    #  / \ /         / \ /
    # ~   +         ~   +
    # |   |         |   |

    wire_src_dict = _ProducerList()
    wire_removal_set = set()  # set of all wirevectors to be removed

    def is_net_slicing_entire_wire(net):
        if net.op != "s":
            return False

        src_wire = net.args[0]
        dst_wire = net.dests[0]
        if len(src_wire) != len(dst_wire):
            return False

        selLower = net.op_param[0]
        selUpper = net.op_param[-1]
        # Check if getting all bits from the src_wire (i.e. consecutive bits, MSB to
        # LSB)
        return net.op_param == tuple(range(selLower, selUpper + 1))

    # one pass to build the map of value producers and all of the nets and wires to be
    # removed
    for net in block.logic:
        if is_net_slicing_entire_wire(net):
            wire_src_dict[net.dests[0]] = net.args[0]
            if not isinstance(net.dests[0], Output):
                wire_removal_set.add(net.dests[0])

    # second full pass to create the new logic without the wire nets
    new_logic = set()
    for net in block.logic:
        if not is_net_slicing_entire_wire(net) or isinstance(net.dests[0], Output):
            new_args = tuple(wire_src_dict.find_producer(x) for x in net.args)
            new_net = LogicNet(net.op, net.op_param, new_args, net.dests)
            new_logic.add(new_net)

    # now update the block with the new logic and remove wirevectors
    block.logic = new_logic
    for dead_wirevector in wire_removal_set:
        del block.wirevector_by_name[dead_wirevector.name]
        block.wirevector_set.remove(dead_wirevector)

    if (not skip_sanity_check) or _get_debug_mode():
        block.sanity_check()


def constant_propagation(block, silence_unexpected_net_warnings=False):
    """Removes excess constants in the block.

    .. note::

        The resulting block can have :class:`WireVectors<WireVector>` that are driven
        but not listened to. These are expected to be removed by
        :func:`_remove_unlistened_nets`
    """
    net_count = _NetCount(block)
    while net_count.shrinking():
        _constant_prop_pass(block, silence_unexpected_net_warnings)


def _constant_prop_pass(block, silence_unexpected_net_warnings=False):
    """Does one constant propagation pass"""
    valid_net_ops = "~&|^nrwcsm@"
    no_optimization_ops = "wcsm@"
    one_var_ops = {
        "~": lambda x, mask: ~x & mask,
        "r": lambda x, _: x,  # This is only valid for constant folding purposes
    }
    two_var_ops = {
        "&": lambda left, right: left & right,
        "|": lambda left, right: left | right,
        "^": lambda left, right: left ^ right,
        "n": lambda left, right: 1 - (left & right),
    }

    def _constant_prop_error(net, error_str):
        if not silence_unexpected_net_warnings:
            msg = f"Unexpected net, {net}, has {error_str}"
            raise PyrtlError(msg)

    def constant_prop_check(net_checking):
        def replace_net(new_net):
            nets_to_remove.add(net_checking)
            nets_to_add.add(new_net)

        def replace_net_with_const(const_val):
            bitwidth = len(net_checking.dests[0])
            new_const_wire = Const(bitwidth=bitwidth, val=const_val, block=block)
            wire_add_set.add(new_const_wire)
            replace_net_with_wire(new_const_wire)

        def replace_net_with_wire(new_wire):
            if isinstance(net_checking.dests[0], Output):
                replace_net(
                    LogicNet("w", None, args=(new_wire,), dests=net_checking.dests)
                )
            else:
                nets_to_remove.add(net_checking)
                new_wire_src[net_checking.dests[0]] = new_wire

        if net_checking.op not in valid_net_ops:
            _constant_prop_error(
                net_checking, "has a net not handled by constant_propagation"
            )
            return  # skip if we are ignoring unoptimizable ops

        num_constants = sum(isinstance(arg, Const) for arg in net_checking.args)

        if num_constants == 0 or net_checking.op in no_optimization_ops:
            return  # assuming wire nets are already optimized

        if (net_checking.op in two_var_ops) and num_constants == 1:
            long_wires = [
                w for w in net_checking.args + net_checking.dests if len(w) != 1
            ]
            if long_wires:
                _constant_prop_error(
                    net_checking,
                    f"has wire(s) {long_wires} with bitwidths that are not 1",
                )
                return  # skip if we are ignoring unoptimizable ops

            # special case
            const_wire, other_wire = net_checking.args
            if isinstance(other_wire, Const):
                const_wire, other_wire = other_wire, const_wire

            outputs = [
                two_var_ops[net_checking.op](const_wire.val, other_val)
                for other_val in (0, 1)
            ]

            if outputs[0] == outputs[1]:
                replace_net_with_const(outputs[0])
            elif outputs[0] == 0:
                replace_net_with_wire(other_wire)
            else:
                replace_net(
                    LogicNet("~", None, args=(other_wire,), dests=net_checking.dests)
                )

        else:
            # this optimization is actually compatible with long wires
            if net_checking.op in two_var_ops:
                output = two_var_ops[net_checking.op](
                    net_checking.args[0].val, net_checking.args[1].val
                )
            else:
                output = one_var_ops[net_checking.op](
                    net_checking.args[0].val, net_checking.args[0].bitmask
                )
            replace_net_with_const(output)

    new_wire_src = _ProducerList()
    wire_add_set = set()
    nets_to_add = set()
    nets_to_remove = set()

    for a_net in block.logic:
        constant_prop_check(a_net)
    # second full pass to cleanup

    new_logic = set()
    for net in block.logic.union(nets_to_add) - nets_to_remove:
        new_args = tuple(new_wire_src.find_producer(x) for x in net.args)
        new_net = LogicNet(net.op, net.op_param, new_args, net.dests)
        new_logic.add(new_net)

    block.logic = new_logic
    for new_wirevector in wire_add_set:
        block.add_wirevector(new_wirevector)

    _remove_unused_wires(block)


def common_subexp_elimination(
    block: Block = None, abs_thresh: float = 1, percent_thresh: float = 0
):
    """Common Subexpression Elimination for PyRTL blocks.

    :param block: the block to run the subexpression elimination on. Defaults to the
        :ref:`working_block`.
    :param abs_thresh: absolute threshold for stopping optimization
    :param percent_thresh: percent threshold for stopping optimization
    """
    block = working_block(block)
    net_count = _NetCount(block)

    while net_count.shrinking(block, percent_thresh, abs_thresh):
        net_table = _find_common_subexps(block)
        _replace_subexps(block, net_table)


ops_where_arg_order_matters = "m@xc<>-"


def _find_common_subexps(block: Block) -> dict[LogicNet, [LogicNet]]:
    """Finds nets that can be considered the same based on op type, op param, and
    arguments.

    Nets are the "same" if:

    1. their op types are the same,

    2. their op_params are the same (e.g. same memory if a memory-related op), and

    3. their arguments are the same (same constant value and bitwidth for const wires,
       otherwise same wire object). The destination wire for a net is not considered.

    :param block: Block to operate over

    :return: mapping from a logic net (with a placehold dest) representing the common
             subexp, to a list of nets matching that common subexp that can be replaced
             with the single common subexp.
    """
    net_table = {}  # {net (without dest) : [net, ...]
    t = ()  # just a placeholder
    const_dict = {}
    for net in block.logic:
        if net.op in ops_where_arg_order_matters:
            new_args = tuple(_const_to_int(w, const_dict) for w in net.args)
        else:
            new_args = tuple(
                sorted((_const_to_int(w, const_dict) for w in net.args), key=hash)
            )
        net_sub = LogicNet(net[0], net[1], new_args, t)  # don't care about dests
        if net_sub in net_table:
            net_table[net_sub].append(net)
        else:
            net_table[net_sub] = [net]
    return net_table


def _const_to_int(wire, const_dict):
    """Return a repr a Const (a tuple composed of width and value) for comparison with
    an 'is'.

    If the wire is not a Const, just return the wire itself; comparison will be done on
    the identity of the wire object instead.
    """
    if isinstance(wire, Const):
        # a very bad hack to make sure two consts will compare
        # correctly with an 'is'
        bitwidth = wire.bitwidth
        val = wire.val
        if bitwidth not in const_dict:
            const_dict[bitwidth] = {val: (bitwidth, val)}
        else:
            if val not in const_dict[bitwidth]:
                const_dict[bitwidth][val] = (bitwidth, val)
        return const_dict[bitwidth][val]

    return wire


def _replace_subexps(block, net_table):
    """Removes unnecessary nets, connecting the common net's dest wire to unnecessary
    net's dest.

    :param block: The block to operate over.
    :param net_table: A mapping from common subexpression (a net) to a list of nets that
        can be replaced with that common net.
    """
    wire_map = {}
    unnecessary_nets = []
    for nets in net_table.values():
        _process_nets_to_discard(nets, wire_map, unnecessary_nets)

    block.logic.difference_update(unnecessary_nets)
    replace_wires(wire_map, block)


def _has_normal_dest_wire(net):
    return not isinstance(net.dests[0], (Register, Output))


def _process_nets_to_discard(nets, wire_map, unnecessary_nets):
    """Helper for tracking how a group of related nets should be replaced with a common
    one.

    :param nets: List of nets that are considered equal and which should be replaced by
        a single common net.
    :param wire_map: Dict that will be updated with a mapping from every old destination
        wire that needs to be removed, to the new destination wire with which it should
        be replaced.
    :param unnecessary_nets: List of nets that are to be discarded.
    """
    if len(nets) == 1:
        return  # also deals with nets with no dest wires
    nets_to_consider = list(filter(_has_normal_dest_wire, nets))

    if len(nets_to_consider) > 1:  # needed to handle cases with only special wires
        net_to_keep = nets_to_consider[0]
        nets_to_discard = nets_to_consider[1:]
        dest_w = net_to_keep.dests[0]
        for net in nets_to_discard:
            old_dst = net.dests[0]
            wire_map[old_dst] = dest_w
            unnecessary_nets.append(net)


def _remove_unlistened_nets(block):
    """Removes all nets that are not connected to an output wirevector.

    :param block: The block to operate over.
    """

    listened_nets = set()
    listened_wires = set()
    prev_listened_net_count = 0

    def add_to_listened(net):
        listened_nets.add(net)
        listened_wires.update(net.args)

    for a_net in block.logic:
        if a_net.op == "@" or any(isinstance(destW, Output) for destW in a_net.dests):
            add_to_listened(a_net)

    while len(listened_nets) > prev_listened_net_count:
        prev_listened_net_count = len(listened_nets)

        for net in block.logic - listened_nets:
            if any((destWire in listened_wires) for destWire in net.dests):
                add_to_listened(net)

    block.logic = listened_nets
    _remove_unused_wires(block)


def _remove_unused_wires(block, keep_inputs=True):
    """Removes all unconnected wires from a block's wirevector_set.

    :param block: The block to operate over.
    :param keep_inputs: If True, retain any Input wires that are not connected to any
        net.
    """
    valid_wires = set()
    for logic_net in block.logic:
        valid_wires.update(logic_net.args, logic_net.dests)

    wire_removal_set = block.wirevector_set.difference(valid_wires)
    for removed_wire in wire_removal_set:
        if isinstance(removed_wire, Input):
            term = " optimized away"
            if keep_inputs:
                valid_wires.add(removed_wire)
                term = " deemed useless by optimization"

            print("Input Wire, " + removed_wire.name + " has been" + term)
        if isinstance(removed_wire, Output):
            PyrtlInternalError("Output wire, " + removed_wire.name + " not driven")

    block.wirevector_set = valid_wires
    block.wirevector_by_name = {wire.name: wire for wire in valid_wires}


# --------------------------------------------------------------------
#    __           ___       ___  __     __
#   /__` \ / |\ |  |  |__| |__  /__` | /__`
#   .__/  |  | \|  |  |  | |___ .__/ | .__/
#


def synthesize(
    update_working_block: bool = True,
    merge_io_vectors: bool = True,
    block: Block = None,
) -> PostSynthBlock:
    """Lower the design to just single-bit "and", "or", "xor", and "not" gates.

    Takes as input a ``block`` (default to :ref:`working_block`) and creates a new block
    which is identical in function but uses only single bit gates and excludes many of
    the more complicated :class:`LogicNet` primitives. The new block should consist
    *almost* exclusively of ``w``, ``&``, ``\\|``, ``^``, and ``~``
    :attr:`ops<LogicNet.op>`, and sequential elements of :class`Registers<Register>`,
    which are one bit as well.

    The two exceptions are for :class:`Inputs<Input>` and :class:`Outputs<Output>`, to
    maintain the same interface, which are immediately broken down into the individual
    bits and memories (read and write ports) which require the reassembly and
    disassembly of the :class:`WireVectors<WireVector>` immediately before and after.
    These are the only two places where ``c`` and ``s`` :attr:`ops<LogicNet.op>` should
    exist. If ``merge_io_vectors`` is ``False``, then these individual bits are not
    reassembled and disassembled before and after, and so no ``c`` and ``s``
    :attr:`ops<LogicNet.op>` will exist. Instead, they will be named ``<name>[n]``,
    where ``n`` is the bit number of original wire to which it corresponds.

    The block that results from synthesis is actually of type :class:`PostSynthBlock`
    which contains a mapping from the original :class:`Inputs<Input>` and
    :class:`Outputs<Output>` to the :class:`Inputs<Input>` and :class:`Outputs<Output>`
    of this block. This is used during :class:`Simulation` to map the
    :class:`Inputs<Input>` and :class:`Outputs<Output>` so that the same testbench can
    be used both pre- and post- synthesis. See documentation for :class:`Simulation` for
    more details.

    :param update_working_block: Boolean specifying if :ref:`working_block` should be
        set to the newly synthesized block.
    :param merge_io_vectors: If ``False``, turn all N-bit IO
        :class:`WireVectors<WireVector>` into N 1-bit IO
        :class:`WireVectors<WireVector>` (i.e. don't maintain interface).
    :param block: The block to synthesize.

    :return: The newly synthesized block, of type :class:`PostSynthBlock`.
    """

    block_pre = working_block(block)
    block_pre.sanity_check()  # before going further, make sure that presynth is valid
    block_in = copy_block(block_pre, update_working_block=False)

    block_out = PostSynthBlock()
    # resulting block should only have one of a restricted set of net ops
    block_out.legal_ops = set("~&|^nrwm@")
    if merge_io_vectors:
        block_out.legal_ops.update(set("cs"))
    wirevector_map = {}  # map from (vector,index) -> new_wire

    with set_working_block(block_out, no_sanity_check=True):
        # First, replace advanced operators with simpler ones
        for op, fun in [
            ("*", _basic_mult),
            ("+", _basic_add),
            ("-", _basic_sub),
            ("x", _basic_select),
            ("=", _basic_eq),
            ("<", _basic_lt),
            (">", _basic_gt),
        ]:
            net_transform(_replace_op(op, fun), block_in)

        # This is a map from the cloned io wirevector created in copy_block,
        # to the original io wirevector found in block_pre. We use it to create
        # the block_out.io_map that is returned to the user.
        orig_io_map = {temp: orig for orig, temp in block_in.io_map.items()}
        orig_reg_map = {temp: orig for orig, temp in block_in.reg_map.items()}

        # Next, create all of the new wires for the new block
        # from the original wires and store them in the wirevector_map
        # for reference.
        for wirevector in block_in.wirevector_subset():
            for i in range(len(wirevector)):
                new_name = "_".join((wirevector.name, "synth", str(i)))
                if isinstance(wirevector, Const):
                    new_val = (wirevector.val >> i) & 0x1
                    new_wirevector = Const(name=new_name, bitwidth=1, val=new_val)
                elif isinstance(wirevector, (Input, Output)):
                    if merge_io_vectors:
                        new_wirevector = WireVector(name="tmp_" + new_name, bitwidth=1)
                    else:
                        # Creating N 1-bit io wires for a given single N-bit io wire.
                        new_name = wirevector.name
                        if len(wirevector) > 1:
                            new_name += "[" + str(i) + "]"
                        new_wirevector = wirevector.__class__(name=new_name, bitwidth=1)
                        block_out.io_map[orig_io_map[wirevector]].append(new_wirevector)
                else:
                    new_wirevector = wirevector.__class__(name=new_name, bitwidth=1)
                    if isinstance(wirevector, Register):
                        block_out.reg_map[orig_reg_map[wirevector]].append(
                            new_wirevector
                        )
                wirevector_map[(wirevector, i)] = new_wirevector

        # Now connect up the inputs and outputs to maintain the interface
        if merge_io_vectors:
            for wirevector in block_in.wirevector_subset(Input):
                input_vector = Input(name=wirevector.name, bitwidth=len(wirevector))
                for i in range(len(wirevector)):
                    wirevector_map[(wirevector, i)] <<= input_vector[i]
                block_out.io_map[orig_io_map[wirevector]].append(input_vector)
            for wirevector in block_in.wirevector_subset(Output):
                output_vector = Output(name=wirevector.name, bitwidth=len(wirevector))
                output_bits = [
                    wirevector_map[(wirevector, i)] for i in range(len(output_vector))
                ]
                output_vector <<= concat_list(output_bits)
                block_out.io_map[orig_io_map[wirevector]].append(output_vector)

        # Now that we have all the wires built and mapped, walk all the blocks
        # and map the logic to the equivalent set of primitives in the system
        out_mems = block_out.mem_map  # dictionary: PreSynth Map -> PostSynth Map
        for net in block_in.logic:
            _decompose(net, wirevector_map, out_mems, block_out)

    if update_working_block:
        set_working_block(block_out, no_sanity_check=True)
    return block_out


def _replace_op(op, fun):
    def _replace_op_inner(net):
        if net.op != op:
            return True
        dest = net.dests[0]
        dest <<= fun(*net.args)
        return False

    return _replace_op_inner


def _decompose(net, wv_map, mems, block_out):
    """Add the wires and logicnets to block_out and wv_map to decompose net"""

    def arg(x, i):
        # return the mapped wire vector for argument x, wire number i
        return wv_map[(net.args[x], i)]

    def destlen():
        # return iterator over length of the destination in bits
        return range(len(net.dests[0]))

    def assign_dest(i, v):
        # assign v to the wiremap for dest[0], wire i
        wv_map[(net.dests[0], i)] <<= v

    one_var_ops = {
        "w": lambda w: w,
        "~": lambda w: ~w,
    }
    c_two_var_ops = {
        "&": lambda left, right: left & right,
        "|": lambda left, right: left | right,
        "^": lambda left, right: left ^ right,
        "n": lambda left, right: left.nand(right),
    }

    if net.op in one_var_ops:
        for i in destlen():
            assign_dest(i, one_var_ops[net.op](arg(0, i)))
    elif net.op in c_two_var_ops:
        for i in destlen():
            assign_dest(i, c_two_var_ops[net.op](arg(0, i), arg(1, i)))
    elif net.op == "s":
        for i in destlen():
            selected_bit = arg(0, net.op_param[i])
            assign_dest(i, selected_bit)
    elif net.op == "c":
        arg_wirelist = []
        # generate list of wires for vectors being concatenated
        for arg_vector in net.args:
            arg_vector_as_list = [
                wv_map[(arg_vector, i)] for i in range(len(arg_vector))
            ]
            arg_wirelist = arg_vector_as_list + arg_wirelist
        for i in destlen():
            assign_dest(i, arg_wirelist[i])
    elif net.op == "r":
        for i in destlen():
            args = (arg(0, i),)
            dests = (wv_map[(net.dests[0], i)],)
            new_net = LogicNet("r", None, args=args, dests=dests)
            block_out.add_net(new_net)
    elif net.op == "m":
        arg0list = [arg(0, i) for i in range(len(net.args[0]))]
        addr = concat_list(arg0list)
        new_mem = _get_new_block_mem_instance(net.op_param, mems, block_out)[1]
        data = as_wires(new_mem[addr])
        for i in destlen():
            assign_dest(i, data[i])
    elif net.op == "@":
        addrlist = [arg(0, i) for i in range(len(net.args[0]))]
        addr = concat_list(addrlist)
        datalist = [arg(1, i) for i in range(len(net.args[1]))]
        data = concat_list(datalist)
        enable = arg(2, 0)
        new_mem = _get_new_block_mem_instance(net.op_param, mems, block_out)[1]
        new_mem[addr] <<= MemBlock.EnabledWrite(data=data, enable=enable)
    else:
        msg = f"Unable to synthesize the following net due to unimplemented op :\n{net}"
        raise PyrtlInternalError(msg)
    return


@transform.all_nets
def nand_synth(net: LogicNet):
    """Synthesizes a :class:`PostSynthBlock` into one consisting of nands and inverters
    in place.

    :param PostSynthBlock block: The block to synthesize.
    """
    if net.op in "~nrwcsm@":
        return True

    def arg(num):
        return net.args[num]

    dest = net.dests[0]
    if net.op == "&":
        dest <<= ~(arg(0).nand(arg(1)))
    elif net.op == "|":
        dest <<= (~arg(0)).nand(~arg(1))
    elif net.op == "^":
        temp_0 = arg(0).nand(arg(1))
        dest <<= temp_0.nand(arg(0)).nand(temp_0.nand(arg(1)))
    else:
        msg = f"Op, '{net.op}' is not supported in nand_synth"
        raise PyrtlError(msg)
    return None


@transform.all_nets
def and_inverter_synth(net: LogicNet):
    """Transforms a decomposed block into one consisting of ands and inverters in place.

    :param Block block: The block to synthesize
    """
    if net.op in "~&rwcsm@":
        return True

    def arg(num):
        return net.args[num]

    dest = net.dests[0]
    if net.op == "|":
        dest <<= ~(~arg(0) & ~arg(1))
    elif net.op == "^":
        all_1 = arg(0) & arg(1)
        all_0 = ~arg(0) & ~arg(1)
        dest <<= ~all_0 & ~all_1
    elif net.op == "n":
        dest <<= ~(arg(0) & arg(1))
    else:
        msg = f"Op, '{net.op}' is not supported in and_inv_synth"
        raise PyrtlError(msg)
    return None


@transform.all_nets
def two_way_concat(net: LogicNet):
    """Transforms a block so all n-way (n > 2) :func:`concats<concat>` are replaced with
    series of 2-way :func:`concats<concat>`.

    This is useful for preparing the netlist for output to other formats, like FIRRTL or
    BTOR2, whose ``concatenate`` operation (``cat`` and ``concat``, respectively), only
    allow two arguments (most-significant wire and least-significant wire).

    :param Block block: The block to transform
    """

    # Turns a netlist of the form (where [] denote nets):
    #
    #  w1  w2  w3
    #   |  |   |
    #   [concat]
    #      |
    #      w4
    #
    # into:
    #
    #  w1 w2   w3
    #   | |    |
    # [concat] |
    #      |   |
    #     [concat]
    #        |
    #      [wire]
    #        |
    #        w4
    if net.op != "c":
        return True

    if len(net.args) <= 2:
        return True

    w = concat(net.args[0], net.args[1])
    for a in net.args[2:]:
        w = concat(w, a)

    dest = net.dests[0]
    dest <<= w
    return None


@transform.all_nets
def one_bit_selects(net: LogicNet):
    """Converts arbitrary-sliced :func:`selects<select>` to concatenations of 1-bit
    :func:`selects<select>`.

    This is useful for preparing the netlist for output to other formats, like FIRRTL or
    BTOR2, whose ``select`` operation (``bits`` and ``slice``, respectively) require
    contiguous ranges.

    Python slices are not necessarily contiguous ranges, e.g. the range ``[::2]``
    (syntactic sugar for ``slice(None, None, 2)``) produces indices ``0``, ``2``, ``4``,
    etc. up to the length of the list on which it is used.

    :param Block block: The block to transform
    """
    if net.op != "s":
        return True

    catlist = [net.args[0][i] for i in net.op_param]
    dest = net.dests[0]
    dest <<= concat_list(catlist)
    return None


def direct_connect_outputs(block=None):
    """Remove 'w' nets immediately before outputs, if possible.

    The 'w' nets that are eligible for removal with this pass meet the following
    requirements:

    - The destination wirevector of the net is an Output

    - The source wirevector of the net doesn't go to any other nets.

    :param block: block to update (defaults to :ref:`working_block`)
    """
    # Turns a netlist of the form (where [] denote nets and o is an Output):
    #
    #  w1 w2
    #   | |
    #   [*]
    #    |
    #    w3
    #    |
    #   [w]
    #    |
    #    o
    #
    # into:
    #
    #  w1 w2
    #   | |
    #   [*]
    #    |
    #    o

    # NOTE: would use transform.all_nets(), but it becomes tricky when we want to remove
    # more than just the current net on a single pass
    block = working_block(block)
    _, dst_nets = block.net_connections()

    nets_to_remove = set()
    nets_to_add = set()
    wirevectors_to_remove = set()

    for net in block.logic:
        if net.op == "@":
            continue

        dest_wire = net.dests[0]
        if dest_wire not in dst_nets or len(dst_nets[dest_wire]) > 1:
            continue

        dst_net = dst_nets[dest_wire][0]
        if dst_net.op != "w" or not isinstance(dst_net.dests[0], Output):
            continue

        new_net = LogicNet(
            op=net.op,
            op_param=net.op_param,
            args=net.args,
            dests=dst_net.dests,
        )
        nets_to_remove.add(net)
        nets_to_remove.add(dst_net)
        wirevectors_to_remove.add(dst_net.args[0])
        nets_to_add.add(new_net)

    block.logic.difference_update(nets_to_remove)
    block.logic.update(nets_to_add)
    for w in wirevectors_to_remove:
        block.remove_wirevector(w)


def _make_tree(wire, block, curr_fanout):
    def f(w, n):
        if n == 1:
            return (w,)
        l_fanout = n // 2
        r_fanout = n - l_fanout
        o = WireVector(len(w), block=block)
        split_net = LogicNet(
            op="w",
            op_param=None,
            args=(w,),
            dests=(o,),
        )
        block.add_net(split_net)
        return f(o, l_fanout) + f(o, r_fanout)

    return f(wire, curr_fanout)


def two_way_fanout(block=None):
    """Update the block such that no wire goes to more than 2 destination nets

    :param block: block to update (defaults to :ref:`working_block`)
    """
    from pyrtl.analysis import fanout

    block = working_block(block)

    _, dst_map = block.net_connections()
    # Two-pass approach: Remember which nets will need to change, in case there are
    # multiple arguments which will be changing along the way.
    nets_to_update = collections.defaultdict(list)
    for wire in block.wirevector_subset(exclude=(Output)):
        curr_fanout = fanout(wire)
        if curr_fanout > 1:
            s = _make_tree(wire, block, curr_fanout)
            curr_ix = 0
            for dst_net in dst_map[wire]:
                for i, arg in enumerate(dst_net.args):
                    if arg is wire:
                        nets_to_update[dst_net].append((wire, i, s[curr_ix]))
                        curr_ix += 1
            if curr_ix != curr_fanout:
                msg = "Calculated fanout does not equal number of wires found"
                raise PyrtlInternalError(msg)

    for old_net, args in nets_to_update.items():

        def get_arg(i, a, args=args):
            for orig, ix, from_tree in args:
                # Checking index as well because the same wire could be used as multiple
                # arguments to the same net.
                if i == ix and a is orig:
                    return from_tree
            return a

        new_net = LogicNet(
            op=old_net.op,
            op_param=old_net.op_param,
            args=tuple(get_arg(ix, a) for ix, a in enumerate(old_net.args)),
            dests=old_net.dests,
        )
        block.add_net(new_net)
        block.logic.remove(old_net)
