import pyrtl
from pyrtl import PyrtlError
from pyrtl.rtllib.matrix import Matrix, matrix_wv_to_list
from pyrtl.rtllib.positadder import posit_add
from pyrtl.rtllib.positmul import posit_mul


def posit_matmul(x: Matrix, y: Matrix, nbits: int, es: int) -> Matrix:
    """Performs matrix multiplication on posits.

    .. doctest only::

    >>> import pyrtl
    >>> from pyrtl.rtllib.matrix import Matrix, matrix_wv_to_list
    >>> pyrtl.reset_working_block()

    Example::

    >>> nbits = 8
    >>> es = 1

    >>> matrix_x = [[0b01000000, 0b01010000], [0b01011000, 0b01100000]]
    >>> test_x = Matrix(2, 2, bits=nbits, value=matrix_x)

    >>> matrix_y = [[0b01000000, 0b01010000], [0b01011000, 0b01100000]]
    >>> test_y = Matrix(2, 2, bits=nbits, value=matrix_y)

    >>> result = posit_matmul(test_x, test_y, nbits, es)

    >>> output = pyrtl.Output(name='output')
    >>> output <<= result.to_wirevector()

    >>> sim = pyrtl.Simulation()
    >>> sim.step()

    >>> raw_matrix = matrix_wv_to_list(
    ...     sim.inspect("output"), result.rows, result.columns, result.bits
    ... )

    >>> pretty_matrix = [[format(val, '08b') for val in row] for row in raw_matrix]
    >>> pretty_matrix
    [['01100110', '01101010'], ['01101111', '01110001']]

    :param x: A :class:`Matrix` to be multiplied.
    :param y: A :class:`Matrix` to be multiplied.
    :param nbits: A :class:`int` representing the bitwidth of each cell of
        the matrix.
    :param es: A :class:`int` representing the exponent size of the posit.

    :return: A :class:`Matrix` that represents the product of two posit
        matrices.
    """
    if not isinstance(x, Matrix):
        msg = f"error: expecting a Matrix, got {type(x)} instead"
        raise PyrtlError(msg)

    if not isinstance(y, Matrix):
        msg = f"error: expecting a Matrix, got {type(y)} instead"
        raise PyrtlError(msg)

    if x.columns != y.rows:
        msg = (
            f"error: rows and columns mismatch. "
            f"Matrix a: {x.columns} columns, Matrix b: {y.rows} rows"
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
                prod = posit_mul(x[i, k], y[k, j], nbits, es)
                acc = posit_add(acc, prod, nbits, es)
            result[i, j] = acc

    return result