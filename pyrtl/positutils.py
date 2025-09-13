"""Implements utility functions for posit operations."""

import math
import pyrtl
from pyrtl.corecircuits import shift_right_logical, shift_left_logical


def decode_posit(
    x: pyrtl.WireVector, nbits: int, es: int
) -> tuple[
    pyrtl.WireVector,
    pyrtl.WireVector,
    pyrtl.WireVector,
    pyrtl.WireVector,
    pyrtl.WireVector,
]:
    """Decode posit into its components and return them as a tuple.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::
        >>> nbits = 8
        >>> es = 2

        >>> a = pyrtl.Input(bitwidth=nbits, name='a')
        >>> sign_out = pyrtl.Output(bitwidth=nbits, name='sign_out')
        >>> k_out = pyrtl.Output(bitwidth=nbits, name='k_out')
        >>> exp_out = pyrtl.Output(bitwidth=es, name='exp_out')
        >>> frac_bits_out = pyrtl.Output(bitwidth=nbits, name='frac_bits_out')
        >>> frac_len_out = pyrtl.Output(bitwidth=nbits, name='frac_len_out')

        >>> sign, k, exp, frac_bits, frac_len = decode_posit(a, nbits, es)

        >>> sign_out <<= sign
        >>> k_out <<= k
        >>> exp_out <<= exp
        >>> frac_bits_out <<= frac_bits
        >>> frac_len_out <<= frac_len

        >>> sim = pyrtl.Simulation()
        >>> sim.step({'a': 0b01011100})

        >>> sim.inspect('sign_out')
        '0'
        >>> sim.inspect('k_out')
        '0'
        >>> sim.inspect('exp_out')
        '3'
        >>> format(sim.inspect('frac_bits_out'), '08b')
        '00000100'
        >>> sim.inspect('frac_len_out')
        '3'

    :param x: A WireVector that represents the posit.
    :param nbits: An int that represents the bitwidth of the posit.
    :param es: An int that represents the exponent size of the posit.

    :return: A tuple consisting of:
        - WireVector for sign
        - WireVector for k
        - WireVector for exponent
        - WireVector for fractional bits
        - WireVector for length of fraction
    """
    sign = x[nbits - 1]
    rest = [x[nbits - 2 - i] for i in range(nbits - 1)]
    regime_bit = rest[0]
    run_len = pyrtl.Const(0, bitwidth=nbits)
    active = pyrtl.Const(1, bitwidth=1)

    for i in range(nbits - 1):
        bit = rest[i]
        is_same = bit == regime_bit
        run_len = run_len + pyrtl.select(
            active & is_same,
            pyrtl.Const(1),
            pyrtl.Const(0),
        )
        active = active & is_same

    k_pos = run_len - pyrtl.Const(1, bitwidth=nbits)
    k_neg = (~run_len) + pyrtl.Const(1, bitwidth=nbits)
    k = pyrtl.select(regime_bit, k_pos, k_neg)

    exp_bits = []
    for j in range(es):
        bit_val = pyrtl.Const(0, bitwidth=1)
        for i in range(nbits - 2):
            cond = run_len == pyrtl.Const(i, bitwidth=nbits)
            # exponent bit is at rest[i + 1 + j]
            target_idx = i + 1 + j
            if target_idx < (nbits - 1):
                bit_val = pyrtl.select(cond, rest[target_idx], bit_val)
        exp_bits.append(bit_val)

    exp = pyrtl.concat_list(exp_bits[::-1]) if es > 0 else pyrtl.Const(0)

    start_idx = run_len + pyrtl.Const(1 + es, bitwidth=nbits)
    fraction_bits = []

    for i in range(nbits - 1):
        in_range = (i >= start_idx) & (i < (nbits - 1))
        bit_val = pyrtl.select(in_range, rest[i], pyrtl.Const(0))
        fraction_bits.append(bit_val)

    frac_result = pyrtl.concat_list(fraction_bits[::-1])
    fraction_length = (
        pyrtl.Const(nbits, bitwidth=nbits)
        - run_len
        - pyrtl.Const(es, bitwidth=nbits)
        - pyrtl.Const(2, bitwidth=nbits)
    )

    return sign, k, exp, frac_result, fraction_length


def get_upto_regime(
    k: pyrtl.WireVector,
    n_val: int,
    sign_final: pyrtl.WireVector,
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    """Calculates the remaining bits and the regime bits.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> nbits = 8
        >>> k_in = pyrtl.Input(bitwidth=nbits, name='k_in')
        >>> sign_final = pyrtl.Input(bitwidth=1, name='sign_final')

        >>> rem_bits_out = pyrtl.Output(bitwidth=nbits, name='rem_bits_out')
        >>> sign_w_regime_out = pyrtl.Output(bitwidth=nbits, name='sign_w_regime_out')

        >>> rem_bits, sign_w_regime = get_upto_regime(k_in, nbits, sign_final)

        >>> rem_bits_out <<= rem_bits
        >>> sign_w_regime_out <<= sign_w_regime

        >>> sim = pyrtl.Simulation()
        >>> sim.step({'k_in': 2, 'sign_final': 0})

        >>> sim.inspect('rem_bits_out')
        '3'
        >>> format(sim.inspect('sign_w_regime_out'), '08b')
        '01110000'

    :param k: A WireVector that represents the k value.
    :param n_val: A int that represents the bitwidth of the posit.
    :param sign_final: A WireVector that represents the final sign.

    :return: A tuple consisting of:
        - WireVector representing the remaining bits.
        - WireVector representing the regime bits with sign bit.
    """
    precomputed_val = (1 << (n_val - 1)) - 1

    n_c = pyrtl.Const(n_val)
    n_minus_1 = pyrtl.Const(n_val - 1)
    n_minus_2 = pyrtl.Const(n_val - 2)
    n_minus_3 = pyrtl.Const(n_val - 3)

    rem_bits = pyrtl.WireVector(bitwidth=n_val)
    sign_w_regime = pyrtl.WireVector(bitwidth=n_val)

    abs_k = pyrtl.WireVector(bitwidth=k.bitwidth)
    abs_k <<= pyrtl.select(
        k >= (1 << (n_val - 1)),
        (~k + 1) & ((1 << n_val) - 1),
        k,
    )

    large_neg_regime = abs_k >= n_minus_1
    large_pos_regime = abs_k >= n_minus_2

    with pyrtl.conditional_assignment:
        with k >= (1 << (n_val - 1)):
            with large_neg_regime:
                rem_bits |= 0
                sign_w_regime |= 0
            with ~large_neg_regime:
                temp_rem = n_c + k - 2
                rem_bits |= temp_rem
                sign_w_regime |= shift_right_logical(
                    pyrtl.Const(1 << (n_val - 2), bitwidth=n_val), abs_k
                )

        with k < (1 << (n_val - 1)):
            with large_pos_regime:
                rem_bits |= 0
                sign_w_regime |= pyrtl.Const(precomputed_val, bitwidth=n_val)
            with ~large_pos_regime:
                temp_rem = n_minus_3 - k
                shift_amt = k + 2
                rem_bits |= temp_rem
                ones = shift_left_logical(
                    pyrtl.Const(1, bitwidth=n_val), shift_amt
                ) - pyrtl.Const(2, bitwidth=n_val)
                shifted = shift_left_logical(ones, temp_rem)
                sign_w_regime |= shifted

    sign_w_regime_trimmed = pyrtl.WireVector(bitwidth=n_val - 1)
    sign_w_regime_trimmed <<= sign_w_regime[: n_val - 1]
    sign_w_regime_final = pyrtl.concat(sign_final, sign_w_regime_trimmed)

    return rem_bits, sign_w_regime_final


def frac_with_hidden_one(
    frac: pyrtl.WireVector,
    frac_length: pyrtl.WireVector,
    nbits: int,
) -> pyrtl.WireVector:
    """Adds a hidden 1 to the fractional bits.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::
        >>> nbits = 8
        >>> frac_in = pyrtl.Input(bitwidth=nbits-1, name='frac_in')
        >>> frac_len_in = pyrtl.Input(bitwidth=nbits, name='frac_len_in')
        >>> frac_out = pyrtl.Output(bitwidth=32, name='frac_out')

        >>> frac_out <<= frac_with_hidden_one(frac_in, frac_len_in, nbits)

        >>> sim = pyrtl.Simulation()
        >>> sim.step({'frac_in': 0b0010101, 'frac_len_in': 5})

        >>> format(sim.inspect('frac_out'), '08b')
        '000110101'

    :param frac: A WireVector that represents the fractional bits.
    :param frac_length: A WireVector that represents the length of the fractional bits.
    :param nbits: An int that represents the bitwidth of the posit.

    :return: A WireVector that represents the fraction with the hidden 1.
    """
    one_table = [pyrtl.Const(1 << i, bitwidth=nbits + 1) for i in range(nbits + 1)]
    one_shifted = pyrtl.Const(0, bitwidth=32)

    for i in range(nbits + 1):
        one_shifted = pyrtl.select(
            frac_length == pyrtl.Const(i, bitwidth=8),
            one_table[i],
            one_shifted,
        )

    frac_32 = pyrtl.concat(pyrtl.Const(0, bitwidth=32 - (nbits - 1)), frac)
    full = one_shifted + frac_32
    return full


def remove_first_one(val: pyrtl.WireVector) -> pyrtl.WireVector:
    """Removes the leading hidden bit of 1.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::
        >>> nbits = 8
        >>> frac_with_one = pyrtl.Input(bitwidth=nbits, name='frac_with_one')
        >>> frac_removed = pyrtl.Output(bitwidth=nbits, name='frac_removed')

        >>> frac_removed <<= remove_first_one(frac_with_one)

        >>> sim = pyrtl.Simulation()
        >>> sim.step({'frac_with_one': 0b10010110})

        >>> format(sim.inspect('frac_removed'), '08b')
        '00010110'

    :param val: A WireVector that represents the fractional bits.

    :return: A WireVector with the hidden bit of 1 removed.
    """
    found = pyrtl.Const(0, bitwidth=1)
    result_bits = []

    for i in range(val.bitwidth):
        bit = val[val.bitwidth - 1 - i]  # MSB first
        new_bit = pyrtl.select(
            (found == 0) & (bit == 1),
            pyrtl.Const(0, bitwidth=1),
            bit,
        )
        result_bits.append(new_bit)

        found = pyrtl.select(
            (found == 0) & (bit == 1),
            pyrtl.Const(1, bitwidth=1),
            found,
        )

    return pyrtl.concat_list(result_bits[::-1])


def twos_comp(x: pyrtl.WireVector, n: int) -> pyrtl.WireVector:
    """Compute the two's complement of an n-bit WireVector.

    Two's complement is the standard way of representing signed integers 
    in binary systems. The process is:
        1. Invert all the bits (one's complement).
        2. Add 1 to the result.
    This function ensures the result is limited to 'n' bits.

    Example::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()
        >>> x = pyrtl.Const(5, bitwidth=4)   # 0101 (decimal 5)
        >>> result = twos_comp(x, 4)
        >>> sim = pyrtl.Simulation()
        >>> sim.step({})
        >>> format(sim.inspect(result), '04b')
        '1011'   # -5 in two's complement

    :param x: The input value as a PyRTL WireVector.
    :param n: Bitwidth to operate on.
    :return: The n-bit two's complement representation of x.
    """

    mask = pyrtl.Const((1 << n) - 1, bitwidth=n)
    inverted = x ^ mask
    added = inverted + 1
    return added & mask

def zero_ext(x: pyrtl.WireVector, new_bw: int) -> pyrtl.WireVector:
    """
    Zero-extend `x` to `new_bw` bits.

    Behavior:
    - If `new_bw == x.bitwidth`, returns `x` unchanged (no copy).
    - If `new_bw > x.bitwidth`, pads MSBs with zeros so the unsigned value is preserved.
    - Truncation is NOT performed here (use `_resize` for that).

    Equivalent to concatenating (new_bw - x.bitwidth) zero bits above `x`.
    """
    assert new_bw >= x.bitwidth
    if new_bw == x.bitwidth:
        return x
    return pyrtl.concat(pyrtl.Const(0, bitwidth=new_bw - x.bitwidth), x)


def resize(x: pyrtl.WireVector, new_bw: int) -> pyrtl.WireVector:
    """
    Resize `x` to exactly `new_bw` bits.

    Behavior:
    - If `new_bw == x.bitwidth`, returns `x` unchanged.
    - If `new_bw < x.bitwidth`, returns the lower `new_bw` bits (truncates MSBs).
    - If `new_bw > x.bitwidth`, zero-extends to widen (unsigned semantics).

    Note: This is UNSIGNED resizing. If you need sign-preserving growth,
    sign-extend externally instead of using `_resize`.
    """
    if new_bw == x.bitwidth:
        return x
    if new_bw < x.bitwidth:
        return x[:new_bw] 
    return zero_ext(x, new_bw)


def sign_ext(x: pyrtl.WireVector, new_bw: int) -> pyrtl.WireVector:
    """
    Sign-extend `x` to bitwidth `new_bw` (two's-complement semantics).

    Behavior:
    - If `new_bw <= x.bitwidth`, returns `x` unchanged (no truncation or copy).
    - If `new_bw > x.bitwidth`, replicates the MSB (sign bit) into the new upper bits
      so that the signed value is preserved under two's-complement interpretation.

    Use when:
    - Widening **signed** quantities (e.g., regime `k`) before arithmetic or shifting.
      For **unsigned** widening, prefer `zero_ext`.

    Implementation note:
    - Captures `signbit = x[x.bitwidth-1]`, creates `new_bw - x.bitwidth` copies,
      and concatenates them above `x`.

    :param x: Source WireVector interpreted as a signed two's-complement value.
    :param new_bw: Target bitwidth to extend to.
    :return: A WireVector of width `new_bw` with the same signed value as `x`.
    """
    if new_bw <= x.bitwidth:
        return x
    signbit = x[x.bitwidth-1]
    pad = pyrtl.concat_list([signbit for _ in range(new_bw - x.bitwidth)])
    return pyrtl.concat(pad, x)


def unify_width(a: pyrtl.WireVector, b: pyrtl.WireVector):
    """
    Return `(a_w, b_w, W)` where both inputs are widened to the same bitwidth `W`.

    - `W = max(a.bitwidth, b.bitwidth)`
    - Widening uses zero-extension (unsigned semantics).
    - Useful before doing comparisons/arithmetic that expects matching widths.

    :return: (a_zero_extended, b_zero_extended, unified_bitwidth)
    """
    W = max(a.bitwidth, b.bitwidth)
    return zero_ext(a, W), zero_ext(b, W), W


def absdiff(a: pyrtl.WireVector, b: pyrtl.WireVector):
    """
    Unsigned absolute difference between `a` and `b`.

    Steps (purely combinational):
    1) Zero-extend to a common width.
    2) Compute `a >= b` to pick subtraction order.
    3) Return `(was_neg, |a-b|)`, where:
       - `was_neg` is 1 when `a < b` (i.e., subtraction would be negative),
       - magnitude is the absolute difference.

    :return: (was_neg:1-bit, magnitude:WireVector)
    """
    aa, bb, W = unify_width(a, b)
    a_ge_b = aa >= bb
    mag = pyrtl.select(a_ge_b, aa - bb, bb - aa)
    was_neg = ~a_ge_b & pyrtl.Const(1, bitwidth=1)  
    return was_neg, mag


def bitlen_u(x: pyrtl.WireVector, out_bw: int) -> pyrtl.WireVector:
    """
    Return the UNSIGNED bit-length of `x` (index of MSB + 1).

    Definition:
    - bitlen(0b00010100) = 5
    - bitlen(0b00000000) = 0

    Implementation detail:
    - Counts leading zeros, then computes `bitlen = width - leading_zeros`.
    - `out_bw` must be large enough to encode up to `x.bitwidth`
      (use >= ceil(log2(x.bitwidth+1)) to be safe).

    :param x: WireVector to analyze (treated as unsigned).
    :param out_bw: Bitwidth of the integer result (e.g., 8 or more).
    :return: WireVector of width `out_bw` with the bit-length of `x`.
    """
    bw = x.bitwidth
    lz   = pyrtl.Const(0, bitwidth=out_bw)  
    seen = pyrtl.Const(0, bitwidth=1)       

    for i in range(bw):
        bit = x[bw - 1 - i]
        inc = (~seen) & (~bit)  
        lz  = lz + pyrtl.select(inc, pyrtl.Const(1, bitwidth=out_bw),
                                     pyrtl.Const(0, bitwidth=out_bw))
        seen = seen | bit

    return pyrtl.Const(bw, bitwidth=out_bw) - lz  


def decimal_to_posit(x: float, nbits: int, es: int) -> int:
    """Convert a decimal float to Posit<nbits, es> representation.

    .. doctest only::

        >>> import math

    Example::

        >>> nbits, es = 16, 2
        >>> format(decimal_to_posit(4992, nbits, es), '016b')
        '0111100000111000'

        >>> nbits, es = 8, 1
        >>> format(decimal_to_posit(5000, nbits, es), '08b')
        '01111111'

    :param x: The decimal float to be converted.
    :param nbits: Total number of bits in the posit representation.
    :param es: Maximum number of exponent bits.
    :return: The integer representation of the posit encoding.
    """
    if x == 0:
        return 0
    
    # handle sign at the end of twos comp
    sign = 0
    if x < 0:
        sign = 1
        x = -x

    useed = 2 ** (2 ** es)

    if x == float('inf'):
        return (1 << (nbits - 1)) - 1  
    if x == 0 or x < useed ** (-(nbits - 2)):
        return 0

    # regime bits
    if x >= 1:
        k = int(math.floor(math.log(x, useed)))
    else:
        k = int(math.floor(math.log(x, useed)))  

    regime_scale = useed ** k
    remaining = x / regime_scale

    # Exponent bits
    exponent = 0
    if es > 0 and remaining > 0:
        exponent = int(math.floor(math.log2(remaining)))
        exponent = max(0, min(exponent, (1 << es) - 1))
        remaining /= 2 ** exponent

    # Frcation bits
    fraction = remaining - 1.0
    frac_bits = []
    
    #Remaning bits
    max_frac_bits = nbits - 1  
    
    for _ in range(max_frac_bits):
        fraction *= 2
        if fraction >= 1:
            frac_bits.append("1")
            fraction -= 1
        else:
            frac_bits.append("0")

    # Build regime bits
    if k >= 0:
        regime_bits = "1" * (k + 1) + "0"
    else:
        regime_bits = "0" * (-k) + "1"

    bits = "0" + regime_bits  
    
    # Add exponent bits
    if es > 0:
        exp_str = format(exponent, f"0{es}b")
        bits += exp_str
    
    # Add fraction bits
    bits += "".join(frac_bits)

    # Trim to nbits with rounding
    if len(bits) > nbits:
        bits = bits[:nbits]
    else:
        bits = bits.ljust(nbits, "0")

    # Convert to integer
    result = int(bits, 2)
    
    # Apply twos complement for negative numbers
    if sign:
        mask = (1 << nbits) - 1
        result = ((~result) + 1) & mask
    
    return result
