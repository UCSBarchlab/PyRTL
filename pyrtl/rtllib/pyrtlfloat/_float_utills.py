import pyrtl

from ._types import FPTypeProperties


class FloatUtils:
    @staticmethod
    def get_sign(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
        return wire[fp_prop.num_mantissa_bits + fp_prop.num_exponent_bits]

    @staticmethod
    def get_exponent(
        fp_prop: FPTypeProperties, wire: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        return wire[
            fp_prop.num_mantissa_bits : fp_prop.num_mantissa_bits
            + fp_prop.num_exponent_bits
        ]

    @staticmethod
    def get_mantissa(
        fp_prop: FPTypeProperties, wire: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        return wire[: fp_prop.num_mantissa_bits]

    @staticmethod
    def is_zero(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
        return (FloatUtils.get_mantissa(fp_prop, wire) == 0) & (
            FloatUtils.get_exponent(fp_prop, wire) == 0
        )

    @staticmethod
    def is_inf(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
        return (FloatUtils.get_mantissa(fp_prop, wire) == 0) & (
            FloatUtils.get_exponent(fp_prop, wire)
            == (1 << fp_prop.num_exponent_bits) - 1
        )

    @staticmethod
    def is_denormalized(
        fp_prop: FPTypeProperties, wire: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        return (FloatUtils.get_mantissa(fp_prop, wire) != 0) & (
            FloatUtils.get_exponent(fp_prop, wire) == 0
        )

    @staticmethod
    def is_NaN(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
        return (FloatUtils.get_mantissa(fp_prop, wire) != 0) & (
            FloatUtils.get_exponent(fp_prop, wire)
            == (1 << fp_prop.num_exponent_bits) - 1
        )

    @staticmethod
    def make_denormals_zero(
        fp_prop: FPTypeProperties, wire: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        out = pyrtl.WireVector(
            bitwidth=fp_prop.num_mantissa_bits + fp_prop.num_exponent_bits + 1
        )
        with pyrtl.conditional_assignment:
            with FloatUtils.get_exponent(fp_prop, wire) == 0:
                out |= pyrtl.concat(
                    FloatUtils.get_sign(fp_prop, wire),
                    FloatUtils.get_exponent(fp_prop, wire),
                    pyrtl.Const(0, bitwidth=fp_prop.num_mantissa_bits),
                )
            with pyrtl.otherwise:
                out |= wire
        return out

    @staticmethod
    def make_output_inf(
        fp_prop: FPTypeProperties,
        exponent: pyrtl.WireVector,
        mantissa: pyrtl.WireVector,
    ) -> None:
        exponent |= (1 << fp_prop.num_exponent_bits) - 1
        mantissa |= 0

    @staticmethod
    def make_output_NaN(
        fp_prop: FPTypeProperties,
        exponent: pyrtl.WireVector,
        mantissa: pyrtl.WireVector,
    ) -> None:
        exponent |= (1 << fp_prop.num_exponent_bits) - 1
        mantissa |= 1 << (fp_prop.num_mantissa_bits - 1)

    @staticmethod
    def make_output_zero(
        exponent: pyrtl.WireVector, mantissa: pyrtl.WireVector
    ) -> None:
        exponent |= 0
        mantissa |= 0

    @staticmethod
    def make_output_largest_finite_number(
        fp_prop: FPTypeProperties,
        exponent: pyrtl.WireVector,
        mantissa: pyrtl.WireVector,
    ) -> None:
        exponent |= (1 << fp_prop.num_exponent_bits) - 2
        mantissa |= (1 << fp_prop.num_mantissa_bits) - 1
