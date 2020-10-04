from functools import reduce

from ..matrix import Matrix
from ..wire import Const, WireVector
from ..corecircuits import select
from ..pyrtlexceptions import PyrtlError


def multiply(first, second):
    ''' Perform the elementwise or scalar multiplication operation.

    :param Matrix first: first matrix.
    :param Matrix/Wirevector second: second matrix.
    :return: a Matrix object with the element wise or scaler multiplication being
    performed.
    '''
    if not isinstance(first, Matrix):
        raise PyrtlError('error, expecting a Matrix'
                         'got %s instead' % type(second))
    return first * second


def sum(matrix, axis=None, bits=None):
    ''' Returns the sum of all the values in two matrices

    :param Matrix/Wirevecot matrix: the matrix to perform sum operation on.
    If it is a wirevector, it will return itself.
    :param None/int axis: The axis to perform the operation on.
    None refers to sum of all item. 0 is sum of column. 1 is sum of rows. Defaults to None.
    :param int bits: The bits per value of the sum. Defaults to bits of old matrix
    :return: A wirevector or Matrix representing sum
    '''
    def sum_2(first, second):
        return first + second

    if isinstance(matrix, WireVector):
        return matrix

    if not isinstance(matrix, Matrix):
        raise PyrtlError('error, expecting a Matrix or Wirevector for matrix'
                         'got %s instead' % type(matrix))

    if not isinstance(bits, int) and bits is not None:
        raise PyrtlError('error, expecting an int/None for bits'
                         'got %s instead' % type(bits))

    if not isinstance(axis, int) and axis is not None:
        raise PyrtlError('error, expecting an int or None for axis'
                         'got %s instead' % type(axis))

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        raise PyrtlError('error, bits cant be negative or zero'
                         'got %s instead' % bits)

    if axis is None:
        inputs = []
        for i in range(matrix.rows):
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
        return reduce(sum_2, inputs)

    if axis == 0:
        result = Matrix(
            1, matrix.columns, signed=matrix.signed, bits=bits)

        for i in range(matrix.columns):
            inputs = []
            for j in range(matrix.rows):
                inputs.append(matrix[j, i])
            result[0, i] = reduce(sum_2, inputs)
        return result

    if axis == 1:
        result = Matrix(
            1, matrix.rows, signed=matrix.signed, bits=bits)
        for i in range(matrix.rows):
            inputs = []
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
            result[0, i] = reduce(sum_2, inputs)
        return result

    raise PyrtlError('Axis Invalid, expected (None, 0, or 1), got %s' % axis)


def min(matrix, axis=None, bits=None):
    ''' Returns the min value in a matrix.

    :param Matrix/Wirevecot matrix: the matrix to perform min operation on.
    If it is a wirevector, it will return itself.
    :param None/int axis: The axis to perform the operation on.
    None refers to min of all item. 0 is min of column. 1 is min of rows. Defaults to None.
    :param int bits: The bits per value of the min. Defaults to bits of old matrix
    :return: A wirevector or Matrix representing the min value
    '''
    def min_2(first, second):
        return select(first < second, first, second)

    if isinstance(matrix, WireVector):
        return matrix

    if not isinstance(matrix, Matrix):
        raise PyrtlError('error, expecting a Matrix or Wirevector for matrix'
                         'got %s instead' % type(matrix))

    if not isinstance(bits, int) and bits is not None:
        raise PyrtlError('error, expecting an int/None for bits'
                         'got %s instead' % type(bits))

    if not isinstance(axis, int) and axis is not None:
        raise PyrtlError('error, expecting an int or None for axis'
                         'got %s instead' % type(axis))

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        raise PyrtlError('error, bits cant be negative or zero'
                         'got %s instead' % bits)

    if axis is None:
        inputs = []
        for i in range(matrix.rows):
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
        return reduce(min_2, inputs)

    if axis == 0:
        result = Matrix(
            1, matrix.columns, signed=matrix.signed, bits=bits)

        for i in range(matrix.columns):
            inputs = []
            for j in range(matrix.rows):
                inputs.append(matrix[j, i])
            result[0, i] = reduce(min_2, inputs)
        return result

    if axis == 1:
        result = Matrix(
            1, matrix.rows, signed=matrix.signed, bits=bits)
        for i in range(matrix.rows):
            inputs = []
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
            result[0, i] = reduce(min_2, inputs)
        return result

    raise PyrtlError('Axis Invalid, expected (None, 0, or 1), got %s' % axis)


def max(matrix, axis=None, bits=None):
    ''' Returns the max value in a matrix.

    :param Matrix/Wirevecot matrix: the matrix to perform max operation on.
    If it is a wirevector, it will return itself.
    :param None/int axis: The axis to perform the operation on.
    None refers to max of all items. 0 is max of the columns. 1 is max of rows.
    Defaults to None.
    :param int bits: The bits per value of the max. Defaults to bits of old matrix
    :return: A wirevector or Matrix representing the max value
    '''
    def max_2(first, second):
        return select(first > second, first, second)

    if isinstance(matrix, WireVector):
        return matrix

    if not isinstance(matrix, Matrix):
        raise PyrtlError('error, expecting a Matrix or Wirevector for matrix'
                         'got %s instead' % type(matrix))

    if not isinstance(bits, int) and bits is not None:
        raise PyrtlError('error, expecting an int/None for bits'
                         'got %s instead' % type(bits))

    if not isinstance(axis, int) and axis is not None:
        raise PyrtlError('error, expecting an int or None for axis'
                         'got %s instead' % type(axis))

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        raise PyrtlError('error, bits cant be negative or zero'
                         'got %s instead' % bits)

    if axis is None:
        inputs = []
        for i in range(matrix.rows):
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
        return reduce(max_2, inputs)

    if axis == 0:
        result = Matrix(
            1, matrix.columns, signed=matrix.signed, bits=bits)

        for i in range(matrix.columns):
            inputs = []
            for j in range(matrix.rows):
                inputs.append(matrix[j, i])
            result[0, i] = reduce(max_2, inputs)
        return result

    if axis == 1:
        result = Matrix(
            1, matrix.rows, signed=matrix.signed, bits=bits)
        for i in range(matrix.rows):
            inputs = []
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
            result[0, i] = reduce(max_2, inputs)
        return result

    raise PyrtlError('Axis Invalid, expected (None, 0, or 1), got %s' % axis)


def argmax(matrix, axis=None, bits=None):
    ''' Returns the index of the max value of the matrix.

    :param Matrix/Wirevecot matrix: the matrix to perform argmax operation on.
    If it is a wirevector, it will return itself.
    :param None/int axis: The axis to perform the operation on.
    None refers to argmax of all items. 0 is argmax of the columns. 1 is argmax of rows.
    Defaults to None.
    :param int bits: The bits per value of the argmax. Defaults to bits of old matrix
    :return: A wirevector or Matrix representing the argmax value

    NOTE: If there are two indices with the same max value, this function
    picks the first instance.
    '''
    if isinstance(matrix, WireVector):
        return Const(0)

    if not isinstance(matrix, Matrix):
        raise PyrtlError('error, expecting a Matrix or Wirevector for matrix'
                         'got %s instead' % type(matrix))

    if not isinstance(bits, int) and bits is not None:
        raise PyrtlError('error, expecting an int/None for bits'
                         'got %s instead' % type(bits))

    if not isinstance(axis, int) and axis is not None:
        raise PyrtlError('error, expecting an int or None for axis'
                         'got %s instead' % type(axis))

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        raise PyrtlError('error, bits cant be negative or zero'
                         'got %s instead' % bits)

    max_number = max(matrix, axis=axis, bits=bits)
    if axis is None:
        index = Const(0)
        arg = matrix.rows * matrix.columns - 1
        for i in reversed(range(matrix.rows)):
            for j in reversed(range(matrix.columns)):
                index = select(
                    max_number == matrix[i, j], Const(arg), index)
                arg -= 1
        return index
    if axis == 0:
        result = Matrix(
            1, matrix.columns, signed=matrix.signed, bits=bits)
        for i in range(matrix.columns):
            local_max = max_number[0, i]
            index = Const(0)
            arg = matrix.rows - 1
            for j in reversed(range(matrix.rows)):
                index = select(
                    local_max == matrix[j, i], Const(arg), index)
                arg -= 1
            result[0, i] = index
        return result
    if axis == 1:
        result = Matrix(
            1, matrix.rows, signed=matrix.signed, bits=bits)
        for i in range(matrix.rows):
            local_max = max_number[0, i]
            index = Const(0)
            arg = matrix.columns - 1
            for j in reversed(range(matrix.columns)):
                index = select(
                    local_max == matrix[i, j], Const(arg), index)
                arg -= 1
            result[0, i] = index
        return result


def dot(first, second):
    ''' Performs the dot product on two matrices.

    :param Matrix first: the first matrix.
    :param Matrix second: the second matrix.
    :return: a PyRTL Matrix that contains the dot product of the
    two PyRTL Matrices.

    Specifically, the dot product on two matrices is
    * If either first or second are wirevectors/have both rows and columns
    equal to 1, it is equivalent to multiply
    * If both first and second are both arrays (have rows or columns equal to 1),
    it is inner product of vectors.
    * Otherwise it is the matrix multiplaction between first and second

    NOTE: Row Vectors and Column Vectors are both treated as arrays
    '''
    if not isinstance(first, (WireVector, Matrix)):
        raise PyrtlError('error, expecting a Matrix'
                         'got %s instead' % type(first))
    if not isinstance(second, (WireVector, Matrix)):
        raise PyrtlError('error, expecting a Matrix/WireVector'
                         'got %s instead' % type(second))

    # First case when it is multiply
    if isinstance(first, WireVector):
        if isinstance(second, WireVector):
            return first * second
        return second[:, :] * first
    if isinstance(second, WireVector):
        return first[:, :] * second
    if (first.rows == 1 and first.columns == 1) \
            or (second.rows == 1 and second.columns == 1):
        return first[:, :] * second[:, :]

    # Second case when it is Inner Product
    if first.rows == 1:
        if second.rows == 1:
            return sum(first * second)
        if second.columns == 1:
            return sum(first * second.transpose())
    elif first.columns == 1:
        if second.rows == 1:
            return sum(first * second.transpose())
        if second.columns == 1:
            return sum(first * second)

    # Third case when it is Matrix Multiply
    return first @ second
