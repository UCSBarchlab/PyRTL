"""Implements utility functions for posit operations"""

import pyrtl
from pyrtl.corecircuits import shift_right_logical, shift_left_logical

#decode posit
def decode_posit(x, nbits, es):
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
            pyrtl.Const(0)
        )
        active = active & is_same

    k_pos = run_len - pyrtl.Const(1, bitwidth=nbits)
    k_neg = (~run_len) + pyrtl.Const(1, bitwidth=nbits)
    k = pyrtl.select(regime_bit, k_pos, k_neg)

    exp = pyrtl.Const(0, bitwidth=es)
    for i in range(nbits - 2):
        exp = pyrtl.select(run_len == pyrtl.Const(i), rest[i + 1], exp)

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

def get_upto_regime(k, n_val, sign_final):
    precomputed_val = (1 << (n_val - 1)) - 1
    n_c = pyrtl.Const(n_val, bitwidth=n_val)
    n_minus_1 = pyrtl.Const(n_val - 1, bitwidth=n_val)
    n_minus_2 = pyrtl.Const(n_val - 2, bitwidth=n_val)
    n_minus_3 = pyrtl.Const(n_val - 3, bitwidth=n_val)

    k_thresh = pyrtl.Const(1 << (n_val - 1), bitwidth=k.bitwidth)
    abs_k = pyrtl.select(
        k >= k_thresh,
        (
            (~k + pyrtl.Const(1, bitwidth=k.bitwidth))
            & pyrtl.Const((1 << n_val) - 1, bitwidth=k.bitwidth)
        ),
        k,
    )

    large_neg_regime = abs_k >= n_minus_1
    large_pos_regime = abs_k >= n_minus_2

    temp_rem1 = (n_c + k) - pyrtl.Const(2, bitwidth=n_val)
    sign_case1_inner = shift_right_logical(
        pyrtl.Const(1 << (n_val - 2), bitwidth=n_val), abs_k
    )

    rem_bits_case1 = pyrtl.select(
        large_neg_regime,
        pyrtl.Const(0, bitwidth=n_val),
        temp_rem1,
    )
    sign_case1 = pyrtl.select(
        large_neg_regime,
        pyrtl.Const(0, bitwidth=n_val),
        sign_case1_inner,
    )

    temp_rem2 = n_minus_3 - k
    shift_amt = k + pyrtl.Const(2, bitwidth=n_val)
    ones = (
        shift_left_logical(pyrtl.Const(1, bitwidth=n_val), shift_amt)
        - pyrtl.Const(2, bitwidth=n_val)
    )
    shifted_case2 = shift_left_logical(ones, temp_rem2)

    rem_bits_case2 = pyrtl.select(
        large_pos_regime,
        pyrtl.Const(0, bitwidth=n_val),
        temp_rem2,
    )
    sign_case2 = pyrtl.select(
        large_pos_regime,
        pyrtl.Const(precomputed_val, bitwidth=n_val),
        shifted_case2,
    )

    cond_k_ge = k >= k_thresh
    rem_bits = pyrtl.select(cond_k_ge, rem_bits_case1, rem_bits_case2)
    sign_w_regime = pyrtl.select(cond_k_ge, sign_case1, sign_case2)

    sign_w_regime_trimmed = sign_w_regime[: n_val - 1]
    sign_w_regime_final = pyrtl.concat(sign_final, sign_w_regime_trimmed)
    return rem_bits, sign_w_regime_final

def frac_with_hidden_one(frac, frac_length, nbits):
    one_table = [
        pyrtl.Const(1 << i, bitwidth=32)
        for i in range(nbits + 1)
    ]
    one_shifted = pyrtl.Const(0, bitwidth=32)

    for i in range(nbits + 1):
        one_shifted = pyrtl.select(
            frac_length == pyrtl.Const(i, bitwidth=8),
            one_table[i],
            one_shifted,
        )

    frac_32 = pyrtl.concat(
        pyrtl.Const(0, bitwidth=32 - (nbits - 1)), frac
    )
    full = one_shifted + frac_32
    return full

def remove_first_one(val):
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
