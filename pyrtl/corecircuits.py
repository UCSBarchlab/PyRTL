""" Some useful hardware generators (e.g. muxes, signed multipliers, etc.)  """

from __future__ import division

import six
import math

from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .core import LogicNet, working_block
from .wire import Const, WireVector
from pyrtl.rtllib import barrel
from pyrtl.rtllib import muxes
from .conditional import otherwise


def mux(index, *mux_ins, **kwargs):
    """ Multiplexer returning the value of the wire from mux_ins according to index.

    :param WireVector index: used as the select input to the multiplexer
    :param WireVector mux_ins: additional WireVector arguments selected when select>1
    :param WireVector kwargs: additional WireVectors, keyword arg "default"
      If you are selecting between fewer items than your index can address, you can
      use the "default" keyword argument to auto-expand those terms.  For example,
      if you have a 3-bit index but are selecting between 6 options, you need to specify
      a value for those other 2 possible values of index (0b110 and 0b111).
    :return: WireVector of length of the longest input (not including select)

    To avoid confusion, if you are using the mux where the select is a "predicate"
    (meaning something that you are checking the truth value of rather than using it
    as a number) it is recommended that you use the select function instead
    as named arguments because the ordering is different from the classic ternary
    operator of some languages.

    Example of mux as "selector" to pick between a0 and a1: ::

        index = WireVector(1)
        mux(index, a0, a1)

    Example of mux as "selector" to pick between a0 ... a3: ::

        index = WireVector(2)
        mux(index, a0, a1, a2, a3)

    Example of "default" to specify additional arguments: ::

        index = WireVector(3)
        mux(index, a0, a1, a2, a3, a4, a5, default=0)
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
    index = as_wires(index)
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

    :param WireVector sel: used as the select input to the multiplexer
    :param WireVector truecase: the WireVector selected if select==1
    :param WireVector falsecase: the WireVector selected if select==0

    The hardware this generates is exactly the same as "mux" but by putting the
    true case as the first argument it matches more of the C-style ternary operator
    semantics which can be helpful for readability.

    Example of mux as "ternary operator" to take the min of 'a' and 5: ::

        select(a<5, truecase=a, falsecase=5)
    """
    sel, f, t = (as_wires(w) for w in (sel, falsecase, truecase))
    f, t = match_bitwidth(f, t)
    outwire = WireVector(bitwidth=len(f))

    net = LogicNet(op='x', op_param=None, args=(sel, f, t), dests=(outwire,))
    working_block().add_net(net)  # this includes sanity check on the mux
    return outwire


def concat(*args):
    """ Concatenates multiple WireVectors into a single WireVector.

    :param WireVector args: inputs to be concatenated
    :return: WireVector with length equal to the sum of the args' lengths

    You can provide multiple arguments and they will be combined with the right-most
    argument being the least significant bits of the result.  Note that if you have
    a list of arguments to concat together you will likely want index 0 to be the least
    significant bit and so if you unpack the list into the arguments here it will be
    backwards.  The function concat_list is provided for that case specifically.

    Example using concat to combine two bytes into a 16-bit quantity: ::

        concat(msb, lsb)
    """
    if len(args) <= 0:
        raise PyrtlError('error, concat requires at least 1 argument')
    if len(args) == 1:
        return as_wires(args[0])

    arg_wirevectors = tuple(as_wires(arg) for arg in args)
    final_width = sum(len(arg) for arg in arg_wirevectors)
    outwire = WireVector(bitwidth=final_width)
    net = LogicNet(
        op='c',
        op_param=None,
        args=arg_wirevectors,
        dests=(outwire,))
    working_block().add_net(net)
    return outwire


def concat_list(wire_list):
    """ Concatenates a list of WireVectors into a single WireVector.

    :param wire_list: list of WireVectors to concat
    :return: WireVector with length equal to the sum of the args' lengths

    This take a list of WireVectors and concats them all into a single
    WireVector with the element at index 0 serving as the least significant bits.
    This is useful when you have a variable number of WireVectors to concatenate,
    otherwise "concat" is prefered.

    Example using concat to combine two bytes into a 16-bit quantity: ::

        mylist = [lsb, msb]
        concat_list(mylist)

    """
    return concat(*reversed(wire_list))


def signed_add(a, b):
    """ Return a WireVector for result of signed addition.

    :param a: a WireVector to serve as first input to addition
    :param b: a WireVector to serve as second input to addition

    Given a length n and length m WireVector the result of the
    signed addition is length max(n,m)+1.  The inputs are twos
    complement sign extended to the same length before adding.
    If an integer is passed to either a or b, it will be converted
    automatically to a two's complemented constant"""
    if isinstance(a, int):
        a = Const(a, signed=True)
    if isinstance(b, int):
        b = Const(b, signed=True)
    a, b = match_bitwidth(as_wires(a), as_wires(b), signed=True)
    result_len = len(a) + 1
    ext_a = a.sign_extended(result_len)
    ext_b = b.sign_extended(result_len)
    # add and truncate to the correct length
    return (ext_a + ext_b)[0:result_len]


def mult_signed(a, b):
    """ mult_signed is now deprecated, use ``signed_mult`` instead """
    return signed_mult(a, b)


def signed_mult(a, b):
    """ Return a*b where a and b are treated as signed values.

    :param a: a wirevector to serve as first input to multiplication
    :param b: a wirevector to serve as second input to multiplication

    If an integer is passed to either a or b, it will be converted
    automatically to a two's complemented constant"""
    # if an integer, convert to a two's complement constant
    if isinstance(a, int):
        a = Const(a, signed=True)
    if isinstance(b, int):
        b = Const(b, signed=True)
    # if not a wirevector yet, use standard conversion method
    a, b = as_wires(a), as_wires(b)
    final_len = len(a) + len(b)
    # sign extend both inputs to the final target length
    a, b = a.sign_extended(final_len), b.sign_extended(final_len)
    # the result is the multiplication of both, but truncated
    # TODO: this may make estimates based on the multiplication overly
    # pessimistic as half of the multiply result is thrown right away!
    return (a * b)[0:final_len]


def signed_lt(a, b):
    """ Return a single bit result of signed less than comparison. """
    a, b = match_bitwidth(as_wires(a), as_wires(b), signed=True)
    r = a - b
    return r[-1] ^ (~a[-1]) ^ (~b[-1])


def signed_le(a, b):
    """ Return a single bit result of signed less than or equal comparison. """
    a, b = match_bitwidth(as_wires(a), as_wires(b), signed=True)
    r = a - b
    return (r[-1] ^ (~a[-1]) ^ (~b[-1])) | (a == b)


def signed_gt(a, b):
    """ Return a single bit result of signed greater than comparison. """
    a, b = match_bitwidth(as_wires(a), as_wires(b), signed=True)
    r = b - a
    return r[-1] ^ (~a[-1]) ^ (~b[-1])


def signed_ge(a, b):
    """ Return a single bit result of signed greater than or equal comparison. """
    a, b = match_bitwidth(as_wires(a), as_wires(b), signed=True)
    r = b - a
    return (r[-1] ^ (~a[-1]) ^ (~b[-1])) | (a == b)


def _check_shift_inputs(a, shamt):
    # TODO: perhaps this should just be implemented directly rather than throwing error
    if isinstance(shamt, int):
        raise PyrtlError('shift_amount is an integer, use slice instead')
    a, shamt = as_wires(a), as_wires(shamt)
    log_length = int(math.log(len(a), 2))
    return a, shamt


def shift_left_arithmetic(bits_to_shift, shift_amount):
    """ Shift left arithmetic operation.

    :param bits_to_shift: WireVector to shift left
    :param shift_amount: WireVector or integer specifying amount to shift
    :return: WireVector of same length as bits_to_shift

    This function returns a new WireVector of length equal to the length
    of the input `bits_to_shift` but where the bits have been shifted
    to the left.  An arithemetic shift is one that treats the value as
    as signed number, although for left shift arithmetic and logic shift
    they are identical.  Note that `shift_amount` is treated as unsigned.
    """
    # shift left arithmetic and logical are the same thing
    return shift_left_logical(bits_to_shift, shift_amount)


def shift_right_arithmetic(bits_to_shift, shift_amount):
    """ Shift right arithmetic operation.

    :param bits_to_shift: WireVector to shift right
    :param shift_amount: WireVector or integer specifying amount to shift
    :return: WireVector of same length as bits_to_shift

    This function returns a new WireVector of length equal to the length
    of the input `bits_to_shift` but where the bits have been shifted
    to the right.  An arithemetic shift is one that treats the value as
    as signed number, meaning the sign bit (the most significant bit of
    `bits_to_shift`) is shifted in. Note that `shift_amount` is treated as
    unsigned.
    """
    if isinstance(shift_amount, int):
        return bits_to_shift[shift_amount:].sign_extended(len(bits_to_shift))

    bit_in = bits_to_shift[-1]  # shift in sign_bit
    dir = Const(0)  # shift right
    return barrel.barrel_shifter(bits_to_shift, bit_in, dir, shift_amount)


def shift_left_logical(bits_to_shift, shift_amount):
    """ Shift left logical operation.

    :param bits_to_shift: WireVector to shift left
    :param shift_amount: WireVector or integer specifying amount to shift
    :return: WireVector of same length as bits_to_shift

    This function returns a new WireVector of length equal to the length
    of the input `bits_to_shift` but where the bits have been shifted
    to the left.  A logical shift is one that treats the value as
    as unsigned number, meaning the zeroes are shifted in.  Note that
    `shift_amount` is treated as unsigned.
    """
    if isinstance(shift_amount, int):
        return concat(bits_to_shift[:-shift_amount], Const(0, shift_amount))

    bit_in = Const(0)  # shift in a 0
    dir = Const(1)  # shift left
    return barrel.barrel_shifter(bits_to_shift, bit_in, dir, shift_amount)


def shift_right_logical(bits_to_shift, shift_amount):
    """ Shift right logical operation.

    :param bits_to_shift: WireVector to shift left
    :param shift_amount: WireVector or integer specifying amount to shift
    :return: WireVector of same length as bits_to_shift

    This function returns a new WireVector of length equal to the length
    of the input `bits_to_shift` but where the bits have been shifted
    to the right.  A logical shift is one that treats the value as
    as unsigned number, meaning the zeros are shifted in regardless of
    the "sign bit".  Note that `shift_amount` is treated as unsigned.
    """
    if isinstance(shift_amount, int):
        return bits_to_shift[shift_amount:].zero_extended(len(bits_to_shift))

    bit_in = Const(0)  # shift in a 0
    dir = Const(0)  # shift right
    return barrel.barrel_shifter(bits_to_shift, bit_in, dir, shift_amount)


def match_bitwidth(*args, **opt):
    """ Matches the argument wires' bitwidth via zero or sign extension, returning new WireVectors

    :param args: WireVectors of which to match bitwidths
    :param opt: Optional keyword argument 'signed=True' (defaults to False)
    :return: tuple of args in order with extended bits

    Example of matching the bitwidths of two WireVectors `a` and `b` with
    with zero extention: ::

        a, b = match_bitwidth(a, b)

    Example of matching the bitwidths of three WireVectors `a`,`b`, and `c` with
    with sign extention: ::

        a, b, c = match_bitwidth(a, b, c, signed=True)
    """
    # TODO: when we drop 2.7 support, this code should be cleaned up with explicit
    # kwarg support for "signed" rather than the less than helpful "**opt"
    if len(opt) == 0:
        signed = False
    else:
        if len(opt) > 1 or 'signed' not in opt:
            raise PyrtlError('error, only supported kwarg to match_bitwidth is "signed"')
        signed = bool(opt['signed'])

    max_len = max(len(wv) for wv in args)
    if signed:
        return (wv.sign_extended(max_len) for wv in args)
    else:
        return (wv.zero_extended(max_len) for wv in args)


def as_wires(val, bitwidth=None, truncating=True, block=None):
    """ Return wires from val which may be wires, integers (including IntEnums), strings, or bools.

    :param val: a wirevector-like object or something that can be converted into a Const
    :param bitwidth: The bitwidth the resulting wire should be
    :param bool truncating: determines whether bits will be dropped to achieve
        the desired bitwidth if it is too long (if true, the most-significant bits
        will be dropped)
    :param Block block: block to use for wire

    This function is mainly used to coerce values into WireVectors (for
    example, operations such as "x+1" where "1" needs to be converted to
    a Const WireVector). An example: ::

        def myhardware(input_a, input_b):
            a = as_wires(input_a)
            b = as_wires(input_b)
        myhardware(3, x)

    The function as_wires will convert the 3 to Const but keep `x` unchanged
    assuming it is a WireVector.

    """
    from .memory import _MemIndexed
    block = working_block(block)

    if isinstance(val, (int, six.string_types)):
        # note that this case captures bool as well (as bools are instances of ints)
        return Const(val, bitwidth=bitwidth, block=block)
    elif isinstance(val, _MemIndexed):
        # convert to a memory read when the value is actually used
        if val.wire is None:
            val.wire = as_wires(val.mem._readaccess(val.index), bitwidth, truncating, block)
        return val.wire
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


def bitfield_update(w, range_start, range_end, newvalue, truncating=False):
    """ Return WireVector w but with some of the bits overwritten by newvalue.

    :param w: a WireVector to use as the starting point for the update
    :param range_start: the start of the range of bits to be updated
    :param range_end: the end of the range of bits to be updated
    :param newvalue: the value to be written in to the start:end range
    :param truncating: if true, silently clip newvalue to the proper bitwidth rather than
          throw an error if the value provided is too large

    Given a WireVector w, this function returns a new WireVector that
    is identical to w except in the range of bits specified.  In that
    specified range, the value newvalue is swapped in.  For example:
    `bitfield_update(w, 20, 23, 0x7)` will return return a WireVector
    of the same length as w, and with the same values as w, but with
    bits 20, 21, and 22 all set to 1.

    Note that range_start and range_end will be inputs to a slice and
    so standard Python slicing rules apply (e.g. negative values for
    end-relative indexing and support for None). ::

        w = bitfield_update(w, 20, 23, 0x7)  # sets bits 20, 21, 22 to 1
        w = bitfield_update(w, 20, 23, 0x6)  # sets bit 20 to 0, bits 21 and 22 to 1
        w = bitfield_update(w, 20, None, 0x7)  # assuming w is 32 bits, sets bits 31..20 = 0x7
        w = bitfield_update(w, -1, None, 0x1)  # set the LSB (bit) to 1
    """
    from .corecircuits import concat_list

    w = as_wires(w)
    idxs = list(range(len(w)))  # we make a list of integers and slice those up to use as indexes
    idxs_middle = idxs[range_start:range_end]
    if len(idxs_middle) == 0:
        raise PyrtlError('Cannot update bitfield of size 0 (i.e. there are no bits to update)')
    idxs_lower = idxs[:idxs_middle[0]]
    idxs_upper = idxs[idxs_middle[-1] + 1:]

    newvalue = as_wires(newvalue, bitwidth=len(idxs_middle), truncating=truncating)
    if len(idxs_middle) != len(newvalue):
        raise PyrtlError('Cannot update bitfield of length %d with value of length %d '
                         'unless truncating=True is specified' % (len(idxs_middle), len(newvalue)))

    result_list = []
    if idxs_lower:
        result_list.append(w[idxs_lower[0]:idxs_lower[-1] + 1])
    result_list.append(newvalue)
    if idxs_upper:
        result_list.append(w[idxs_upper[0]:idxs_upper[-1] + 1])
    result = concat_list(result_list)

    if len(result) != len(w):
        raise PyrtlInternalError('len(result)=%d, len(original)=%d' % (len(result), len(w)))
    return result


def bitfield_update_set(w, update_set, truncating=False):
    """ Return WireVector w but with some of the bits overwritten by values in update_set.

    :param w: a WireVector to use as the starting point for the update
    :param update_set: a map from tuples of integers (bit ranges) to the new values
    :param truncating: if true, silently clip new values to the proper bitwidth rather than
          throw an error if the value provided is too large

    Given a WireVector w, this function returns a new WireVector that is identical to w except
    in the range of bits specified.  When multiple non-overlapping fields need to be updated
    in a single cycle this provides a clearer way to describe that behavior than iterative calls to
    bitfield_update (although that is, in fact, what it is doing). ::

        w = bitfield_update_set(w, {
                (20, 23):    0x6,      # sets bit 20 to 0, bits 21 and 22 to 1
                (26, None):  0x7,      # assuming w is 32 bits, sets bits 31..26 to 0x7
                (-1, None):  0x0       # set the LSB (bit) to 0
                })
    """
    w = as_wires(w)
    # keep a list of bits that are updated to find overlaps
    setlist = [False] * len(w)
    # call bitfield for each one
    for range in update_set:
        range_start, range_end = range
        new_value = update_set[range]
        # check for overlaps
        setbits = setlist[range_start:range_end]
        if any(setbits):
            raise PyrtlError('Bitfields for update are overlapping')
        setlist[range_start:range_end] = [True] * len(setbits)
        # do the actual update
        w = bitfield_update(w, range_start, range_end, new_value, truncating)
    return w


def enum_mux(cntrl, table, default=None, strict=True):
    """ Build a mux for the control signals specified by an enum.

    :param cntrl: is a WireVector and control for the mux.
    :param table: is a dictionary of the form mapping enum->WireVector.
    :param default: is a WireVector to use when the key is not present. In addition
        it is possible to use the key 'otherwise' to specify a default value, but
        it is an error if both are supplied.
    :param strict: is flag, that when set, will cause enum_mux to check
        that the dictionary has an entry for every possible value in the enum.
        Note that if a default is set, then this check is not performed as
        the default will provide valid values for any underspecified keys.
    :return: a WireVector which is the result of the mux.

    Examples::

        from enum import IntEnum

        class Command(IntEnum):
            ADD = 1
            SUB = 2
        enum_mux(cntrl, {Command.ADD: a+b, Command.SUB: a-b})
        enum_mux(cntrl, {Command.ADD: a+b}, strict=False)  # SUB case undefined
        enum_mux(cntrl, {Command.ADD: a+b, otherwise: a-b})
        enum_mux(cntrl, {Command.ADD: a+b}, default=a-b)

    """
    # check dictionary keys are of the right type
    keytypeset = set(type(x) for x in table.keys() if x is not otherwise)
    if len(keytypeset) != 1:
        raise PyrtlError('table mixes multiple types {} as keys'.format(keytypeset))
    keytype = list(keytypeset)[0]
    # check that dictionary is complete for the enum
    try:
        enumkeys = list(keytype.__members__.values())
    except AttributeError:
        raise PyrtlError('type {} not an Enum and does not support the same interface'
                         .format(keytype))
    missingkeys = [e for e in enumkeys if e not in table]

    # check for "otherwise" in table and move it to a default
    if otherwise in table:
        if default is not None:
            raise PyrtlError('both "otherwise" and default provided to enum_mux')
        else:
            default = table[otherwise]

    if strict and default is None and missingkeys:
        raise PyrtlError('table provided is incomplete, missing: {}'.format(missingkeys))

    # generate the actual mux
    vals = {k.value: d for k, d in table.items() if k is not otherwise}
    if default is not None:
        vals['default'] = default
    return muxes.sparse_mux(cntrl, vals)


def and_all_bits(vector):
    """ Returns WireVector, the result of "and"ing all items of the argument vector.

    :param vector: Takes a single arbitrary length WireVector
    :return: Returns a 1 bit result, the bitwise `and` of all of
    the bits in the vector to a single bit.
    """
    return tree_reduce(lambda a, b: a & b, vector)


def or_all_bits(vector):
    """ Returns WireVector, the result of "or"ing all items of the argument vector.

    :param vector: Takes a single arbitrary length WireVector
    :return: Returns a 1 bit result, the bitwise `or` of all of
    the bits in the vector to a single bit.
    """
    return tree_reduce(lambda a, b: a | b, vector)


def xor_all_bits(vector):
    """ Returns WireVector, the result of "xor"ing all items of the argument vector.

    :param vector: Takes a single arbitrary length WireVector
    :return: Returns a 1 bit result, the bitwise `xor` of all of
    the bits in the vector to a single bit.
    """
    return tree_reduce(lambda a, b: a ^ b, vector)


parity = xor_all_bits  # shadowing the xor_all_bits function


def tree_reduce(op, vector):
    if len(vector) < 1:
        raise PyrtlError("Cannot reduce empty vectors")
    if len(vector) == 1:
        return vector[0]
    left = tree_reduce(op, vector[:len(vector) // 2])
    right = tree_reduce(op, vector[len(vector) // 2:])
    return op(left, right)


def _apply_op_over_all_bits(op, vector):
    if len(vector) < 1:
        raise PyrtlError("Cannot reduce empty vectors")
    if len(vector) == 1:
        return vector[0]
    rest = _apply_op_over_all_bits(op, vector[1:])
    return op(vector[0], rest)


def rtl_any(*vectorlist):
    """ Hardware equivalent of Python native "any".

    :param WireVector vectorlist: all arguments are WireVectors of length 1
    :return: WireVector of length 1

    Returns a 1-bit WireVector which will hold a '1' if any of the inputs
    are '1' (i.e. it is a big ol' OR gate).  If no inputs are provided it
    will return a Const 0 (since there are no '1's present) similar to python's
    any function called with an empty list.

    Examples::

        rtl_any(thing1, thing2, thing3)  # same as thing1 | thing2 | thing3
        rtl_any(*[list_of_things])  # the unpack operator ("*") can be used for lists
        rtl_any()  # returns Const(False) which comes up if the list above is empty
    """
    if len(vectorlist) == 0:
        return as_wires(False)
    converted_vectorlist = [as_wires(v) for v in vectorlist]
    if any(len(v) != 1 for v in converted_vectorlist):
        raise PyrtlError('only length 1 WireVectors can be inputs to rtl_any')
    return or_all_bits(concat_list(converted_vectorlist))


def rtl_all(*vectorlist):
    """ Hardware equivalent of Python native "all".

    :param WireVector vectorlist: all arguments are WireVectors of length 1
    :return: WireVector of length 1

    Returns a 1-bit WireVector which will hold a '1' only if all of the
    inputs are '1' (i.e. it is a big ol' AND gate).  If no inputs are provided it
    will return a Const 1 (since there are no '0's present) similar to python's
    all function called with an empty list.

    Examples::

        rtl_all(thing1, thing2, thing3)  # same as thing1 & thing2 & thing3
        rtl_all(*[list_of_things])  # the unpack operator ("*") can be used for lists
        rtl_all()  # returns Const(True) which comes up if the list above is empty
    """
    if len(vectorlist) == 0:
        return as_wires(True)
    converted_vectorlist = [as_wires(v) for v in vectorlist]
    if any(len(v) != 1 for v in converted_vectorlist):
        raise PyrtlError('only length 1 WireVectors can be inputs to rtl_all')
    return and_all_bits(concat_list(converted_vectorlist))


def _basic_mult(A, B):
    """ A stripped-down copy of the Wallace multiplier in rtllib """
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
    sa = concat(*[~s] * len(a))
    sb = concat(*[s] * len(b))
    return (a & sa) | (b & sb)
