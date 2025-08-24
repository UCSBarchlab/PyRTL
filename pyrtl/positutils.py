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
    one_table = [pyrtl.Const(1 << i, bitwidth=32) for i in range(nbits + 1)]
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

    sign = 0
    if x < 0:
        sign = 1
        x = -x

    useed = 2 ** (2 ** es)
    k = int(math.floor(math.log(x, useed)))
    regime_value = useed ** k

    remaining = x / regime_value
    exponent = int(math.floor(math.log2(remaining)))
    exponent = max(0, exponent)
    remaining /= (2 ** exponent)

    fraction = remaining - 1.0
    frac_bits = []

    for _ in range(nbits * 2):
        fraction *= 2
        if fraction >= 1:
            frac_bits.append("1")
            fraction -= 1
        else:
            frac_bits.append("0")

    if k >= 0:
        regime_bits = "1" * (k + 1) + "0"
    else:
        regime_bits = "0" * (-k) + "1"

    bits = str(sign)
    bits += regime_bits
    exp_str = bin(exponent)[2:].zfill(es)
    bits += exp_str
    bits += "".join(frac_bits)

    bits = bits[:nbits].ljust(nbits, "0")

    return int(bits, 2)