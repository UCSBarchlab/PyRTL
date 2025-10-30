from __future__ import annotations

import pyrtl

from ._types import FloatingPointType, PyrtlFloatConfig, PyrtlFloatException
from .floatoperations import FloatOperations


class Float16WireVector(pyrtl.WireVector):
    def __init__(self):
        super().__init__()
        self.bitwidth = 16

    def __ilshift__(self, other):
        if isinstance(other, (pyrtl.WireVector, Float16WireVector)):
            super().__ilshift__(other)
        else:
            msg = (
                "FloatWireVector16 can only be driven by a FloatWireVector16 "
                "or a PyRTL WireVector."
            )
            raise PyrtlFloatException(msg)
        return self

    def _get_config(self) -> PyrtlFloatConfig | None:
        return PyrtlFloatConfig(
            FloatingPointType.FLOAT16.value, FloatOperations.default_rounding_mode
        )

    def __add__(self, other: Float16WireVector) -> Float16WireVector:
        ret = Float16WireVector()
        ret <<= FloatOperations.add(self._get_config(), self, other)
        return ret

    def __sub__(self, other: Float16WireVector) -> Float16WireVector:
        ret = Float16WireVector()
        ret <<= FloatOperations.sub(self._get_config(), self, other)
        return ret

    def __mul__(self, other: Float16WireVector) -> Float16WireVector:
        ret = Float16WireVector()
        ret <<= FloatOperations.multiply(self._get_config(), self, other)
        return ret


# will create BFloat16WireVector, Float32WireVector, and Float64WireVector the same way
