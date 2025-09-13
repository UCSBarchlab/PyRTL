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

    .. doctest::

        >>> import pyrtl
        >>> from positutils import decimal_to_posit
        >>> from positsub import posit_sub
        >>> pyrtl.reset_working_block()
        >>> nbits, es = 8, 1
        >>> a = pyrtl.Input(bitwidth=nbits, name='a')
        >>> b = pyrtl.Input(bitwidth=nbits, name='b')
        >>> out = pyrtl.Output(bitwidth=nbits, name='out')
        >>> out <<= posit_sub(a, b, nbits, es)
        >>> sim = pyrtl.Simulation()
        >>> aval = decimal_to_posit(4.5, nbits, es)
        >>> bval = decimal_to_posit(2.0, nbits, es)
        >>> sim.step({'a': aval, 'b': bval})  # 4.5 - 2.0 = 2.5
        >>> sim.inspect('out') == decimal_to_posit(2.5, nbits, es)
        True
    """
    # special cases
    nar  = pyrtl.Const(1 << (nbits - 1), bitwidth=nbits)
    zero = pyrtl.Const(0, bitwidth=nbits)
    mask = pyrtl.Const((1 << nbits) - 1, bitwidth=nbits)
    maxpos = pyrtl.Const((1 << (nbits - 1)) - 1, bitwidth=nbits)

    is_nar = (a == nar) | (b == nar)
    negb_quick = ((~b) + pyrtl.Const(1, bitwidth=nbits)) & mask
    quick = pyrtl.select(
        is_nar,
        nar,
        pyrtl.select(
            a == zero,
            negb_quick,
            pyrtl.select(b == zero, a, zero),
        ),
    )
    have_quick = is_nar | (a == zero) | (b == zero)

    # Decode input posit
    sign1, k1, exponent1, frac1, fl1 = decode_posit(a, nbits, es)
    sign2, k2, exponent2, frac2, fl2 = decode_posit(b, nbits, es)

    # check if inputs are opposite sign
    opp = sign1 != sign2
    neg_a = twos_comp(a, nbits)
    neg_b = twos_comp(b, nbits)
    sum_posneg = posit_add(a,    neg_b, nbits, es)                
    sum_negpos = twos_comp(posit_add(neg_a, b,    nbits, es), nbits)  
    sum_v = pyrtl.select(sign1 == pyrtl.Const(0, 1), sum_posneg, sum_negpos)

    # Internal widths
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

    # compute scale = k*2^es + exponent
    if es == 0:
        scale1 = k1_se + exp1_ze
        scale2 = k2_se + exp2_ze
    else:
        sh_es_sc = pyrtl.Const(es, bitwidth=SC_BW)
        scale1 = shift_left_logical(k1_se, sh_es_sc) + exp1_ze
        scale2 = shift_left_logical(k2_se, sh_es_sc) + exp2_ze

    #Align fraction precision to max(fl1, fl2)
    frac_bits = pyrtl.select(fl1 > fl2, fl1, fl2)
    shift12 = fl1 - fl2
    shift21 = fl2 - fl1
    f1a = pyrtl.select(fl1 >= fl2, frac1, shift_left_logical(frac1, shift21))
    f2a = pyrtl.select(fl2 >= fl1, frac2, shift_left_logical(frac2, shift12))

    one_n = pyrtl.Const(1, bitwidth=nbits)
    one_frac = shift_left_logical(one_n, frac_bits)

    # offset calculation between scales
    offset = scale1 - scale2
    off_neg = offset[SC_BW - 1]
    abs_off = pyrtl.select(off_neg, ((~offset) + pyrtl.Const(1, bitwidth=SC_BW)), offset)

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
    sign_C = pyrtl.select(was_neg_C, base_sign_C ^ pyrtl.Const(1, 1), base_sign_C)

    is_zero_off = abs_off == pyrtl.Const(0, bitwidth=SC_BW)

    # choose diff/scale/sign by offset sign
    res_frac0 = pyrtl.select(is_zero_off, diff_A, pyrtl.select(off_neg, diff_C, diff_B))
    res_scale0 = pyrtl.select(is_zero_off, scale_A, pyrtl.select(off_neg, scale_C, scale_B))
    sign0      = pyrtl.select(is_zero_off, sign_A, pyrtl.select(off_neg, sign_C, sign_B))

    # exact cancel (same fields when abs_off==0)
    same_fields = (k1 == k2) & (exponent1 == exponent2) & (frac1 == frac2)
    is_exact_cancel = is_zero_off & same_fields
    res_frac0 = pyrtl.select(is_exact_cancel, pyrtl.Const(0, bitwidth=W), res_frac0)
    sign0     = pyrtl.select(is_exact_cancel, pyrtl.Const(0, bitwidth=1), sign0)

    # Only for es==0, same-sign, nonzero offset, and neg result.
    same_sign = ~opp
    nonzero_off = abs_off != pyrtl.Const(0, bitwidth=SC_BW)
    es_is_zero = pyrtl.Const(1, bitwidth=1) if es == 0 else pyrtl.Const(0, bitwidth=1)
    need_k_corr = same_sign & nonzero_off & es_is_zero & (sign0 == pyrtl.Const(1, bitwidth=1))
    res_scale0 = pyrtl.select(need_k_corr, res_scale0 + pyrtl.Const(1, bitwidth=SC_BW), res_scale0)

    # Normalize to target precision
    blen_bw = max(8, int(math.ceil(math.log2(W + 1))))
    bitlen0 = bitlen_u(res_frac0, blen_bw)

    fb_target = resize(frac_bits, blen_bw) + pyrtl.Const(1, bitwidth=blen_bw)

    diff_needed = fb_target - bitlen0
    need_extend = ~diff_needed[blen_bw - 1]
    extend_amt = resize(diff_needed[:W], W)
    max_shift = pyrtl.Const(W - 1, bitwidth=W)
    extend_amt = pyrtl.select(extend_amt > max_shift, max_shift, extend_amt)

    res_frac1  = pyrtl.select(need_extend, shift_left_logical(res_frac0, extend_amt), res_frac0)
    res_scale1 = pyrtl.select(need_extend, res_scale0 - resize(extend_amt, SC_BW), res_scale0)
    bitlen1    = pyrtl.select(need_extend, fb_target, bitlen0)

    # scale tweak for same-sign: + (bitlen - 1 - |offset| - frac_bits)
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

    # Regime packing
    rem_bits, regime = get_upto_regime(
        resize(resultk, nbits), nbits, pyrtl.Const(0, bitwidth=1)
    )

    # Small posit path
    es_nb = pyrtl.Const(es, bitwidth=nbits)
    is_small = rem_bits <= es_nb
    shift_amt_small = es_nb - rem_bits
    exp_shifted_small = shift_right_logical(resize(resultExponent_sc, nbits), shift_amt_small)
    small_value = regime + exp_shifted_small

    # For exponent drop (rem_bits < es)
    shift_amt_small_nz = shift_amt_small != pyrtl.Const(0, bitwidth=nbits)
    sam1 = pyrtl.select(
        shift_amt_small_nz,
        shift_amt_small - pyrtl.Const(1, bitwidth=nbits),
        pyrtl.Const(0, bitwidth=nbits),
    )
    guard_src_small = shift_right_logical(resize(resultExponent_sc, SC_BW), resize(sam1, SC_BW))
    guard_exp = pyrtl.select(shift_amt_small_nz, guard_src_small[0], pyrtl.Const(0, bitwidth=1))

    one_sc = pyrtl.Const(1, bitwidth=SC_BW)
    lower_mask_small = pyrtl.select(
        shift_amt_small_nz,
        shift_left_logical(one_sc, resize(sam1, SC_BW)) - one_sc,
        pyrtl.Const(0, bitwidth=SC_BW),
    )
    sticky_exp = (resize(resultExponent_sc, SC_BW) & lower_mask_small) != pyrtl.Const(0, bitwidth=SC_BW)

    # Normal packing fields
    rem_gt_es = rem_bits > es_nb
    frac_bits_avail = pyrtl.select(rem_gt_es, rem_bits - es_nb, pyrtl.Const(0, bitwidth=nbits))

    sum_keep = resize(frac_bits_avail, blen_bw) + pyrtl.Const(1, bitwidth=blen_bw)

    bitlen1_u, sum_keep_u, Wc = unify_width(bitlen1, sum_keep)
    ge = bitlen1_u >= sum_keep_u

    r_amt_wide = pyrtl.select(ge, bitlen1_u - sum_keep_u, pyrtl.Const(0, bitwidth=Wc))
    l_amt_wide = pyrtl.select(ge, pyrtl.Const(0, bitwidth=Wc), sum_keep_u - bitlen1_u)
    r_amt = resize(r_amt_wide, W)
    l_amt = resize(l_amt_wide, W)

    kept_plus_hidden = pyrtl.select(
        ge, shift_right_logical(res_frac1, r_amt), shift_left_logical(res_frac1, l_amt)
    )

    r_amt_nonzero = r_amt_wide != pyrtl.Const(0, bitwidth=Wc)
    r_amt_minus1  = resize(r_amt - pyrtl.Const(1, bitwidth=r_amt.bitwidth), W)
    guard_src     = shift_right_logical(res_frac1, r_amt_minus1)
    guard_frac    = pyrtl.select(ge & r_amt_nonzero, guard_src[0], pyrtl.Const(0, bitwidth=1))

    trimmed = shift_right_logical(res_frac1, r_amt)
    recon   = shift_left_logical(trimmed, r_amt)
    sticky_frac = pyrtl.select(ge & r_amt_nonzero, (res_frac1 != recon), pyrtl.Const(0, bitwidth=1))

    # Remove hidden one to form fraction field
    oneW = pyrtl.Const(1, bitwidth=W)
    one_keep = shift_left_logical(oneW, resize(frac_bits_avail, W))
    frac_field_w = kept_plus_hidden - one_keep

    exp_shifted = shift_left_logical(resize(resultExponent_sc, nbits), frac_bits_avail)
    frac_mask = shift_left_logical(pyrtl.Const(1, bitwidth=nbits), frac_bits_avail) - pyrtl.Const(1, bitwidth=nbits)
    frac_field = resize(frac_field_w, nbits) & frac_mask

    value_large = regime + exp_shifted + frac_field

    # Tie LSBs for rounding-to-even
    lsb_large = value_large[0]
    lsb_small = small_value[0]

    # Normal path rounding
    round_up_large = guard_frac & (sticky_frac | lsb_large)
    value_rounded = pyrtl.select((value_large != maxpos) & round_up_large, value_large + 1, value_large)

    any_frac = r_amt_nonzero & (guard_frac | sticky_frac) 
    guard_small_final  = pyrtl.select(shift_amt_small_nz, guard_exp,  guard_frac)
    sticky_small_final = pyrtl.select(shift_amt_small_nz, (sticky_exp | any_frac), sticky_frac)

    round_up_small = guard_small_final & (sticky_small_final | lsb_small)
    small_value_rounded = pyrtl.select((small_value != maxpos) & round_up_small, small_value + 1, small_value)

    # Select packed (unsigned) posit
    packed_pos = pyrtl.select(is_small, small_value_rounded, value_rounded)

    # Apply sign of result
    packed_signed = pyrtl.select(
        sign0 == pyrtl.Const(1, bitwidth=1),
        ((~packed_pos) + pyrtl.Const(1, bitwidth=nbits)) & mask,
        packed_pos,
    )

    is_zero_res = (res_frac1 == pyrtl.Const(0, bitwidth=W)) | is_exact_cancel
    same_sign_out = pyrtl.select(is_zero_res, zero, packed_signed)

    # Final select: special case / opposite sign / same sign
    nonquick = pyrtl.select(opp, sum_v, same_sign_out)
    result = pyrtl.select(have_quick, quick, nonquick)
    return result



