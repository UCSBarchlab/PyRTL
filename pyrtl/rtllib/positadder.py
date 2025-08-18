import pyrtl
from pyrtl.corecircuits import shift_left_logical, shift_right_logical
from pyrtl.positutils import decode_posit, get_upto_regime, frac_with_hidden_one, remove_first_one

def posit_add(a, b, nbits, es):
    """Adds two numbers in posit format and returns their sum.

    :param a: A :class:`WireVector` to add. Bitwidths need to match.
    :param b: A :class:`WireVector` to add. Bitwidths need to match.
    :param nbits: A :class:`int` representing the total bitwidth of the posit.
    :param es: A :class:`int` representing the exponent size of the posit.

    :return: A :class:`WireVector` that represents the sum of the two posits. 
    """
    # Decode input posits into regime (k), exponent, fraction, and fraction length
    _, k_a, exp_a, frac_a, frac_len_a = decode_posit(a, nbits, es)
    _, k_b, exp_b, frac_b, frac_len_b = decode_posit(b, nbits, es)

    # match bitwidths of fractional part
    frac_a_aligned = pyrtl.WireVector(bitwidth=nbits)
    frac_b_aligned = pyrtl.WireVector(bitwidth=nbits)
    
    frac_len_a_aligned = pyrtl.WireVector(bitwidth=nbits)
    frac_len_b_aligned = pyrtl.WireVector(bitwidth=nbits)

    with pyrtl.conditional_assignment:
        with frac_len_a > frac_len_b:
            shift_amt = frac_len_a - frac_len_b
            frac_b_aligned |= shift_left_logical(frac_b, shift_amt)
            frac_a_aligned |= frac_a
            frac_len_b_aligned |= frac_len_b + shift_amt
            frac_len_a_aligned |= frac_len_a

        with frac_len_a < frac_len_b:
            shift_amt = frac_len_b - frac_len_a
            frac_a_aligned |= shift_left_logical(frac_a, shift_amt)
            frac_b_aligned |= frac_b
            frac_len_a_aligned |= frac_len_a + shift_amt
            frac_len_b_aligned |= frac_len_b

        with pyrtl.otherwise:
            frac_a_aligned |= frac_a
            frac_b_aligned |= frac_b
            frac_len_a_aligned |= frac_len_a
            frac_len_b_aligned |= frac_len_b

    # Add hidden leading one to fractions
    frac_a_full = frac_with_hidden_one(frac_a_aligned, frac_len_a_aligned,
                                       nbits)
    frac_b_full = frac_with_hidden_one(frac_b_aligned, frac_len_b_aligned,
                                       nbits)

    # Compute scales (regime*k + exponent)
    scale_a = shift_left_logical(k_a, es) + exp_a
    scale_b = shift_left_logical(k_b, es) + exp_b

    offset = scale_a - scale_b

    is_neg_offset = pyrtl.select(
        offset > pyrtl.Const(127, bitwidth=nbits),
        truecase=pyrtl.Const(1, bitwidth=nbits),
        falsecase=pyrtl.Const(0, bitwidth=nbits)
    )

    shifted_a = pyrtl.WireVector(bitwidth=frac_a_full.bitwidth)
    shifted_b = pyrtl.WireVector(bitwidth=frac_b_full.bitwidth)
    result_scale = pyrtl.WireVector(bitwidth=offset.bitwidth)
    result_exp = pyrtl.WireVector(bitwidth=es)

    neg_offset = (~offset) + pyrtl.Const(1, bitwidth=offset.bitwidth)

    # Align fractions based on offset
    with pyrtl.conditional_assignment:
        with is_neg_offset == pyrtl.Const(0, bitwidth=nbits):
            shifted_b |= frac_b_full
            shifted_a |= shift_left_logical(frac_a_full, offset)
            result_scale |= scale_a
            result_exp |= exp_a

        with is_neg_offset == pyrtl.Const(1, bitwidth=nbits):
            shifted_b |= shift_left_logical(frac_b_full, neg_offset)
            shifted_a |= frac_a_full
            result_scale |= scale_b
            result_exp |= exp_b

    # Add shifted fractions
    result_frac = shifted_a + shifted_b

    # checking for overflow, if overflow, increase scale
    result_scale = pyrtl.select(
        offset == pyrtl.Const(0, bitwidth=offset.bitwidth),
        result_scale + 1,
        result_scale
    )
    result_k = shift_right_logical(result_scale,
                                   pyrtl.Const(es, bitwidth=nbits))

    # Extract regime bits
    rem_bits, regime_bits = get_upto_regime(result_k, nbits, 0)

    # Extract exponent from scale
    result_exp = result_scale - shift_left_logical(result_k, es)
    result_exp = shift_left_logical(
        result_exp, rem_bits - pyrtl.Const(es, bitwidth=nbits)
    )

    # Remaining fraction length
    frac_len = rem_bits - es

    # handling rounding of fractional bits
    count = pyrtl.Const(0, bitwidth=nbits)
    rounded_frac = pyrtl.Const(0, bitwidth=nbits)
    found = pyrtl.Const(0, bitwidth=nbits)

    for i in range(nbits):
        bit = result_frac[nbits - 1 - i]
        cond = pyrtl.select(bit == pyrtl.Const(1), 1, found)
        found = found | cond
        count = pyrtl.select(found == pyrtl.Const(1),
                             count + 1, count)

    # Exclude leading one
    count = count - 1
    bits_to_shift = count - frac_len

    # Normalize fraction
    truncated_frac = shift_right_logical(result_frac, bits_to_shift)

    # Guard, Round, Sticky bits
    ground_bit = result_frac & shift_right_logical(
        pyrtl.Const(1, bitwidth=nbits), (bits_to_shift - 1)
    )
    round_bit = result_frac & shift_right_logical(
        pyrtl.Const(1, bitwidth=nbits), (bits_to_shift - 2)
    )
    sticky_bit = result_frac & shift_right_logical(
        pyrtl.Const(1, bitwidth=nbits), (bits_to_shift - 3)
    )

    cond = ground_bit & (round_bit | sticky_bit)
    rounded_frac = pyrtl.WireVector(bitwidth=nbits)

    # Apply rounding rules
    with pyrtl.conditional_assignment:
        with ground_bit == pyrtl.Const(0):
            rounded_frac |= truncated_frac
        with cond == pyrtl.Const(1):
            rounded_frac |= truncated_frac + 1
        with cond == pyrtl.Const(0):
            with truncated_frac[0] == 1:
                rounded_frac |= truncated_frac + 1
            with truncated_frac[0] == 0:
                rounded_frac |= truncated_frac

    # Remove hidden one from rounded fraction
    rounded_frac = remove_first_one(rounded_frac)

    # Combine regime, exponent, and fraction
    added_posit = (
        pyrtl.Const(0, bitwidth=nbits) +
        regime_bits +
        result_exp +
        rounded_frac
    )
    result_posit = pyrtl.WireVector(bitwidth=nbits)

    # Checking for special cases (NaR and 0)
    isNar = (
        pyrtl.select(a == pyrtl.Const(1 << nbits - 1, bitwidth=nbits), 1, 0) |
        pyrtl.select(b == pyrtl.Const(1 << nbits - 1, bitwidth=nbits), 1, 0)
    )

    with pyrtl.conditional_assignment:
        with isNar == pyrtl.Const(1, bitwidth=nbits):
            result_posit |= pyrtl.Const(1 << nbits - 1, bitwidth=nbits)

        with a == pyrtl.Const(0, bitwidth=nbits):
            result_posit |= b

        with b == pyrtl.Const(0, bitwidth=nbits):
            result_posit |= a

        with pyrtl.otherwise:
            result_posit |= added_posit

    return result_posit