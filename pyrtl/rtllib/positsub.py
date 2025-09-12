import pyrtl
from pyrtl.corecircuits import (
    shift_left_logical,
    shift_right_logical,
    shift_right_arithmetic,
)
from pyrtl.positutils import (
    decode_posit,
    get_upto_regime,
    zero_ext,
    resize,
    unify_width,
    absdiff,
    bitlen_u,
    twos_comp,
    sign_ext,
)
from pyrtl.rtllib.positadd import posit_add


def posit_sub(
    a: pyrtl.WireVector, b: pyrtl.WireVector, nbits: int, es: int
) -> pyrtl.WireVector:
    """Subtracts two numbers in posit format and returns their difference.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> nbits = 8
        >>> es = 1
        >>> a = pyrtl.Input(bitwidth=nbits, name='a')
        >>> b = pyrtl.Input(bitwidth=nbits, name='b')
        >>> posit = pyrtl.Output(bitwidth=nbits, name='posit')
        >>> result = posit_add(a, b, nbits, es)
        >>> posit <<= result
        >>> sim = pyrtl.Simulation()
        >>> sim.step({'a': 0b01011100, 'b': 0b01100000})  # 4.5 - 2 = 2.5
        >>> format(sim.inspect('posit'), '08b')
        '01100111'

    :param a: A :class:`.WireVector` to sub. Bitwidths need to match.
    :param b: A :class:`WireVector` to sub. Bitwidths need to match.
    :param nbits: A :class:`.int` representing the total bitwidth of the posit.
    :param es: A :class:`.int` representing the exponent size of the posit.

    :return: A :class:`WireVector` that represents the differnece of the two
             posits.
    """
    # Subtraction of special cases
    nar = pyrtl.Const(1 << (nbits - 1), bitwidth=nbits)
    zero = pyrtl.Const(0, bitwidth=nbits)
    mask = pyrtl.Const((1 << nbits) - 1, bitwidth=nbits)

    is_nar = (a == nar) | (b == nar)
    neg_b = ((~b) + pyrtl.Const(1, bitwidth=nbits)) & mask
    quick = pyrtl.select(
        is_nar,
        nar,
        pyrtl.select(
            a == zero,
            neg_b,
            pyrtl.select(b == zero, a, pyrtl.Const(0, bitwidth=nbits)),
        ),
    )
    have_quick = quick != pyrtl.Const(0, bitwidth=nbits)

    # Decode input posits
    sign1, k1, exponent1, frac1, fl1 = decode_posit(a, nbits, es)
    sign2, k2, exponent2, frac2, fl2 = decode_posit(b, nbits, es)

    # Opposite sign detection
    opp = sign1 != sign2

    neg_a = twos_comp(a, nbits)
    neg_b = twos_comp(b, nbits)

    # a positive, b negative : a + |b|
    sum_posneg = posit_add(a, neg_b, nbits, es)

    # a negative, b positive : |a| + b, then negate the final sum
    sum_negpos_pos = posit_add(neg_a, b, nbits, es)
    sum_negpos = twos_comp(sum_negpos_pos, nbits)

    # Final opposite-sign sum
    sum_v = pyrtl.select(
        sign1 == pyrtl.Const(0, bitwidth=1), sum_posneg, sum_negpos
    )

    SC_BW = max(
        nbits + es + 6,
        k1.bitwidth + es + 2,
        k2.bitwidth + es + 2,
        exponent1.bitwidth + 2,
        exponent2.bitwidth + 2,
    )

    k1_se = sign_ext(k1, SC_BW)
    k2_se = sign_ext(k2, SC_BW)
    exp1_ze = zero_ext(exponent1, SC_BW)
    exp2_ze = zero_ext(exponent2, SC_BW)

    # Compute scale = k*2^es * exponent
    if es == 0:
        scale1 = k1_se + exp1_ze
        scale2 = k2_se + exp2_ze
    else:
        sh_es_sc = pyrtl.Const(es, bitwidth=SC_BW)
        scale1 = shift_left_logical(k1_se, sh_es_sc) + exp1_ze
        scale2 = shift_left_logical(k2_se, sh_es_sc) + exp2_ze

    # Align fraction precision to max(fl1, fl2)
    frac_bits = pyrtl.select(fl1 > fl2, fl1, fl2)
    shift12 = fl1 - fl2
    shift21 = fl2 - fl1
    f1a = pyrtl.select(fl1 >= fl2, frac1, shift_left_logical(frac1, shift21))
    f2a = pyrtl.select(fl2 >= fl1, frac2, shift_left_logical(frac2, shift12))

    one_n = pyrtl.Const(1, bitwidth=nbits)
    one_frac = shift_left_logical(one_n, frac_bits)

    # Compute offsets
    offset = scale1 - scale2
    off_neg = offset[SC_BW - 1]
    abs_off = pyrtl.select(
        off_neg,
        ((~offset) + pyrtl.Const(1, bitwidth=SC_BW)),
        offset,
    )

    W = max(nbits * 2, one_frac.bitwidth + SC_BW + 2)
    f1w = zero_ext(f1a, W)
    f2w = zero_ext(f2a, W)
    onew = zero_ext(one_frac, W)
    offW = resize(abs_off, W)

    # Add hidden one to both sides and align by offset
    a_sum = f1w + onew
    b_sum = f2w + onew
    a_sh = shift_left_logical(a_sum, offW[: a_sum.bitwidth])
    b_sh = shift_left_logical(b_sum, offW[: b_sum.bitwidth])

    was_neg_A, diff_A = absdiff(f1w, f2w)
    scale_A = scale1
    sign_A = sign1 ^ was_neg_A

    was_neg_B, diff_B = absdiff(a_sh, b_sum)
    scale_B = scale1
    sign_B = pyrtl.select(was_neg_B, sign1 ^ pyrtl.Const(1, 1), sign1)

    was_neg_C, diff_C = absdiff(b_sh, a_sum)
    scale_C = scale2
    base_sign_C = sign1 ^ pyrtl.Const(1, 1)
    sign_C = pyrtl.select(
        was_neg_C, base_sign_C ^ pyrtl.Const(1, 1), base_sign_C
    )

    is_zero_off = abs_off == pyrtl.Const(0, bitwidth=SC_BW)

    res_frac0 = pyrtl.select(
        is_zero_off, diff_A, pyrtl.select(off_neg, diff_C, diff_B)
    )
    res_scale0 = pyrtl.select(
        is_zero_off, scale_A, pyrtl.select(off_neg, scale_C, scale_B)
    )
    sign0 = pyrtl.select(
        is_zero_off, sign_A, pyrtl.select(off_neg, sign_C, sign_B)
    )

    same_fields = (k1 == k2) & (exponent1 == exponent2) & (frac1 == frac2)
    is_exact_cancel = is_zero_off & same_fields
    res_frac0 = pyrtl.select(
        is_exact_cancel, pyrtl.Const(0, bitwidth=W), res_frac0
    )
    sign0 = pyrtl.select(is_exact_cancel, pyrtl.Const(0, bitwidth=1), sign0)

    # Normalize to target precision: same-sign => target = frac_bits
    blen_bw = max(8, int(math.ceil(math.log2(W + 1))))
    bitlen0 = bitlen_u(res_frac0, blen_bw)

    fb_target = bitlen_u(frac_bits, blen_bw)
    diff_needed = fb_target - bitlen0
    need_extend = ~diff_needed[blen_bw - 1]
    extend_amt = diff_needed[:W]
    max_shift = pyrtl.Const(W - 1, bitwidth=W)
    extend_amt = pyrtl.select(
        extend_amt > max_shift, max_shift, extend_amt
    )

    res_frac1 = pyrtl.select(
        need_extend, shift_left_logical(res_frac0, extend_amt), res_frac0
    )
    res_scale1 = pyrtl.select(
        need_extend, res_scale0 - resize(extend_amt, SC_BW), res_scale0
    )
    bitlen1 = pyrtl.select(need_extend, fb_target, bitlen0)

    # Final scale tweak (same_sign): + (bitlength - 1 - |offset| - frac_bits)
    adj1 = resize(bitlen1, SC_BW) - pyrtl.Const(1, bitwidth=SC_BW)
    adj2 = adj1 - resize(abs_off, SC_BW) - resize(frac_bits, SC_BW)
    scale_final = res_scale1 + adj2

    # Extract k and exponent
    if es == 0:
        resultk = scale_final
        resultExponent_sc = pyrtl.Const(0, bitwidth=SC_BW)
    else:
        shamt_sf = pyrtl.Const(es, bitwidth=SC_BW)
        resultk = shift_right_arithmetic(scale_final, shamt_sf)
        k_lsl_sc = shift_left_logical(resize(resultk, SC_BW), shamt_sf)
        resultExponent_sc = scale_final - k_lsl_sc

    # Regime with sign=0
    rem_bits, regime = get_upto_regime(
        resize(resultk, nbits), nbits, pyrtl.Const(0, bitwidth=1)
    )

    # Small posit if no room for exponent+fraction
    is_small = rem_bits <= pyrtl.Const(es, bitwidth=nbits)
    shift_amt_small = pyrtl.Const(es, bitwidth=nbits) - rem_bits
    exp_shifted_small = shift_right_logical(
        resize(resultExponent_sc, nbits), shift_amt_small
    )
    small_value = regime + exp_shifted_small

    # normal form - frac_bits_avail = rem_bits - es
    frac_bits_avail = rem_bits - pyrtl.Const(es, bitwidth=nbits)

    sum_keep = (
        resize(frac_bits_avail, blen_bw) + pyrtl.Const(1, bitwidth=blen_bw)
    )

    bitlen1_u, sum_keep_u, Wc = unify_width(bitlen1, sum_keep)
    ge = bitlen1_u >= sum_keep_u

    r_amt_wide = pyrtl.select(
        ge, bitlen1_u - sum_keep_u, pyrtl.Const(0, bitwidth=Wc)
    )
    r_amt = resize(r_amt_wide, W)
    l_amt_wide = pyrtl.select(
        ge, pyrtl.Const(0, bitwidth=Wc), sum_keep_u - bitlen1_u
    )
    l_amt = resize(l_amt_wide, W)

    kept_plus_hidden = pyrtl.select(
        ge, shift_right_logical(res_frac1, r_amt), shift_left_logical(res_frac1, l_amt)
    )

    r_amt_nonzero = r_amt_wide != pyrtl.Const(0, bitwidth=Wc)
    r_amt_minus1 = resize(r_amt - pyrtl.Const(1, bitwidth=r_amt.bitwidth), W)
    guard_src = shift_right_logical(res_frac1, r_amt_minus1)
    guard_bit = pyrtl.select(
        ge & r_amt_nonzero, guard_src & pyrtl.Const(1, bitwidth=W), pyrtl.Const(0, bitwidth=W)
    )
    guard_is_one = guard_bit != pyrtl.Const(0, bitwidth=W)

    # Remove hidden one
    oneW = pyrtl.Const(1, bitwidth=W)
    one_keep = shift_left_logical(oneW, resize(frac_bits_avail, W))
    frac_field_w = kept_plus_hidden - one_keep

    exp_shifted = shift_left_logical(
        resize(resultExponent_sc, nbits), frac_bits_avail
    )
    frac_mask = (
        shift_left_logical(pyrtl.Const(1, bitwidth=nbits), frac_bits_avail)
        - pyrtl.Const(1, bitwidth=nbits)
    )
    frac_field = resize(frac_field_w, nbits) & frac_mask

    value_large = regime + exp_shifted + frac_field
    all_ones = pyrtl.Const((1 << nbits) - 1, bitwidth=nbits)
    not_all_ones = value_large != all_ones

    # Rounding final posit
    do_round = guard_is_one & not_all_ones
    value_rounded = pyrtl.select(do_round, value_large + 1, value_large)

    packed_pos = pyrtl.select(is_small, small_value, value_rounded)

    packed_signed = pyrtl.select(
        sign0 == pyrtl.Const(1, bitwidth=1),
        ((~packed_pos) + pyrtl.Const(1, bitwidth=nbits)) & mask,
        packed_pos,
    )

    exp_shifted = shift_left_logical(
        resize(resultExponent_sc, nbits), frac_bits_avail
    )
    frac_mask = (
        shift_left_logical(pyrtl.Const(1, bitwidth=nbits), frac_bits_avail)
        - pyrtl.Const(1, bitwidth=nbits)
    )
    frac_field = resize(frac_field_w, nbits) & frac_mask

    value_large = regime + exp_shifted + frac_field
    all_ones = pyrtl.Const((1 << nbits) - 1, bitwidth=nbits)
    not_all_ones = value_large != all_ones

    do_round = guard_is_one & not_all_ones
    value_rounded = pyrtl.select(do_round, value_large + 1, value_large)

    packed_pos = pyrtl.select(is_small, small_value, value_rounded)

    packed_signed = pyrtl.select(
        sign0 == pyrtl.Const(1, bitwidth=1),
        ((~packed_pos) + pyrtl.Const(1, bitwidth=nbits)) & mask,
        packed_pos,
    )

    is_zero_res = (res_frac1 == pyrtl.Const(0, bitwidth=W)) | is_exact_cancel
    same_sign_out = pyrtl.select(is_zero_res, zero, packed_signed)

    nonquick = pyrtl.select(opp, sum_v, same_sign_out)
    result = pyrtl.select(have_quick, quick, nonquick)
    return result
