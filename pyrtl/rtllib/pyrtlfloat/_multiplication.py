import pyrtl

from ._float_utills import FloatUtils
from ._types import PyrtlFloatConfig, RoundingMode


class MultiplicationHelper:
    @staticmethod
    def multiply(
        config: PyrtlFloatConfig,
        operand_a: pyrtl.WireVector,
        operand_b: pyrtl.WireVector,
    ) -> pyrtl.WireVector:
        fp_type_props = config.fp_type_properties
        rounding_mode = config.rounding_mode
        num_exp_bits = fp_type_props.num_exponent_bits
        num_mant_bits = fp_type_props.num_mantissa_bits

        operand_a_daz = FloatUtils.make_denormals_zero(fp_type_props, operand_a)
        operand_b_daz = FloatUtils.make_denormals_zero(fp_type_props, operand_b)
        a_sign = FloatUtils.get_sign(fp_type_props, operand_a_daz)
        b_sign = FloatUtils.get_sign(fp_type_props, operand_b_daz)
        a_exponent = FloatUtils.get_exponent(fp_type_props, operand_a_daz)
        b_exponent = FloatUtils.get_exponent(fp_type_props, operand_b_daz)

        exponent_bias = 2 ** (fp_type_props.num_exponent_bits - 1) - 1

        result_sign = a_sign ^ b_sign
        operand_exponent_sums = a_exponent + b_exponent
        product_exponent = operand_exponent_sums - pyrtl.Const(exponent_bias)

        a_mantissa = pyrtl.concat(
            pyrtl.Const(1), FloatUtils.get_mantissa(fp_type_props, operand_a_daz)
        )
        b_mantissa = pyrtl.concat(
            pyrtl.Const(1), FloatUtils.get_mantissa(fp_type_props, operand_b_daz)
        )
        product_mantissa = a_mantissa * b_mantissa

        normalized_product_exponent = pyrtl.WireVector(bitwidth=num_exp_bits + 1)
        normalized_product_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)

        need_to_normalize = product_mantissa[-1]

        if rounding_mode == RoundingMode.RNE:
            guard = pyrtl.WireVector(bitwidth=1)
            sticky = pyrtl.WireVector(bitwidth=1)
            last = pyrtl.WireVector(bitwidth=1)

        with pyrtl.conditional_assignment:
            with need_to_normalize:
                normalized_product_mantissa |= product_mantissa[-num_mant_bits - 1 :]
                normalized_product_exponent |= product_exponent + 1
                if rounding_mode == RoundingMode.RNE:
                    guard |= product_mantissa[-num_mant_bits - 2]
                    sticky |= product_mantissa[: -num_mant_bits - 2] != 0
                    last |= product_mantissa[-num_mant_bits - 1]
            with pyrtl.otherwise:
                normalized_product_mantissa |= product_mantissa[-num_mant_bits - 2 : -1]
                normalized_product_exponent |= product_exponent
                if rounding_mode == RoundingMode.RNE:
                    guard |= product_mantissa[-num_mant_bits - 3]
                    sticky |= product_mantissa[: -num_mant_bits - 3] != 0
                    last |= product_mantissa[-num_mant_bits - 2]

        if rounding_mode == RoundingMode.RNE:
            rounded_product_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)
            rounded_product_exponent = pyrtl.WireVector(bitwidth=num_exp_bits + 1)
            exponent_incremented = pyrtl.WireVector(bitwidth=1)
            with pyrtl.conditional_assignment:
                with guard & (last | sticky):
                    with normalized_product_mantissa == (1 << num_mant_bits) - 1:
                        rounded_product_mantissa |= 0
                        rounded_product_exponent |= normalized_product_exponent + 1
                        exponent_incremented |= 1
                    with pyrtl.otherwise:
                        rounded_product_mantissa |= normalized_product_mantissa + 1
                        rounded_product_exponent |= normalized_product_exponent
                        exponent_incremented |= 0
                with pyrtl.otherwise:
                    rounded_product_mantissa |= normalized_product_mantissa
                    rounded_product_exponent |= normalized_product_exponent
                    exponent_incremented |= 0

        result_exponent = pyrtl.WireVector(bitwidth=num_exp_bits)
        result_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)

        operand_a_nan = FloatUtils.is_NaN(fp_type_props, operand_a_daz)
        operand_b_nan = FloatUtils.is_NaN(fp_type_props, operand_b_daz)
        operand_a_inf = FloatUtils.is_inf(fp_type_props, operand_a_daz)
        operand_b_inf = FloatUtils.is_inf(fp_type_props, operand_b_daz)
        operand_a_zero = FloatUtils.is_zero(fp_type_props, operand_a_daz)
        operand_b_zero = FloatUtils.is_zero(fp_type_props, operand_b_daz)
        operand_a_denormalized = FloatUtils.is_denormalized(
            fp_type_props, operand_a_daz
        )
        operand_b_denormalized = FloatUtils.is_denormalized(
            fp_type_props, operand_b_daz
        )

        # Overflow and underflow checks (only for normal cases)
        sum_exponent_max_value = pyrtl.Const(2**num_exp_bits - 2 + exponent_bias)
        sum_exponent_min_value = pyrtl.Const(1 + exponent_bias)
        if rounding_mode == RoundingMode.RNE:
            exponent_max_value = (
                sum_exponent_max_value - need_to_normalize - exponent_incremented
            )
            exponent_min_value = (
                sum_exponent_min_value - need_to_normalize - exponent_incremented
            )
        else:
            exponent_max_value = sum_exponent_max_value - need_to_normalize
            exponent_min_value = sum_exponent_min_value - need_to_normalize

        if rounding_mode == RoundingMode.RNE:
            raw_result_exponent = rounded_product_exponent[0:num_exp_bits]
            raw_result_mantissa = rounded_product_mantissa
        else:
            raw_result_exponent = normalized_product_exponent[0:num_exp_bits]
            raw_result_mantissa = normalized_product_mantissa

        with pyrtl.conditional_assignment:
            # nan
            with (
                operand_a_nan
                | operand_b_nan
                | (operand_a_inf & operand_b_zero)
                | (operand_a_zero & operand_b_inf)
            ):
                FloatUtils.make_output_NaN(
                    fp_type_props, result_exponent, result_mantissa
                )
            # infinity
            with operand_a_inf | operand_b_inf:
                FloatUtils.make_output_inf(
                    fp_type_props, result_exponent, result_mantissa
                )
            # overflow
            with operand_exponent_sums > exponent_max_value:
                if rounding_mode == RoundingMode.RNE:
                    FloatUtils.make_output_inf(
                        fp_type_props, result_exponent, result_mantissa
                    )
                else:
                    FloatUtils.make_output_largest_finite_number(
                        fp_type_props, result_exponent, result_mantissa
                    )
            # zero or underflow
            with (
                operand_a_zero
                | operand_b_zero
                | (operand_exponent_sums < exponent_min_value)
                | operand_a_denormalized
                | operand_b_denormalized
            ):
                FloatUtils.make_output_zero(result_exponent, result_mantissa)
            with pyrtl.otherwise:
                result_exponent |= raw_result_exponent
                result_mantissa |= raw_result_mantissa

        return pyrtl.concat(result_sign, result_exponent, result_mantissa)
