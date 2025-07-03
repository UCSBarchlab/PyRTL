from __future__ import annotations

import builtins
from functools import reduce

from pyrtl import (
    Const,
    PyrtlError,
    WireVector,
    as_wires,
    concat,
    formatted_str_to_val,
    select,
)
from pyrtl.rtllib.multipliers import fused_multiply_adder
from pyrtl.wire import WireVectorLike


class Matrix:
    """Class for making a Matrix using PyRTL.

    Provides the ability to perform different matrix operations.
    """

    # Internally, this class uses a Python list of lists of WireVectors.
    # So, a Matrix is represented as follows for a 2 x 2:
    # [[WireVector, WireVector],
    #  [WireVector, WireVector]]
    def __init__(
        self,
        rows: int,
        columns: int,
        bits: int,
        signed: bool = False,  # noqa: ARG002
        value: WireVector | list[list[WireVectorLike]] = None,
        max_bits: int = 64,
    ):
        """Constructs a Matrix object.

        :param rows: The number of rows in the matrix. Must be greater than 0.
        :param columns: The number of columns in the matrix. Must be greater than 0.
        :param bits: The number of bits per :class:`.WireVector` matrix element. Must be
            greater than 0.
        :param signed: Currently not supported (will be added in the future).
        :param value: The value you want to initialize the ``Matrix`` to. If a
            :class:`.WireVector`, must be of size ``rows * columns * bits``. If a
            :class:`list`, must have ``rows`` rows and ``columns`` columns, and every
            element must be representable with a :attr:`~.WireVector.bitwidth` of
            ``bits``. If ``None``, the matrix initializes to 0.
        :param max_bits: The maximum number of bits each :class:`.WireVector` element
            can grow to. Operations like multiplication and addition can produce
            matrices with more ``bits``, but results will be limited to ``max_bits``.
        """
        if not isinstance(rows, int):
            msg = (
                f'Rows must be of type int, instead "{rows}" was passed of type '
                f"{type(rows)}"
            )
            raise PyrtlError(msg)
        if rows <= 0:
            msg = (
                f"Rows cannot be less than or equal to zero. Rows value passed: {rows}"
            )
            raise PyrtlError(msg)

        if not isinstance(columns, int):
            msg = (
                f'Columns must be of type int, instead "{columns}" was passed of type '
                f"{type(columns)}"
            )
            raise PyrtlError(msg)
        if columns <= 0:
            msg = (
                "Columns cannot be less than or equal to zero. Columns value passed: "
                f"{columns}"
            )
            raise PyrtlError(msg)

        if not isinstance(bits, int):
            msg = (
                f'Bits must be of type int, instead "{bits}" was passed of type '
                f"{type(bits)}"
            )
            raise PyrtlError(msg)
        if bits <= 0:
            msg = f'Bits cannot be negative or zero, instead "{bits}" was passed'
            raise PyrtlError(msg)

        if max_bits is not None and bits > max_bits:
            bits = max_bits

        self._matrix = [[0 for _ in range(columns)] for _ in range(rows)]

        if value is None:
            for i in range(rows):
                for j in range(columns):
                    self._matrix[i][j] = Const(0)
        elif isinstance(value, WireVector):
            if value.bitwidth != bits * rows * columns:
                msg = (
                    "Initialized bitwidth value does not match given value.bitwidth: "
                    f"{value.bitwidth}, expected: {bits * rows * columns}"
                )
                raise PyrtlError(msg)
            for i in range(rows):
                for j in range(columns):
                    start_index = (j * bits) + (i * columns * bits)
                    self._matrix[rows - i - 1][columns - j - 1] = as_wires(
                        value[start_index : start_index + bits], bitwidth=bits
                    )

        elif isinstance(value, list):
            if len(value) != rows or any(len(row) != columns for row in value):
                msg = (
                    "Rows and columns mismatch\n"
                    f"Rows: {len(value)}, expected: {rows}\n"
                    f"Columns: {len(value[0])}, expected: {columns}"
                )
                raise PyrtlError(msg)
            for i in range(rows):
                for j in range(columns):
                    self._matrix[i][j] = as_wires(value[i][j], bitwidth=bits)

        else:
            msg = (
                "Initialized value must be of type WireVector or list. Instead was "
                f"passed value of type {type(value)}"
            )
            raise PyrtlError(msg)

        self.rows = rows
        self.columns = columns
        self._bits = bits
        self.bits = bits
        self.signed = False
        self.max_bits = max_bits

    @property
    def bits(self) -> int:
        """The number of bits for each matrix element.

        Reducing the number of ``bits`` will :meth:`~.WireVector.truncate` the most
        significant bits of each matrix element.
        """
        return self._bits

    @bits.setter
    def bits(self, bits):
        if not isinstance(bits, int):
            msg = (
                f'Bits must be of type int, instead "{bits}" was passed of type '
                f"{type(bits)}"
            )
            raise PyrtlError(msg)
        if bits <= 0:
            msg = f'Bits cannot be negative or zero, instead "{bits}" was passed'
            raise PyrtlError(msg)

        self._bits = bits
        for i in range(self.rows):
            for j in range(self.columns):
                self._matrix[i][j] = self._matrix[i][j][:bits]

    def __len__(self) -> int:
        """Returns the total bitwidth for all elements in the ``Matrix``.

        :return: The ``Matrix``'s total :attr:`~.WireVector.bitwidth`: ``rows * columns
            * bits``.
        """
        return self.bits * self.rows * self.columns

    def to_wirevector(self) -> WireVector:
        """Returns all elements in the ``Matrix`` in one :class:`.WireVector`.

        This :func:`concatenates<.concat>` all the ``Matrix``'s elements together, in
        row-major order.

        For example, a 2 x 1 matrix ``[[wire_a, wire_b]]`` would become
        ``pyrtl.concat(wire_a, wire_b)``.

        :return: A concatenated :class:`.WireVector` containing all of the ``Matrix``'s
                 elements.
        """
        result = []

        for i in range(len(self._matrix)):
            for j in range(len(self._matrix[0])):
                result.append(as_wires(self[i, j], bitwidth=self.bits))

        return as_wires(concat(*result), bitwidth=len(self))

    def transpose(self) -> Matrix:
        """
        :return: A ``Matrix`` representing the transpose of ``self``.
        """
        result = Matrix(self.columns, self.rows, self.bits, max_bits=self.max_bits)
        for i in range(result.rows):
            for j in range(result.columns):
                result[i, j] = self[j, i]
        return result

    def __reversed__(self) -> Matrix:
        """Invoked with the :func:`reversed` builtin.

        :return: A ``Matrix`` with all row and column indices reversed.
        """
        result = Matrix(self.rows, self.columns, self.bits, max_bits=self.max_bits)
        for i in range(self.rows):
            for j in range(self.columns):
                result[i, j] = self[self.rows - 1 - i, self.columns - 1 - j]
        return result

    def __getitem__(self, key: int | slice | tuple[int, int]) -> WireVector | Matrix:
        """Access elements in the ``Matrix``.

        Invoked with square brackets, like ``matrix[...]``.

        Examples::

            int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
            matrix = Matrix(rows=3, columns=3, bits=4, value=int_matrix)

            # Retrieve the second row.
            matrix[1] == [3, 4, 5]

            # Retrieve the last row.
            matrix[-1] == [6, 7, 8]

            # Retrieve the element in row 2, column 0.
            matrix[2, 0] == 6
            matrix[(2, 0)] = 6

            # Retrieve the first two rows.
            matrix[slice(0, 2), slice(0, 3)] == [[0, 1, 2], [3, 4, 5]]
            matrix[0:2, 0:3] == [[0, 1, 2], [3, 4, 5]]
            matrix[:2] == [[0, 1, 2], [3, 4, 5]]

            # Retrieve the last two rows.
            matrix[-2:] == [[3, 4, 5], [6, 7, 8]]

        :param key: The key value to get.

        :return: :class:`.WireVector` or ``Matrix`` containing the value of key.
        """
        if isinstance(key, tuple):
            rows, columns = key

            # First set up proper slice
            if not isinstance(rows, slice):
                if not isinstance(rows, int):
                    msg = (
                        f'Rows must be of type int or slice, instead "{rows}" was '
                        f"passed of type {type(rows)}"
                    )
                    raise PyrtlError(msg)
                if rows < 0:
                    rows = self.rows - abs(rows)
                    if rows < 0:
                        msg = (
                            f"Invalid bounds for rows. Max rows: {self.rows}, got: "
                            f"{rows}"
                        )
                        raise PyrtlError(msg)
                rows = slice(rows, rows + 1, 1)

            if not isinstance(columns, slice):
                if not isinstance(columns, int):
                    msg = (
                        f'Columns must be of type int or slice, instead "{columns}" '
                        f"was passed of type {type(columns)}"
                    )
                    raise PyrtlError(msg)
                if columns < 0:
                    columns = self.columns - abs(columns)
                    if columns < 0:
                        msg = (
                            f"Invalid bounds for columns. Max columns: {self.columns}, "
                            f"got: {columns}"
                        )
                        raise PyrtlError(msg)
                columns = slice(columns, columns + 1, 1)

            if rows.start is None:
                rows = slice(0, rows.stop, rows.step)
            elif rows.start < 0:
                rows = slice(self.rows - abs(rows.start), rows.stop, rows.step)

            if rows.stop is None:
                rows = slice(rows.start, self.rows, rows.step)
            elif rows.stop < 0:
                rows = slice(rows.start, self.rows - abs(rows.stop), rows.step)

            rows = slice(rows.start, rows.stop, 1)

            if columns.start is None:
                columns = slice(0, columns.stop, columns.step)
            elif columns.start < 0:
                columns = slice(
                    self.columns - abs(columns.start), columns.stop, columns.step
                )

            if columns.stop is None:
                columns = slice(columns.start, self.columns, columns.step)
            elif columns.stop < 0:
                columns = slice(
                    columns.start, self.columns - abs(columns.stop), columns.step
                )

            columns = slice(columns.start, columns.stop, 1)

            # Check slice bounds
            if (
                rows.start > self.rows
                or rows.stop > self.rows
                or rows.start < 0
                or rows.stop < 0
            ):
                msg = (
                    f"Invalid bounds for rows. Max rows: {self.rows}, got: "
                    f"{rows.start}:{rows.stop}"
                )
                raise PyrtlError(msg)
            if (
                columns.start > self.columns
                or columns.stop > self.columns
                or columns.start < 0
                or columns.stop < 0
            ):
                msg = (
                    f"Invalid bounds for columns. Max columns: {self.columns}, got: "
                    f"{columns.start}:{columns.stop}"
                )
                raise PyrtlError(msg)

            # If it's a single value we want to return a wirevector
            if rows.stop - rows.start == 1 and columns.stop - columns.start == 1:
                return as_wires(self._matrix[rows][0][columns][0], bitwidth=self.bits)

            # Otherwise set up matrix and return that
            result = [
                [0 for _ in range(columns.stop - columns.start)]
                for _ in range(rows.stop - rows.start)
            ]

            for i in range(len(result)):
                for j in range(len(result[0])):
                    result[i][j] = self._matrix[i + rows.start][j + columns.start]
            return Matrix(
                len(result),
                len(result[0]),
                self._bits,
                signed=self.signed,
                value=result,
                max_bits=self.max_bits,
            )

        # Second case when we just want to get full row
        if isinstance(key, int):
            if key < 0:
                start = self.rows - abs(key)
                if start < 0:
                    msg = (
                        f"Index {key} is out of bounds for matrix with {self.rows} rows"
                    )
                    raise PyrtlError(msg)
                key = slice(start, start + 1, None)
            else:
                key = slice(key, key + 1, None)
            return self[key, :]

        # Third case when we want multiple rows
        if isinstance(key, slice):
            return self[key, :]

        # Otherwise improper value was passed
        msg = (
            f'Rows must be of type int or slice, instead "{key}" was passed of type '
            f"{type(key)}"
        )
        raise PyrtlError(msg)

    def __setitem__(
        self,
        key: int | slice | tuple[int, int],
        value: WireVectorLike | Matrix,
    ):
        """Mutate the ``Matrix``.

        Invoked with square brackets, like ``matrix[a, b] = value``. ``value`` will be
        truncated so it fits in :attr:`bits`.

        This modifies the ``Matrix``'s :class:`lists<list>` in its internal
        :class:`list` of :class:`list` of :class:`WireVectors<.WireVector>`, which makes
        the ``Matrix`` use a different set of :class:`WireVectors<.WireVector>` as its
        elements. It does not modify any :class:`WireVectors<.WireVector>`.

        :param key: The key value to set.
        :param value: The value in which to set the key.
        """

        if isinstance(key, tuple):
            rows, columns = key

            # First ensure that slices are correct
            if not isinstance(rows, slice):
                if not isinstance(rows, int):
                    msg = (
                        f'Rows must be of type int or slice, instead "{rows}" was '
                        f"passed of type {type(rows)}"
                    )
                    raise PyrtlError(msg)
                rows = slice(rows, rows + 1, 1)

            if not isinstance(columns, slice):
                if not isinstance(columns, int):
                    msg = (
                        f'Columns must be of type int or slice, instead "{columns}" '
                        f"was passed of type {type(columns)}"
                    )
                    raise PyrtlError(msg)
                columns = slice(columns, columns + 1, 1)

            if rows.start is None:
                rows = slice(0, rows.stop, rows.step)
            elif rows.start < 0:
                rows = slice(self.rows - abs(rows.start), rows.stop, rows.step)

            if rows.stop is None:
                rows = slice(rows.start, self.rows, rows.step)
            elif rows.stop < 0:
                rows = slice(rows.start, self.rows - abs(rows.stop), rows.step)

            if columns.start is None:
                columns = slice(0, columns.stop, columns.step)
            elif columns.start < 0:
                columns = slice(
                    self.columns - abs(columns.start), columns.stop, columns.step
                )

            if columns.stop is None:
                columns = slice(columns.start, self.columns, columns.step)
            elif columns.stop < 0:
                columns = slice(
                    columns.start, self.columns - abs(columns.stop), columns.step
                )

            # Check Slice Bounds
            if (
                rows.start > self.rows
                or rows.stop > self.rows
                or rows.start < 0
                or rows.stop < 0
            ):
                msg = (
                    f"Invalid bounds for rows. Max rows: {self.rows}, got: "
                    f"{rows.start}:{rows.stop}"
                )
                raise PyrtlError(msg)
            if (
                columns.start > self.columns
                or columns.stop > self.columns
                or columns.start < 0
                or columns.stop < 0
            ):
                msg = (
                    f"Invalid bounds for columns. Max columns: {self.columns}, got: "
                    f"{columns.start}:{columns.stop}"
                )
                raise PyrtlError(msg)

            # First case when setting value to Matrix
            if isinstance(value, Matrix):
                if value.rows != (rows.stop - rows.start):
                    msg = (
                        "Value rows mismatch. Expected Matrix of rows "
                        f'"{rows.stop - rows.start}", instead received Matrix of rows '
                        f'"{value.rows}"'
                    )
                    raise PyrtlError(msg)
                if value.columns != (columns.stop - columns.start):
                    msg = (
                        "Value columns mismatch. Expected Matrix of columns "
                        f'"{columns.stop - columns.start}", instead received Matrix of '
                        f'columns "{value.columns}"'
                    )
                    raise PyrtlError(msg)

                for i in range(rows.stop - rows.start):
                    for j in range(columns.stop - columns.start):
                        self._matrix[rows.start + i][columns.start + j] = as_wires(
                            value[i, j], bitwidth=self.bits
                        )

            # Second case when setting value to wirevector
            elif isinstance(value, (int, WireVector)):
                if ((rows.stop - rows.start) != 1) or (
                    (columns.stop - columns.start) != 1
                ):
                    msg = "Value mismatch: expected Matrix, instead received WireVector"
                    raise PyrtlError(msg)
                self._matrix[rows.start][columns.start] = as_wires(
                    value, bitwidth=self.bits
                )
            # Otherwise Error
            else:
                msg = f"Invalid value of type {type(value)}"
                raise PyrtlError(msg)
        else:
            # Second case if we just want to set a full row
            if isinstance(key, int):
                if key < 0:
                    start = self.rows - abs(key)
                    if start < 0:
                        msg = (
                            f"Index {key} is out of bounds for matrix with {self.rows} "
                            "rows"
                        )
                        raise PyrtlError(msg)
                    key = slice(start, start + 1, None)
                else:
                    key = slice(key, key + 1, None)
                self[key, :] = value
            # Third case if we want to set full rows
            elif isinstance(key, slice):
                self[key, :] = value
            else:
                msg = (
                    f'Rows must be of type int or slice, instead "{key}" was passed of '
                    f"type {type(key)}"
                )
                raise PyrtlError(msg)

    def copy(self) -> Matrix:
        """Constructs a copy of the ``Matrix``.

        The returned copy will have new set of :class:`WireVectors<.WireVector>` for its
        elements, but each new :class:`WireVector` will be wired to the corresponding
        :class:`WireVector` in the original ``Matrix``.

        :return: A new instance of ``Matrix`` that indirectly refers to the same
                 underlying :class:`WireVectors<.WireVector>` as ``self``.
        """
        return Matrix(
            self.rows,
            self.columns,
            self.bits,
            value=self.to_wirevector(),
            max_bits=self.max_bits,
        )

    def __iadd__(self, other: Matrix) -> Matrix:
        """Perform the in-place addition operation.

        Invoked with ``a += b``. Performs elementwise addition.

        :return: a Matrix object with the elementwise addition being performed.
        """
        new_value = self + other
        self._matrix = new_value._matrix
        self.bits = new_value._bits
        return self.copy()

    def __add__(self, other: Matrix) -> Matrix:
        """Perform the addition operation.

        Invoked with ``a + b``. Performs elementwise addition.

        :return: a Matrix object containing the elementwise sum.
        """
        if not isinstance(other, Matrix):
            msg = f"error: expecting a Matrix, got {type(other)} instead"
            raise PyrtlError(msg)

        if self.columns != other.columns:
            msg = (
                f"error: columns mismatch. Matrix a: {self.columns} columns, Matrix b: "
                f"{other.columns} columns"
            )
            raise PyrtlError(msg)
        if self.rows != other.rows:
            msg = (
                f"error: row mismatch. Matrix a: {self.rows} rows, Matrix b: "
                f"{other.rows} rows"
            )
            raise PyrtlError(msg)

        new_bits = self.bits
        if other.bits > new_bits:
            new_bits = other.bits

        result = Matrix(self.rows, self.columns, new_bits + 1, max_bits=self.max_bits)

        for i in range(result.rows):
            for j in range(result.columns):
                result[i, j] = self[i, j] + other[i, j]
        return result

    def __isub__(self, other: Matrix) -> Matrix:
        """Perform the inplace subtraction opperation.

        Invoked with ``a -= b``. Performs elementwise subtraction.

        :param other: The ``Matrix`` to subtract.

        :return: A ``Matrix`` object with the result of elementwise subtraction.
        """
        new_value = self - other
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __sub__(self, other: Matrix) -> Matrix:
        """Perform the subtraction operation.

        Invoked with ``a - b``. Performs elementwise subtraction.

        .. note::

            If ``signed=False``, the result will be floored at 0.

        :param other: The ``Matrix`` to subtract.

        :return: a ``Matrix`` object with the result of elementwise subtraction.
        """
        if not isinstance(other, Matrix):
            msg = f"error: expecting a Matrix, got {type(other)} instead"
            raise PyrtlError(msg)

        if self.columns != other.columns:
            msg = (
                f"error: columns mismatch. Matrix a: {self.columns} columns, "
                f"Matrix b: {other.columns} columns"
            )
            raise PyrtlError(msg)

        if self.rows != other.rows:
            msg = (
                f"error: row mismatch. Matrix a: {self.rows} rows, Matrix b: "
                f"{other.rows} rows"
            )
            raise PyrtlError(msg)

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
                        self[i, j] > other[i, j], self[i, j] - other[i, j], Const(0)
                    )

        return result

    def __imul__(self, other: Matrix | WireVector) -> Matrix:
        """Perform the in-place multiplication operation.

        Invoked with ``a *= b``. Performs elementwise or scalar multiplication.

        :param other: The ``Matrix`` or scalar to multiply.

        :return: A ``Matrix`` object with the product.
        """
        new_value = self * other
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __mul__(self, other: Matrix | WireVector) -> Matrix:
        """Perform the elementwise or scalar multiplication operation.

        Invoked with ``a * b``.

        :param other: The ``Matrix`` or scalar to multiply.

        :return: A ``Matrix`` object with the product.
        """

        if isinstance(other, Matrix):
            if self.columns != other.columns:
                msg = (
                    f"error: columns mismatch. Matrix a: {self.columns} columns, "
                    f"Matrix b: {other.columns} columns"
                )
                raise PyrtlError(msg)
            if self.rows != other.rows:
                msg = (
                    f"error, row mismatch Matrix a: {self.rows} rows, Matrix b: "
                    f"{other.rows} rows"
                )
                raise PyrtlError(msg)

            bits = self.bits + other.bits
        elif isinstance(other, WireVector):
            bits = self.bits + len(other)
        else:
            msg = f"Expecting a Matrix or WireVector got {type(other)} instead"
            raise PyrtlError(msg)

        result = Matrix(self.rows, self.columns, bits, max_bits=self.max_bits)

        for i in range(self.rows):
            for j in range(self.columns):
                if isinstance(other, Matrix):
                    result[i, j] = self[i, j] * other[i, j]
                else:
                    result[i, j] = self[i, j] * other
        return result

    def __imatmul__(self, other: Matrix) -> Matrix:
        """Performs the inplace matrix multiplication operation.

        Invoked with ``a @= b``.

        :param other: The second ``Matrix``.

        :return: A ``Matrix`` that contains the product.
        """
        new_value = self.__matmul__(other)
        self.columns = new_value.columns
        self.rows = new_value.rows
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __matmul__(self, other: Matrix) -> Matrix:
        """Performs the inplace matrix multiplication operation.

        Invoked with ``a @ b``.

        :param other: The second ``Matrix``.

        :return: A ``Matrix`` that contains the product.
        """
        if not isinstance(other, Matrix):
            msg = f"error: expecting a Matrix, got {type(other)} instead"
            raise PyrtlError(msg)

        if self.columns != other.rows:
            msg = (
                f"error: rows and columns mismatch. Matrix a: {self.columns} columns, "
                f"Matrix b: {other.rows} rows"
            )
            raise PyrtlError(msg)

        result = Matrix(
            self.rows,
            other.columns,
            self.columns * other.rows * (self.bits + other.bits),
            max_bits=self.max_bits,
        )

        for i in range(self.rows):
            for j in range(other.columns):
                for k in range(self.columns):
                    result[i, j] = fused_multiply_adder(
                        self[i, k], other[k, j], result[i, j], signed=self.signed
                    )

        return result

    def __ipow__(self, power: int) -> Matrix:
        """Performs the matrix power operation.

        Invoked with ``a **= b``.

        This performs a chain of matrix multiplications, where ``self`` is matrix
        multiplied by ``self``, ``power`` times.

        :param power: The power to raise the matrix to.

        :return: A ``Matrix`` containing the result.
        """
        new_value = self**power
        self._matrix = new_value._matrix
        self._bits = new_value._bits
        return self.copy()

    def __pow__(self, power: int) -> Matrix:
        """Performs the matrix power operation.

        Invoked with ``a ** b``.

        This performs a chain of matrix multiplications, where ``self`` is matrix
        multiplied by ``self``, ``power`` times.

        :param power: The power to raise the matrix to.

        :return: A ``Matrix`` containing the result.
        """
        if not isinstance(power, int):
            msg = (
                "Unexpected power given. Type int expected, but received type "
                f"{type(power)}"
            )
            raise PyrtlError(msg)

        if self.rows != self.columns:
            msg = "Matrix must be square"
            raise PyrtlError(msg)

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

        msg = "Power must be greater than or equal to 0"
        raise PyrtlError(msg)

    def put(
        self,
        ind: int | list[int] | tuple[int],
        v: int | list[int] | tuple[int] | Matrix,
        mode: str = "raise",
    ):
        """Replace specified elements of the ``Matrix`` with values ``v``.

        Note that the index ``ind`` is on the flattened matrix.

        :param ind: Target indices.
        :param v: Values to place in ``Matrix`` at ``ind``. If ``v`` is shorter than
                  ``ind``, ``v`` will be repeated.
        :param mode: How out-of-bounds indices behave. ``raise`` raises an error,
            ``wrap`` wraps around, and ``clip`` clips to the range.
        """
        count = self.rows * self.columns
        if isinstance(ind, int):
            ind = (ind,)
        elif not isinstance(ind, (tuple, list)):
            msg = f"Expected int or list-like indices, got {type(ind)}"
            raise PyrtlError(msg)

        if isinstance(v, int):
            v = (v,)

        if isinstance(v, (tuple, list)) and len(v) == 0:
            return
        if isinstance(v, Matrix) and v.rows != 1:
            msg = f"Expected a row-vector matrix, instead got matrix with {v.rows} rows"
            raise PyrtlError(msg)

        if mode not in ["raise", "wrap", "clip"]:
            msg = (
                f"Unexpected mode {mode}; allowable modes are 'raise', 'wrap', and "
                "'clip'"
            )
            raise PyrtlError(msg)

        def get_ix(ix):
            if ix < 0:
                ix = count - abs(ix)
            if ix < 0 or ix >= count:
                if mode == "raise":
                    msg = f"index {ix} is out of bounds with size {count}"
                    raise PyrtlError(msg)
                if mode == "wrap":
                    ix = ix % count
                elif mode == "clip":
                    ix = 0 if ix < 0 else count - 1
            return ix

        def get_value(ix):
            if isinstance(v, (tuple, list)):
                if ix >= len(v):
                    return v[-1]  # if v is shorter than ind, repeat last as necessary
                return v[ix]
            if isinstance(v, Matrix):
                if ix >= count:
                    return v[0, -1]
                return v[0, ix]
            return None

        for v_ix, mat_ix in enumerate(ind):
            mat_ix = get_ix(mat_ix)
            row = mat_ix // self.columns
            col = mat_ix % self.columns
            self[row, col] = get_value(v_ix)

    def reshape(self, *newshape: int | tuple, order: str = "C"):
        """Create a ``Matrix`` of the given shape from ``self``.

        One shape dimension in ``newshape`` can be ``-1``; in this case, the value for
        that dimension is inferred from the other given dimension (if any) and the
        number of elements in ``self``.

        Examples::

            int_matrix = [[0, 1, 2, 3], [4, 5, 6, 7]]
            matrix = Matrix.Matrix(2, 4, 4, value=int_matrix)

            matrix.reshape(-1) == [[0, 1, 2, 3, 4, 5, 6, 7]]
            matrix.reshape(8) == [[0, 1, 2, 3, 4, 5, 6, 7]]
            matrix.reshape(1, 8) == [[0, 1, 2, 3, 4, 5, 6, 7]]
            matrix.reshape((1, 8)) == [[0, 1, 2, 3, 4, 5, 6, 7]]
            matrix.reshape((1, -1)) == [[0, 1, 2, 3, 4, 5, 6, 7]]

            matrix.reshape(4, 2) == [[0, 1], [2, 3], [4, 5], [6, 7]]
            matrix.reshape(-1, 2) == [[0, 1], [2, 3], [4, 5], [6, 7]]
            matrix.reshape(4, -1) == [[0, 1], [2, 3], [4, 5], [6, 7]]

        :param newshape: Shape of the matrix to return. If ``newshape`` is a single
            :class:`int`, the new shape will be a 1-D row-vector of that length. If
            ``newshape`` is a :class:`tuple`, the :class:`tuple` specifies the new
            number of rows and columns. ``newshape`` can also be varargs.
        :param order: ``C`` means to read from self using row-major order (C-style), and
            ``F`` means to read from self using column-major order (Fortran-style).

        :return: A copy of the matrix with same data, with a new number of rows and
                 columns.
        """
        count = self.rows * self.columns
        if isinstance(newshape, int):
            if newshape == -1:
                newshape = (1, count)
            else:
                newshape = (1, newshape)
        elif isinstance(newshape, tuple):
            if isinstance(newshape[0], tuple):
                newshape = newshape[0]
            if len(newshape) == 1:
                newshape = (1, newshape[0])
            if len(newshape) > 2:
                msg = "length of newshape tuple must be <= 2"
                raise PyrtlError(msg)
            rows, cols = newshape
            if not isinstance(rows, int) or not isinstance(cols, int):
                msg = (
                    "newshape dimensions must be integers, instead got "
                    f"{type(newshape)}"
                )
                raise PyrtlError(msg)
            if rows == -1 and cols == -1:
                msg = "Both dimensions in newshape cannot be -1"
                raise PyrtlError(msg)
            if rows == -1:
                rows = count // cols
                newshape = (rows, cols)
            elif cols == -1:
                cols = count // rows
                newshape = (rows, cols)
        else:
            msg = (
                f"newshape can be an integer or tuple of integers, not {type(newshape)}"
            )
            raise PyrtlError(msg)

        rows, cols = newshape
        if rows * cols != count:
            msg = f"Cannot reshape matrix of size {count} into shape {newshape}"
            raise PyrtlError(msg)

        if order not in "CF":
            msg = (
                f"Invalid order {order}. Acceptable orders are 'C' (for row-major "
                "C-style order) and 'F' (for column-major Fortran-style order)."
            )
            raise PyrtlError(msg)

        value = [[0] * cols for _ in range(rows)]
        ix = 0
        if order == "C":
            # Read and write in row-wise order
            for newr in range(rows):
                for newc in range(cols):
                    r = ix // self.columns
                    c = ix % self.columns
                    value[newr][newc] = self[r, c]
                    ix += 1
        else:
            # Read and write in column-wise order
            for newc in range(cols):
                for newr in range(rows):
                    r = ix % self.rows
                    c = ix // self.rows
                    value[newr][newc] = self[r, c]
                    ix += 1

        return Matrix(rows, cols, self.bits, self.signed, value, self.max_bits)

    def flatten(self, order: str = "C"):
        """Flatten the ``Matrix`` into a single row.

        :param order: ``C`` means row-major order (C-style), and ``F`` means
            column-major order (Fortran-style)

        :return: A copy of the ``Matrix`` flattened into a row vector.
        """
        return self.reshape(self.rows * self.columns, order=order)


def multiply(first: Matrix, second: Matrix | WireVector) -> Matrix:
    """Perform the elementwise or scalar multiplication operation.

    .. WARNING::

        Use :meth:`Matrix.__mul__` instead.

    :param first: first matrix
    :param second: second matrix

    :return: a Matrix object with the element wise or scalar multiplication being
             performed
    """
    if not isinstance(first, Matrix):
        msg = f"error: expecting a Matrix, got {type(second)} instead"
        raise PyrtlError(msg)
    return first * second


def sum(
    matrix: Matrix | WireVector, axis: int | None = None, bits: int | None = None
) -> Matrix | WireVector:
    """Returns the sum of values in a ``Matrix`` across ``axis``.

    This performs a reduction, summing over the specified ``axis``.

    :param matrix: The matrix to perform sum operation on. If it is a
        :class:`.WireVector`, it will return itself.
    :param axis: The axis to perform the operation on. ``None`` refers to sum of all
        elements. ``0`` is sum of column. ``1`` is sum of rows. Defaults to ``None``.
    :param bits: The bits per element of the sum. Defaults to ``matrix.bits``.

    :return: A :class:`.WireVector` or ``Matrix`` representing the sum.
    """

    def sum_2(first, second):
        return first + second

    if isinstance(matrix, WireVector):
        return matrix

    if not isinstance(matrix, Matrix):
        msg = (
            f"error: expecting a Matrix or WireVector for matrix, got {type(matrix)} "
            "instead"
        )
        raise PyrtlError(msg)

    if not isinstance(bits, int) and bits is not None:
        msg = f"error: expecting an int/None for bits, got {type(bits)} instead"
        raise PyrtlError(msg)

    if not isinstance(axis, int) and axis is not None:
        msg = f"error: expecting an int or None for axis, got {type(axis)} instead"
        raise PyrtlError(msg)

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        msg = f"error: bits cannot be negative or zero, got {bits} instead"
        raise PyrtlError(msg)

    if axis is None:
        inputs = []
        for i in range(matrix.rows):
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
        return reduce(sum_2, inputs)

    if axis == 0:
        result = Matrix(1, matrix.columns, signed=matrix.signed, bits=bits)

        for i in range(matrix.columns):
            inputs = []
            for j in range(matrix.rows):
                inputs.append(matrix[j, i])
            result[0, i] = reduce(sum_2, inputs)
        return result

    if axis == 1:
        result = Matrix(1, matrix.rows, signed=matrix.signed, bits=bits)
        for i in range(matrix.rows):
            inputs = []
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
            result[0, i] = reduce(sum_2, inputs)
        return result

    msg = f"Axis invalid: expected (None, 0, or 1), got {axis}"
    raise PyrtlError(msg)


def min(
    matrix: Matrix | WireVector, axis: int | None = None, bits: int | None = None
) -> Matrix | WireVector:
    """Returns the minimum value in a ``Matrix``.

    This performs a reduction, taking the minimum over the specified ``axis``.

    :param matrix: The matrix to take the mimimum of. If it is a :class:`.WireVector`,
        it will return itself.
    :param axis: The axis to perform the minimum on. ``None`` refers to min of all
        elements. ``0`` is min of columns. ``1`` is min of rows. Defaults to ``None``.
    :param bits: The bits per element of the min. Defaults to ``matrix.bits``.

    :return: A :class:`.WireVector` or ``Matrix`` representing the min value.
    """

    def min_2(first, second):
        return select(first < second, first, second)

    if isinstance(matrix, WireVector):
        return matrix

    if not isinstance(matrix, Matrix):
        msg = (
            f"error: expecting a Matrix or WireVector for matrix, got {type(matrix)} "
            "instead"
        )
        raise PyrtlError(msg)

    if not isinstance(bits, int) and bits is not None:
        msg = f"error: expecting an int/None for bits, got {type(bits)} instead"
        raise PyrtlError(msg)

    if not isinstance(axis, int) and axis is not None:
        msg = f"error: expecting an int or None for axis, got {type(axis)} instead"
        raise PyrtlError(msg)

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        msg = f"error: bits cannot be negative or zero, got {bits} instead"
        raise PyrtlError(msg)

    if axis is None:
        inputs = []
        for i in range(matrix.rows):
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
        return reduce(min_2, inputs)

    if axis == 0:
        result = Matrix(1, matrix.columns, signed=matrix.signed, bits=bits)

        for i in range(matrix.columns):
            inputs = []
            for j in range(matrix.rows):
                inputs.append(matrix[j, i])
            result[0, i] = reduce(min_2, inputs)
        return result

    if axis == 1:
        result = Matrix(1, matrix.rows, signed=matrix.signed, bits=bits)
        for i in range(matrix.rows):
            inputs = []
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
            result[0, i] = reduce(min_2, inputs)
        return result

    msg = f"Axis invalid: expected (None, 0, or 1), got {axis}"
    raise PyrtlError(msg)


def max(
    matrix: Matrix | WireVector, axis: int | None = None, bits: int | None = None
) -> Matrix | WireVector:
    """Returns the maximum value in a ``Matrix``.

    This performs a reduction, taking the maximum over the specified ``axis``.

    :param matrix: The matrix to take the mimimum of. If it is a :class:`.WireVector`,
        it will return itself.
    :param axis: The axis to perform the maximum on. ``None`` refers to max of all
        elements. ``0`` is max of columns. ``1`` is max of rows. Defaults to ``None``.
    :param bits: The bits per element of the max. Defaults to ``matrix.bits``.

    :return: A :class:`.WireVector` or ``Matrix`` representing the max value.
    """

    def max_2(first, second):
        return select(first > second, first, second)

    if isinstance(matrix, WireVector):
        return matrix

    if not isinstance(matrix, Matrix):
        msg = (
            f"error: expecting a Matrix or WireVector for matrix, got {type(matrix)} "
            "instead"
        )
        raise PyrtlError(msg)

    if not isinstance(bits, int) and bits is not None:
        msg = f"error: expecting an int/None for bits, got {type(bits)} instead"
        raise PyrtlError(msg)

    if not isinstance(axis, int) and axis is not None:
        msg = f"error: expecting an int or None for axis, got {type(axis)} instead"
        raise PyrtlError(msg)

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        msg = f"error: bits cannot be negative or zero, got {bits} instead"
        raise PyrtlError(msg)

    if axis is None:
        inputs = []
        for i in range(matrix.rows):
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
        return reduce(max_2, inputs)

    if axis == 0:
        result = Matrix(1, matrix.columns, signed=matrix.signed, bits=bits)

        for i in range(matrix.columns):
            inputs = []
            for j in range(matrix.rows):
                inputs.append(matrix[j, i])
            result[0, i] = reduce(max_2, inputs)
        return result

    if axis == 1:
        result = Matrix(1, matrix.rows, signed=matrix.signed, bits=bits)
        for i in range(matrix.rows):
            inputs = []
            for j in range(matrix.columns):
                inputs.append(matrix[i, j])
            result[0, i] = reduce(max_2, inputs)
        return result

    msg = f"Axis invalid: expected (None, 0, or 1), got {axis}"
    raise PyrtlError(msg)


def argmax(
    matrix: Matrix | WireVector, axis: int | None = None, bits: int | None = None
) -> Matrix | WireVector:
    """Returns the index of the max value of the ``Matrix``.

    .. note::

        If there are two indices with the same max value, this function picks the first
        instance.

    :param matrix: The ``Matrix`` to perform argmax operation on. If it is a
        :class:`.WireVector`, it will return itself.
    :param axis: The axis to perform the operation on. ``None`` refers to argmax of all
        items. ``0`` is argmax of the columns. ``1`` is argmax of rows. Defaults to
        ``None``.
    :param bits: The bits per element of the argmax. Defaults to ``matrix.bits``.

    :return: A :class:`.WireVector` or ``Matrix`` representing the argmax value.
    """
    if isinstance(matrix, WireVector):
        return Const(0)

    if not isinstance(matrix, Matrix):
        msg = (
            f"error: expecting a Matrix or WireVector for matrix, got {type(matrix)} "
            "instead"
        )
        raise PyrtlError(msg)

    if not isinstance(bits, int) and bits is not None:
        msg = f"error: expecting an int/None for bits, got {type(bits)} instead"
        raise PyrtlError(msg)

    if not isinstance(axis, int) and axis is not None:
        msg = f"error: expecting an int or None for axis, got {type(axis)} instead"
        raise PyrtlError(msg)

    if bits is None:
        bits = matrix.bits

    if bits <= 0:
        msg = f"error: bits cannot be negative or zero, got {bits} instead"
        raise PyrtlError(msg)

    max_number = max(matrix, axis=axis, bits=bits)
    if axis is None:
        index = Const(0)
        arg = matrix.rows * matrix.columns - 1
        for i in reversed(range(matrix.rows)):
            for j in reversed(range(matrix.columns)):
                index = select(max_number == matrix[i, j], Const(arg), index)
                arg -= 1
        return index
    if axis == 0:
        result = Matrix(1, matrix.columns, signed=matrix.signed, bits=bits)
        for i in range(matrix.columns):
            local_max = max_number[0, i]
            index = Const(0)
            arg = matrix.rows - 1
            for j in reversed(range(matrix.rows)):
                index = select(local_max == matrix[j, i], Const(arg), index)
                arg -= 1
            result[0, i] = index
        return result
    if axis == 1:
        result = Matrix(1, matrix.rows, signed=matrix.signed, bits=bits)
        for i in range(matrix.rows):
            local_max = max_number[0, i]
            index = Const(0)
            arg = matrix.columns - 1
            for j in reversed(range(matrix.columns)):
                index = select(local_max == matrix[i, j], Const(arg), index)
                arg -= 1
            result[0, i] = index
        return result
    return None


def dot(first: Matrix, second: Matrix) -> Matrix:
    """Performs the dot product on two matrices.

    Specifically, the dot product on two matrices is:

    1. If either ``first`` or ``second`` are :class:`WireVectors<.WireVector>`, or have
       both rows and columns equal to 1, ``dot`` is equivalent to :meth:`Matrix.__mul__`

    2. If ``first`` and ``second`` are both arrays (have rows or columns equal to 1),
       ``dot`` is the inner product of the vectors.

    3. Otherwise ``dot`` is :meth:`Matrix.__matmul__` between ``first`` and ``second``.

    .. note::

        Row vectors and column vectors are both treated as arrays.

    :param first: The first matrix.
    :param second: The second matrix.

    :return: A ``Matrix`` that contains the dot product of ``first`` and ``second``.
    """
    if not isinstance(first, (WireVector, Matrix)):
        msg = f"error: expecting a Matrix, got {type(first)} instead"
        raise PyrtlError(msg)
    if not isinstance(second, (WireVector, Matrix)):
        msg = f"error: expecting a Matrix/WireVector, got {type(second)} instead"
        raise PyrtlError(msg)

    # First case when it is multiply
    if isinstance(first, WireVector):
        if isinstance(second, WireVector):
            return first * second
        return second[:, :] * first
    if isinstance(second, WireVector):
        return first[:, :] * second
    if (first.rows == 1 and first.columns == 1) or (
        second.rows == 1 and second.columns == 1
    ):
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


def hstack(*matrices: Matrix) -> Matrix:
    """Stack ``matrices`` in sequence horizontally (column-wise).

    All the ``matrices`` must have the same number of rows and the same ``signed``
    value.

    For example::

        m1 = Matrix(rows=2, columns=3, bits=5,
                    value=[[1, 2, 3],
                           [4, 5, 6]])
        m2 = Matrix(rows=2, columns=1, bits=10,
                    value=[[17],
                           [23]]])
        m3 = hstack(m1, m2)

    ``m3`` will look like::

        [[1, 2, 3, 17],
         [4, 5, 6, 23]]

    And ``m3.bits`` will be ``10``.

    :param matrices: Matrices to concatenate together horizontally.

    :return: A new ``Matrix``, with the same number of rows as the original, and columns
             equal to the sum of the columns of ``matrices``. The new ``Matrix``'s
             bitwidth is the max of the bitwidths of all ``matrices``.
    """
    if len(matrices) == 0:
        msg = "Must supply at least one matrix to hstack()"
        raise PyrtlError(msg)

    if any(not isinstance(matrix, Matrix) for matrix in matrices):
        msg = "All arguments to hstack must be matrices."
        raise PyrtlError(msg)

    if len(matrices) == 1:
        return matrices[0].copy()

    new_rows = matrices[0].rows
    if any(m.rows != new_rows for m in matrices):
        msg = "All matrices being hstacked together must have the same number of rows"
        raise PyrtlError(msg)

    new_signed = matrices[0].signed
    if any(m.signed != new_signed for m in matrices):
        msg = "All matrices being hstacked together must have the same signedness"
        raise PyrtlError(msg)

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


def vstack(*matrices: Matrix) -> Matrix:
    """Stack matrices in sequence vertically (row-wise).

    All the ``matrices`` must have the same number of columns and the same ``signed``
    value.

    For example::

        m1 = Matrix(rows=2, columns=3, bits=5,
                    value=[[1, 2, 3],
                           [4, 5, 6]])
        m2 = Matrix(rows=1, columns=3, bits=10,
                    value=[[7, 8, 9]])
        m3 = vstack(m1, m2)

    ``m3`` will look like::

        [[1, 2, 3],
         [4, 5, 6],
         [7, 8, 9]]

    And ``m3.bits`` will be ``10``.

    :param matrices: Matrices to concatenate together vertically

    :return: A new ``Matrix``, with the same number of columns as the original, and rows
             equal to the sum of the rows of ``matricies``. The new ``Matrix``'s
             bitwidth is the max of the bitwidths of all ``matrices``.
    """
    if len(matrices) == 0:
        msg = "Must supply at least one matrix to vstack()"
        raise PyrtlError(msg)

    if any(not isinstance(matrix, Matrix) for matrix in matrices):
        msg = "All arguments to vstack must be matrices."
        raise PyrtlError(msg)

    if len(matrices) == 1:
        return matrices[0].copy()

    new_cols = matrices[0].columns
    if any(m.columns != new_cols for m in matrices):
        msg = (
            "All matrices being vstacked together must have the same number of columns"
        )
        raise PyrtlError(msg)

    new_signed = matrices[0].signed
    if any(m.signed != new_signed for m in matrices):
        msg = "All matrices being vstacked together must have the same signedness"
        raise PyrtlError(msg)

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


def concatenate(matrices: Matrix, axis: int = 0) -> Matrix:
    """Join a sequence of ``matrices`` along an existing ``axis``.

    This function is just a wrapper around :func:`hstack` and :func:`vstack`.

    :param matrices: Matrices to concatenate together.
    :param axis: Axis along which to concatenate. ``0`` is horizontally, ``1`` is
        vertically. Defaults to ``0``.

    :return: A new ``Matrix`` composed of the given matrices concatenated together.
    """
    if axis == 0:
        return hstack(*matrices)
    if axis == 1:
        return vstack(*matrices)
    msg = "Only allowable axes are 0 or 1"
    raise PyrtlError(msg)


def matrix_wv_to_list(
    matrix_wv: WireVector, rows: int, columns: int, bits: int
) -> list[list[int]]:
    """Convert a :class:`.WireVector` representing a :class:`Matrix` into a Python list
    of lists.

    During :class:`.Simulation`, this is useful when printing the value of an
    :meth:`inspected<.Simulation.inspect>` wire that represents a :class:`Matrix`.

    Example::

        m = Matrix.Matrix(rows=2, columns=3, bits=4,
                          values=[[1, 2, 3],
                                  [4, 5, 6]])

        output = Output(name="output")
        output <<= m.to_wirevector()

        sim = Simulation()
        sim.step()

        raw_matrix = Matrix.matrix_wv_to_list(
            sim.inspect("output"), m.rows, m.columns, m.bits)
        print(raw_matrix)

        # Produces:
        # [[1, 2, 3], [4, 5, 6]]

    :param matrix_wv: Result of calling :meth:`Matrix.to_wirevector`.
    :param rows: Number of rows in the matrix.
    :param columns: Number of columns in the matrix.
    :param bits: Number of bits for each element in the matrix.

    :return: A Python list of lists.
    """
    value = bin(matrix_wv)[2:].zfill(rows * columns * bits)

    result = [[0 for _ in range(columns)] for _ in range(rows)]

    bit_pointer = 0
    for i in range(rows):
        for j in range(columns):
            int_value = int(value[bit_pointer : bit_pointer + bits], 2)
            result[i][j] = int_value
            bit_pointer += bits
    return result


def list_to_int(matrix: list[list[int]], n_bits: int) -> int:
    """Convert a Python matrix (a :class:`list` of :class:`lists<list>`) into an
    :class:`int`.

    Integers that are signed will automatically be converted to their two's complement
    form.

    This function is helpful for turning a pure Python list of lists into a very large
    integer suitable for creating a :class:`.Const` that can be used as
    :meth:`Matrix.__init__`'s ``value`` argument, or for passing into a
    :meth:`.Simulation.step`'s ``provided_inputs`` for an :class:`.Input` wire.

    For example, calling ``list_to_int([3, 5], [7, 9], n_bits=4)`` produces ``13689``,
    which in binary looks like::

        0011 0101 0111 1001

    Note how the elements of the list of lists were added, 4 bits at a time, in row
    order, such that the element at row 0, column 0 is in the most significant 4 bits,
    and the element at row 1, column 1 is in the least significant 4 bits.

    Here's an example of using it in :class:`.Simulation`::

        a_vals = [[0, 1], [2, 3]]
        b_vals = [[2, 4, 6], [8, 10, 12]]

        a_in = pyrtl.Input(name="a_in", bitwidth=2 * 2 * 4)
        b_in = pyrtl.Input(name="b_in", bitwidth=2 * 3 * 4)
        a = Matrix.Matrix(rows=2, columns=2, bits=4, value=a_in)
        b = Matrix.Matrix(rows=2, columns=3, bits=4, value=b_in)
        ...

        sim = pyrtl.Simulation()
        sim.step({
            'a_in': Matrix.list_to_int(a_vals, n_bits=a.bits)
            'b_in': Matrix.list_to_int(b_vals, n_bits=b.bits)
        })

    :param matrix: A :class:`list` of :class:`lists<list>` of :class:`ints<int>`
        representing the data in a :class:`Matrix`.
    :param n_bits: The number of bits used to represent each element. If an element
        doesn't fit in ``n_bits``, its most significant bits will be truncated.

    :return: An :class:`int` with bitwidth ``N * n_bits``, containing the elements of
             ``matrix``, where ``N`` is the number of elements in ``matrix``.
    """
    if n_bits <= 0:
        msg = f"Number of bits per element must be positive, instead got {n_bits}"
        raise PyrtlError(msg)

    result = 0

    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            val = formatted_str_to_val(str(matrix[i][j]), "s" + str(n_bits))
            result = (result << n_bits) | val

    return result
