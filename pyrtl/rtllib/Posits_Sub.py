import pyrtl
from pyrtl.corecircuits import shift_left_logical, shift_right_logical
from positutils import (
    decode_posit,
    get_upto_regime,
    frac_with_hidden_one,
    remove_first_one,
    twos_comp
)


def posit_sub(a, b, nbits, es):

    inf = pyrtl.Const((1 << nbits) - 1, bitwidth=nbits)
    is_inf = (a == inf) | (b == inf)
    is_a_zero = (a == 0)
    is_b_zero = (b == 0)

    signbit1, k_a, exp_a, frac_a, frac_len_a = decode_posit(a, nbits, es)
    signbit2, k_b, exp_b, frac_b, frac_len_b = decode_posit(b, nbits, es)

    sign_final = signbit1 ^ signbit2

    neg_b = ~b + 1

    res_inf = inf
    res_a_zero = neg_b
    res_b_zero = a
    scale_a = (k_a if es == 0 else shift_left_logical(k_a, es)) + exp_a
    scale_b = (k_b if es == 0 else shift_left_logical(k_b, es)) + exp_b

    frac_bits = pyrtl.select(frac_len_a > frac_len_b, frac_len_a, frac_len_b)

    shift_amt1 = frac_a - frac_b
    shift_amt2 = frac_b - frac_a

    frac2_shifted = pyrtl.shift_left_logical(frac_b, shift_amt1)
    frac1_shifted = pyrtl.shift_right_logical(frac_a, shift_amt2)


    frac_a = pyrtl.select(frac_a > frac_b, frac_a, frac1_shifted)
    frac_b = pyrtl.select(frac_a > frac_b, frac2_shifted, frac_b)

    offset = scale_a - scale_b
    is_equal = (offset == 0)

    frac_diff = frac_a - frac_b

    resultFrac_default = pyrtl.Const(0, bitwidth=nbits)
    resultScale_default = pyrtl.Const(0, bitwidth=nbits)

    resultFrac = pyrtl.select(is_equal, frac_diff, resultFrac_default)
    resultScale = pyrtl.select(is_equal, scale_a, resultScale_default)

    is_offset_pos = offset > 0

    one_shifted = shift_left_logical(pyrtl.Const(1, bitwidth=nbits), frac_bits)
    frac1_ext = frac_a + one_shifted
    frac2_ext = frac_b + one_shifted


    shifted_frac1 = shift_left_logical(frac1_ext, offset)

    frac_diff_pos = shifted_frac1 - frac2_ext

    resultFrac_default = pyrtl.Const(0, bitwidth=nbits)
    resultScale_default = pyrtl.Const(0, bitwidth=nbits)

    resultFrac = pyrtl.select(is_offset_pos, frac_diff_pos, resultFrac_default)
    resultScale = pyrtl.select(is_offset_pos, scale_a, resultScale_default)

    is_offset_neg = offset < 0

    signbit1_flipped = signbit1 ^ pyrtl.Const(1, bitwidth=1)

    one_shifted = shift_left_logical(pyrtl.Const(1, bitwidth=nbits), frac_bits)
    frac1_ext = frac_a + one_shifted
    frac2_ext = frac_b + one_shifted

    offset_neg = ~offset + pyrtl.Const(1, bitwidth=offset.bitwidth)

    offset_abs = pyrtl.select(is_offset_neg, offset_neg, offset)

    shifted_frac2 = shift_left_logical(frac2_ext, offset_abs)

    frac_diff_neg = shifted_frac2 - frac1_ext


    resultFrac_default2 = pyrtl.Const(0, bitwidth=nbits)
    resultScale_default2 = pyrtl.Const(0, bitwidth=nbits)

    is_offset_neg = offset < 0
    resultFrac = pyrtl.select(is_offset_neg, frac_diff_neg, resultFrac_default2)
    resultScale = pyrtl.select(is_offset_neg, scale_b, resultScale_default2)
    signbit1    = pyrtl.select(is_offset_neg, signbit1_flipped, signbit1)

    is_resultFrac_neg = resultFrac[-1]   

    signbit1_flipped = signbit1 ^ pyrtl.Const(1, bitwidth=1)

    resultFrac_neg = ~resultFrac + pyrtl.Const(1, bitwidth=resultFrac.bitwidth)

    signbit1 = pyrtl.select(is_resultFrac_neg, signbit1_flipped, signbit1)
    resultFrac = pyrtl.select(is_resultFrac_neg, resultFrac_neg, resultFrac)


    bitlength = resultFrac.bitwidth

    needs_shift = frac_bits > bitlength
    shift_amt = frac_bits - bitlength

 
    shifted_resultFrac = shift_left_logical(resultFrac, shift_amt)

    resultFrac_if = pyrtl.select(needs_shift, shifted_resultFrac, resultFrac)
    resultScale_if = pyrtl.select(needs_shift, resultScale - shift_amt, resultScale)
    bitlength_if   = pyrtl.select(needs_shift, frac_bits, bitlength)   

    resultFrac = resultFrac_if
    resultScale = resultScale_if
    bitlength = bitlength_if

    offset_neg = ~offset + pyrtl.Const(1, bitwidth=offset.bitwidth)
    offset_abs = pyrtl.select(offset < 0, offset_neg, offset)


    resultScale = resultScale + (bitlength - pyrtl.Const(1, bitwidth=bitlength.bitwidth)
                                - offset_abs - frac_bits)

    mask = (1 << es) - 1          
    mask_const = pyrtl.Const(mask, bitwidth=resultScale.bitwidth)

    scale_mod = resultScale & mask_const

    resultExponent = resultScale & scale_mod

    resultk = shift_right_logical(resultScale, es)

    rem_bits, regime = get_upto_regime(resultk, nbits, sign_final)

    frac_bits = rem_bits - es
    bitlength_gt = bitlength > (frac_bits + 1)
    bitlength_lt = bitlength < (frac_bits + 1)

    resultFrac_shifted = pyrtl.select(bitlength_gt,
        pyrtl.shift_right_logical(resultFrac, bitlength - frac_bits - 1),
        pyrtl.select(bitlength_lt,
            pyrtl.shift_left_logical(resultFrac, frac_bits + 1 - bitlength),
            resultFrac
        )
    )

    resultFrac_bitwidth = resultFrac.bitwidth
    roundup = pyrtl.select(bitlength_gt,
        (pyrtl.shift_right_logical(resultFrac, resultFrac_bitwidth - frac_bits - 2)) & 1,
        pyrtl.Const(0, 1)
    )

    resultFrac_adj = resultFrac_shifted - pyrtl.shift_left_logical(pyrtl.Const(1, resultFrac_shifted.bitwidth), frac_bits)
    value = regime + pyrtl.shift_left_logical(resultExponent, frac_bits) + resultFrac_adj

    rem_bits_le_es = rem_bits <= es
    bitlength_gt = bitlength > (frac_bits + 1)
    bitlength_lt = bitlength < (frac_bits + 1)
    roundup_nonzero = roundup != 0
    value_not_max = value != ((1 << nbits) - 1)

    final_value = pyrtl.select(rem_bits_le_es,
        regime + pyrtl.shift_right_logical(resultExponent, es - rem_bits),
 
        pyrtl.select(signbit1,
            twos_comp(
                pyrtl.select(roundup_nonzero & value_not_max,
                    value + 1,
                    value
                ), nbits
            ),

            pyrtl.select(roundup_nonzero & value_not_max,
                value + 1,
                value
            )
        )
    )

    result = pyrtl.select(
        is_inf, res_inf,
        pyrtl.select(
            is_a_zero, res_a_zero,
            pyrtl.select(
                is_b_zero, res_b_zero,
                final_value 
            )
        )
    )

    return result
