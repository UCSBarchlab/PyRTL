"""
Add, subtract, and multiply floating point numbers.

Several standard ``Float`` formats like :class:`Float16` and :class:`Float32` are
predefined. Users may also define custom floating point formats.

The main operators are :func:`add`, :func:`sub`, and :func:`mult`. These operators all
accept and return one of these ``Float`` formats. Inputs to an operator must share
the same ``Float`` format. The operator's output will be in the same ``Float`` format as
its inputs.
"""

from .add_sub import add, sub
from .multiplication import mult
from .types import BFloat16, Float16, Float32, Float64, RoundingMode
from .utils import get_default_rounding_mode, set_default_rounding_mode

__all__ = [
    "BFloat16",
    "Float16",
    "Float32",
    "Float64",
    "RoundingMode",
    "add",
    "get_default_rounding_mode",
    "mult",
    "sub",
    "set_default_rounding_mode",
]
