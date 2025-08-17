import pyrtl
from pyrtl import PyrtlError
from pyrtl.rtllib.matrix import Matrix
from positadder import posit_add
from positmul import posit_mul

def posit_matmul(x, y, nbits, es):
    if not isinstance(x, Matrix):
        msg = f"error: expecting a Matrix, got {type(x)} instead"
        raise PyrtlError(msg)
    if not isinstance(y, Matrix):
        msg = f"error: expecting a Matrix, got {type(y)} instead"
        raise PyrtlError(msg)
    
    if x.columns != y.rows:
        msg = (
                f"error: rows and columns mismatch. Matrix a: {x.columns} columns, "
                f"Matrix b: {y.rows} rows"
            )
        raise PyrtlError(msg)
    
    result = Matrix(
            x.rows,
            y.columns,
            nbits,
            max_bits=x.max_bits,
        )
    
    for i in range(x.rows):
        for j in range(y.columns):
            acc = pyrtl.Const(0, bitwidth=nbits)
            for k in range(x.columns):
                prod = posit_mul(nbits, es, x[i, k], y[k, j])
                acc = posit_add(acc, prod, nbits, es)
            result[i, j] = acc
    
    return result