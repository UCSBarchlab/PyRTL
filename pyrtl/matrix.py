import builtins
from functools import reduce

from pyrtl.rtllib import multipliers as mult

from .wire import Const, WireVector
from .corecircuits import as_wires, concat_list, select
from .pyrtlexceptions import PyrtlError


class Matrix():
    '''Class for making a Matrix using PyRTL.
    Provides the ability to perform different matrix opperations.
    '''
    # Internally, this class uses a python matrix of wirevectors.
    # So, a Matrix is represented as follows for a 2 x 2:
    # [[Wirevector, Wirevector], [Wirevector, Wirevector]]

    def __init__(self, rows, columns, bits, signed=False, value=None, max_bits=64):
        ''' Constructs a Matrix Object.

        :param int rows: the number of rows in the matrix.
        Must be greater than 0.
        :param int columns: the number of columns in the matrix.
        Must be greater than 0.
        :param bool signed: Currently not supported (will be added in the future)
        :param WireVector value: The value you want to initalize
        the Matrix with. Must be of size rows * columns * bits.
        If not given the matrix initializes to 0.
        :param int bits: The amount of bits per wirevector.
        Must be greater than 0. Default is 4.
        :return: a constructed Matrix object.
        '''
        if not isinstance(rows, int):
            raise PyrtlError('Rows must be from type int, instead "%s"'
                             ' was passed of type %s' %
                             (str(rows), type(rows)))
        if rows <= 0:
            raise PyrtlError("Rows can't be equal to or less than zero."
                             'Rows Value Passed: %s' % str(rows))

        if not isinstance(columns, int):
            raise PyrtlError('Columns must be from type int, instead "%s"'
                             ' was passed of type %s' %
                             (str(columns), type(columns)))
        if columns <= 0:
            raise PyrtlError("Columns can't be equal to or less than zero."
                             'Columns Value Passed: %s' % str(columns))

        if not isinstance(bits, int):
            raise PyrtlError('Bits must be from type int, instead "%s"'
                             ' was passed of type %s' %
                             (str(bits), type(bits)))
        if bits <= 0:
            raise PyrtlError(
                'Bits cant be negative or zero,'
                'instead "%s" was passed' % str(bits))

        if max_bits is not None:
            bits = builtins.min(bits, max_bits)

        self._matrix = [[0 for _ in range(columns)]
                        for _ in range(rows)]

        if value is None:
            for i in range(rows):
                for j in range(columns):
                    self._matrix[i][j] = Const(0)
        elif isinstance(value, WireVector):
            if value.bitwidth != bits * rows * columns:
                raise PyrtlError('Initialized Value bitwidth does not match'
                                 'Value bitwidth: %s Expected: %s'
                                 '' % (str(value.bitwidth),
                                       str(bits * rows * columns)))
            for i in range(rows):
                for j in range(columns):
                    start_index = (j * bits) + (i * columns * bits)
                    self._matrix[rows
                                 - i - 1][columns - j - 1] = as_wires(
                                     value[start_index:start_index + bits],
                                     bitwidth=bits)

        elif isinstance(value, list):
            if len(value) != rows and len(value[0]) != columns:
                raise PyrtlError('Rows and columns mismatch\n'
                                 'Rows: %s Expected: %s '
                                 'Columns: %s Expected: %s'
                                 '' % (str(len(value)), str(rows), str(
                                     len(value[0])), str(columns)))
            for i in range(rows):
                for j in range(columns):
                    self._matrix[i][j] = as_wires(
                        value[i][j], bitwidth=bits)

        else:
            raise PyrtlError('Initialized must be from type WireVector or,'
                             'list. Instead was passed of type %s'
                             '' % (type(value)))

        self.rows = rows
        self.columns = columns
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
        NOTE: This function will trunicate the most significant bits.
        '''
        if not isinstance(bits, int):
            raise PyrtlError('Bits must be from type int, instead "%s"'
                             ' was passed of type %s' %
                             (str(bits), type(bits)))
        if bits <= 0:
            raise PyrtlError(
                'Bits cant be negative or zero,'
                'instead "%s" was passed' % str(bits))

        self._bits = bits
        for i in range(self.rows):
            for j in range(self.columns):
                self._matrix[i][j] = self._matrix[i][j][:bits]

    def __len__(self):
        ''' Gets the output wirevector length.

        :return: a integer representing output wirevector bitwidth

        Used with default len() function
        '''
        return self.bits * self.rows * self.columns

    def to_WireVector(self):
        ''' Outputs the PyRTL Matrix as a singular concatenated Wirevector.

        :return: a Wirevector representing the whole pyrtl matrix.

        For instance, if we had a 2 x 1 matrix [[wire_a,wire_b]] it would
        return the concatenated wire: wire = wire_a.wire_b
        '''
        result = []

        for i in range(len(self._matrix)):
            for j in range(len(self._matrix[0])):
                result.append(as_wires(self[i, j], bitwidth=self.bits))

        result.reverse()
        return as_wires(concat_list(result), bitwidth=len(self))

    def transpose(self):
        ''' Constructs the transpose of the matrix

        :return: a Matrix object representing the transpose.
        '''
        result = Matrix(self.columns, self.rows,
                        self.bits, max_bits=self.max_bits)
        for i in range(result.rows):
            for j in range(result.columns):
                result[i, j] = self[j, i]
        return result

    def __reversed__(self):
        ''' Constructs the reverse of matrix

        :return: a Matrix object representing the reverse.

        Used with the reversed() method
        '''
        result = Matrix(self.rows, self.columns,
                        self.bits, max_bits=self.max_bits)
        for i in range(self.rows):
            for j in range(self.columns):
                result[i, j] = self[self.rows - 1 - i, self.columns - 1 - j]
        return result

    def __getitem__(self, key):
        ''' Accessor for the matrix.

        :param (int/slice row, int/slice column) key: The key value to get
        :return: Wirevector or Matrix containing the value of key

        Called when using square brackets ([]).
        '''
        if isinstance(key, tuple):
            rows, columns = key

            # First Set up proper slice
            if not isinstance(rows, slice):
                if not isinstance(rows, int):
                    raise PyrtlError('Rows must be from type int or slice, '
                                     'instead "%s" was passed of type %s' %
                                     (str(rows), type(rows)))
                rows = slice(rows, rows + 1, 1)

            if not isinstance(columns, slice):
                if not isinstance(columns, int):
                    raise PyrtlError('Columns must be from type int or slice, '
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

            # Check Slice Bounds
            if rows.start > self.rows or rows.stop > self.rows \
                    or rows.start < 0 or rows.stop < 0:
                raise PyrtlError("Invalid bounds for rows. Max Rows: %s, Got: %s" % (
                    str(self.rows), str(rows.start) + ":" + str(rows.stop)))
            if columns.start > self.columns or columns.stop > self.columns \
                    or columns.start < 0 or columns.stop < 0:
                raise PyrtlError("Invalid bounds for Columns. Max Columns: %s, Got: %s" % (
                    str(self.columns), str(columns.start) + ":" + str(columns.stop)))

            # If its a single value we want to return a wirevector
            if rows.stop - rows.start == 1 and \
                    columns.stop - columns.start == 1:
                return as_wires(self._matrix[rows][0][columns][0],
                                bitwidth=self.bits)

            # Otherwise Set Up Matrix and return that
            result = [[0 for _ in range(columns.stop - columns.start)]
                      for _ in range(rows.stop - rows.start)]

            for i in range(len(result)):
                for j in range(len(result[0])):
                    result[i][j] = self._matrix[i +
                                                rows.start][j + columns.start]
            return Matrix(len(result), len(result[0]), self._bits,
                          signed=self.signed, value=result, max_bits=self.max_bits)

        # Second Case When we just want to get full columns
        if isinstance(key, (int, slice)):
            key = slice(key, key + 1, None)
            return self[key, :]

        # Otherwise improper value was passed
        raise PyrtlError('Rows must be from type int or slice, '
                         'instead "%s" was passed of type %s' %
                         (str(key), type(key)))

    def __setitem__(self, key, value):
        ''' Mutator for the matrix.

        :param (slice/int rows, slice/int columns) key: The key value to set
        :param Wirevector/Matrix value: The value in which to set the key

        Called when setting a value using square brackets.
        (e.g. matrix[a, b] = value)
        '''

        if isinstance(key, tuple):
            rows, columns = key

            # First ensure that slices are correct
            if not isinstance(rows, slice):
                if not isinstance(rows, int):
                    raise PyrtlError('Rows must be from type int or slice, '
                                     'instead "%s" was passed of type %s' %
                                     (str(rows), type(rows)))
                rows = slice(rows, rows + 1, 1)

            if not isinstance(columns, slice):
                if not isinstance(columns, int):
                    raise PyrtlError('Columns must be from type int or slice, '
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
                raise PyrtlError("Invalid bounds for rows. Max Rows: %s, Got: %s" % (
                    str(self.rows), str(rows.start) + ":" + str(rows.stop)))
            if columns.start > self.columns or columns.stop > self.columns \
                    or columns.start < 0 or columns.stop < 0:
                raise PyrtlError("Invalid bounds for Columns. Max Columns: %s, Got: %s" % (
                    str(self.columns), str(columns.start) + ":" + str(columns.stop)))

            # First case when setting value to Matrix
            if isinstance(value, Matrix):
                if value.rows != (rows.stop - rows.start):
                    raise PyrtlError(
                        'Value Rows Mismatch. Expected Matrix'
                        'of rows "%s", instead recieved Matrix of rows "%s' %
                        (str(rows.stop - rows.start), str(value.rows)))
                if value.columns != (columns.stop - columns.start):
                    raise PyrtlError(
                        'Value Columns Mismatch. Expected Matrix'
                        'of columns "%s", instead recieved Matrix of columns "%s' %
                        (str(columns.stop - columns.start), str(value.columns)))

                for i in range(rows.stop - rows.start):
                    for j in range(columns.stop - columns.start):
                        self._matrix[rows.start +
                                     i][columns.start + j] = as_wires(
                                         value[i, j], bitwidth=self.bits)
            # Second Case when setting value to wirevector
            elif isinstance(value, WireVector):
                if ((rows.stop - rows.start) != 1) or \
                        ((columns.stop - columns.start) != 1):
                    raise PyrtlError(
                        'Value mismatch, Expected Matrix instead recieved WireVector')
                self._matrix[rows.start][columns.start] = as_wires(
                    value, bitwidth=self.bits)
            # Otherwise Error
            else:
                raise PyrtlError('Invalid Value Type')
        else:
            # Second Case if we just want to get a full column
            if isinstance(key, (slice, int)):
                key = slice(key, key + 1, None)
                self[key, :] = value
            else:
                raise PyrtlError('Rows must be from type int or slice, '
                                 'instead "%s" was passed of type %s' %
                                 (str(key), type(key)))

    def copy(self):
        ''' Constructs a deep copy of the Matrix.
        :return: a Matrix copy
        '''
        return Matrix(self.rows, self.columns, self.bits,
                      value=self.to_WireVector(), max_bits=self.max_bits)

    def __iadd__(self, other):
        ''' Perform the in-place addition operation.

        :return: a Matrix object with the element wise addition
          being preformed.

        Is used with a += b. Preforms an elementwise addition.
        '''
        new_value = (self + other)
        self._matrix = new_value._matrix
        self.bits = new_value._bits
        return self.copy()

    def __add__(self, other):
        ''' Perform the addition operation.

        :return: a Matrix object with the element wise addition
         being preformed.

        Is used with a + b. Preforms an elementwise addition.
        '''
        if not isinstance(other, Matrix):
            raise PyrtlError('error, expecting a Matrix'
                             'got %s instead' % type(other))

        if self.columns != other.columns:
            raise PyrtlError('error, columns mismatch'
                             'Martrix a: %s columns, Matrix b: %s rows' %
                             (str(self.columns), str(other.columns)))
        elif self.rows != other.rows:
            raise PyrtlError('error, row mismatch'
                             'Martrix a: %s columns, Matrix b: %s column' %
                             (str(self.rows), str(other.rows)))

        result = Matrix(self.rows, self.columns,
                        builtins.max(self.bits, other.bits) + 1,
                        max_bits=self.max_bits)

        for i in range(result.rows):
            for j in range(result.columns):
                result[i, j] = self[i, j] + other[i, j]
        return result

    def __isub__(self, other):
        ''' Perform the inplace subtraction opperation.

        :Matrix other: the PyRTL Matrix to subtract
        :return: a Matrix object with the element wise subtraction
        being preformed.

        Is used with a -= b. Preforms an elementwise subtraction.
        '''
        new_value = self - other
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __sub__(self, other):
        ''' Perform the subtraction operation.

        :Matrix other: the PyRTL Matrix to subtract
        :return: a Matrix object with the element wise subtraction
        being preformed.

        Is used with a - b. Preforms an elementwise subtraction.
        '''
        if not isinstance(other, Matrix):
            raise PyrtlError('error, expecting a Matrix'
                             'got %s instead' % type(other))

        if self.columns != other.columns:
            raise PyrtlError('error, columns mismatch'
                             'Martrix a: %s columns, Matrix b: %s rows' %
                             (str(self.columns), str(other.columns)))

        if self.rows != other.rows:
            raise PyrtlError('error, row mismatch'
                             'Martrix a: %s columns, Matrix b: %s column' %
                             (str(self.rows), str(other.rows)))

        result = Matrix(self.rows, self.columns,
                        builtins.max(self.bits, other.bits),
                        max_bits=self.max_bits)
        for i in range(result.rows):
            for j in range(result.columns):
                result[i, j] = self[i, j] - other[i, j]
        return result

    def __imul__(self, other):
        ''' Perform the inplace multiplication operation.

        :Matrix/Wirevector other: the Matrix or scalar to multiply
        :return: a Matrix object with the resulting multiplication operation
        being preformed.

        Is used with a *= b. Preforms an elementwise or scalar multiplication.
        '''
        new_value = self * other
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __mul__(self, other):
        ''' Perform the multiplication operation.

        :Matrix/Wirevector other: the Matrix to multiply
        :return: a Matrix object with the resulting multiplication operation
        being preformed.

        Is used with a * b. Preforms an elementwise or scalar multiplication.
        '''

        if isinstance(other, Matrix):
            if self.columns != other.columns:
                raise PyrtlError('error, columns mismatch '
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

        result = Matrix(self.rows, self.columns,
                        bits, max_bits=self.max_bits)

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
        :return: a PyRTL Matrix that contains the matrix multiplication product
        of this and other

        Is used with a @= b
        '''
        new_value = self @ other
        self.columns = new_value.columns
        self.rows = new_value.rows
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __matmul__(self, other):
        ''' Performs the matrix multiplication operation.

        :param Matrix other: the second matrix.
        :return: a PyRTL Matrix that contains the matrix multiplication product
        of this and other

        Is used with a @ b
        '''
        if not isinstance(other, Matrix):
            raise PyrtlError('error, expecting a Matrix'
                             'got %s instead' % type(other))

        if self.columns != other.rows:
            raise PyrtlError('error, rows and columns mismatch'
                             'Martrix a: %s columns, Matrix b: %s rows' %
                             (str(self.columns), str(other.rows)))

        result = Matrix(self.rows, other.columns,
                        self.columns * other.rows
                        * (self.bits + other.bits),
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
            raise PyrtlError('Unexpected Power given. Type int expected,'
                             ' but recieved type %s' % type(power))

        if self.rows != self.columns:
            raise PyrtlError("Matrix must be square")

        result = self.copy()

        # First Case Return Identity Matrix
        if power == 0:
            for i in range(self.rows):
                for j in range(self.columns):
                    if i != j:
                        result[i, j] = Const(0)
                    else:
                        result[i, j] = Const(1)
            return result
        # Second Case Do Matrix Multiplications
        if power >= 1:
            inputs = [result] * power

            def pow_2(first, second):
                return first@second
            return reduce(pow_2, inputs)

        raise PyrtlError('Power must be greater than or equal to 0')
