"""
Defines a set of helper functions that make constructing hardware easier.

The set of functions includes
as_wires: converts consts to wires if needed (and does nothing to wires)
and_all_bits, or_all_bits, xor_all_bits: apply function across all bits
parity: same as xor_all_bits
mux: generate a multiplexer
concat: concatenate multiple wirevectors into one long vector
get_block: get the block of the arguments, throw error if they are different
appropriate_register_type: return the register needed to capture the given type
"""

import core
import wire
import memblock


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
    block = core.working_block(block)

    if isinstance(val, (int, basestring)):
        # note that this case captures bool as well (as bools are instances of ints)
        return wire.Const(val, bitwidth=bitwidth, block=block)
    elif isinstance(val, memblock._MemIndexed):
        return val.mem._readaccess(val.index)
    elif not isinstance(val, wire.WireVector):
        raise core.PyrtlError('error, expecting a wirevector, int, or verilog-style const string')
    elif bitwidth == '0':
        raise core.PyrtlError('error, bitwidth must be >= 1')
    elif bitwidth and bitwidth > val.bitwidth:
        return val.extended(bitwidth)  # extend appropriately
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
        return func(vector[0], rest)


def mux(select, falsecase, truecase):
    """ Multiplexer returning falsecase for select==0, otherwise truecase.

    To avoid confusion it is recommended that you use "falsecase" and "truecase"
    as named arguments because the ordering is different from the classic ternary
    operator of some languages
    """

    block = get_block(select, falsecase, truecase)
    select = as_wires(select, block=block)
    a = as_wires(falsecase, block=block)
    b = as_wires(truecase, block=block)

    if len(select) != 1:
        raise core.PyrtlError('error, select input to the mux must be 1-bit wirevector')
    if len(a) < len(b):
        a = a.extended(len(b))
    elif len(b) < len(a):
        b = b.extended(len(a))
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
    block = None
    for arg in arglist:
        if isinstance(arg, wire.WireVector):
            if block and block is not arg.block:
                raise core.PyrtlError('get_block passed WireVectors from differnt blocks')
            else:
                block = arg.block
    # use working block is block is still None
    block = core.working_block(block)
    return block


def concat(*args):
    """ Take any number of wire vector params and return a wire vector concatinating them.
    
    The arguments should be WireVectors (or convertable to WireVectors through as_wires).
    The concatination order places the MSB as arg[0] with less signficant bits following."""

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


def appropriate_register_type(t):
    """ take a type t, return a type which is appropriate for registering t (signed or unsigned)."""

    if isinstance(t, (wire.Output, wire.Const)):
        # includes signed versions
        raise core.PyrtlError('error, no appropriate register type for outputs or constants')
    elif isinstance(t, (wire.SignedWireVector, wire.SignedInput, wire.SignedRegister)):
        return wire.SignedRegister
    elif isinstance(t, (wire.WireVector, wire.Input, wire.Register)):
        return wire.Register
    else:
        raise core.PyrtlError('error, unknown type "%s" passed as argument' % str(type(t)))
