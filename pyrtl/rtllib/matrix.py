from functools import reduce
from six.moves import builtins

from pyrtl.rtllib import multipliers as mult

from ..wire import Const, WireVector
from ..corecircuits import as_wires, concat, select
from ..pyrtlexceptions import PyrtlError


class Matrix(object):
    '''Class for making a Matrix using PyRTL.

    Provides the ability to perform different matrix operations.
    '''
    # Internally, this class uses a Python matrix of WireVectors.
    # So, a Matrix is represented as follows for a 2 x 2:
    # [[WireVector, WireVector], [WireVector, WireVector]]

    def __init__(self, rows, columns, bits, signed=False, value=None, max_bits=64):
        ''' Constructs a Matrix object.

        :param int rows: the number of rows in the matrix.  Must be greater than 0.
        :param int columns: the number of columns in the matrix.  Must be greater than 0.
        :param int bits: The amount of bits per wirevector. Must be greater than 0.
        :param bool signed: Currently not supported (will be added in the future)
        :param (WireVector/list) value: The value you want to initialize the Matrix with.
            If a WireVector, must be of size `rows * columns * bits`. If a list, must have
            `rows` rows and `columns` columns, and every element must fit in `bits` size.
            If not given, the matrix initializes to 0.
        :param int max_bits:
        :return: a constructed Matrix object.
        '''
        if not isinstance(rows, int):
            raise PyrtlError('Rows must be of type int, instead "%s" '
                             'was passed of type %s' %
                             (str(rows), type(rows)))
        if rows <= 0:
            raise PyrtlError('Rows cannot be less than or equal to zero. '
                             'Rows value passed: %s' % str(rows))

        if not isinstance(columns, int):
            raise PyrtlError('Columns must be of type int, instead "%s" '
                             'was passed of type %s' %
                             (str(columns), type(columns)))
        if columns <= 0:
            raise PyrtlError('Columns cannot be less than or equal to zero. '
                             'Columns value passed: %s' % str(columns))

        if not isinstance(bits, int):
            raise PyrtlError('Bits must be of type int, instead "%s" '
                             'was passed of type %s' %
                             (str(bits), type(bits)))
        if bits <= 0:
            raise PyrtlError(
                'Bits cannot be negative or zero, '
                'instead "%s" was passed' % str(bits))

        if max_bits is not None:
            if bits > max_bits:
                bits = max_bits

        self._matrix = [[0 for _ in range(columns)] for _ in range(rows)]

        if value is None:
            for i in range(rows):
                for j in range(columns):
                    self._matrix[i][j] = Const(0)
        elif isinstance(value, WireVector):
            if value.bitwidth != bits * rows * columns:
                raise PyrtlError('Initialized bitwidth value does not match '
                                 'given value.bitwidth: %s, expected: %s'
                                 '' % (str(value.bitwidth),
                                       str(bits * rows * columns)))
            for i in range(rows):
                for j in range(columns):
                    start_index = (j * bits) + (i * columns * bits)
                    self._matrix[rows - i - 1][columns - j - 1] =\
                        as_wires(value[start_index:start_index + bits], bitwidth=bits)

        elif isinstance(value, list):
            if len(value) != rows or any(len(row) != columns for row in value):
                raise PyrtlError('Rows and columns mismatch\n'
                                 'Rows: %s, expected: %s\n'
                                 'Columns: %s, expected: %s'
                                 '' % (str(len(value)), str(rows),
                                       str(len(value[0])), str(columns)))
            for i in range(rows):
                for j in range(columns):
                    self._matrix[i][j] = as_wires(value[i][j], bitwidth=bits)

        else:
            raise PyrtlError('Initialized value must be of type WireVector or '
                             'list. Instead was passed value of type %s' % (type(value)))

        self.rows = rows
        self.columns = columns
        self._bits = bits
        self.bits = bits
        self.signed = False
        self.max_bits = max_bits

    @property
    def bits(self):
        ''' Gets the number of bits each value is allowed to hold.

        :return: an integer representing the number of bits.
        '''
        return self._bits

    @bits.setter
    def bits(self, bits):
        ''' Sets the number of bits.

        :param int bits: The number of bits. Must be greater than 0.

        Called automatically when bits is changed.
        NOTE: This function will truncate the most significant bits.
        '''
        if not isinstance(bits, int):
            raise PyrtlError('Bits must be of type int, instead "%s" '
                             'was passed of type %s' %
                             (str(bits), type(bits)))
        if bits <= 0:
            raise PyrtlError(
                'Bits cannot be negative or zero, '
                'instead "%s" was passed' % str(bits))

        self._bits = bits
        for i in range(self.rows):
            for j in range(self.columns):
                self._matrix[i][j] = self._matrix[i][j][:bits]

    def __len__(self):
        ''' Gets the output WireVector length.

        :return: an integer representing the output WireVector bitwidth

        Used with default len() function
        '''
        return self.bits * self.rows * self.columns

    def to_wirevector(self):
        ''' Outputs the PyRTL Matrix as a singular concatenated Wirevector.

        :return: a Wirevector representing the whole PyRTL matrix.

        For instance, if we had a 2 x 1 matrix [[wire_a, wire_b]] it would
        return the concatenated wire: wire = wire_a.wire_b
        '''
        result = []

        for i in range(len(self._matrix)):
            for j in range(len(self._matrix[0])):
                result.append(as_wires(self[i, j], bitwidth=self.bits))

        return as_wires(concat(*result), bitwidth=len(self))

    def transpose(self):
        ''' Constructs the transpose of the matrix

        :return: a Matrix object representing the transpose.
        '''
        result = Matrix(self.columns, self.rows, self.bits, max_bits=self.max_bits)
        for i in range(result.rows):
            for j in range(result.columns):
                result[i, j] = self[j, i]
        return result

    def __reversed__(self):
        ''' Constructs the reverse of matrix

        :return: a Matrix object representing the reverse.

        Used with the reversed() method
        '''
        result = Matrix(self.rows, self.columns, self.bits, max_bits=self.max_bits)
        for i in range(self.rows):
            for j in range(self.columns):
                result[i, j] = self[self.rows - 1 - i, self.columns - 1 - j]
        return result

    def __getitem__(self, key):
        ''' Accessor for the matrix.

        :param (int/slice row, int/slice column) key: The key value to get
        :return: WireVector or Matrix containing the value of key

        Called when using square brackets ([]).

        Examples::

            int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
            matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)

            matrix[1] == [3, 4, 5]
            matrix[2, 0] == 6
            matrix[(2, 0)] = 6
            matrix[slice(0, 2), slice(0, 3)] == [[0, 1, 2], [3, 4, 5]]
            matrix[0:2, 0:3] == [[0, 1, 2], [3, 4, 5]]
            matrix[:2] == [[0, 1, 2], [3, 4, 5]]
            matrix[-1] == [6, 7, 8]
            matrix[-2:] == [[3, 4, 5], [6, 7, 8]]
        '''
        if isinstance(key, tuple):
            rows, columns = key

            # First set up proper slice
            if not isinstance(rows, slice):
                if not isinstance(rows, int):
                    raise PyrtlError('Rows must be of type int or slice, '
                                     'instead "%s" was passed of type %s' %
                                     (str(rows), type(rows)))
                rows = slice(rows, rows + 1, 1)

            if not isinstance(columns, slice):
                if not isinstance(columns, int):
                    raise PyrtlError('Columns must be of type int or slice, '
                                     'instead "%s" was passed of type %s' %
                                     (str(columns), type(columns)))
                columns = slice(columns, columns + 1, 1)

            if rows.start is None:
                rows = slice(0, rows.stop, rows.step)
            elif rows.start < 0:
                rows = slice(self.rows - abs(rows.start),
                             rows.stop, rows.step)

            if rows.stop is None:
                rows = slice(rows.start, self.rows, rows.step)
            elif rows.stop < 0:
                rows = slice(rows.start, self.rows - abs(rows.stop),
                             rows.step)

            rows = slice(rows.start, rows.stop, 1)

            if columns.start is None:
                columns = slice(0, columns.stop, columns.step)
            elif columns.start < 0:
                columns = slice(self.columns - abs(columns.start),
                                columns.stop, columns.step)

            if columns.stop is None:
                columns = slice(columns.start, self.columns, columns.step)
            elif columns.stop < 0:
                columns = slice(
                    columns.start, self.columns - abs(columns.stop),
                    columns.step)

            columns = slice(columns.start, columns.stop, 1)

            # Check slice bounds
            if rows.start > self.rows or rows.stop > self.rows \
                    or rows.start < 0 or rows.stop < 0:
                raise PyrtlError("Invalid bounds for rows. Max rows: %s, got: %s" % (
                    str(self.rows), str(rows.start) + ":" + str(rows.stop)))
            if columns.start > self.columns or columns.stop > self.columns \
                    or columns.start < 0 or columns.stop < 0:
                raise PyrtlError("Invalid bounds for columns. Max columns: %s, got: %s" % (
                    str(self.columns), str(columns.start) + ":" + str(columns.stop)))

            # If it's a single value we want to return a wirevector
            if rows.stop - rows.start == 1 and \
                    columns.stop - columns.start == 1:
                return as_wires(self._matrix[rows][0][columns][0],
                                bitwidth=self.bits)

            # Otherwise set up matrix and return that
            result = [[0 for _ in range(columns.stop - columns.start)]
                      for _ in range(rows.stop - rows.start)]

            for i in range(len(result)):
                for j in range(len(result[0])):
                    result[i][j] = self._matrix[i + rows.start][j + columns.start]
            return Matrix(len(result), len(result[0]), self._bits,
                          signed=self.signed, value=result, max_bits=self.max_bits)

        # Second case when we just want to get full row
        if isinstance(key, int):
            if key < 0:
                start = self.rows - abs(key)
                if start < 0:
                    raise PyrtlError('Index %d is out of bounds for '
                                     'matrix with %d rows' % (key, self.rows))
                key = slice(start, start + 1, None)
            else:
                key = slice(key, key + 1, None)
            return self[key, :]

        # Third case when we want multiple rows
        if isinstance(key, slice):
            return self[key, :]

        # Otherwise improper value was passed
        raise PyrtlError('Rows must be of type int or slice, '
                         'instead "%s" was passed of type %s' %
                         (str(key), type(key)))

    def __setitem__(self, key, value):
        ''' Mutator for the matrix.

        :param (slice/int rows, slice/int columns) key: The key value to set
        :param Wirevector/int/Matrix value: The value in which to set the key

        Called when setting a value using square brackets.
        (e.g. matrix[a, b] = value)

        The value given will be truncated to match the bitwidth of all the elements
        in the matrix.
        '''

        if isinstance(key, tuple):
            rows, columns = key

            # First ensure that slices are correct
            if not isinstance(rows, slice):
                if not isinstance(rows, int):
                    raise PyrtlError('Rows must be of type int or slice, '
                                     'instead "%s" was passed of type %s' %
                                     (str(rows), type(rows)))
                rows = slice(rows, rows + 1, 1)

            if not isinstance(columns, slice):
                if not isinstance(columns, int):
                    raise PyrtlError('Columns must be of type int or slice, '
                                     'instead "%s" was passed of type %s' %
                                     (str(columns), type(columns)))
                columns = slice(columns, columns + 1, 1)

            if rows.start is None:
                rows = slice(0, rows.stop, rows.step)
            elif rows.start < 0:
                rows = slice(self.rows - abs(rows.start),
                             rows.stop, rows.step)

            if rows.stop is None:
                rows = slice(rows.start, self.rows, rows.step)
            elif rows.stop < 0:
                rows = slice(rows.start, self.rows - abs(rows.stop),
                             rows.step)

            if columns.start is None:
                columns = slice(0, columns.stop, columns.step)
            elif columns.start < 0:
                columns = slice(self.columns - abs(columns.start),
                                columns.stop, columns.step)

            if columns.stop is None:
                columns = slice(columns.start, self.columns, columns.step)
            elif columns.stop < 0:
                columns = slice(
                    columns.start, self.columns - abs(columns.stop),
                    columns.step)

            # Check Slice Bounds
            if rows.start > self.rows or rows.stop > self.rows \
                    or rows.start < 0 or rows.stop < 0:
                raise PyrtlError("Invalid bounds for rows. Max rows: %s, got: %s" % (
                    str(self.rows), str(rows.start) + ":" + str(rows.stop)))
            if columns.start > self.columns or columns.stop > self.columns \
                    or columns.start < 0 or columns.stop < 0:
                raise PyrtlError("Invalid bounds for columns. Max columns: %s, got: %s" % (
                    str(self.columns), str(columns.start) + ":" + str(columns.stop)))

            # First case when setting value to Matrix
            if isinstance(value, Matrix):
                if value.rows != (rows.stop - rows.start):
                    raise PyrtlError(
                        'Value rows mismatch. Expected Matrix '
                        'of rows "%s", instead recieved Matrix of rows "%s"' %
                        (str(rows.stop - rows.start), str(value.rows)))
                if value.columns != (columns.stop - columns.start):
                    raise PyrtlError(
                        'Value columns mismatch. Expected Matrix '
                        'of columns "%s", instead recieved Matrix of columns "%s"' %
                        (str(columns.stop - columns.start), str(value.columns)))

                for i in range(rows.stop - rows.start):
                    for j in range(columns.stop - columns.start):
                        self._matrix[rows.start + i][columns.start + j] =\
                            as_wires(value[i, j], bitwidth=self.bits)

            # Second case when setting value to wirevector
            elif isinstance(value, (int, WireVector)):
                if ((rows.stop - rows.start) != 1) or \
                        ((columns.stop - columns.start) != 1):
                    raise PyrtlError(
                        'Value mismatch: expected Matrix, instead received WireVector')
                self._matrix[rows.start][columns.start] = as_wires(value, bitwidth=self.bits)
            # Otherwise Error
            else:
                raise PyrtlError('Invalid value of type %s' % type(value))
        else:
            # Second case if we just want to set a full row
            if isinstance(key, int):
                if key < 0:
                    start = self.rows - abs(key)
                    if start < 0:
                        raise PyrtlError('Index %d is out of bounds for '
                                         'matrix with %d rows' % (key, self.rows))
                    key = slice(start, start + 1, None)
                else:
                    key = slice(key, key + 1, None)
                self[key, :] = value
            # Third case if we want to set full rows
            elif isinstance(key, slice):
                self[key, :] = value
            else:
                raise PyrtlError('Rows must be of type int or slice, '
                                 'instead "%s" was passed of type %s' %
                                 (str(key), type(key)))

    def copy(self):
        ''' Constructs a deep copy of the Matrix.

        :return: a Matrix copy
        '''
        return Matrix(self.rows, self.columns, self.bits,
                      value=self.to_wirevector(), max_bits=self.max_bits)

    def __iadd__(self, other):
        ''' Perform the in-place addition operation.

        :return: a Matrix object with the element wise addition being preformed.

        Is used with a += b. Performs an elementwise addition.
        '''
        new_value = (self + other)
        self._matrix = new_value._matrix
        self.bits = new_value._bits
        return self.copy()

    def __add__(self, other):
        ''' Perform the addition operation.

        :return: a Matrix object with the element wise addition being performed.

        Is used with a + b. Performs an elementwise addition.
        '''
        if not isinstance(other, Matrix):
            raise PyrtlError('error: expecting a Matrix, '
                             'got %s instead' % type(other))

        if self.columns != other.columns:
            raise PyrtlError('error: columns mismatch. '
                             'Matrix a: %s columns, Matrix b: %s rows' %
                             (str(self.columns), str(other.columns)))
        elif self.rows != other.rows:
            raise PyrtlError('error: row mismatch. '
                             'Matrix a: %s columns, Matrix b: %s column' %
                             (str(self.rows), str(other.rows)))

        new_bits = self.bits
        if other.bits > new_bits:
            new_bits = other.bits

        result = Matrix(self.rows, self.columns, new_bits + 1, max_bits=self.max_bits)

        for i in range(result.rows):
            for j in range(result.columns):
                result[i, j] = self[i, j] + other[i, j]
        return result

    def __isub__(self, other):
        ''' Perform the inplace subtraction opperation.

        :Matrix other: the PyRTL Matrix to subtract
        :return: a Matrix object with the element wise subtraction being performed.

        Is used with a -= b. Performs an elementwise subtraction.
        '''
        new_value = self - other
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __sub__(self, other):
        ''' Perform the subtraction operation.

        :Matrix other: the PyRTL Matrix to subtract
        :return: a Matrix object with the elementwise subtraction being performed.

        Is used with a - b. Performs an elementwise subtraction.

        Note: If using unsigned numbers, the result will be floored at 0
        '''
        if not isinstance(other, Matrix):
            raise PyrtlError('error: expecting a Matrix, '
                             'got %s instead' % type(other))

        if self.columns != other.columns:
            raise PyrtlError('error: columns mismatch. '
                             'Matrix a: %s columns, Matrix b: %s rows' %
                             (str(self.columns), str(other.columns)))

        if self.rows != other.rows:
            raise PyrtlError('error: row mismatch. '
                             'Matrix a: %s columns, Matrix b: %s column' %
                             (str(self.rows), str(other.rows)))

        new_bits = self.bits
        if other.bits > new_bits:
            new_bits = other.bits

        result = Matrix(self.rows, self.columns, new_bits, max_bits=self.max_bits)

        for i in range(result.rows):
            for j in range(result.columns):
                if self.signed:
                    result[i, j] = self[i, j] - other[i, j]
                else:
                    result[i, j] = select(
                        self[i, j] > other[i, j], self[i, j] - other[i, j], Const(0))

        return result

    def __imul__(self, other):
        ''' Perform the in-place multiplication operation.

        :Matrix/Wirevector other: the Matrix or scalar to multiply
        :return: a Matrix object with the resulting multiplication operation being preformed.

        Is used with a *= b. Performs an elementwise or scalar multiplication.
        '''
        new_value = self * other
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __mul__(self, other):
        ''' Perform the multiplication operation.

        :Matrix/Wirevector other: the Matrix to multiply
        :return: a Matrix object with the resulting multiplication operation being performed.

        Is used with a * b. Performs an elementwise or scalar multiplication.
        '''

        if isinstance(other, Matrix):
            if self.columns != other.columns:
                raise PyrtlError('error: columns mismatch. '
                                 'Martrix a: %s columns, Matrix b: %s rows' %
                                 (str(self.columns), str(other.columns)))
            if self.rows != other.rows:
                raise PyrtlError('error, row mismatch '
                                 'Martrix a: %s columns, Matrix b: %s column' %
                                 (str(self.rows), str(other.rows)))

            bits = self.bits + other.bits
        elif isinstance(other, WireVector):
            bits = self.bits + len(other)
        else:
            raise PyrtlError('Expecting a Matrix or WireVector '
                             'got %s instead' % type(other))

        result = Matrix(self.rows, self.columns, bits, max_bits=self.max_bits)

        for i in range(self.rows):
            for j in range(self.columns):
                if isinstance(other, Matrix):
                    result[i, j] = self[i, j] * other[i, j]
                else:
                    result[i, j] = self[i, j] * other
        return result

    def __imatmul__(self, other):
        ''' Performs the inplace matrix multiplication operation.

        :param Matrix other: the second matrix.
        :return: a PyRTL Matrix that contains the matrix multiplication product of this and other

        Is used with a @= b

        Note: The matmul symbol (@) only works in python 3.5+. Otherwise you must
        call `__imatmul__(other)`.
        '''
        new_value = self.__matmul__(other)
        self.columns = new_value.columns
        self.rows = new_value.rows
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __matmul__(self, other):
        ''' Performs the matrix multiplication operation.

        :param Matrix other: the second matrix.
        :return: a PyRTL Matrix that contains the matrix multiplication product of this and other

        Is used with a @ b

        Note: The matmul symbol (@) only works in python 3.5+. Otherwise you must
        call `__matmul__(other)`.
        '''
        if not isinstance(other, Matrix):
            raise PyrtlError('error: expecting a Matrix, '
                             'got %s instead' % type(other))

        if self.columns != other.rows:
            raise PyrtlError('error: rows and columns mismatch. '
                             'Matrix a: %s columns, Matrix b: %s rows' %
                             (str(self.columns), str(other.rows)))

        result = Matrix(self.rows, other.columns,
                        self.columns * other.rows * (self.bits + other.bits),
                        max_bits=self.max_bits)

        for i in range(self.rows):
            for j in range(other.columns):
                for k in range(self.columns):
                    result[i, j] = mult.fused_multiply_adder(
                        self[i, k], other[k, j], result[i, j], signed=self.signed)

        return result

    def __ipow__(self, power):
        ''' Performs the matrix power operation.

        :param int power: the power to perform the matrix on
        :return: a PyRTL Matrix that contains the matrix power product

        Is used with a **= b
        '''
        new_value = self ** power
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __pow__(self, power):
        ''' Performs the matrix power operation.

        :param int power: the power to perform the matrix on
        :return: a PyRTL Matrix that contains the matrix power product

        Is used with a ** b
        '''
        if not isinstance(power, int):
            raise PyrtlError('Unexpected power given. Type int expected, '
                             'but recieved type %s' % type(power))

        if self.rows != self.columns:
            raise PyrtlError("Matrix must be square")

        result = self.copy()

        # First case: return identity matrix
        if power == 0:
            for i in range(self.rows):
                for j in range(self.columns):
                    if i != j:
                        result[i, j] = Const(0)
                    else:
                        result[i, j] = Const(1)
            return result
        # Second case: do matrix multiplications
        if power >= 1:
            inputs = [result] * power

            def pow_2(first, second):
                return first.__matmul__(second)
            return reduce(pow_2, inputs)

        raise PyrtlError('Power must be greater than or equal to 0')


def multiply(first, second):
    ''' Perform the elementwise or scalar multiplication operation.

    :param Matrix first: first matrix.
    :param Matrix/Wirevector second: second matrix.
    :return: a Matrix object with the element wise or scaler multiplication being performed.
    '''
    if not isinstance(first, Matrix):
        raise PyrtlError('error: expecting a Matrix, '
                         'got %s instead' % type(second))
    return first * second


def sum(matrix, axis=None, bits=None):
    ''' Returns the sum of all the values in a matrix

    :param Matrix/Wirevector matrix: the matrix to perform sum operation on.
        If it is a WireVector, it will return itself.
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
        raise PyrtlError('error: expecting a Matrix or Wirevector for matrix, '
                         'got %s instead' % type(matrix))

    if not isinstance(bits, int) and bits is not None:
        raise PyrtlError('error: expecting an int/None for bits, '
                         'got %s instead' % type(bits))

    if not isinstance(axis, int) and axis is not None:
        raise PyrtlError('error: expecting an int or None for axis, '
                         'got %s instead' % type(axis))

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        raise PyrtlError('error: bits cannot be negative or zero, '
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

    raise PyrtlError('Axis invalid: expected (None, 0, or 1), got %s' % axis)


def min(matrix, axis=None, bits=None):
    ''' Returns the minimum value in a matrix.

    :param Matrix/Wirevector matrix: the matrix to perform min operation on.
        If it is a WireVector, it will return itself.
    :param None/int axis: The axis to perform the operation on.
        None refers to min of all item. 0 is min of column. 1 is min of rows. Defaults to None.
    :param int bits: The bits per value of the min. Defaults to bits of old matrix
    :return: A WireVector or Matrix representing the min value
    '''
    def min_2(first, second):
        return select(first < second, first, second)

    if isinstance(matrix, WireVector):
        return matrix

    if not isinstance(matrix, Matrix):
        raise PyrtlError('error: expecting a Matrix or Wirevector for matrix, '
                         'got %s instead' % type(matrix))

    if not isinstance(bits, int) and bits is not None:
        raise PyrtlError('error: expecting an int/None for bits, '
                         'got %s instead' % type(bits))

    if not isinstance(axis, int) and axis is not None:
        raise PyrtlError('error: expecting an int or None for axis, '
                         'got %s instead' % type(axis))

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        raise PyrtlError('error: bits cannot be negative or zero, '
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

    raise PyrtlError('Axis invalid: expected (None, 0, or 1), got %s' % axis)


def max(matrix, axis=None, bits=None):
    ''' Returns the max value in a matrix.

    :param Matrix/Wirevector matrix: the matrix to perform max operation on.
        If it is a wirevector, it will return itself.
    :param None/int axis: The axis to perform the operation on.
        None refers to max of all items. 0 is max of the columns. 1 is max of rows.
        Defaults to None.
    :param int bits: The bits per value of the max. Defaults to bits of old matrix
    :return: A WireVector or Matrix representing the max value
    '''
    def max_2(first, second):
        return select(first > second, first, second)

    if isinstance(matrix, WireVector):
        return matrix

    if not isinstance(matrix, Matrix):
        raise PyrtlError('error: expecting a Matrix or WireVector for matrix, '
                         'got %s instead' % type(matrix))

    if not isinstance(bits, int) and bits is not None:
        raise PyrtlError('error: expecting an int/None for bits, '
                         'got %s instead' % type(bits))

    if not isinstance(axis, int) and axis is not None:
        raise PyrtlError('error: expecting an int or None for axis, '
                         'got %s instead' % type(axis))

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        raise PyrtlError('error: bits cannot be negative or zero, '
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

    raise PyrtlError('Axis invalid: expected (None, 0, or 1), got %s' % axis)


def argmax(matrix, axis=None, bits=None):
    ''' Returns the index of the max value of the matrix.

    :param Matrix/Wirevector matrix: the matrix to perform argmax operation on.
        If it is a WireVector, it will return itself.
    :param None/int axis: The axis to perform the operation on.
        None refers to argmax of all items. 0 is argmax of the columns. 1 is argmax of rows.
        Defaults to None.
    :param int bits: The bits per value of the argmax. Defaults to bits of old matrix
    :return: A WireVector or Matrix representing the argmax value

    NOTE: If there are two indices with the same max value, this function
    picks the first instance.
    '''
    if isinstance(matrix, WireVector):
        return Const(0)

    if not isinstance(matrix, Matrix):
        raise PyrtlError('error: expecting a Matrix or Wirevector for matrix, '
                         'got %s instead' % type(matrix))

    if not isinstance(bits, int) and bits is not None:
        raise PyrtlError('error: expecting an int/None for bits, '
                         'got %s instead' % type(bits))

    if not isinstance(axis, int) and axis is not None:
        raise PyrtlError('error: expecting an int or None for axis, '
                         'got %s instead' % type(axis))

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        raise PyrtlError('error: bits cannot be negative or zero, '
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
    :return: a PyRTL Matrix that contains the dot product of the two PyRTL Matrices.

    Specifically, the dot product on two matrices is
        * If either first or second are WireVectors/have both rows and columns
          equal to 1, it is equivalent to multiply
        * If both first and second are both arrays (have rows or columns equal to 1),
          it is inner product of vectors.
        * Otherwise it is the matrix multiplaction between first and second

    NOTE: Row vectors and column vectors are both treated as arrays
    '''
    if not isinstance(first, (WireVector, Matrix)):
        raise PyrtlError('error: expecting a Matrix, '
                         'got %s instead' % type(first))
    if not isinstance(second, (WireVector, Matrix)):
        raise PyrtlError('error: expecting a Matrix/WireVector, '
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
    return first.__matmul__(second)


def hstack(*matrices):
    """ Stack matrices in sequence horizontally (column-wise).

    :param list[Matrix] matrices: a list of matrices to concatenate one after another horizontally
    :return Matrix: a new Matrix, with the same number of rows as the original, with
        a bitwidth equal to the max of the bitwidths of all the matrices

    All the matrices must have the same number of rows and same 'signed' value.

    For example:

        m1 = Matrix(2, 3, bits=5,  value=[[1,2,3],
                                          [4,5,6]])
        m2 = Matrix(2, 1, bits=10, value=[[17],
                                          [23]]])
        m3 = hstack(m1, m2)

    m3 looks like:

        [[1,2,3,17],
         [4,5,6,23]]
    """
    if len(matrices) == 0:
        raise PyrtlError("Must supply at least one matrix to hstack()")

    if len(matrices) == 1:
        return matrices[0].copy()

    new_rows = matrices[0].rows
    if any([m.rows != new_rows for m in matrices]):
        raise PyrtlError("All matrices being hstacked together must have the same number of rows")

    new_signed = matrices[0].signed
    if any([m.signed != new_signed for m in matrices]):
        raise PyrtlError("All matrices being hstacked together must have the same signedness")

    new_cols = builtins.sum(m.columns for m in matrices)
    new_bits = builtins.max(m.bits for m in matrices)
    new_max_bits = builtins.max(m.max_bits for m in matrices)
    new = Matrix(new_rows, new_cols, new_bits, max_bits=new_max_bits)

    new_c = 0
    for matrix in matrices:
        for c in range(matrix.columns):
            for r in range(matrix.rows):
                new[r, new_c] = matrix[r, c]
            new_c += 1

    return new


def vstack(*matrices):
    """ Stack matrices in sequence vertically (row-wise).

    :param list[Matrix] matrices: a list of matrices to concatenate one after another vertically
    :return Matrix: a new Matrix, with the same number of columns as the original, with
        a bitwidth equal to the max of the bitwidths of all the matrices

    All the matrices must have the same number of columns and same 'signed' value.

    For example:

        m1 = Matrix(2, 3, bits=5,  value=[[1,2,3],
                                          [4,5,6]])
        m2 = Matrix(1, 3, bits=10, value=[[7,8,9]])
        m3 = vstack(m1, m2)

    m3 looks like:

        [[1,2,3],
         [4,5,6],
         [7,8,9]]
    """
    if len(matrices) == 0:
        raise PyrtlError("Must supply at least one matrix to hstack()")

    if len(matrices) == 1:
        return matrices[0].copy()

    new_cols = matrices[0].columns
    if any([m.columns != new_cols for m in matrices]):
        raise PyrtlError("All matrices being vstacked together must have the "
                         "same number of columns")

    new_signed = matrices[0].signed
    if any([m.signed != new_signed for m in matrices]):
        raise PyrtlError("All matrices being hstacked together must have the same signedness")

    new_rows = builtins.sum(m.rows for m in matrices)
    new_bits = builtins.max(m.bits for m in matrices)
    new_max_bits = builtins.max(m.max_bits for m in matrices)
    new = Matrix(new_rows, new_cols, new_bits, max_bits=new_max_bits)

    new_r = 0
    for matrix in matrices:
        for r in range(matrix.rows):
            for c in range(matrix.columns):
                new[new_r, c] = matrix[r, c]
            new_r += 1

    return new


def concatenate(matrices, axis=0):
    """ Join a sequence of matrices along an existing axis.

    :param list[Matrix] matrices: a list of matrices to concatenate one after another
    :param int axix: axis along which to join; 0 is horizontally, 1 is vertically (defaults to 0)
    :return: a new Matrix composed of the given matrices joined together

    This function essentially wraps hstack/vstack.
    """
    if axis == 0:
        return hstack(*matrices)
    elif axis == 1:
        return vstack(*matrices)
    else:
        raise PyrtlError("Only allowable axes are 0 or 1")
