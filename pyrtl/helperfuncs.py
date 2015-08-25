"""
 Defines a set of helper functions that make constructing hardware easier.

The set of functions includes
as_wires: converts consts to wires if needed (and does nothing to wires)
and_all_bits, or_all_bits, xor_all_bits: apply function across all bits
parity: same as xor_all_bits
mux: generate a multiplexer
concat: concatenate multiple wirevectors into one long vector
get_block: get the block of the arguments, throw error if they are different
"""

import core
import wire
import inspect

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
    import memory
    block = core.working_block(block)

    if isinstance(val, (int, basestring)):
        # note that this case captures bool as well (as bools are instances of ints)
        return wire.Const(val, bitwidth=bitwidth, block=block)
    elif isinstance(val, memory._MemIndexed):
        # covert to a memory read when the value is actually used
        return val.mem._readaccess(val.index)
    elif not isinstance(val, wire.WireVector):
        raise core.PyrtlError('error, expecting a wirevector, int, or verilog-style const string')
    elif bitwidth == '0':
        raise core.PyrtlError('error, bitwidth must be >= 1')
    elif val.bitwidth is None:
        raise core.PyrtlError('error, attempting to use wirevector with no defined bitwidth')
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
        raise core.PyrtlError('rtl_any requires at least 1 argument')
    block = get_block(*vectorlist)
    converted_vectorlist = [as_wires(v, block=block) for v in vectorlist]
    for v in converted_vectorlist:
        if len(v) != 1:
            raise core.PyrtlError('only length 1 wirevectors can be inputs to rtl_any')
    return or_all_bits(concat(*converted_vectorlist))


def rtl_all(*vectorlist):
    """ Hardware equivelent of python native "all".

    :param WireVector *vectorlist: all arguments are WireVectors of length 1
    :return: WireVector of length 1

    Returns a 1-bit wirevector which will hold a '1' only if all of the
    inputs are '1' (i.e. it is a big 'ol AND gate)
    """
    if len(vectorlist) <= 0:
        raise core.PyrtlError('rtl_all requires at least 1 argument')
    block = get_block(*vectorlist)
    converted_vectorlist = [as_wires(v, block=block) for v in vectorlist]
    print converted_vectorlist
    for v in converted_vectorlist:
        if len(v) != 1:
            raise core.PyrtlError('only length 1 wirevectors can be inputs to rtl_any')
    return and_all_bits(concat(*converted_vectorlist))


def mux(select, falsecase, truecase, *rest):
    """ Multiplexer returning falsecase for select==0, otherwise truecase.

    :param WireVector select: used as the select input to the multiplexor
    :param WireVector falsecase: the wirevector selected if select==0
    :param WireVector truecase: the wirevector selected if select==1
    :param additional WireVector arguments *rest: wirevectors selected when select>1
    :return: WireVector of length of the longest input (not including select)

    To avoid confusion, if you are using the mux where the select is a "predicate"
    (meaning something that you are checking the truth value of rather than using it
    as a number) it is recommended that you use "falsecase" and "truecase"
    as named arguments because the ordering is different from the classic ternary
    operator of some languages.

    Example of mux as "ternary operator" to take the max of 'a' and 5:
        mux( a<5, truecase=a, falsecase=5)

    Example of mux as "selector" to pick between a0 and a1:
        mux( index, a0, a1 )

    Example of mux as "selector" to pick between a0 ... a3:
        mux( index, a0, a1, a2, a3 )
    """
    block = get_block(select, falsecase, truecase, *rest)
    select = as_wires(select, block=block)
    ins = [falsecase, truecase] + list(rest)

    if 2 ** len(select) != len(ins):
        raise core.PyrtlError(
            'error, mux select line is %d bits, but selecting from %d inputs'
            % (len(select), len(ins)))

    if len(select) == 1:
        result = _mux2(select, ins[0], ins[1])
    else:
        half = int(len(ins) / 2)
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
        raise core.PyrtlError('error, select input to the mux must be 1-bit wirevector')
    a, b = match_bitwidth(a, b)
    resultlen = len(a)  # both are the same length now

    outwire = wire.WireVector(bitwidth=resultlen, block=block)
    net = core.LogicNet(
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
    import memory

    blocks = set()
    for arg in arglist:
        if isinstance(arg, memory._MemIndexed):
            argblock = arg.mem.block
        elif isinstance(arg, wire.WireVector):
            argblock = arg.block
        else:
            argblock = None
        blocks.add(argblock)

    blocks.difference_update({None})  # remove the non block elements

    if len(blocks) > 1:
        raise core.PyrtlError('get_block passed WireVectors from different blocks')
    elif len(blocks):
        block = blocks.pop()
    else:
        block = core.working_block()

    return block


def concat(*args):
    """ Take any number of wire vector params and return a wire vector concatinating them.
    The arguments should be WireVectors (or convertable to WireVectors through as_wires).
    The concatination order places the MSB as arg[0] with less signficant bits following.
    """

    block = get_block(*args)
    if len(args) <= 0:
        raise core.PyrtlError('error, concat requires at least 1 argument')
    if len(args) == 1:
        return as_wires(args[0], block=block)
    else:
        arg_wirevectors = [as_wires(arg, block=block) for arg in args]
        final_width = sum([len(arg) for arg in arg_wirevectors])
        outwire = wire.WireVector(bitwidth=final_width, block=block)
        net = core.LogicNet(
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
    if not isinstance(w, wire.WireVector):
        raise core.PyrtlError('Only WireVectors can be probed')

    if w.init_call_stack:
        print '(Probe-%d) Traceback for probed wire, most recent call last' % _probe_number
        for frame in w.init_call_stack[0:-1]:
            print frame,
        print
    else:
        print '(Probe-%d)' % _probe_number,
        print '    No call info found: use set_debug_mode() to provide more information\n'

    if name:
        pname = '(Probe-%d : %s : %s)' % (_probe_number, name, w.name)
    else:
        pname = '(Probe-%d : %s)' % (_probe_number, w.name)

    p = wire.Output(name=pname, block=get_block(w))
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

    if not isinstance(w, wire.WireVector):
        raise core.PyrtlError('Only WireVectors can be asserted with rtl_assert')
    if len(w) != 1:
        raise core.PyrtlError('rtl_assert checks only a WireVector of bitwidth 1')

    assertion_name = 'assertion%d' % _rtl_assert_number
    assert_wire = wire.Output(bitwidth=1, name=assertion_name, block=get_block(w))
    assert_wire <<= w
    _rtl_assert_number += 1
    _rtl_assert_dict[assert_wire] = msg
    return assert_wire
