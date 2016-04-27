""" Defines a set of helper functions that make constructing hardware easier.

The set of functions includes
as_wires: converts consts to wires if needed (and does nothing to wires)
and_all_bits, or_all_bits, xor_all_bits: apply function across all bits
parity: same as xor_all_bits
mux: generate a multiplexer
concat: concatenate multiple wirevectors into one long vector
get_block: get the block of the arguments, throw error if they are different
"""

from __future__ import print_function, unicode_literals

import six

from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .core import working_block, LogicNet
from .wire import WireVector, Input, Output, Const, Register

_rtl_assert_number = 1
_probe_number = 1

# -----------------------------------------------------------------
#        ___       __   ___  __   __
#  |__| |__  |    |__) |__  |__) /__`
#  |  | |___ |___ |    |___ |  \ .__/
#


def input_list(names, bitwidth=1):
    """ Allocate and return a list of Inputs. """
    return wirevector_list(names, bitwidth, wvtype=Input)


def output_list(names, bitwidth=1):
    """ Allocate and return a list of Outputs. """
    return wirevector_list(names, bitwidth, wvtype=Output)


def register_list(names, bitwidth=1):
    """ Allocate and return a list of Registers. """
    return wirevector_list(names, bitwidth, wvtype=Register)


def wirevector_list(names, bitwidth=1, wvtype=WireVector):
    """ Allocate and return a list of WireVectors. """
    if '/' in names and bitwidth != 1:
        raise PyrtlError('only one of optional "/" or bitwidth parameter allowed')
    names = names.replace(',', ' ')

    wirelist = []
    for fullname in names.split():
        try:
            name, bw = fullname.split('/')
        except:
            name, bw = fullname, bitwidth
        wirelist.append(wvtype(bitwidth=bw, name=name))
    return wirelist


def as_wires(val, bitwidth=None, truncating=True, block=None):
    """ Return wires from val which may be wires, integers, strings, or bools.

    :param val: a wirevector-like object or something that can be converted into
      a Const
    :param bitwidth: The bitwidth the resulting wire should be
    :param bool truncating: determines whether bits will be dropped to acheive
     the desired bitwidth if it is too long (if true, the most-significant-bits
     will be dropped)
    :param Block block: block to use for wire

    This function is mainly used to coerce values into WireVectors (for
    example, operations such as "x+1" where "1" needs to be converted to
    a Const WireVector.)
    """
    from .memory import _MemIndexed
    block = working_block(block)

    if isinstance(val, (int, six.string_types)):
        # note that this case captures bool as well (as bools are instances of ints)
        return Const(val, bitwidth=bitwidth, block=block)
    elif isinstance(val, _MemIndexed):
        # covert to a memory read when the value is actually used
        return as_wires(val.mem._readaccess(val.index), bitwidth, truncating, block)
    elif not isinstance(val, WireVector):
        raise PyrtlError('error, expecting a wirevector, int, or verilog-style '
                         'const string got %s instead' % repr(val))
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
    """ Returns WireVector, the result of "and"ing all items of the argument vector."""
    return _apply_op_over_all_bits(lambda a, b: a & b, vector)


def or_all_bits(vector):
    """ Returns WireVector, the result of "or"ing all items of the argument vector."""
    return _apply_op_over_all_bits(lambda a, b: a | b, vector)


def xor_all_bits(vector):
    """ Returns WireVector, the result of "xor"ing all items of the argument vector."""
    return _apply_op_over_all_bits(lambda a, b: a ^ b, vector)


parity = xor_all_bits  # shadowing the xor_all_bits_function


def _apply_op_over_all_bits(op, vector):
    if len(vector) == 1:
        return vector[0]
    rest = _apply_op_over_all_bits(op, vector[1:])
    return op(vector[0], rest)


def rtl_any(*vectorlist):
    """ Hardware equivalent of python native "any".

    :param WireVector *vectorlist: all arguments are WireVectors of length 1
    :return: WireVector of length 1

    Returns a 1-bit wirevector which will hold a '1' if any of the inputs
    are '1' (i.e. it is a big 'ol OR gate)
    """
    if len(vectorlist) <= 0:
        raise PyrtlError('rtl_any requires at least 1 argument')
    block = get_block(*vectorlist)
    converted_vectorlist = [as_wires(v, block=block) for v in vectorlist]
    if any(len(v) != 1 for v in converted_vectorlist):
        raise PyrtlError('only length 1 wirevectors can be inputs to rtl_any')
    return or_all_bits(concat_list(converted_vectorlist))


def rtl_all(*vectorlist):
    """ Hardware equivalent of python native "all".

    :param WireVector *vectorlist: all arguments are WireVectors of length 1
    :return: WireVector of length 1

    Returns a 1-bit wirevector which will hold a '1' only if all of the
    inputs are '1' (i.e. it is a big 'ol AND gate)
    """
    if len(vectorlist) <= 0:
        raise PyrtlError('rtl_all requires at least 1 argument')
    block = get_block(*vectorlist)
    converted_vectorlist = [as_wires(v, block=block) for v in vectorlist]
    if any(len(v) != 1 for v in converted_vectorlist):
        raise PyrtlError('only length 1 wirevectors can be inputs to rtl_all')
    return and_all_bits(concat_list(converted_vectorlist))


def _basic_mult(A, B):
    """ a stripped down copy of the wallace multiplier in rtllib """
    if len(B) == 1:
        A, B = B, A  # so that we can reuse the code below :)
    if len(A) == 1:
        return concat_list(list(A & b for b in B) + [Const(0)])  # keep WireVector len consistent

    result_bitwidth = len(A) + len(B)
    bits = [[] for weight in range(result_bitwidth)]
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            bits[i + j].append(a & b)

    while not all(len(i) <= 2 for i in bits):
        deferred = [[] for weight in range(result_bitwidth + 1)]
        for i, w_array in enumerate(bits):  # Start with low weights and start reducing
            while len(w_array) >= 3:  # build a new full adder
                a, b, cin = (w_array.pop(0) for j in range(3))
                deferred[i].append(a ^ b ^ cin)
                deferred[i + 1].append(a & b | a & cin | b & cin)
            if len(w_array) == 2:
                a, b = w_array
                deferred[i].append(a ^ b)
                deferred[i + 1].append(a & b)
            else:
                deferred[i].extend(w_array)
        bits = deferred[:result_bitwidth]

    import six
    add_wires = tuple(six.moves.zip_longest(*bits, fillvalue=Const(0)))
    adder_result = concat_list(add_wires[0]) + concat_list(add_wires[1])
    return adder_result[:result_bitwidth]


def _one_bit_add(a, b, carry_in):
    assert len(a) == len(b) == 1
    sumbit = a ^ b ^ carry_in
    carry_out = a & b | a & carry_in | b & carry_in
    return sumbit, carry_out


def _add_helper(a, b, carry_in):
    a, b = match_bitwidth(a, b)
    if len(a) == 1:
        sumbits, carry_out = _one_bit_add(a, b, carry_in)
    else:
        lsbit, ripplecarry = _one_bit_add(a[0], b[0], carry_in)
        msbits, carry_out = _add_helper(a[1:], b[1:], ripplecarry)
        sumbits = concat(msbits, lsbit)
    return sumbits, carry_out


def _basic_add(a, b):
    sumbits, carry_out = _add_helper(a, b, 0)
    return concat(carry_out, sumbits)


def _basic_sub(a, b):
    sumbits, carry_out = _add_helper(a, ~b, 1)
    return concat(carry_out, sumbits)


def _basic_eq(a, b):
    return ~ or_all_bits(a ^ b)


def _basic_lt(a, b):
    assert len(a) == len(b)
    a_msb = a[-1]
    b_msb = b[-1]
    if len(a) == 1:
        return (b_msb & ~a_msb)
    small = _basic_lt(a[:-1], b[:-1])
    return (b_msb & ~a_msb) | (small & ~(a_msb ^ b_msb))


def _basic_gt(a, b):
    return _basic_lt(b, a)


def _basic_select(s, a, b):
    assert len(a) == len(b)
    assert len(s) == 1
    sa = concat(*[~s]*len(a))
    sb = concat(*[s]*len(b))
    return (a & sa) | (b & sb)


def mux(index, *mux_ins, **kwargs):
    """ Multiplexer returning the value of the wire in .

    :param WireVector index: used as the select input to the multiplexor
    :param additional WireVector arguments *mux_ins: wirevectors selected when select>1
    :param additional WireVector arguments **default: keyword arg "default"
      If you are selecting between less items than your index can address, you can
      use the "default" keyword argument to auto-expand those terms.  For example,
      if you have a 3-bit index but are selecting between 6 options, you need to specify
      a value for those other 2 possible values of index (0b110 and 0b111).
    :return: WireVector of length of the longest input (not including select)

    To avoid confusion, if you are using the mux where the select is a "predicate"
    (meaning something that you are checking the truth value of rather than using it
    as a number) it is recommended that you use the select function instead
    as named arguments because the ordering is different from the classic ternary
    operator of some languages.

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
    if kwargs:  # only "default" is allowed as kwarg.
        if len(kwargs) != 1 or 'default' not in kwargs:
            try:
                result = select(index, **kwargs)
                import warnings
                warnings.warn("Predicates are being deprecated in Mux. "
                              "Use the select operator instead.", stacklevel=2)
                return result
            except Exception:
                bad_args = [k for k in kwargs.keys() if k != 'default']
                raise PyrtlError('unknown keywords %s applied to mux' % str(bad_args))
        default = kwargs['default']
    else:
        default = None

    # find the diff between the addressable range and number of inputs given
    short_by = 2**len(index) - len(mux_ins)
    if short_by > 0:
        if default is not None:  # extend the list to appropriate size
            mux_ins = list(mux_ins)
            extention = [default] * short_by
            mux_ins.extend(extention)

    if 2 ** len(index) != len(mux_ins):
        raise PyrtlError(
            'Mux select line is %d bits, but selecting from %d inputs. '
            % (len(index), len(mux_ins)))

    if len(index) == 1:
        return select(index, falsecase=mux_ins[0], truecase=mux_ins[1])
    half = len(mux_ins) // 2
    return select(index[-1],
                  falsecase=mux(index[0:-1], *mux_ins[:half]),
                  truecase=mux(index[0:-1], *mux_ins[half:]))


def select(sel, truecase, falsecase):
    """ Multiplexer returning falsecase for select==0, otherwise truecase.

    :param WireVector sel: used as the select input to the multiplexor
    :param WireVector falsecase: the wirevector selected if select==0
    :param WireVector truecase: the wirevector selected if select==1
    Example of mux as "ternary operator" to take the max of 'a' and 5:
        mux( a<5, truecase=a, falsecase=5)
    """

    block = get_block(sel, falsecase, truecase)
    sel, f, t = (as_wires(w, block=block) for w in (sel, falsecase, truecase))

    if len(sel) != 1:
        raise PyrtlError('error, select input to the mux must be 1-bit wirevector')
    f, t = match_bitwidth(f, t)
    resultlen = len(f)  # both are the same length now

    outwire = WireVector(bitwidth=resultlen, block=block)
    net = LogicNet(op='x', op_param=None,
                   args=(sel, f, t), dests=(outwire,))
    block.add_net(net)
    return outwire


def get_block(*arglist):
    """ Take any number of wire vector params and return the block they are all in.

    If any of the arguments come from different blocks, throw an error.
    If none of the arguments are wirevectors, return the working_block.
    """
    blocks = set()
    for arg in arglist:
        if isinstance(arg, WireVector):
            blocks.add(arg.block)

    blocks.difference_update({None})  # remove the non block elements

    if len(blocks) > 1:
        raise PyrtlError('get_block passed WireVectors from different blocks')
    elif len(blocks):
        block = blocks.pop()
    else:
        block = working_block()

    return block


def concat(*args):
    """
    Concats multiple wirevectors into a single wirevector

    :type args: WireVector
    :return wirevector: wirevector with length equal
      to the sum of the args' lengths

    Usually you will want to use concat_list as you will not need to reverse the list
    The concatenation order places the MSB as arg[0] with less significant bits following.
    """
    if len(args) <= 0:
        raise PyrtlError('error, concat requires at least 1 argument')
    if len(args) == 1:
        return as_wires(args[0])

    block = get_block(*args)
    arg_wirevectors = tuple(as_wires(arg, block=block) for arg in args)
    final_width = sum(len(arg) for arg in arg_wirevectors)
    outwire = WireVector(bitwidth=final_width, block=block)
    net = LogicNet(
        op='c',
        op_param=None,
        args=arg_wirevectors,
        dests=(outwire,))
    block.add_net(net)
    return outwire


def concat_list(wire_list):
    """
    Concats a list of wirevectors into a single wirevector

    :param wire_list: List of wirevectors to concat
    :return wirevector: wirevector with length equal
      to the sum of the args' lengths

    The concatenation order is LSB (UNLIKE Concat)
    """
    return concat(*reversed(wire_list))


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

    print('(Probe-%d)' % _probe_number, end=' ')
    print(get_stack(w))

    if name:
        pname = '(Probe-%d : %s : %s)' % (_probe_number, name, w.name)
    else:
        pname = '(Probe-%d : %s)' % (_probe_number, w.name)

    p = Output(name=pname, block=get_block(w))
    p <<= w  # late assigns len from w automatically
    _probe_number += 1
    return w


def get_stacks(*wires):
    call_stack = getattr(wires[0], 'init_call_stack', None)
    if not call_stack:
        return '    No call info found for wires: use set_debug_mode() ' \
               'to provide more information\n'
    else:
        return '\n'.join(str(wire) + ":\n" + get_stack(wire) for wire in wires)


def get_stack(wire):
    if not isinstance(wire, WireVector):
        raise PyrtlError('Only WireVectors can be traced')

    call_stack = getattr(wire, 'init_call_stack', None)
    if call_stack:
        frames = ' '.join(frame for frame in call_stack[:-1])
        return "Wire Traceback, most recent call last \n" + frames + "\n"
    else:
        return '    No call info found for wire: use set_debug_mode()'\
               ' to provide more information'


def rtl_assert(w, exp, block=None):
    """ Add hardware assertions to be checked on the RTL design.

    :param w: should be a WireVector
    :param Exception exp: Exception to throw when assertion fails
    :param Block block: block to which the assertion should be added (default to working block)
    :return: the Output wire for the assertion (can be ignored in most cases)

    If at any time during execution the wire w is not `true` (i.e. asserted low)
    then simulation will raise exp.
    """

    global _rtl_assert_number

    block = working_block(block)

    if not isinstance(w, WireVector):
        raise PyrtlError('Only WireVectors can be asserted with rtl_assert')
    if len(w) != 1:
        raise PyrtlError('rtl_assert checks only a WireVector of bitwidth 1')
    if not isinstance(exp, Exception):
        raise PyrtlError('the second argument to rtl_assert must be an instance of Exception')
    if isinstance(exp, KeyError):
        raise PyrtlError('the second argument to rtl_assert cannot be a KeyError')
    if get_block(w) is not block:
        raise PyrtlError('assertion wire not part of the block to which it is being added')
    if w not in block.wirevector_set:
        raise PyrtlError('assertion not a known wirevector in the target block')

    if w in block.rtl_assert_dict:
        raise PyrtlInternalError('assertion conflicts with existing registered assertion')

    assertion_name = 'assertion%d' % _rtl_assert_number
    assert_wire = Output(bitwidth=1, name=assertion_name, block=block)
    assert_wire <<= w
    _rtl_assert_number += 1
    block.rtl_assert_dict[assert_wire] = exp
    return assert_wire


def check_rtl_assertions(sim):
    """ Checks the values in sim to see if any registers assertions fail.

    :param sim: Simulation in which to check the assertions
    :return: None
    """

    for (w, exp) in sim.block.rtl_assert_dict.items():
        try:
            value = sim.inspect(w)
            if not value:
                raise exp
        except KeyError:
            pass


def _check_for_loop(block=None):
    block = working_block(block)
    logic_left = block.logic.copy()
    wires_left = block.wirevector_subset(exclude=(Input, Const, Output, Register))
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
        return None
    return wires_left, logic_left


def find_loop(block=None):
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
            return loop_info
    raise PyrtlError("Error in detecting loop")


def find_and_print_loop(block=None):
    loop_data = find_loop(block)
    print_loop(loop_data)
    return loop_data


def print_loop(loop_data):
    if not loop_data:
        print("No Loop Found")
    else:
        print("Loop found:")
        print('\n'.join("{}".format(fs.net) for fs in loop_data))
        # print '\n'.join("{} (dest wire: {})".format(fs.net, fs.dst_w) for fs in loop_info)
        print("")


def _currently_in_ipython():
    """ Return true if running under ipython, otherwise return False. """
    try:
        __IPYTHON__  # pylint: disable=undefined-variable
        return True
    except NameError:
        return False
