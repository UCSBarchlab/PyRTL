import pyrtl
from pyrtl.corecircuits import shift_right_logical, shift_left_logical
from pyrtl.positutils import decode_posit, get_upto_regime


def posit_mul(
    a: pyrtl.WireVector, b: pyrtl.WireVector, nbits: int, es: int
) -> pyrtl.WireVector:
    """Multiplies two numbers in posit format and returns their product.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()
        >>> nbits, es = 8, 1
        >>> a = pyrtl.Input(bitwidth=nbits, name='a')
        >>> b = pyrtl.Input(bitwidth=nbits, name='b')
        >>> out = pyrtl.Output(bitwidth=nbits, name='out')
        >>> out <<= posit_mul(a, b, nbits, es)
        >>> sim = pyrtl.Simulation()
        >>> sim.step({'a': 0b01011100, 'b': 0b01000000})  # 3.5 * 2 = 7.0 (approx)
        >>> format(sim.inspect('out'), '08b')  # doctest: +ELLIPSIS
        '...'

    :param a: A WireVector posit multiplicand.
    :param b: A WireVector posit multiplier.
    :param nbits: Total bitwidth of the posit.
    :param es: Exponent size of the posit.
    :return: A WireVector representing the product of the two posits.
    """

    # Decode inputs
    sign_a, k_a, exp_a, frac_a, fraclength_a = decode_posit(a, nbits, es)
    sign_b, k_b, exp_b, frac_b, fraclength_b = decode_posit(b, nbits, es)

    # Handle multiplication of special cases
    either_zero = (a == 0) | (b == 0)
    either_inf = (a == (1 << (nbits - 1))) | (b == (1 << (nbits - 1)))

    final_value = pyrtl.WireVector(bitwidth=nbits, name='final_value')
    result_zero = pyrtl.Const(0, bitwidth=nbits)
    result_nar = pyrtl.Const(1 << (nbits - 1), bitwidth=nbits)
    normal_case = ~(either_zero | either_inf)

    # Compute resultant sign
    sign_final = sign_a ^ sign_b

    # Compute scale
    scale_a = k_a * pyrtl.Const(2 ** es) + exp_a
    scale_b = k_b * pyrtl.Const(2 ** es) + exp_b
    scale_sum = scale_a + scale_b

    # Fraction multiplication with implicit 1
    one_table = [pyrtl.Const(1 << i, bitwidth=32) for i in range(nbits)]
    one_shifted_a = pyrtl.Const(0, bitwidth=32)
    one_shifted_b = pyrtl.Const(0, bitwidth=32)
    for i in range(nbits):
        one_shifted_a = pyrtl.select(fraclength_a == i, one_table[i], one_shifted_a)
        one_shifted_b = pyrtl.select(fraclength_b == i, one_table[i], one_shifted_b)

    frac_a_32 = pyrtl.concat(pyrtl.Const(0, bitwidth=24), frac_a)
    frac_b_32 = pyrtl.concat(pyrtl.Const(0, bitwidth=24), frac_b)
    frac_a_full = one_shifted_a + frac_a_32
    frac_b_full = one_shifted_b + frac_b_32

    frac_product = frac_a_full * frac_b_full

    # Normalize fraction
    fraclen_total = fraclength_a + fraclength_b
    threshold = shift_left_logical(pyrtl.Const(1, bitwidth=32), fraclen_total + 1)
    frac = frac_product
    scale = pyrtl.Const(0, bitwidth=8)
    for _ in range(8):
        shifted = shift_right_logical(frac, 1)
        should_shift = frac >= threshold
        frac = pyrtl.select(should_shift, shifted, frac)
        scale = pyrtl.select(should_shift, scale + 1, scale)
    normalized_frac = frac
    normalized_scale = scale

    # Remove extra 1
    mask_table = [pyrtl.Const((1 << i) - 1, bitwidth=32) for i in range(33)]
    mask_val = pyrtl.Const(0)
    for i in range(1, 33):
        mask_val = pyrtl.select(fraclen_total == i, mask_table[i], mask_val)
    frac_result = normalized_frac & mask_val

    # Final scale
    final_scale = scale_sum + normalized_scale

    # Extract k and exponent
    resultk = shift_right_logical(final_scale, pyrtl.Const(es, bitwidth=8))
    mod_mask = pyrtl.Const((1 << es) - 1, bitwidth=final_scale.bitwidth)
    resultExponent = final_scale & mod_mask

    # Get remaining bits and regime
    rem_bits, sign_w_regime = get_upto_regime(resultk, nbits, sign_final)

    # Fraction bits with rounding
    frac_bits = rem_bits - es
    is_small = rem_bits <= es

    shift_amt_small = es - rem_bits
    exp_shifted_small = shift_right_logical(resultExponent, shift_amt_small)
    value_small = sign_w_regime + exp_shifted_small

    sum_fraclens = fraclength_a + fraclength_b
    roundup_bit = pyrtl.Const(0, bitwidth=1)
    cond_round = sum_fraclens > frac_bits
    shift_amt1 = sum_fraclens - frac_bits - 1
    shift_amt2 = sum_fraclens - frac_bits

    roundup_candidate = shift_right_logical(frac_result, shift_amt1) & 1
    frac_shifted = shift_right_logical(frac_result, shift_amt2)
    frac_shifted_else = shift_left_logical(frac_result, frac_bits - sum_fraclens)

    frac_final = pyrtl.WireVector(bitwidth=nbits)
    frac_final <<= pyrtl.select(cond_round, frac_shifted, frac_shifted_else)

    roundup_bit = pyrtl.WireVector(bitwidth=1, name='roundup_bit')
    roundup_bit <<= pyrtl.select(cond_round, roundup_candidate, pyrtl.Const(0, bitwidth=1))

    exp_shifted_large = shift_left_logical(resultExponent, frac_bits)
    value_large = sign_w_regime + exp_shifted_large + frac_final
    all_ones = pyrtl.Const((1 << nbits) - 1, bitwidth=nbits)
    value_rounded = pyrtl.select(
        (roundup_bit & (value_large != all_ones)), value_large + 1, value_large
    )

    computed_value = pyrtl.select(is_small, value_small, value_rounded)

    # Select between normal values and special computed value
    final_value <<= pyrtl.select(
        either_zero, result_zero, pyrtl.select(either_inf, result_nar, computed_value)
    )

    return final_value
