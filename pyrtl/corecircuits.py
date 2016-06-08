"""
A set of basic circuits for PyRTL users to use
Some of these circuits are used internally
"""


from .pyrtlexceptions import PyrtlError
from .helperfuncs import match_bitwidth, as_wires
from .core import LogicNet, working_block
from .wire import Const, WireVector


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
    converted_vectorlist = [as_wires(v) for v in vectorlist]
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
    converted_vectorlist = [as_wires(v) for v in vectorlist]
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
    sel, f, t = (as_wires(w) for w in (sel, falsecase, truecase))
    f, t = match_bitwidth(f, t)
    outwire = WireVector(bitwidth=len(f))

    net = LogicNet(op='x', op_param=None, args=(sel, f, t), dests=(outwire,))
    working_block().add_net(net)  # this includes sanity check on the mux
    return outwire


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
    """
    Concats a list of wirevectors into a single wirevector

    :param wire_list: List of wirevectors to concat
    :return wirevector: wirevector with length equal
      to the sum of the args' lengths

    The concatenation order is LSB (UNLIKE Concat)
    """
    return concat(*reversed(wire_list))
