import pyrtl

from ._float_utills import FloatUtils
from ._types import PyrtlFloatConfig, RoundingMode


class AddSubHelper:
    @staticmethod
    def add(
        config: PyrtlFloatConfig,
        operand_a: pyrtl.WireVector,
        operand_b: pyrtl.WireVector,
    ) -> pyrtl.WireVector:
        fp_type_props = config.fp_type_properties
        rounding_mode = config.rounding_mode
        num_exp_bits = fp_type_props.num_exponent_bits
        num_mant_bits = fp_type_props.num_mantissa_bits
        total_bits = num_exp_bits + num_mant_bits + 1

        operand_a_daz = FloatUtils.make_denormals_zero(fp_type_props, operand_a)
        operand_b_daz = FloatUtils.make_denormals_zero(fp_type_props, operand_b)

        # operand_smaller is the operand with the smaller absolute value and
        # operand_larger is the operand with the larger absolute value
        operand_smaller = pyrtl.WireVector(bitwidth=total_bits)
        operand_larger = pyrtl.WireVector(bitwidth=total_bits)

        with pyrtl.conditional_assignment:
            exponent_and_mantissa_len = num_mant_bits + num_exp_bits
            with (
                operand_a_daz[:exponent_and_mantissa_len]
                < operand_b_daz[:exponent_and_mantissa_len]
            ):
                operand_smaller |= operand_a_daz
                operand_larger |= operand_b_daz
            with pyrtl.otherwise:
                operand_smaller |= operand_b_daz
                operand_larger |= operand_a_daz

        smaller_operand_sign = FloatUtils.get_sign(fp_type_props, operand_smaller)
        larger_operand_sign = FloatUtils.get_sign(fp_type_props, operand_larger)
        smaller_operand_exponent = FloatUtils.get_exponent(
            fp_type_props, operand_smaller
        )
        larger_operand_exponent = FloatUtils.get_exponent(fp_type_props, operand_larger)
        smaller_operand_mantissa = pyrtl.concat(
            pyrtl.Const(1), FloatUtils.get_mantissa(fp_type_props, operand_smaller)
        )
        larger_operand_mantissa = pyrtl.concat(
            pyrtl.Const(1), FloatUtils.get_mantissa(fp_type_props, operand_larger)
        )

        exponent_diff = larger_operand_exponent - smaller_operand_exponent
        smaller_mantissa_shifted = pyrtl.shift_right_logical(
            smaller_operand_mantissa, exponent_diff
        )
        grs = pyrtl.WireVector(bitwidth=3)  # guard, round, sticky bits for rounding
        with pyrtl.conditional_assignment:
            with exponent_diff >= 2:
                guard_and_round = pyrtl.shift_right_logical(
                    smaller_operand_mantissa, exponent_diff - 2
                )[:2]
                mask = (
                    pyrtl.shift_left_logical(
                        pyrtl.Const(1, bitwidth=num_mant_bits), exponent_diff - 2
                    )
                    - 1
                )
                sticky = (smaller_operand_mantissa & mask) != 0
                grs |= pyrtl.concat(guard_and_round, sticky)
            with exponent_diff == 1:
                grs |= pyrtl.concat(
                    smaller_operand_mantissa[0], pyrtl.Const(0, bitwidth=2)
                )
            with pyrtl.otherwise:
                grs |= 0
        smaller_mantissa_shifted_grs = pyrtl.concat(smaller_mantissa_shifted, grs)
        larger_mantissa_extended = pyrtl.concat(
            larger_operand_mantissa, pyrtl.Const(0, bitwidth=3)
        )

        sum_exponent, sum_mantissa, sum_grs, sum_carry = AddSubHelper._add_operands(
            larger_operand_exponent,
            smaller_mantissa_shifted_grs,
            larger_mantissa_extended,
        )

        sub_exponent, sub_mantissa, sub_grs, num_leading_zeros = (
            AddSubHelper._sub_operands(
                num_mant_bits,
                larger_operand_exponent,
                smaller_mantissa_shifted_grs,
                larger_mantissa_extended,
            )
        )

        # WireVectors for the raw addition or subtraction result, before handling
        # special cases
        raw_result_exponent = pyrtl.WireVector(bitwidth=num_exp_bits)
        raw_result_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)
        if rounding_mode == RoundingMode.RNE:
            raw_result_grs = pyrtl.WireVector(bitwidth=3)

        with pyrtl.conditional_assignment:
            with smaller_operand_sign == larger_operand_sign:  # add
                raw_result_exponent |= sum_exponent
                raw_result_mantissa |= sum_mantissa
                if rounding_mode == RoundingMode.RNE:
                    raw_result_grs |= sum_grs
            with pyrtl.otherwise:  # sub
                raw_result_exponent |= sub_exponent
                raw_result_mantissa |= sub_mantissa
                if rounding_mode == RoundingMode.RNE:
                    raw_result_grs |= sub_grs

        if rounding_mode == RoundingMode.RNE:
            (
                raw_result_rounded_exponent,
                raw_result_rounded_mantissa,
                rounding_exponent_incremented,
            ) = AddSubHelper._round(
                num_mant_bits,
                num_exp_bits,
                raw_result_exponent,
                raw_result_mantissa,
                raw_result_grs,
            )

        smaller_operand_nan = FloatUtils.is_NaN(fp_type_props, operand_smaller)
        larger_operand_nan = FloatUtils.is_NaN(fp_type_props, operand_larger)
        smaller_operand_inf = FloatUtils.is_inf(fp_type_props, operand_smaller)
        larger_operand_inf = FloatUtils.is_inf(fp_type_props, operand_larger)
        smaller_operand_zero = FloatUtils.is_zero(fp_type_props, operand_smaller)
        larger_operand_zero = FloatUtils.is_zero(fp_type_props, operand_larger)

        # WireVectors for the final result after handling special cases
        final_result_sign = pyrtl.WireVector(bitwidth=1)
        final_result_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)
        final_result_exponent = pyrtl.WireVector(bitwidth=num_exp_bits)

        # handle special cases
        with pyrtl.conditional_assignment:
            # if either operand is NaN or both operands are infinity of opposite signs,
            # the result is NaN
            with (
                smaller_operand_nan
                | larger_operand_nan
                | (
                    smaller_operand_inf
                    & larger_operand_inf
                    & (larger_operand_sign != smaller_operand_sign)
                )
            ):
                final_result_sign |= larger_operand_sign
                FloatUtils.make_output_NaN(
                    fp_type_props, final_result_exponent, final_result_mantissa
                )
            # infinities
            with smaller_operand_inf:
                final_result_sign |= larger_operand_sign
                FloatUtils.make_output_inf(
                    fp_type_props, final_result_exponent, final_result_mantissa
                )
            with larger_operand_inf:
                final_result_sign |= larger_operand_sign
                FloatUtils.make_output_inf(
                    fp_type_props, final_result_exponent, final_result_mantissa
                )
            # +num + -num = +0
            with (
                (smaller_operand_mantissa == larger_operand_mantissa)
                & (smaller_operand_exponent == larger_operand_exponent)
                & (larger_operand_sign != smaller_operand_sign)
            ):
                final_result_sign |= 0
                FloatUtils.make_output_zero(
                    final_result_exponent, final_result_mantissa
                )
            with smaller_operand_zero:
                final_result_sign |= larger_operand_sign
                final_result_mantissa |= larger_operand_mantissa
                final_result_exponent |= larger_operand_exponent
            with larger_operand_zero:
                final_result_sign |= smaller_operand_sign
                final_result_mantissa |= smaller_operand_mantissa
                final_result_exponent |= smaller_operand_exponent
            # overflow and underflow
            initial_larger_exponent_max_value = pyrtl.Const(2**num_exp_bits - 2)
            if rounding_mode == RoundingMode.RNE:
                larger_exponent_max_value = (
                    initial_larger_exponent_max_value
                    - sum_carry
                    - rounding_exponent_incremented
                )
            else:
                larger_exponent_max_value = (
                    initial_larger_exponent_max_value - sum_carry
                )
            initial_larger_exponent_min_value = pyrtl.Const(1)
            if rounding_mode == RoundingMode.RNE:
                larger_exponent_min_value = (
                    initial_larger_exponent_min_value
                    + num_leading_zeros
                    - rounding_exponent_incremented
                )
            else:
                larger_exponent_min_value = (
                    initial_larger_exponent_min_value + num_leading_zeros
                )
            with (smaller_operand_sign == larger_operand_sign) & (
                larger_operand_exponent > larger_exponent_max_value
            ):  # detect overflow on addition
                final_result_sign |= larger_operand_sign
                if rounding_mode == RoundingMode.RNE:
                    FloatUtils.make_output_inf(
                        fp_type_props, final_result_exponent, final_result_mantissa
                    )
                else:
                    FloatUtils.make_output_largest_finite_number(
                        fp_type_props, final_result_exponent, final_result_mantissa
                    )
            with (smaller_operand_sign != larger_operand_sign) & (
                larger_operand_exponent < larger_exponent_min_value
            ):  # detect underflow on subtraction
                final_result_sign |= larger_operand_sign
                FloatUtils.make_output_zero(
                    final_result_exponent, final_result_mantissa
                )
            with pyrtl.otherwise:
                final_result_sign |= larger_operand_sign
                if rounding_mode == RoundingMode.RNE:
                    final_result_exponent |= raw_result_rounded_exponent
                    final_result_mantissa |= raw_result_rounded_mantissa
                else:
                    final_result_exponent |= raw_result_exponent
                    final_result_mantissa |= raw_result_mantissa

        return pyrtl.concat(
            final_result_sign, final_result_exponent, final_result_mantissa
        )

    @staticmethod
    def sub(
        config: PyrtlFloatConfig,
        operand_a: pyrtl.WireVector,
        operand_b: pyrtl.WireVector,
    ) -> pyrtl.WireVector:
        num_exp_bits = config.fp_type_properties.num_exponent_bits
        num_mant_bits = config.fp_type_properties.num_mantissa_bits
        operand_b_negated = operand_b ^ pyrtl.concat(
            pyrtl.Const(1, bitwidth=1),
            pyrtl.Const(0, bitwidth=num_exp_bits + num_mant_bits),
        )
        return AddSubHelper.add(config, operand_a, operand_b_negated)

    @staticmethod
    def _add_operands(
        larger_operand_exponent: pyrtl.WireVector,
        smaller_mantissa_shifted_grs: pyrtl.WireVector,
        larger_mantissa_extended: pyrtl.WireVector,
    ) -> tuple[pyrtl.WireVector, pyrtl.WireVector, pyrtl.WireVector, pyrtl.WireVector]:
        sum_mantissa_grs = pyrtl.WireVector()
        sum_mantissa_grs <<= larger_mantissa_extended + smaller_mantissa_shifted_grs
        sum_carry = sum_mantissa_grs[-1]
        sum_mantissa = pyrtl.select(
            sum_carry, sum_mantissa_grs[4:], sum_mantissa_grs[3:-1]
        )
        sum_grs = pyrtl.select(
            sum_carry,
            pyrtl.concat(sum_mantissa_grs[2:4], sum_mantissa_grs[:2] != 0),
            sum_mantissa_grs[:3],
        )
        sum_exponent = pyrtl.select(
            sum_carry, larger_operand_exponent + 1, larger_operand_exponent
        )
        return sum_exponent, sum_mantissa, sum_grs, sum_carry

    @staticmethod
    def _sub_operands(
        num_mant_bits: int,
        larger_operand_exponent: pyrtl.WireVector,
        smaller_mantissa_shifted_grs: pyrtl.WireVector,
        larger_mantissa_extended: pyrtl.WireVector,
    ) -> tuple[pyrtl.WireVector, pyrtl.WireVector, pyrtl.WireVector, pyrtl.WireVector]:
        def leading_zero_priority_encoder(wire: pyrtl.WireVector, length: int):
            out = pyrtl.WireVector(
                bitwidth=pyrtl.infer_val_and_bitwidth(length - 1).bitwidth
            )
            with pyrtl.conditional_assignment:
                for i in range(wire.bitwidth - 1, wire.bitwidth - length - 1, -1):
                    with wire[i]:
                        out |= wire.bitwidth - i - 1
            return out

        sub_mantissa_grs = pyrtl.WireVector(bitwidth=num_mant_bits + 4)
        sub_mantissa_grs <<= larger_mantissa_extended - smaller_mantissa_shifted_grs
        num_leading_zeros = leading_zero_priority_encoder(
            sub_mantissa_grs, num_mant_bits + 1
        )
        sub_mantissa_grs_shifted = pyrtl.shift_left_logical(
            sub_mantissa_grs, num_leading_zeros
        )
        sub_mantissa = sub_mantissa_grs_shifted[3:]
        sub_grs = sub_mantissa_grs_shifted[:3]
        sub_exponent = larger_operand_exponent - num_leading_zeros
        return sub_exponent, sub_mantissa, sub_grs, num_leading_zeros

    @staticmethod
    def _round(
        num_mant_bits: int,
        num_exp_bits: int,
        raw_result_exponent: pyrtl.WireVector,
        raw_result_mantissa: pyrtl.WireVector,
        raw_result_grs: pyrtl.WireVector,
    ) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
        last = raw_result_mantissa[0]
        guard = raw_result_grs[2]
        round = raw_result_grs[1]
        sticky = raw_result_grs[0]
        round_up = guard & (last | round | sticky)
        raw_result_rounded_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)
        raw_result_rounded_exponent = pyrtl.WireVector(bitwidth=num_exp_bits)
        rounding_exponent_incremented = pyrtl.WireVector(bitwidth=1)
        with pyrtl.conditional_assignment:
            with round_up:
                with raw_result_mantissa == (1 << num_mant_bits) - 1:
                    raw_result_rounded_mantissa |= 0
                    raw_result_rounded_exponent |= raw_result_exponent + 1
                    rounding_exponent_incremented |= 1
                with pyrtl.otherwise:
                    raw_result_rounded_mantissa |= raw_result_mantissa + 1
                    raw_result_rounded_exponent |= raw_result_exponent
                    rounding_exponent_incremented |= 0
            with pyrtl.otherwise:
                raw_result_rounded_mantissa |= raw_result_mantissa
                raw_result_rounded_exponent |= raw_result_exponent
                rounding_exponent_incremented |= 0
        return (
            raw_result_rounded_exponent,
            raw_result_rounded_mantissa,
            rounding_exponent_incremented,
        )
