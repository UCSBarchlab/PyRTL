""" Defines a set of helper functions that make constructing hardware easier.

The set of functions includes
as_wires: converts consts to wires if needed (and does nothing to wires)
and_all_bits, or_all_bits, xor_all_bits: apply function across all bits
parity: same as xor_all_bits
mux: generate a multiplexer
concat: concatenate multiple wirevectors into one long vector
get_block: get the block of the arguments, throw error if they are different
"""

from __future__ import print_function
from __future__ import unicode_literals

import inspect

from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .core import working_block, LogicNet
from .wire import WireVector, Input, Output, Const, Register

_rtl_assert_number = 1
_rtl_assert_dict = {}
_probe_number = 1

# -----------------------------------------------------------------
#        ___       __   ___  __   __
#  |__| |__  |    |__) |__  |__) /__`
#  |  | |___ |___ |    |___ |  \ .__/
#


def as_wires(val, bitwidth=None, truncating=True, block=None):
    """ Return wires from val which may be wires, integers, strings, or bools.

    If the option "truncating" is set to false as_wires will never drop
    bits in doing the conversion -- otherwise it will drop most-significant-bits
    to acheive the desired bitwidth (if one is specified).  This function is used by
    most operations in an attempt to coerce values into WireVectors (for example,
    operations such as "x+1" where "1" needs to be converted to a Const WireVectors.)
    """
    from .memory import _MemIndexed
    block = working_block(block)

    if isinstance(val, (int, str)):
        # note that this case captures bool as well (as bools are instances of ints)
        return Const(val, bitwidth=bitwidth, block=block)
    elif isinstance(val, _MemIndexed):
        # covert to a memory read when the value is actually used
        return as_wires(val.mem._readaccess(val.index), bitwidth, truncating, block)
    elif not isinstance(val, WireVector):
        raise PyrtlError('error, expecting a wirevector, int, or verilog-style const string')
    elif bitwidth == '0':
        raise PyrtlError('error, bitwidth must be >= 1')
    elif val.bitwidth is None:
        raise PyrtlError('error, attempting to use wirevector with no defined bitwidth')
    elif bitwidth and bitwidth > val.bitwidth:
        return val.zero_extended(bitwidth)
    elif bitwidth and truncating and bitwidth < val.bitwidth:
        return val[:bitwidth]  # truncate the upper bits
    else:
        return val


def and_all_bits(vector):
    """ Returns 1 bit WireVector, the result of "and"ing all bits of the argument vector."""
    return _apply_op_over_all_bits('__and__', vector)


def or_all_bits(vector):
    """ Returns 1 bit WireVector, the result of "or"ing all bits of the argument vector."""
    return _apply_op_over_all_bits('__or__', vector)


def xor_all_bits(vector):
    """ Returns 1 bit WireVector, the result of "xor"ing all bits of the argument vector."""
    return _apply_op_over_all_bits('__xor__', vector)


def parity(vector):
    """ Returns 1 bit WireVector, the result of "xor"ing all bits of the argument vector."""
    return _apply_op_over_all_bits('__xor__', vector)


def _apply_op_over_all_bits(op, vector):
    if len(vector) == 1:
        return vector
    else:
        rest = _apply_op_over_all_bits(op, vector[1:])
        func = getattr(vector[0], op)
        # note that func is method bound to vector[0], which gives vector[0] as a first parameter
        return func(rest)


def rtl_any(*vectorlist):
    """ Hardware equivelent of python native "any".

    :param WireVector *vectorlist: all arguments are WireVectors of length 1
    :return: WireVector of length 1

    Returns a 1-bit wirevector which will hold a '1' if any of the inputs
    are '1' (i.e. it is a big 'ol OR gate)
    """
    if len(vectorlist) <= 0:
        raise PyrtlError('rtl_any requires at least 1 argument')
    block = get_block(*vectorlist)
    converted_vectorlist = [as_wires(v, block=block) for v in vectorlist]
    for v in converted_vectorlist:
        if len(v) != 1:
            raise PyrtlError('only length 1 wirevectors can be inputs to rtl_any')
    return or_all_bits(concat(*converted_vectorlist))


def rtl_all(*vectorlist):
    """ Hardware equivelent of python native "all".

    :param WireVector *vectorlist: all arguments are WireVectors of length 1
    :return: WireVector of length 1

    Returns a 1-bit wirevector which will hold a '1' only if all of the
    inputs are '1' (i.e. it is a big 'ol AND gate)
    """
    if len(vectorlist) <= 0:
        raise PyrtlError('rtl_all requires at least 1 argument')
    block = get_block(*vectorlist)
    converted_vectorlist = [as_wires(v, block=block) for v in vectorlist]
    print(converted_vectorlist)
    for v in converted_vectorlist:
        if len(v) != 1:
            raise PyrtlError('only length 1 wirevectors can be inputs to rtl_any')
    return and_all_bits(concat(*converted_vectorlist))


def mux(select, falsecase, truecase, *rest, **kwargs):
    """ Multiplexer returning falsecase for select==0, otherwise truecase.

    :param WireVector select: used as the select input to the multiplexor
    :param WireVector falsecase: the wirevector selected if select==0
    :param WireVector truecase: the wirevector selected if select==1
    :param additional WireVector arguments *rest: wirevectors selected when select>1
    :param additional WireVector arguments **default: keyword arg "default"
    :return: WireVector of length of the longest input (not including select)

    If you are selecting between less items than your index can address, you can
    use the "default" keyword argument to auto-expand those terms.  For example,
    if you have a 3-bit index but are selecting between 6 options, you need to specify
    a value for those other 2 possible values of index (0b110 and 0b111).  You can
    do that by passing in a default argument, an example of which is below.

    To avoid confusion, if you are using the mux where the select is a "predicate"
    (meaning something that you are checking the truth value of rather than using it
    as a number) it is recommended that you use "falsecase" and "truecase"
    as named arguments because the ordering is different from the classic ternary
    operator of some languages.

    Example of mux as "ternary operator" to take the max of 'a' and 5:
        mux( a<5, truecase=a, falsecase=5)

    Example of mux as "selector" to pick between a0 and a1:
        index = WireVector(1)
        mux( index, a0, a1 )

    Example of mux as "selector" to pick between a0 ... a3:
        index = WireVector(2)
        mux( index, a0, a1, a2, a3 )

    Example of "default" to specify additional arguments:
        index = WireVector(3)
        mux( index, a0, a1, a2, a3, a4, a5, default=0 )
    """

    # only "default" is allowed as kwarg.  If there is a default arg, then
    # copy it out to the
    if kwargs:
        if len(kwargs) != 1 or 'default' not in kwargs:
            bad_args = [k for k in kwargs.keys() if k != 'default']
            raise PyrtlError('unknown keywords %s applied to mux' % str(bad_args))
        default = kwargs['default']
    else:
        default = None

    block = get_block(select, falsecase, truecase, default, *rest)
    select = as_wires(select, block=block)
    ins = [falsecase, truecase] + list(rest)

    if default is not None:
        # find the diff between the addressable range and number of inputs given
        short_by = 2**len(select) - len(ins)
        if short_by > 0:
            # fill in the rest with the default inputs
            extention = [default] * short_by
            ins.extend(extention)

    if 2 ** len(select) != len(ins):
        raise PyrtlError(
            'Mux select line is %d bits, but selecting from %d inputs. '
            % (len(select), len(ins)))

    if len(select) == 1:
        result = _mux2(select, ins[0], ins[1])
    else:
        half = int(len(ins) // 2)
        result = _mux2(select[-1],
                       mux(select[0:-1], *ins[:half]),
                       mux(select[0:-1], *ins[half:]))
    return result


def _mux2(select, falsecase, truecase):
    block = get_block(select, falsecase, truecase)
    select = as_wires(select, block=block)
    a = as_wires(falsecase, block=block)
    b = as_wires(truecase, block=block)

    if len(select) != 1:
        raise PyrtlError('error, select input to the mux must be 1-bit wirevector')
    a, b = match_bitwidth(a, b)
    resultlen = len(a)  # both are the same length now

    outwire = WireVector(bitwidth=resultlen, block=block)
    net = LogicNet(
        op='x',
        op_param=None,
        args=(select, a, b),
        dests=(outwire,))
    outwire.block.add_net(net)
    return outwire


def get_block(*arglist):
    """ Take any number of wire vector params and return the block they are all in.

    If any of the arguments come from different blocks, throw an error.
    If none of the arguments are wirevectors, return the working_block.
    """
    from .memory import _MemIndexed

    blocks = set()
    for arg in arglist:
        if isinstance(arg, _MemIndexed):
            argblock = arg.mem.block
        elif isinstance(arg, WireVector):
            argblock = arg.block
        else:
            argblock = None
        blocks.add(argblock)

    blocks.difference_update({None})  # remove the non block elements

    if len(blocks) > 1:
        raise PyrtlError('get_block passed WireVectors from different blocks')
    elif len(blocks):
        block = blocks.pop()
    else:
        block = working_block()

    return block


def concat(*args):
    """ Take any number of wire vector params and return a wire vector concatinating them.
    The arguments should be WireVectors (or convertable to WireVectors through as_wires).
    The concatination order places the MSB as arg[0] with less signficant bits following.
    """

    block = get_block(*args)
    if len(args) <= 0:
        raise PyrtlError('error, concat requires at least 1 argument')
    if len(args) == 1:
        return as_wires(args[0], block=block)
    else:
        arg_wirevectors = [as_wires(arg, block=block) for arg in args]
        final_width = sum([len(arg) for arg in arg_wirevectors])
        outwire = WireVector(bitwidth=final_width, block=block)
        net = LogicNet(
            op='c',
            op_param=None,
            args=tuple(arg_wirevectors),
            dests=(outwire,))
        outwire.block.add_net(net)
        return outwire


def match_bitwidth(*args):
    # TODO: allow for custom bit extension functions
    """ Matches the bitwidth of all of the input arguments

    :type args: WireVector
    :return tuple of args in order with extended bits
    """
    max_len = max(len(wv) for wv in args)
    return (wv.zero_extended(max_len) for wv in args)


def probe(w, name=None):
    """ Print useful information about a WireVector when in debug mode.

    :type w: WireVector
    :type name: None or string
    :return: original WireVector w

    Probe can be inserted into a existing design easily as it returns the original wire unmodified.
    For example "y <<= x[0:3] + 4" could be turned into "y <<= probe(x)[0:3] + 4" to give visibility
    into both the origin of x (including the line that WireVector was originally created) and the
    run-time values of x (which will be named and thus show up by default in a trace.  Likewise
    "y <<= probe(x[0:3]) + 4", "y <<= probe(x[0:3] + 4)", and "probe(y) <<= x[0:3] + 4" are all
    valid uses of probe.  Note: probe does actually add wire to the working block of w (which can
    confuse various post-processing transforms such as output to verilog)
    """
    global _probe_number
    if not isinstance(w, WireVector):
        raise PyrtlError('Only WireVectors can be probed')

    if w.init_call_stack:
        print('(Probe-%d) Traceback for probed wire, most recent call last' % _probe_number)
        for frame in w.init_call_stack[0:-1]:
            print(frame, end=' ')
        print()
    else:
        print('(Probe-%d)' % _probe_number, end=' ')
        print('    No call info found: use set_debug_mode() to provide more information\n')

    if name:
        pname = '(Probe-%d : %s : %s)' % (_probe_number, name, w.name)
    else:
        pname = '(Probe-%d : %s)' % (_probe_number, w.name)

    p = Output(name=pname, block=get_block(w))
    p <<= w  # late assigns len from w automatically
    _probe_number += 1
    return w


def rtl_assert(w, msg):
    """ Add hardware assertions to be checked on the RTL design.

    w should be a WireVector
    msg should be a string
    returns the Output wire for the assertion (can be ignored in most cases)
    """

    global _rtl_assert_number
    global _rtl_assert_dict

    if not isinstance(w, WireVector):
        raise PyrtlError('Only WireVectors can be asserted with rtl_assert')
    if len(w) != 1:
        raise PyrtlError('rtl_assert checks only a WireVector of bitwidth 1')

    assertion_name = 'assertion%d' % _rtl_assert_number
    assert_wire = Output(bitwidth=1, name=assertion_name, block=get_block(w))
    assert_wire <<= w
    _rtl_assert_number += 1
    _rtl_assert_dict[assert_wire] = msg
    return assert_wire


def _check_for_loop(block=None):
    block = working_block(block)
    logic_left = block.logic.copy()
    wires_left = set(w for w in block.wirevector_set
                     if not isinstance(w, (Input, Const, Output, Register)))
    prev_logic_left = len(logic_left) + 1
    while prev_logic_left > len(logic_left):
        prev_logic_left = len(logic_left)
        nets_to_remove = set()  # bc it's not safe to mutate a set inside its own iterator
        for net in logic_left:
            if not any(n_wire in wires_left for n_wire in net.args):
                nets_to_remove.add(net)
                wires_left.discard(*net.dests)
        logic_left -= nets_to_remove

    if 0 == len(logic_left):
        print("No Loop Found")
        return None
    return wires_left, logic_left


def find_loop(block=None, print_result=True):
    result = _check_for_loop(block)
    if not result:
        return
    wires_left, logic_left = result
    import random

    class _FilteringState(object):
        def __init__(self, dst_w):
            self.dst_w = dst_w
            self.arg_num = -1

    def dead_end():
        # clean up after a wire is found to not be part of the loop
        wires_left.discard(cur_item.dst_w)
        current_wires.discard(cur_item.dst_w)
        del checking_stack[-1]

    # now making a map to quickly look up nets
    dest_nets = {dest_w: net_ for net_ in logic_left for dest_w in net_.dests}
    initial_w = random.sample(wires_left, 1)[0]

    current_wires = set()
    checking_stack = [_FilteringState(initial_w)]

    # we don't use a recursive method as Python has a limited stack (default: 999 frames)
    while len(checking_stack):
        cur_item = checking_stack[-1]
        if cur_item.arg_num == -1:
            #  first time testing this item
            if cur_item.dst_w not in wires_left:
                dead_end()
                continue
            current_wires.add(cur_item.dst_w)
            cur_item.net = dest_nets[cur_item.dst_w]
            if cur_item.net.op == 'r':
                dead_end()
                continue
        cur_item.arg_num += 1  # go to the next item
        if cur_item.arg_num == len(cur_item.net.args):
            dead_end()
            continue
        next_wire = cur_item.net.args[cur_item.arg_num]
        if next_wire not in current_wires:
            current_wires.add(next_wire)
            checking_stack.append(_FilteringState(next_wire))
        else:  # We have found the loop!!!!!
            loop_info = []
            for f_state in reversed(checking_stack):
                loop_info.append(f_state)
                if f_state.dst_w is next_wire:
                    break
            else:
                raise PyrtlError("Shouldn't get here! Couldn't figure out the loop")
            if print_result:
                print("Loop found:")
                print('\n'.join("{}".format(fs.net) for fs in loop_info))
                # print '\n'.join("{} (dest wire: {})".format(fs.net, fs.dst_w) for fs in loop_info)
                print("")
            return loop_info
    raise PyrtlError("Error in detecting loop")
