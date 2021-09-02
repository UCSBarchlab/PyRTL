import random
import math
import unittest

import pyrtl
import pyrtl.rtllib.matrix as Matrix


class MatrixTestBase(unittest.TestCase):

    def check_against_expected(self, result, expected_output, floored=False):
        """
        :param Matrix result: matrix that is the result of some operation we're testing
        :param list[list] expected_output: a list of lists to compare against
            the resulting matrix after simulation
        :param bool floored: needed to indicate that we're checking the result of
            a matrix subtraction, to ensure the matrix properly floored results to
            zero when needed (defaults to False)
        """
        output = pyrtl.Output(name='output')

        if isinstance(result, pyrtl.WireVector):
            output <<= result
        else:
            output <<= result.to_wirevector()

        sim = pyrtl.Simulation()
        sim.step({})

        if isinstance(result, pyrtl.WireVector):
            given_output = sim.inspect("output")
        else:
            given_output = Matrix.matrix_wv_to_list(
                sim.inspect("output"), result.rows, result.columns, result.bits
            )

        if isinstance(given_output, int):
            self.assertEqual(given_output, expected_output)
        else:
            for r in range(len(expected_output)):
                for c in range(len(expected_output[0])):
                    expected = expected_output[r][c]
                    if floored and expected < 0:
                        expected = 0
                    self.assertEqual(given_output[r][c], expected)


class TestMatrixInit(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_init_basic(self):
        self.init_int_matrix([[0]], 1, 1, 2)

    def test_init_basic_wirevector(self):
        self.init_wirevector([[0]], 1, 1, 2)

    def test_init_three_by_three(self):
        self.init_int_matrix([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_init_three_by_three_wirevector(self):
        self.init_wirevector([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_init_one_by_four(self):
        self.init_int_matrix([[0, 0, 0, 0]], 1, 4, 4)

    def test_init_one_by_four_wirevector(self):
        self.init_wirevector([[0, 0, 0, 0]], 1, 4, 4)

    def test_init_fail_int_instead_of_matrix(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix(0, 1, 1, 2)

    def test_init_fail_zero_row(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0], [0], [0], [0]], 0, 4, 4)

    def test_init_fail_zero_row_wirevector(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_wirevector([[0], [0], [0], [0]], 0, 4, 4)

    def test_init_fail_bad_number_of_rows(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0], [0]], 1, 1, 4)

    def test_init_fail_bad_number_of_columns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0, 0], [0], [0, 0]], 3, 2, 4)

    def test_init_fail_string_row(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0]], "1", 1, 2)

    def test_init_fail_negative_row(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0]], -1, 1, 2)

    def test_init_fail_zero_column(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0, 0, 0, 0]], 4, 0, 4)

    def test_init_fail_zero_column_wirevector(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_wirevector([[0, 0, 0, 0]], 4, 0, 4)

    def test_init_fail_string_column(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0]], 1, "1", 2)

    def test_init_fail_negative_column(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0]], 1, -1, 2)

    def test_init_fail_zero_bits(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0]], 1, 1, 0)

    def test_init_fail_zero_bits_wirevector(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_wirevector([[0]], 1, 1, 0)

    def test_init_fail_string_bit(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0]], 1, 1, "2")

    def test_init_fail_negative_bits(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.init_int_matrix([[0]], 1, 1, -1)

    def test_init_wirevector_mismatch(self):
        matrix_input = pyrtl.Input(1 * 1, 'matrix_input')
        with self.assertRaises(pyrtl.PyrtlError):
            _matrix = Matrix.Matrix(1, 1, 3, value=matrix_input)

    def test_init_random(self):
        rows, columns, bits = random.randint(
            1, 20), random.randint(1, 20), random.randint(1, 20)

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.init_int_matrix(matrix, rows, columns, bits)

    def test_init_random_wirevector(self):
        rows, columns, bits = random.randint(
            1, 20), random.randint(1, 20), random.randint(1, 20)

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.init_wirevector(matrix, rows, columns, bits)

    def init_wirevector(self, matrix_value, rows, columns, bits):
        matrix_input = pyrtl.Const(Matrix.list_to_int(matrix_value, bits), rows * columns * bits)
        matrix = Matrix.Matrix(rows, columns, bits, value=matrix_input)

        self.assertEqual(rows, matrix.rows)
        self.assertEqual(columns, matrix.columns)
        self.assertEqual(bits, matrix.bits)
        self.assertEqual(len(matrix), (rows * columns * bits))
        self.check_against_expected(matrix, matrix_value)

    def init_int_matrix(self, int_matrix, rows, columns, bits):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)

        self.assertEqual(rows, matrix.rows)
        self.assertEqual(columns, matrix.columns)
        self.assertEqual(bits, matrix.bits)
        self.assertEqual(len(matrix), (rows * columns * bits))
        self.check_against_expected(matrix, int_matrix)


class TestMatrixBits(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_bits_no_change(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)

        self.assertEqual(matrix.bits, 4)
        self.check_against_expected(matrix, int_matrix)

    def test_bits_basic_change_bits(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        matrix.bits = 5

        self.assertEqual(matrix.bits, 5)
        self.check_against_expected(matrix, int_matrix)

    def test_bits_basic_change_bits_trunicate(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        matrix.bits = 2
        int_matrix = [[0, 1, 2], [3, 0, 1], [2, 3, 0]]

        self.assertEqual(matrix.bits, 2)
        self.check_against_expected(matrix, int_matrix)

    def test_bits_fail_change_bits_zero(self):
        matrix = Matrix.Matrix(3, 3, 4, value=[[0, 1, 2], [3, 4, 5], [6, 7, 8]])
        with self.assertRaises(pyrtl.PyrtlError):
            matrix.bits = 0

    def test_bits_fail_change_bits_negative(self):
        matrix = Matrix.Matrix(3, 3, 4, value=[[0, 1, 2], [3, 4, 5], [6, 7, 8]])
        with self.assertRaises(pyrtl.PyrtlError):
            matrix.bits = -1

    def test_bits_fail_change_bits_string(self):
        matrix = Matrix.Matrix(3, 3, 4, value=[[0, 1, 2], [3, 4, 5], [6, 7, 8]])
        with self.assertRaises(pyrtl.PyrtlError):
            matrix.bits = "1"


class TestMatrixGetItem(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_getitem_basic_case(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 1, None), slice(0, 1, None), 0)

    def test_getitem_2_by_2_slice(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 2, None), slice(0, 2, None), [[0, 1], [3, 4]])

    def test_getitem_3_by_3_slice(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 3, None), slice(0, 3, None), [[0, 1, 2], [3, 4, 5], [6, 7, 8]])

    def test_getitem_2_3_slice(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 2, None), slice(0, 3, None), [[0, 1, 2], [3, 4, 5]])

    def test_getitem_3_2_slice(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 3, None), slice(0, 2, None), [[0, 1], [3, 4], [6, 7]])

    '''
    def test_getitem_random(self):
        x_start = random.randint(0, 2)
        x_stop = random.randint(x_start + 1, 3)

        y_start = random.randint(0, 2)
        y_stop = random.randint(y_start + 1, 3)
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(x_start, x_stop, None),
                      slice(y_start, y_stop, None), )
    '''

    def test_getitem_fail_string_rows(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix["2", 3]

    def test_getitem_fail_string_columns(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix[2, "2"]

    def test_getitem_fail_out_of_bounds_rows(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix[4, 2]

    def test_getitem_fail_out_of_bounds_row_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix[-4]

    def test_getitem_fail_out_of_bounds_rows_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix[-4, 2]

    def test_getitem_fail_out_of_bounds_columns(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix[1, 4]

    def test_getitem_fail_out_of_bounds_columns_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix[1, -4]

    def test_getitem_fail_out_of_bounds_rows_slice(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix[1:4, 1]

    def test_getitem_fail_out_of_bounds_columns_slice(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix[1, 1:4]

    def test_getitem_fail_string_column_only(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = matrix["1"]

    def get_item(self, value_array, rows, columns, bits, x_slice, y_slice, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=value_array)
        item = matrix[x_slice, y_slice]

        out_rows, out_columns = x_slice.stop - x_slice.start, y_slice.stop - y_slice.start
        if isinstance(item, Matrix.Matrix):
            self.assertEqual(out_rows, item.rows)
            self.assertEqual(out_columns, item.columns)
            self.assertEqual(bits, item.bits)
            self.assertEqual(len(item), out_rows * out_columns * bits)
        self.check_against_expected(item, expected_output)

    def test_getitem_with_tuple_indices(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[2, 0]
        self.check_against_expected(item, 6)

    def test_getitem_with_slice_indices_raw(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[slice(0, 2), slice(0, 3)]
        self.check_against_expected(item, [[0, 1, 2], [3, 4, 5]])

    def test_getitem_with_slice_indices_shorthand(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[0:2, 0:3]
        self.check_against_expected(item, [[0, 1, 2], [3, 4, 5]])

    def test_getitem_full(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[:, :]
        self.check_against_expected(item, int_matrix)

    def test_getitem_full_row(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[1]
        self.check_against_expected(item, [[3, 4, 5]])

    def test_getitem_full_rows_with_slice_front(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[:2]
        self.check_against_expected(item, [[0, 1, 2], [3, 4, 5]])

    def test_getitem_full_rows_with_slice_back(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[1:]
        self.check_against_expected(item, [[3, 4, 5], [6, 7, 8]])

    def test_getitem_negative_returns_single(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[-2:-1, -2:-1]
        self.check_against_expected(item, 4)

    def test_getitem_negative_returns_row_v1(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[-1]
        self.check_against_expected(item, [[6, 7, 8]])

    def test_getitem_negative_returns_row_v2(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[-2]
        self.check_against_expected(item, [[3, 4, 5]])

    def test_getitem_negative_returns_rows(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[-2:]
        self.check_against_expected(item, [[3, 4, 5], [6, 7, 8]])

    def test_getitem_negative_in_tuple_with_slice_returns_row_1(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[-3, :]
        self.check_against_expected(item, [[0, 1, 2]])

    def test_getitem_negative_in_tuple_with_slice_returns_row_2(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[-2, :]
        self.check_against_expected(item, [[3, 4, 5]])

    def test_getitem_negative_in_tuple_with_slice_returns_row_3(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[-1, :]
        self.check_against_expected(item, [[6, 7, 8]])

    def test_getitem_negative_in_tuple_with_slice_returns_column_1(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[:, -3]
        self.check_against_expected(item, [[0], [3], [6]])

    def test_getitem_negative_in_tuple_with_slice_returns_column_2(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[:, -2]
        self.check_against_expected(item, [[1], [4], [7]])

    def test_getitem_negative_in_tuple_with_slice_returns_column_3(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[:, -1]
        self.check_against_expected(item, [[2], [5], [8]])

    def test_getitem_negative_in_tuple_returns_single(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        item = matrix[0, -1]
        self.check_against_expected(item, 2)


class TestMatrixSetItem(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_setitem_basic_case(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 1, None), slice(0, 1, None), [[1]], [[1, 1, 2],
                                                                          [3, 4, 5],
                                                                          [6, 7, 8]])

    def test_setitem_2_by_2(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 2, None), slice(0, 2, None),
                      [[1, 0], [1, 0]], [[1, 0, 2],
                                         [1, 0, 5],
                                         [6, 7, 8]])

    def test_setitem_3_by_3(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 3, None), slice(0, 3, None),
                      [[8, 7, 6], [5, 4, 3], [2, 1, 0]], [[8, 7, 6],
                                                          [5, 4, 3],
                                                          [2, 1, 0]])

    def test_setitem_2_by_3(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 2, None), slice(0, 3, None),
                      [[8, 7, 6], [5, 4, 3]], [[8, 7, 6],
                                               [5, 4, 3],
                                               [6, 7, 8]])

    def test_setitem_3_by_2(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 3, None), slice(0, 2, None),
                      [[8, 7], [5, 4], [2, 1]], [[8, 7, 2],
                                                 [5, 4, 5],
                                                 [2, 1, 8]])

    '''
    def test_setitem_random_case(self):
        x_start = random.randint(0, 2)
        x_stop = random.randint(x_start + 1, 3)

        y_start = random.randint(0, 2)
        y_stop = random.randint(y_start + 1, 3)

        value = [[0 for _ in range(y_stop - y_start)]
                 for _ in range(x_stop - x_start)]

        for i in range(len(value)):
            for j in range(len(value[0])):
                value[i][j] = random.randint(0, 2**4-1)

        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(x_start, x_stop, None),
                      slice(y_start, y_stop, None), value)
    '''

    def test_setitem_fail_string_row(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix["2", 3] = pyrtl.Const(0)

    def test_setitem_fail_string_column(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[2, "2"] = pyrtl.Const(0)

    def test_setitem_fail_out_of_bounds_rows(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[4, 2] = pyrtl.Const(0)

    def test_setitem_fail_out_of_bounds_rows_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[-4, 2] = pyrtl.Const(0)

    def test_setitem_fail_out_of_bounds_columns(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[1, 4] = pyrtl.Const(0)

    def test_setitem_fail_out_of_bounds_columns_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[1, -4] = pyrtl.Const(0)

    def test_setitem_fail_out_of_bounds_rows_slice(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[1:4, 2] = pyrtl.Const(0, bitwidth=9)

    def test_setitem_fail_out_of_bounds_columns_slice(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[1:4, 2] = pyrtl.Const(0, bitwidth=9)

    def test_setitem_fail_string_rows_only(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix["1"] = pyrtl.Const(0, bitwidth=9)

    def test_setitem_fail_wire_for_matrix(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[1, 0:2] = pyrtl.Const(0, bitwidth=3)

    def test_setitem_fail_value_matrix_incorrect_rows(self):
        matrix = Matrix.Matrix(3, 3, 3)
        value_matrix = Matrix.Matrix(2, 1, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[0:1, 0:1] = value_matrix

    def test_setitem_fail_value_matrix_incorrect_columns(self):
        matrix = Matrix.Matrix(3, 3, 3)
        value_matrix = Matrix.Matrix(1, 2, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            matrix[0:1, 0:1] = value_matrix

    def set_item(self, int_matrix, rows, columns, bits,
                 x_slice, y_slice, value, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)
        value_matrix = Matrix.Matrix(
            x_slice.stop - x_slice.start, y_slice.stop - y_slice.start,
            bits, value=value)
        matrix[x_slice, y_slice] = value_matrix
        self.check_against_expected(matrix, expected_output)

    def test_setitem_with_tuple_indices(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        expected_output = [[0, 1, 2], [3, 4, 5], [9, 7, 8]]
        matrix[2, 0] = 9
        self.check_against_expected(matrix, expected_output)

    def test_setitem_with_slice_indices_raw(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_int_matrix = [[9, 8, 7], [6, 5, 4]]
        value_matrix = Matrix.Matrix(2, 3, 4, value=value_int_matrix)
        matrix[slice(0, 2), slice(0, 3)] = value_matrix
        expected_output = [[9, 8, 7], [6, 5, 4], [6, 7, 8]]
        self.check_against_expected(matrix, expected_output)

    def test_setitem_with_slice_indices_shorthand(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_int_matrix = [[9, 8, 7], [6, 5, 4]]
        value_matrix = Matrix.Matrix(2, 3, 4, value=value_int_matrix)
        matrix[:2, :3] = value_matrix
        expected_output = [[9, 8, 7], [6, 5, 4], [6, 7, 8]]
        self.check_against_expected(matrix, expected_output)

    def test_setitem_negative(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        matrix[-2:-1, -2:-1] = pyrtl.Const(0)
        expected_output = [[0, 1, 2], [3, 0, 5], [6, 7, 8]]
        self.check_against_expected(matrix, expected_output)

    def test_setitem_raw_int(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        matrix[-2:-1, -2:-1] = 9
        expected_output = [[0, 1, 2], [3, 9, 5], [6, 7, 8]]
        self.check_against_expected(matrix, expected_output)

    def test_setitem_full(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[8, 7, 6], [5, 4, 3], [2, 1, 0]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = Matrix.Matrix(3, 3, 4, value=value_int_matrix)
        matrix[:, :] = value_matrix
        self.check_against_expected(matrix, value_int_matrix)

    def test_setitem_full_rows_with_slice_front(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[9, 8, 7], [6, 5, 4]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = Matrix.Matrix(2, 3, 4, value=value_int_matrix)
        matrix[:2] = value_matrix
        expected_output = [[9, 8, 7], [6, 5, 4], [6, 7, 8]]
        self.check_against_expected(matrix, expected_output)

    def test_setitem_full_rows_with_slice_back(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[9, 8, 7], [6, 5, 4]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = Matrix.Matrix(2, 3, 4, value=value_int_matrix)
        matrix[1:] = value_matrix
        expected_output = [[0, 1, 2], [9, 8, 7], [6, 5, 4]]
        self.check_against_expected(matrix, expected_output)

    def test_setitem_full_row_item(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[8, 7, 6]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = Matrix.Matrix(1, 3, 4, value=value_int_matrix)
        matrix[1] = value_matrix
        expected_output = [[0, 1, 2], [8, 7, 6], [6, 7, 8]]
        self.check_against_expected(matrix, expected_output)

    def test_setitem_row_with_negative_index_v1(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[9, 8, 7]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = Matrix.Matrix(1, 3, 4, value=value_int_matrix)
        matrix[-1] = value_matrix
        expected_output = [[0, 1, 2], [3, 4, 5], [9, 8, 7]]
        self.check_against_expected(matrix, expected_output)

    def test_setitem_row_with_negative_index_v2(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[9, 8, 7]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = Matrix.Matrix(1, 3, 4, value=value_int_matrix)
        matrix[-2] = value_matrix
        expected_output = [[0, 1, 2], [9, 8, 7], [6, 7, 8]]
        self.check_against_expected(matrix, expected_output)

    def test_setitem_rows_with_negative_index_slice(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[9, 8, 7], [6, 5, 4]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = Matrix.Matrix(2, 3, 4, value=value_int_matrix)
        matrix[-2:] = value_matrix
        expected_output = [[0, 1, 2], [9, 8, 7], [6, 5, 4]]
        self.check_against_expected(matrix, expected_output)


class TestMatrixCopy(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_copy_basic(self):
        self.copy([[0]], 1, 1, 2, [[1]])

    def test_copy_three_by_three(self):
        self.copy([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                  [[1, 2, 3], [1, 2, 3], [1, 2, 3]])

    def test_copy_one_by_four(self):
        self.copy([[0, 0, 0, 0]], 1, 4, 4, [[1, 1, 1, 1]])

    def copy(self, first_value, rows, columns, bits, second_value):
        matrix = Matrix.Matrix(rows, columns, bits, value=first_value)
        change_matrix = Matrix.Matrix(rows, columns, bits, value=second_value)
        copy_matrix = matrix.copy()

        self.assertEqual(copy_matrix.rows, matrix.rows)
        self.assertEqual(copy_matrix.columns, matrix.columns)
        self.assertEqual(copy_matrix.bits, matrix.bits)
        self.assertEqual(len(copy_matrix), len(matrix))

        copy_output = pyrtl.Output(name="copy_output", bitwidth=len(copy_matrix))
        copy_output <<= copy_matrix.to_wirevector()

        matrix_output = pyrtl.Output(name="matrix_output", bitwidth=len(matrix))
        matrix_output <<= matrix.to_wirevector()

        copy_matrix[:, :] = change_matrix[:, :]

        matrix_output_1 = pyrtl.Output(name="matrix_output_1", bitwidth=len(matrix))
        matrix_output_1 <<= matrix.to_wirevector()

        copy_output_1 = pyrtl.Output(name="copy_output_1", bitwidth=len(copy_matrix))
        copy_output_1 <<= copy_matrix.to_wirevector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = Matrix.matrix_wv_to_list(sim.inspect("matrix_output"), rows, columns, bits)
        expected_output = Matrix.matrix_wv_to_list(sim.inspect("copy_output"), rows, columns, bits)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], expected_output[i][j])

        given_output = Matrix.matrix_wv_to_list(sim.inspect("matrix_output_1"),
                                                rows, columns, bits)
        expected_output = Matrix.matrix_wv_to_list(sim.inspect("copy_output_1"),
                                                   rows, columns, bits)

        for i in range(rows):
            for j in range(columns):
                self.assertNotEqual(first_value[i][j], second_value[i][j])
                self.assertNotEqual(given_output[i][j], expected_output[i][j])


class TestMatrixTranspose(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_transpose_basic(self):
        self.transpose([[0]], 1, 1, 2, [[0]])

    def test_transpose_3_by_3(self):
        self.transpose([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[0, 3, 6],
                                                                    [1, 4, 7],
                                                                    [2, 5, 8]])

    def test_transpose_1_by_4(self):
        self.transpose([[0, 1, 0, 2]], 1, 4, 4, [[0], [1], [0], [2]])

    def test_transpose_4_by_1(self):
        self.transpose([[0], [1], [0], [2]], 4, 1, 4, [[0, 1, 0, 2]])

    '''
    def test_transpose_random_case(self):
        rows, columns, bits = random.randint(
            1, 20), random.randint(1, 20), random.randint(1, 20)

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.transpose(matrix, rows, columns, bits)
    '''

    def transpose(self, int_matrix, rows, columns, bits, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)
        transpose_matrix = matrix.transpose()

        self.assertEqual(columns, transpose_matrix.rows)
        self.assertEqual(rows, transpose_matrix.columns)
        self.assertEqual(bits, transpose_matrix.bits)
        self.assertEqual(len(transpose_matrix), rows * columns * bits)
        self.check_against_expected(transpose_matrix, expected_output)


class TestMatrixReverse(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_reverse_basic(self):
        self.reverse([[0]], 1, 1, 2, [[0]])

    def test_reverse_3_by_3(self):
        self.reverse([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[8, 7, 6],
                                                                  [5, 4, 3],
                                                                  [2, 1, 0]])

    def test_reverse_1_by_4(self):
        self.reverse([[0, 1, 3, 2]], 1, 4, 4, [[2, 3, 1, 0]])

    def test_reverse_4_by_1(self):
        self.reverse([[0], [1], [3], [2]], 4, 1, 4, [[2],
                                                     [3],
                                                     [1],
                                                     [0]])

    '''
    def test_reverse_random(self):
        rows, columns, bits = random.randint(
            1, 20), random.randint(1, 20), random.randint(1, 20)

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.reverse(matrix, rows, columns, bits)
    '''

    def reverse(self, int_matrix, rows, columns, bits, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)
        reversed_matrix = reversed(matrix)

        self.assertEqual(rows, reversed_matrix.rows)
        self.assertEqual(columns, reversed_matrix.columns)
        self.assertEqual(bits, reversed_matrix.bits)
        self.assertEqual(len(reversed_matrix), rows * columns * bits)
        self.check_against_expected(reversed_matrix, expected_output)


class TestMatrixAdd(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_add_basic_case(self):
        self.add([[0]], 1, 1, 2, [[0]], 1, 1, 3, [[0]])

    def test_add_2_by_3(self):
        self.add([[0, 1, 2], [3, 4, 5]], 2, 3, 4,
                 [[0, 1, 2], [3, 4, 5]], 2, 3, 4, [[0, 2, 4],
                                                   [6, 8, 10]])

    def test_add_3_by_2(self):
        self.add([[2, 4], [5, 4], [2, 5]], 3, 2, 4,
                 [[0, 1], [3, 4], [6, 7]], 3, 2, 4, [[2, 5],
                                                     [8, 8],
                                                     [8, 12]])

    def test_add_3_by_3_same(self):
        self.add([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[0, 2, 4],
                                                              [6, 8, 10],
                                                              [12, 14, 16]])

    def test_add_3_by_3_different(self):
        self.add([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[2, 5, 5],
                                                              [8, 8, 12],
                                                              [8, 12, 9]])

    def test_add_fail_2_by_2_add_3_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.add([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1], [0, 1], [0, 1]], 2, 3, 4, [[]])

    def test_add_fail_3_by_3_add_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.add([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1, 1], [0, 1, 1]], 2, 3, 4, [[]])

    def test_add_fail_3_by_3_add_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.add([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1], [0, 1], [1, 1]], 3, 2, 4, [[]])

    def test_add_fail_add_one(self):
        first_matrix = Matrix.Matrix(1, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _result = first_matrix + 1

    '''
    def test_add_random_case(self):
        rows, columns, bits1, bits2 = random.randint(
            1, 20), random.randint(1, 20), random.randint(
                1, 20), random.randint(1, 20)

        first = [[0 for _ in range(columns)]
                 for _ in range(rows)]

        second = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                first[i][j] = random.randint(1, 2**bits1 - 1)
                second[i][j] = random.randint(1, 2**bits2 - 1)
        self.add(first, rows, columns, bits1, second, rows, columns, bits2)
    '''

    def add(self, first_int_matrix, rows1, columns1, bits1, second_int_matrix,
            rows2, columns2, bits2, expected_output):
        first_matrix = Matrix.Matrix(rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(rows2, columns2, bits2, value=second_int_matrix)
        result_matrix = first_matrix + second_matrix

        self.assertEqual(result_matrix.rows, rows1)
        self.assertEqual(result_matrix.columns, columns1)
        self.check_against_expected(result_matrix, expected_output)


class TestMatrixInplaceAdd(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_iadd_basic(self):
        self.iadd([[0]], 1, 1, 2, [[0]], 1, 1, 3, [[0]])

    def test_iadd_3_by_3_same(self):
        self.iadd([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                  [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[0, 2, 4], [6, 8, 10], [12, 14, 16]])

    def test_iadd_3_by_3_different(self):
        self.iadd([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                  [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[2, 5, 5], [8, 8, 12], [8, 12, 9]])

    def test_iadd_fail_3_by_3_add_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.iadd([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                      [[0, 1], [0, 1], [0, 1]], 2, 3, 4, [[]])

    def test_iadd_fail_3_by_3_add_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.iadd([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                      [[0, 1, 1], [0, 1, 1]], 3, 2, 4, [[]])

    '''
    def test_iadd_random_case(self):
        rows, columns, bits1, bits2 = random.randint(
            1, 20), random.randint(1, 20), random.randint(
                1, 20), random.randint(1, 20)

        first = [[0 for _ in range(columns)]
                 for _ in range(rows)]

        second = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                first[i][j] = random.randint(1, 2**bits1 - 1)
                second[i][j] = random.randint(1, 2**bits2 - 1)

        self.iadd(first, rows, columns, bits1, second, rows, columns, bits2)
    '''

    def iadd(self, first_int_matrix, rows1, columns1, bits1, second_int_matrix,
             rows2, columns2, bits2, expected_output):
        first_matrix = Matrix.Matrix(rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(rows2, columns2, bits2, value=second_int_matrix)
        first_matrix += second_matrix

        self.assertEqual(first_matrix.rows, rows1)
        self.assertEqual(first_matrix.columns, columns1)
        self.check_against_expected(first_matrix, expected_output)


class TestMatrixSub(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_sub_basic(self):
        self.sub([[0]], 1, 1, 2, [[0]], 1, 1, 3, [[0]])

    def test_sub_3_by_3_same(self):
        self.sub([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[0, 0, 0], [0, 0, 0], [0, 0, 0]])

    def test_sub_3_by_3_different(self):
        self.sub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[2, 3, 1], [2, 0, 2], [-4, -2, -7]])

    def test_sub_fail_int(self):
        first_matrix = Matrix.Matrix(1, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _result = first_matrix - 1

    def test_sub_fail_3_by_3_sub_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.sub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1], [0, 1], [0, 1]], 3, 2, 4, [[]])

    def test_sub_fail_3_by_3_sub_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.sub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1, 1], [0, 1, 1]], 2, 3, 4, [[]])

    '''
    def test_sub_random_case(self):
        rows, columns, bits1, bits2 = random.randint(
            1, 20), random.randint(1, 20), random.randint(
                1, 20), random.randint(1, 20)

        first = [[0 for _ in range(columns)]
                 for _ in range(rows)]

        second = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                first[i][j] = random.randint(1, 2**bits1 - 1)
                second[i][j] = random.randint(1, 2**bits2 - 1)
        self.sub(first, rows, columns, bits1, second, rows, columns, bits2)
    '''

    def sub(self, first_int_matrix, rows1, columns1, bits1, second_int_matrix,
            rows2, columns2, bits2, expected_output):
        first_matrix = Matrix.Matrix(rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(rows2, columns2, bits2, value=second_int_matrix)
        result_matrix = first_matrix - second_matrix

        self.assertEqual(result_matrix.rows, rows1)
        self.assertEqual(result_matrix.columns, columns1)
        self.check_against_expected(result_matrix, expected_output, floored=True)


class TestMatrixInplaceSub(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_isub_basic(self):
        self.isub([[0]], 1, 1, 2, [[0]], 1, 1, 3, [[0]])

    def test_isub_3_by_3_same(self):
        self.isub([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                  [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[0, 0, 0], [0, 0, 0], [0, 0, 0]])

    def test_isub_3_by_3_different_positive_result(self):
        self.isub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                  [[0, 1, 2], [3, 4, 5], [1, 4, 0]], 3, 3, 4, [[2, 3, 1], [2, 0, 2], [1, 1, 1]])

    def test_isub_fail_3_by_3_sub_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.isub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                      [[0, 1], [0, 1], [0, 1]], 2, 3, 4, [[]])

    def test_isub_fail_3_by_3_sub_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.isub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                      [[0, 1, 1], [0, 1, 1]], 3, 2, 4, [[]])

    '''
    def test_isub_random_case(self):
        rows, columns, bits1 = random.randint(
            1, 20), random.randint(1, 20), random.randint(
                1, 20)

        first = [[0 for _ in range(columns)]
                 for _ in range(rows)]

        second = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                first_num, second_num = random.randint(
                    1, 2**bits1 - 1), random.randint(1, 2**bits1 - 1)
                if first_num > second_num:
                    first[i][j] = first_num
                    second[i][j] = second_num
                else:
                    first[i][j] = second_num
                    second[i][j] = first_num

        self.isub(first, rows, columns, bits1, second, rows, columns, bits1)
    '''

    def isub(self, first_int_matrix, rows1, columns1, bits1, second_int_matrix,
             rows2, columns2, bits2, expected_output):
        first_matrix = Matrix.Matrix(rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(rows2, columns2, bits2, value=second_int_matrix)
        first_matrix -= second_matrix

        self.assertEqual(first_matrix.rows, rows1)
        self.assertEqual(first_matrix.columns, columns1)
        self.check_against_expected(first_matrix, expected_output)


class TestMatrixMultiply(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_element_wise_multiply_basic(self):
        self.element_wise_multiply([[0]], 1, 1, 2, [[0]], 1, 1, 3, [[0]])

    def test_element_wise_multiply_2_by_3(self):
        self.element_wise_multiply([[2, 4, 3], [5, 4, 7]], 2, 3, 4,
                                   [[0, 1, 2], [3, 4, 5]], 2, 3, 4, [[0, 4, 6],
                                                                     [15, 16, 35]])

    def test_element_wise_multiply_3_by_2(self):
        self.element_wise_multiply([[2, 4], [5, 7], [2, 5]], 3, 2, 4,
                                   [[0, 2], [3, 4], [6, 7]], 3, 2, 4, [[0, 8],
                                                                       [15, 28],
                                                                       [12, 35]])

    def test_element_wise_multiply_3_by_3_same(self):
        self.element_wise_multiply([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                                   [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[0, 1, 4],
                                                                                [9, 16, 25],
                                                                                [36, 49, 64]])

    def test_element_wise_multiply_3_by_3_different(self):
        self.element_wise_multiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                                   [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[0, 4, 6],
                                                                                [15, 16, 35],
                                                                                [12, 35, 8]])

    def test_element_wise_multiply_fail_3_by_3_multiply_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_multiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                                       [[0, 1], [0, 1], [0, 1]], 3, 2, 4, [[]])

    def test_element_wise_multiply_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_multiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                                       [[0, 1, 1], [0, 1, 1]], 2, 3, 4, [[]])

    '''
    def test_element_wise_multiply_random_case(self):
        rows, columns, bits1, bits2 = random.randint(
            1, 10), random.randint(1, 10), random.randint(
                1, 10), random.randint(1, 10)

        first = [[0 for _ in range(columns)]
                 for _ in range(rows)]

        second = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                first[i][j] = random.randint(1, 2**bits1 - 1)
                second[i][j] = random.randint(1, 2**bits2 - 1)
        self.element_wise_multiply(
            first, rows, columns, bits1, second, rows, columns, bits2)
    '''

    def element_wise_multiply(self, first_int_matrix, rows1, columns1, bits1,
                              second_int_matrix, rows2, columns2, bits2, expected_output):
        first_matrix = Matrix.Matrix(rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(rows2, columns2, bits2, value=second_int_matrix)
        result_matrix = first_matrix * second_matrix

        self.assertEqual(result_matrix.rows, rows1)
        self.assertEqual(result_matrix.columns, columns1)
        self.check_against_expected(result_matrix, expected_output)

    def test_multiply_scalar_basic(self):
        self.multiply_number([[2]], 1, 1, 3, 1, [[2]])

    def test_multiply_scalar_basic_zero(self):
        self.multiply_number([[1]], 1, 1, 2, 0, [[0]])

    def test_multiply_scalar_basic_one(self):
        self.multiply_number([[1]], 1, 1, 2, 1, [[1]])

    def test_multiply_scalar_3_by_3(self):
        self.multiply_number([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 3, [[0, 3, 6],
                                                                             [9, 12, 15],
                                                                             [18, 21, 24]])

    def test_multiply_scalar_4_by_1(self):
        self.multiply_number([[0, 1, 0, 2]], 1, 4, 4, 5, [[0, 5, 0, 10]])

    def test_multiply_scalar_1_by_4(self):
        self.multiply_number([[0], [1], [0], [2]], 4, 1,
                             4, 5, [[0], [5], [0], [10]])

    '''
    def test_multiply_scalar_random_case(self):
        rows, columns, bits, number = random.randint(
            1, 10), random.randint(1, 10), random.randint(
                1, 10), random.randint(1, 10)

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)
        self.multiply_number(matrix, rows, columns, bits, number)
    '''

    def multiply_number(self, int_matrix, rows, columns, bits, number, expected_output):
        first_matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)
        bits = int(math.log(number, 2)) + 1 if number != 0 else 1
        result_matrix = first_matrix * pyrtl.Const(number, bits)

        self.assertEqual(result_matrix.rows, rows)
        self.assertEqual(result_matrix.columns, columns)
        self.check_against_expected(result_matrix, expected_output)

    def test_multiply_fail_int(self):
        first_matrix = Matrix.Matrix(3, 2, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _result = first_matrix * 1


class TestMatrixInplaceMultiply(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_element_wise_imultiply_basic(self):
        self.element_wise_imultiply([[0]], 1, 1, 2, [[0]], 1, 1, 3, [[0]])

    def test_element_wise_imultiply_3_by_3_same(self):
        self.element_wise_imultiply([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                                    [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[0, 1, 4],
                                                                                 [9, 16, 25],
                                                                                 [36, 49, 64]])

    def test_element_wise_imultiply_3_by_3_different(self):
        self.element_wise_imultiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                                    [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[0, 4, 6],
                                                                                 [15, 16, 35],
                                                                                 [12, 35, 8]])

    def test_element_wise_imultiply_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_imultiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                                        [[0, 1], [0, 1], [0, 1]], 2, 3, 4, [[]])

    def test_element_wise_imultiply_fail_3_by_3_multiply_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_imultiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                                        [[0, 1, 1], [0, 1, 1]], 3, 2, 4, [[]])

    '''
    def test_element_wise_imultiply_random_case(self):
        rows, columns, bits1, bits2 = random.randint(
            1, 10), random.randint(1, 10), random.randint(
                1, 10), random.randint(1, 10)

        first = [[0 for _ in range(columns)]
                 for _ in range(rows)]

        second = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                first[i][j] = random.randint(1, 2**bits1 - 1)
                second[i][j] = random.randint(1, 2**bits2 - 1)
        self.element_wise_imultiply(
            first, rows, columns, bits1, second, rows, columns, bits2)
    '''

    def element_wise_imultiply(self, first_int_matrix, rows1, columns1, bits1,
                               second_int_matrix, rows2, columns2, bits2, expected_output):
        first_matrix = Matrix.Matrix(rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(rows2, columns2, bits2, value=second_int_matrix)
        first_matrix *= second_matrix

        self.assertEqual(first_matrix.rows, rows1)
        self.assertEqual(first_matrix.columns, columns1)
        self.check_against_expected(first_matrix, expected_output)


class TestMatrixMatrixMultiply(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_mat_mul_basic(self):
        self.matmul([[0]], 1, 1, 2, [[0]], 1, 1, 3, [[0]])

    def test_mat_mul_1_by_2_multiply_2_by_1(self):
        self.matmul([[1, 2]], 1, 2, 2, [[1], [2]], 2, 1, 3, [[5]])

    def test_mat_mul_3_by_3_multiply_3_by_3_same(self):
        self.matmul([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                    [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[15, 18, 21],
                                                                 [42, 54, 66],
                                                                 [69, 90, 111]])

    def test_mat_mul_3_by_3_multiply_3_by_3_different(self):
        self.matmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                    [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[30, 39, 48],
                                                                 [54, 70, 86],
                                                                 [21, 29, 37]])

    def test_mat_mul_fail_int(self):
        first_matrix = Matrix.Matrix(3, 2, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _result = first_matrix.__matmul__(1)

    def test_mat_mul_fail_3_by_3_multiply_2_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                        [[0, 1], [0, 1], [0, 1]], 2, 3, 4, [[]])

    def test_mat_mul_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                        [[0, 1, 1], [0, 1, 1]], 2, 3, 4, [[]])

    def test_mat_mul_fail_3_by_2_multiply_3_by_2(self):
        first_matrix = Matrix.Matrix(3, 2, 3)
        second_matrix = Matrix.Matrix(3, 2, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _result = first_matrix.__matmul__(second_matrix)

    '''
    def test_mat_mul_random_case(self):
        rows, columns1, columns2, bits1, bits2 = random.randint(
            1, 5), random.randint(1, 5), random.randint(
                1, 5), random.randint(1, 5), random.randint(1, 5)

        first = [[0 for _ in range(columns1)]
                 for _ in range(rows)]

        second = [[0 for _ in range(columns2)]
                  for _ in range(columns1)]

        for i in range(rows):
            for j in range(columns1):
                first[i][j] = random.randint(1, 2**bits1 - 1)
        for i in range(columns1):
            for j in range(columns2):
                second[i][j] = random.randint(1, 2**bits2 - 1)

        self.matmul(first, rows, columns1, bits1,
                    second, columns1, columns2, bits2)
    '''

    def matmul(self, first_int_matrix, rows1, columns1, bits1,
               second_int_matrix, rows2, columns2, bits2, expected_output):
        first_matrix = Matrix.Matrix(rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(rows2, columns2, bits2, value=second_int_matrix)
        result_matrix = first_matrix.__matmul__(second_matrix)

        self.assertEqual(result_matrix.rows, rows1)
        self.assertEqual(result_matrix.columns, columns2)
        self.check_against_expected(result_matrix, expected_output)


class TestMatrixInplaceMatrixMultiply(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_imat_mul_basic(self):
        self.imatmul([[0]], 1, 1, 2, [[0]], 1, 1, 3, [[0]])

    def test_imat_mul_1_by_2_multiply_2_by_1(self):
        self.imatmul([[1, 2]], 1, 2, 2, [[1], [2]], 2, 1, 3, [[5]])

    def test_imat_mul_3_by_3_multiply_3_by_3_same(self):
        self.imatmul([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                     [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[15, 18, 21],
                                                                  [42, 54, 66],
                                                                  [69, 90, 111]])

    def test_imat_mul_3_by_3_multiply_3_by_3_different(self):
        self.imatmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[30, 39, 48],
                                                                  [54, 70, 86],
                                                                  [21, 29, 37]])

    def test_imat_mul_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.imatmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                         [[0, 1], [0, 1], [0, 1]], 2, 3, 4, [[]])

    def test_imat_mul_fail_3_by_3_multiply_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.imatmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                         [[0, 1, 1], [0, 1, 1]], 3, 2, 4, [[]])

    '''
    def test_imat_mul_random_case(self):
        rows, columns1, columns2, bits1, bits2 = random.randint(
            1, 5), random.randint(1, 5), random.randint(
                1, 5), random.randint(1, 5), random.randint(1, 5)

        first = [[0 for _ in range(columns1)]
                 for _ in range(rows)]

        second = [[0 for _ in range(columns2)]
                  for _ in range(columns1)]

        for i in range(rows):
            for j in range(columns1):
                first[i][j] = random.randint(1, 2**bits1 - 1)
        for i in range(columns1):
            for j in range(columns2):
                second[i][j] = random.randint(1, 2**bits2 - 1)

        self.imatmul(first, rows, columns1, bits1,
                     second, columns1, columns2, bits2)
    '''

    def imatmul(self, first_int_matrix, rows1, columns1, bits1,
                second_int_matrix, rows2, columns2, bits2, expected_output):
        first_matrix = Matrix.Matrix(rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(rows2, columns2, bits2, value=second_int_matrix)
        first_matrix.__imatmul__(second_matrix)

        self.assertEqual(first_matrix.rows, rows1)
        self.assertEqual(first_matrix.columns, columns2)
        self.check_against_expected(first_matrix, expected_output)


class TestMatrixMatrixPower(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_matrix_power_3_by_3_power_0(self):
        self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]],
                          3, 3, 4, 0, [[1, 0, 0],
                                       [0, 1, 0],
                                       [0, 0, 1]])

    def test_matrix_power_3_by_3_power_1(self):
        self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]],
                          3, 3, 4, 1, [[0, 1, 2],
                                       [3, 4, 5],
                                       [6, 7, 8]])

    def test_matrix_power_3_by_3_power_2(self):
        self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 2, [[15, 18, 21],
                                                                          [42, 54, 66],
                                                                          [69, 90, 111]])

    def test_matrix_power_fail_nonsquare(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matrix_power([[0, 0, 0, 0]], 1, 4, 4, 3, [[]])

    def test_matrix_power_fail_string(self):
        first_matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _result = first_matrix ** "1"

    def test_matrix_power_fail_negative_power(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, -1, [[]])

    '''
    def test_matrix_power_random_case(self):
        self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]],
                          3, 3, 4, random.randint(0, 2))
    '''

    def matrix_power(self, int_matrix, rows, columns, bits, exp, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)
        result_matrix = matrix ** exp
        self.check_against_expected(result_matrix, expected_output)


class TestMatrixInplaceMatrixPower(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_imatrix_power_3_by_3_power_0(self):
        self.imatrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0, [[1, 0, 0],
                                                                           [0, 1, 0],
                                                                           [0, 0, 1]])

    def test_imatrix_power_3_by_3_power_1(self):
        self.imatrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1, [[0, 1, 2],
                                                                           [3, 4, 5],
                                                                           [6, 7, 8]])

    def test_imatrix_power_3_by_3_power_2(self):
        self.imatrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 2, [[15, 18, 21],
                                                                           [42, 54, 66],
                                                                           [69, 90, 111]])

    def imatrix_power(self, int_matrix, rows, columns, bits, exp, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)
        matrix **= exp
        self.check_against_expected(matrix, expected_output)


class TestMultiply(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_multiply_scalar(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        first_matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        result_matrix = Matrix.multiply(first_matrix, pyrtl.Const(3))
        expected_output = [[0, 3, 6], [9, 12, 15], [18, 21, 24]]

        self.assertEqual(result_matrix.rows, 3)
        self.assertEqual(result_matrix.columns, 3)
        self.check_against_expected(result_matrix, expected_output)

    def test_multiply_matrix(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        first_matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        second_matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        result_matrix = Matrix.multiply(first_matrix, second_matrix)
        expected_output = [[0, 1, 4], [9, 16, 25], [36, 49, 64]]

        self.assertEqual(result_matrix.rows, 3)
        self.assertEqual(result_matrix.columns, 3)
        self.check_against_expected(result_matrix, expected_output)

    def test_multiply_fail_string(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        second_matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        with self.assertRaises(pyrtl.PyrtlError):
            _result_matrix = Matrix.multiply(1, second_matrix)


class TestReshape(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def check_reshape(self, original, rows, columns, shape, expected, order='C'):
        matrix = Matrix.Matrix(rows, columns, 4, value=original)
        reshaped = matrix.reshape(shape, order=order)
        self.check_against_expected(reshaped, expected)

    def test_reshape_negative_one_shape(self):
        self.check_reshape([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4, -1,
                           [[0, 1, 2, 3, 4, 5, 6, 7]])

    def test_reshape_single_int_shape(self):
        self.check_reshape([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4, 8,
                           [[0, 1, 2, 3, 4, 5, 6, 7]])

    def test_reshape_normal_tuple_shape(self):
        self.check_reshape([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4, (1, 8),
                           [[0, 1, 2, 3, 4, 5, 6, 7]])

    def test_reshape_tuple_with_negative_one_shape(self):
        self.check_reshape([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4, (1, -1),
                           [[0, 1, 2, 3, 4, 5, 6, 7]])

    def test_reshape_varargs_shape(self):
        matrix = Matrix.Matrix(2, 4, 4, value=[[0, 1, 2, 3], [4, 5, 6, 7]])
        reshaped = matrix.reshape(1, 8)
        self.check_against_expected(reshaped, [[0, 1, 2, 3, 4, 5, 6, 7]])

    def test_reshape_nonsquare_tuple_shape_1(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (2, 6),
                           [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11]])

    def test_reshape_nonsquare_tuple_shape_2(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (6, 2),
                           [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]])

    def test_reshape_nonsquare_tuple_shape_3(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (3, 4),
                           [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]])

    def test_reshape_nonsquare_tuple_shape_4(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5]], 2, 3, (3, 2),
                           [[0, 1], [2, 3], [4, 5]])

    def test_reshape_nonsquare_tuple_shape_5(self):
        self.check_reshape([[0, 1, 2]], 1, 3, (3, 1),
                           [[0], [1], [2]])

    def test_reshape_nonsquare_int_shape(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, 12,
                           [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]])

    def test_reshape_nonsquare_negative_one_shape(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, -1,
                           [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]])

    def test_reshape_nonsquare_tuple_with_negative_one_shape_1(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (-1, 12),
                           [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]])

    def test_reshape_nonsquare_tuple_with_negative_one_shape_2(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (12, -1),
                           [[0], [1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11]])

    def test_reshape_nonsquare_incomplete_tuple_shape(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (12,),
                           [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]])

    def test_reshape_nonsquare_incomplete_tuple_with_negative_one_shape(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (-1,),
                           [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]])

    def test_reshape_negative_one_shape_column_order(self):
        self.check_reshape([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4, -1,
                           [[0, 4, 1, 5, 2, 6, 3, 7]], order='F')

    def test_reshape_single_int_shape_column_order(self):
        self.check_reshape([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4, 8,
                           [[0, 4, 1, 5, 2, 6, 3, 7]], order='F')

    def test_reshape_normal_tuple_shape_column_order(self):
        self.check_reshape([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4, (1, 8),
                           [[0, 4, 1, 5, 2, 6, 3, 7]], order='F')

    def test_reshape_tuple_with_negative_one_shape_column_order(self):
        self.check_reshape([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4, (1, -1),
                           [[0, 4, 1, 5, 2, 6, 3, 7]], order='F')

    def test_reshape_varargs_shape_column_order(self):
        matrix = Matrix.Matrix(2, 4, 4, value=[[0, 1, 2, 3], [4, 5, 6, 7]])
        reshaped = matrix.reshape(1, 8, order='F')
        self.check_against_expected(reshaped, [[0, 4, 1, 5, 2, 6, 3, 7]])

    def test_reshape_nonsquare_tuple_shape_column_order_1(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (2, 6),
                           [[0, 6, 1, 7, 2, 8], [3, 9, 4, 10, 5, 11]], order='F')

    def test_reshape_nonsquare_tuple_shape_column_order_2(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (6, 2),
                           [[0, 7], [3, 10], [6, 2], [9, 5], [1, 8], [4, 11]], order='F')

    def test_reshape_nonsquare_tuple_shape_column_order_3(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (3, 4),
                           [[0, 9, 7, 5], [3, 1, 10, 8], [6, 4, 2, 11]], order='F')

    def test_reshape_nonsquare_tuple_shape_column_order_4(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5]], 2, 3, (3, 2),
                           [[0, 4], [3, 2], [1, 5]], order='F')

    def test_reshape_nonsquare_tuple_shape_column_order_5(self):
        self.check_reshape([[0, 1, 2]], 1, 3, (3, 1),
                           [[0], [1], [2]], order='F')

    def test_reshape_nonsquare_int_shape_column_order(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, 12,
                           [[0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11]], order='F')

    def test_reshape_nonsquare_negative_one_shape_column_order(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, -1,
                           [[0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11]], order='F')

    def test_reshape_nonsquare_tuple_with_negative_one_shape_1_column_order(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (-1, 12),
                           [[0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11]], order='F')

    def test_reshape_nonsquare_tuple_with_negative_one_shape_2_column_order(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (12, -1),
                           [[0], [3], [6], [9], [1], [4], [7], [10], [2], [5], [8], [11]],
                           order='F')

    def test_reshape_nonsquare_incomplete_tuple_shape_column_order(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (12,),
                           [[0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11]], order='F')

    def test_reshape_nonsquare_incomplete_tuple_with_negative_one_shape_column_order(self):
        self.check_reshape([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], 4, 3, (-1,),
                           [[0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11]], order='F')

    def check_raises_bad_shape(self, shape, order='C'):
        matrix = Matrix.Matrix(2, 3, 4, value=[[0, 1, 2], [3, 4, 5]])
        with self.assertRaises(pyrtl.PyrtlError):
            matrix.reshape(shape, order=order)

    def test_reshape_bad_tuple_shape_1(self):
        self.check_raises_bad_shape((4,))

    def test_reshape_bad_tuple_shape_2(self):
        self.check_raises_bad_shape((1, 6, 12))

    def test_reshape_bad_tuple_shape_3(self):
        self.check_raises_bad_shape((1, 'bad'))

    def test_reshape_bad_tuple_shape_4(self):
        self.check_raises_bad_shape('bad')

    def test_reshape_bad_tuple_shape_5(self):
        self.check_raises_bad_shape((-1, -1))

    def test_reshape_bad_tuple_shape_count(self):
        self.check_raises_bad_shape((1, 7))

    def test_reshape_bad_tuple_shape_order(self):
        self.check_raises_bad_shape((1, 6), order='Z')


class TestFlatten(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def check_flattened(self, original, rows, columns, expected, order='C'):
        matrix = Matrix.Matrix(rows, columns, 4, value=original)
        flattened = matrix.flatten(order)
        self.check_against_expected(flattened, expected)

    def test_flatten_row_wise(self):
        self.check_flattened([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3,
                             [[0, 1, 2, 3, 4, 5, 6, 7, 8]])

    def test_flatten_row_wise_nonsquare_1(self):
        self.check_flattened([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4,
                             [[0, 1, 2, 3, 4, 5, 6, 7]])

    def test_flatten_row_wise_nonsquare_2(self):
        self.check_flattened([[0], [1], [2], [3]], 4, 1,
                             [[0, 1, 2, 3]])

    def test_flatten_row_wise_nonsquare_3(self):
        self.check_flattened([[0, 1, 2, 3, 4, 5, 6, 7]], 1, 8,
                             [[0, 1, 2, 3, 4, 5, 6, 7]])

    def test_flatten_column_wise(self):
        self.check_flattened([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3,
                             [[0, 3, 6, 1, 4, 7, 2, 5, 8]], order='F')

    def test_flatten_column_wise_nonsquare_1(self):
        self.check_flattened([[0, 1, 2, 3], [4, 5, 6, 7]], 2, 4,
                             [[0, 4, 1, 5, 2, 6, 3, 7]], order='F')

    def test_flatten_column_wise_nonsquare_2(self):
        self.check_flattened([[0], [1], [2], [3]], 4, 1,
                             [[0, 1, 2, 3]], order='F')

    def test_flatten_column_wise_nonsquare_3(self):
        self.check_flattened([[0, 1, 2, 3, 4, 5, 6, 7]], 1, 8,
                             [[0, 1, 2, 3, 4, 5, 6, 7]], order='F')

    def test_flatten_invalid_order(self):
        value = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=value)
        with self.assertRaises(pyrtl.PyrtlError):
            _flattened = matrix.flatten(order='Z')


class TestPut(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def check_put(self, original, rows, columns, ind, v, expected, mode='raise'):
        matrix = Matrix.Matrix(rows, columns, 4, value=original)
        matrix.put(ind, v, mode=mode)
        self.check_against_expected(matrix, expected)

    def test_put_indices_list_values_1(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, [0, 2], [12, 13],
                       [[12, 1, 13], [3, 4, 5]])

    def test_put_indices_list_values_2(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, [-1, 2, 3], [12, 13, 15],
                       [[0, 1, 13], [15, 4, 12]])

    def test_put_indices_tuple_values(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, [-1, 2, 3], (12, 13, 15),
                       [[0, 1, 13], [15, 4, 12]])

    def test_put_tuple_indices(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, (-1, 2, 3), [12, 13, 15],
                       [[0, 1, 13], [15, 4, 12]])

    def test_put_matrix(self):
        v = Matrix.Matrix(1, 3, 4, value=[[12, 13, 15]])
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, [2, 3, 4], v,
                       [[0, 1, 12], [13, 15, 5]])

    def test_put_indices_list_repeat_v_1(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, [-1, 2, 3], [12],
                       [[0, 1, 12], [12, 4, 12]])

    def test_put_indices_list_repeat_v_2(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, [-1, 2, 3], 12,
                       [[0, 1, 12], [12, 4, 12]])

    def test_put_indices_negative(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, -4, 12,
                       [[0, 1, 12], [3, 4, 5]])

    def test_put_empty(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, [0, 1], [],
                       [[0, 1, 2], [3, 4, 5]])

    def test_put_indices_raise_1(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, 22, 12,
                           [[0, 1, 2], [3, 4, 12]])

    def test_put_indices_raise_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, -22, 12,
                           [[12, 1, 2], [3, 4, 5]])

    def test_put_indices_wrap_1(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, 22, 12,
                       [[0, 1, 2], [3, 12, 5]], mode='wrap')

    def test_put_indices_wrap_2(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, -22, 12,
                       [[0, 1, 12], [3, 4, 5]], mode='wrap')

    def test_put_indices_clip_1(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, 22, 12,
                       [[0, 1, 2], [3, 4, 12]], mode='clip')

    def test_put_indices_clip_2(self):
        self.check_put([[0, 1, 2], [3, 4, 5]], 2, 3, -22, 12,
                       [[12, 1, 2], [3, 4, 5]], mode='clip')


class TestSum(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_sum_basic(self):
        self.sum([[0]], 1, 1, 2, None, 0)

    def test_sum_basic_column(self):
        self.sum([[0]], 1, 1, 2, 0, [[0]])

    def test_sum_basic_row(self):
        self.sum([[0]], 1, 1, 2, 1, [[0]])

    def test_sum_3_by_3(self):
        self.sum([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, None, 36)

    def test_sum_3_by_3_column(self):
        self.sum([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0, [[9, 12, 15]])

    def test_sum_3_by_3_row(self):
        self.sum([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1, [[3, 12, 21]])

    def test_sum_4_by_1(self):
        self.sum([[0], [1], [0], [1]], 4, 1, 4, None, 2)

    def test_sum_4_by_1_column(self):
        self.sum([[0], [1], [0], [1]], 4, 1, 4, 0, [[2]])

    def test_sum_4_by_1_row(self):
        self.sum([[0], [1], [0], [1]], 4, 1, 4, 1, [[0, 1, 0, 1]])

    def test_sum_1_by_4(self):
        self.sum([[0, 1, 0, 1]], 1, 4, 4, None, 2)

    def test_sum_1_by_4_column(self):
        self.sum([[0, 1, 0, 1]], 1, 4, 4, 0, [[0, 1, 0, 1]])

    def test_sum_1_by_4_row(self):
        self.sum([[0, 1, 0, 1]], 1, 4, 4, 1, [[2]])

    '''
    def test_sum_random_case(self):
        rows, columns, bits, axis = random.randint(
            1, 5), random.randint(1, 5), random.randint(1, 5), random.randint(0, 2)
        if axis == 2:
            axis = None

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.sum(matrix, rows, columns, bits, axis)
    '''

    def test_sum_wire(self):
        sum_wire = Matrix.sum(pyrtl.Const(3))
        self.check_against_expected(sum_wire, 3)

    def test_sum_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.sum("1", 0)

    def test_sum_fail_negative_axis(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.sum(matrix, -1)

    def test_sum_fail_axis_out_of_bounds(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.sum(matrix, 2)

    def test_sum_fail_string_axis(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.sum(matrix, "0")

    def test_sum_fail_string_bits(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.sum(matrix, axis=0, bits="0")

    def test_sum_fail_negative_bits(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.sum(matrix, axis=0, bits=-1)

    def test_sum_fail_zero_bits(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.sum(matrix, axis=0, bits=0)

    def sum(self, int_matrix, rows, columns, bits, axis, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix, max_bits=bits * rows)
        result = Matrix.sum(matrix, axis=axis, bits=bits * max(rows, columns))
        self.check_against_expected(result, expected_output)


class TestMin(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_min_basic(self):
        self.min([[0]], 1, 1, 2, None, 0)

    def test_min_basic_column(self):
        self.min([[0]], 1, 1, 2, 0, [[0]])

    def test_min_basic_row(self):
        self.min([[0]], 1, 1, 2, 1, [[0]])

    def test_min_3_by_3(self):
        self.min([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, None, 0)

    def test_min_3_by_3_column(self):
        self.min([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0, [[0, 1, 2]])

    def test_min_3_by_3_row(self):
        self.min([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1, [[0, 3, 6]])

    def test_min_4_by_1(self):
        self.min([[0], [1], [0], [1]], 4, 1, 4, None, 0)

    def test_min_4_by_1_column(self):
        self.min([[0], [1], [0], [1]], 4, 1, 4, 0, [[0]])

    def test_min_4_by_1_row(self):
        self.min([[0], [1], [0], [1]], 4, 1, 4, 1, [[0, 1, 0, 1]])

    def test_min_1_by_4(self):
        self.min([[0, 1, 0, 1]], 1, 4, 4, None, 0)

    def test_min_1_by_4_column(self):
        self.min([[0, 1, 0, 1]], 1, 4, 4, 0, [[0, 1, 0, 1]])

    def test_min_1_by_4_row(self):
        self.min([[0, 1, 0, 1]], 1, 4, 4, 1, [[0]])

    '''
    def test_min_random_case(self):
        rows, columns, bits, axis = random.randint(
            1, 5), random.randint(1, 5), random.randint(1, 5), random.randint(0, 2)
        if axis == 2:
            axis = None

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.min(matrix, rows, columns, bits, axis)
    '''

    def test_min_wire(self):
        min_wire = Matrix.min(pyrtl.Const(3))
        self.check_against_expected(min_wire, 3)

    def test_min_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.min("1", 0)

    def test_min_fail_axis_out_of_bounds(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.min(matrix, 4)

    def test_min_fail_axis_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.min(matrix, -1)

    def test_min_fail_axis_string(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.min(matrix, "0")

    def test_min_fail_bits_string(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.min(matrix, axis=0, bits="1")

    def test_min_fail_bits_zero(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.min(matrix, axis=0, bits=0)

    def test_min_fail_bits_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.min(matrix, axis=0, bits=-2)

    def min(self, int_matrix, rows, columns, bits, axis, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix, max_bits=bits * rows)
        result = Matrix.min(matrix, axis=axis, bits=bits * max(rows, columns))
        self.check_against_expected(result, expected_output)


class TestMax(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_max_basic(self):
        self.max([[0]], 1, 1, 2, None, 0)

    def test_max_basic_columns(self):
        self.max([[0]], 1, 1, 2, 0, [[0]])

    def test_max_basic_rows(self):
        self.max([[0]], 1, 1, 2, 1, [[0]])

    def test_max_3_by_3(self):
        self.max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, None, 8)

    def test_max_3_by_3_columns(self):
        self.max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0, [[6, 7, 8]])

    def test_max_3_by_3_rows(self):
        self.max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1, [[2, 5, 8]])

    def test_max_4_by_1(self):
        self.max([[0], [1], [0], [1]], 4, 1, 4, None, 1)

    def test_max_4_by_1_columns(self):
        self.max([[0], [1], [0], [1]], 4, 1, 4, 0, [[1]])

    def test_max_4_by_1_rows(self):
        self.max([[0], [1], [0], [1]], 4, 1, 4, 1, [[0, 1, 0, 1]])

    def test_max_1_by_4(self):
        self.max([[0, 1, 0, 1]], 1, 4, 4, None, 1)

    def test_max_1_by_4_columns(self):
        self.max([[0, 1, 0, 1]], 1, 4, 4, 0, [[0, 1, 0, 1]])

    def test_max_1_by_4_rows(self):
        self.max([[0, 1, 0, 1]], 1, 4, 4, 1, [[1]])

    '''
    def test_max_random_case(self):
        rows, columns, bits, axis = random.randint(
            1, 5), random.randint(1, 5), random.randint(1, 5), random.randint(0, 2)
        if axis == 2:
            axis = None

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.max(matrix, rows, columns, bits, axis)
    '''

    def test_max_wire(self):
        max_wire = Matrix.max(pyrtl.Const(3))
        self.check_against_expected(max_wire, 3)

    def test_max_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.max("1", 0)

    def test_max_fail_axis_out_of_bounds(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.max(matrix, 4)

    def test_max_fail_axis_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.max(matrix, -1)

    def test_max_fail_axis_string(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.max(matrix, "0")

    def test_max_fail_bits_string(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.max(matrix, axis=0, bits="1")

    def test_max_fail_bits_zero(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.max(matrix, axis=0, bits=0)

    def test_max_fail_bits_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.max(matrix, axis=0, bits=-1)

    def max(self, int_matrix, rows, columns, bits, axis, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix, max_bits=bits * rows)
        result = Matrix.max(matrix, axis=axis, bits=bits * max(rows, columns))
        self.check_against_expected(result, expected_output)


class TestArgMax(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_argument_max_basic(self):
        self.argument_max([[0]], 1, 1, 2, None, 0)

    def test_argument_max_basic_columns(self):
        self.argument_max([[0]], 1, 1, 2, 0, [[0]])

    def test_argument_max_basic_rows(self):
        self.argument_max([[0]], 1, 1, 2, 1, [[0]])

    def test_argument_max_3_by_3(self):
        self.argument_max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, None, 8)

    def test_argument_max_3_by_3_columns(self):
        self.argument_max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0, [[2, 2, 2]])

    def test_argument_max_3_by_3_rows(self):
        self.argument_max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1, [[2, 2, 2]])

    def test_argument_max_4_by_1(self):
        self.argument_max([[0], [1], [0], [1]], 4, 1, 4, None, 1)

    def test_argument_max_4_by_1_columns(self):
        self.argument_max([[0], [1], [0], [1]], 4, 1, 4, 0, [[1]])

    def test_argument_max_4_by_1_rows(self):
        self.argument_max([[0], [1], [0], [1]], 4, 1, 4, 1, [[0, 0, 0, 0]])

    def test_argument_max_1_by_4(self):
        self.argument_max([[0, 1, 0, 1]], 1, 4, 4, None, 1)

    def test_argument_max_1_by_4_columns(self):
        self.argument_max([[0, 1, 0, 1]], 1, 4, 4, 0, [[0, 0, 0, 0]])

    def test_argument_max_1_by_4_rows(self):
        self.argument_max([[0, 1, 0, 1]], 1, 4, 4, 1, [[1]])

    '''
    def test_argument_max_random_case(self):
        rows, columns, bits, axis = random.randint(
            1, 5), random.randint(1, 5), random.randint(1, 5), random.randint(0, 2)
        if axis == 2:
            axis = None

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.argument_max(matrix, rows, columns, bits, axis)
    '''

    def test_argument_max_wire(self):
        arg_max_wire = Matrix.argmax(pyrtl.Const(3))
        self.check_against_expected(arg_max_wire, 0)

    def test_argument_max_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.argmax("1", axis=0)

    def test_argument_max_axis_out_of_bounds(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.argmax(matrix, axis=4)

    def test_argument_max_axis_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.argmax(matrix, axis=-1)

    def test_argument_max_axis_string(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.argmax(matrix, "1")

    def test_argument_max_bits_string(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.argmax(matrix, axis=1, bits="1")

    def test_argument_max_bits_negative(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.argmax(matrix, axis=1, bits=-1)

    def test_argument_max_bits_zero(self):
        matrix = Matrix.Matrix(3, 3, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _output = Matrix.argmax(matrix, axis=1, bits=0)

    def argument_max(self, int_matrix, rows, columns, bits, axis, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix, max_bits=bits * rows)
        result = Matrix.argmax(matrix, axis=axis, bits=bits * max(rows, columns))
        self.check_against_expected(result, expected_output)


class TestDot(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_dot_basic(self):
        self.dot([[0]], 1, 1, 2, [[0]], 1, 1, 3, 0)

    def test_dot_1_by_2_multiply_2_by_1(self):
        self.dot([[1, 2]], 1, 2, 2, [[1], [2]], 2, 1, 3, 5)

    def test_dot_1_by_2_multiply_1_by_2(self):
        self.dot([[1, 2]], 1, 2, 2, [[1, 2]], 1, 2, 3, 5)

    def test_dot_2_by_1_multiply_2_by_1(self):
        self.dot([[1], [2]], 2, 1, 3, [[1], [2]], 2, 1, 3, 5)

    def test_dot_2_by_1_multiply_1_by_2(self):
        self.dot([[1], [2]], 2, 1, 3, [[1, 2]], 1, 2, 3, 5)

    def test_dot_3_by_3_multiply_3_by_3_same(self):
        self.dot([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[15, 18, 21],
                                                              [42, 54, 66],
                                                              [69, 90, 111]])

    def test_dot_3_by_3_multiply_3_by_3_different(self):
        self.dot([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, [[30, 39, 48],
                                                              [54, 70, 86],
                                                              [21, 29, 37]])

    def test_dot_both_wires(self):
        first = pyrtl.Const(5)
        second = pyrtl.Const(3)
        dot_product = Matrix.dot(first, second)
        self.check_against_expected(dot_product, 15)

    def test_dot_first_wire(self):
        first = pyrtl.Const(5)
        second = Matrix.Matrix(1, 1, 3, value=[[3]])
        dot_product = Matrix.dot(first, second)
        self.check_against_expected(dot_product, 15)

    def test_dot_second_wire(self):
        first = Matrix.Matrix(1, 1, 3, value=[[5]])
        second = pyrtl.Const(3)
        dot_product = Matrix.dot(first, second)
        self.check_against_expected(dot_product, 15)

    def test_dot_fail_int_second(self):
        first_matrix = Matrix.Matrix(3, 2, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _result = Matrix.dot(first_matrix, 1)

    def test_dot_fail_int_first(self):
        first_matrix = Matrix.Matrix(3, 2, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            _result = Matrix.dot(1, first_matrix)

    def test_dot_fail_1_by_2_multiply_1_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.dot([[1, 2]], 1, 2, 2, [[1, 2, 3]], 1, 3, 3, [[]])

    def test_dot_fail_3_by_3_multiply_2_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.dot([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1], [0, 1]], 2, 2, 4, [[]])

    '''
    def test_dot_random_inner_product(self):
        columns, bits1, bits2 = random.randint(
            1, 5), random.randint(1, 5), random.randint(1, 5)

        first = [[0 for _ in range(columns)]
                 for _ in range(1)]

        second = [[0 for _ in range(columns)]
                  for _ in range(1)]

        for i in range(1):
            for j in range(columns):
                first[i][j] = random.randint(1, 2**bits1 - 1)
        for i in range(1):
            for j in range(columns):
                second[i][j] = random.randint(1, 2**bits2 - 1)

        self.dot(first, 1, columns, bits1,
                 second, 1, columns, bits2)
    '''

    '''
    def test_dot_random_matrix_multiply(self):
        rows, columns1, columns2, bits1, bits2 = random.randint(
            2, 3), random.randint(2, 3), random.randint(
                2, 3), random.randint(1, 5), random.randint(1, 5)

        first = [[0 for _ in range(columns1)]
                 for _ in range(rows)]

        second = [[0 for _ in range(columns2)]
                  for _ in range(columns1)]

        for i in range(rows):
            for j in range(columns1):
                first[i][j] = random.randint(1, 2**bits1 - 1)
        for i in range(columns1):
            for j in range(columns2):
                second[i][j] = random.randint(1, 2**bits2 - 1)

        self.dot(first, rows, columns1, bits1,
                 second, columns1, columns2, bits2)
    '''

    def dot(self, first_int_matrix, rows1, columns1, bits1,
            second_int_matrix, rows2, columns2, bits2, expected_output):
        first_matrix = Matrix.Matrix(rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(rows2, columns2, bits2, value=second_int_matrix)
        result_matrix = Matrix.dot(first_matrix, second_matrix)
        self.check_against_expected(result_matrix, expected_output)


class TestHStack(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_hstack_two_row_vectors(self):
        v1 = Matrix.Matrix(1, 3, bits=4, value=[[1, 2, 3]])
        v2 = Matrix.Matrix(1, 5, bits=8, value=[[4, 5, 6, 7, 8]])
        v3 = Matrix.hstack(v1, v2)
        self.assertEqual(v3.bits, 8)
        self.assertEqual(v3.max_bits, max(v1.max_bits, v2.max_bits))
        self.check_against_expected(v3, [[1, 2, 3, 4, 5, 6, 7, 8]])

    def test_hstack_one_row_vector(self):
        v1 = Matrix.Matrix(1, 3, bits=4, value=[[1, 2, 3]])
        v2 = Matrix.hstack(v1)
        self.assertEqual(v2.bits, 4)
        self.assertEqual(v2.max_bits, v1.max_bits)
        self.check_against_expected(v2, [[1, 2, 3]])

    def test_concatenate(self):
        m1 = Matrix.Matrix(2, 3, bits=4, value=[[1, 2, 3], [4, 5, 6]])
        m2 = Matrix.Matrix(2, 5, bits=8, value=[[7, 8, 9, 10, 11], [12, 13, 14, 15, 16]])
        m3 = Matrix.concatenate([m1, m2])
        self.check_against_expected(
            m3,
            [[1, 2, 3, 7, 8, 9, 10, 11],
             [4, 5, 6, 12, 13, 14, 15, 16]]
        )

    def test_hstack_several_matrices(self):
        m1 = Matrix.Matrix(2, 3, bits=4, value=[[1, 2, 3], [4, 5, 6]])
        m2 = Matrix.Matrix(2, 5, bits=8, value=[[7, 8, 9, 10, 11], [12, 13, 14, 15, 16]])
        m3 = Matrix.Matrix(2, 1, bits=3, value=[[0], [1]])
        m4 = Matrix.hstack(m1, m2, m3)
        self.assertEqual(m4.bits, 8)
        self.assertEqual(m4.max_bits, max(m1.max_bits, m2.max_bits, m3.max_bits))
        self.check_against_expected(
            m4,
            [[1, 2, 3, 7, 8, 9, 10, 11, 0],
             [4, 5, 6, 12, 13, 14, 15, 16, 1]]
        )

    def test_hstack_fail_on_inconsistent_rows(self):
        m1 = Matrix.Matrix(1, 2, bits=2, value=[[0, 1]])
        m2 = Matrix.Matrix(2, 2, bits=4, value=[[1, 2], [3, 4]])
        m3 = Matrix.Matrix(1, 4, bits=3, value=[[0, 0, 0, 0]])
        with self.assertRaises(pyrtl.PyrtlError):
            _v = Matrix.hstack(m1, m2, m3)

    def test_hstack_empty_args_fails(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _v = Matrix.hstack()

    def test_hstack_on_non_matrices_fails(self):
        w = pyrtl.WireVector(1)
        m = Matrix.Matrix(1, 2, bits=2, value=[[0, 1]])
        with self.assertRaises(pyrtl.PyrtlError):
            _v = Matrix.hstack(w, m)


class TestVStack(MatrixTestBase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_vstack_two_column_vectors(self):
        v1 = Matrix.Matrix(3, 1, bits=4, value=[[1], [2], [3]])
        v2 = Matrix.Matrix(5, 1, bits=8, value=[[4], [5], [6], [7], [8]])
        v3 = Matrix.vstack(v1, v2)
        self.assertEqual(v3.bits, 8)
        self.assertEqual(v3.max_bits, max(v1.max_bits, v2.max_bits))
        self.check_against_expected(v3, [[1], [2], [3], [4], [5], [6], [7], [8]])

    def test_vstack_one_column_vector(self):
        v1 = Matrix.Matrix(3, 1, bits=4, value=[[1], [2], [3]])
        v2 = Matrix.vstack(v1)
        self.assertEqual(v2.bits, 4)
        self.assertEqual(v2.max_bits, v1.max_bits)
        self.check_against_expected(v2, [[1], [2], [3]])

    def test_concatenate(self):
        m1 = Matrix.Matrix(2, 3, bits=5, value=[[1, 2, 3], [4, 5, 6]])
        m2 = Matrix.Matrix(1, 3, bits=10, value=[[7, 8, 9]])
        m3 = Matrix.concatenate([m1, m2], axis=1)
        self.check_against_expected(
            m3,
            [[1, 2, 3],
             [4, 5, 6],
             [7, 8, 9]]
        )

    def test_vstack_several_matrix(self):
        m1 = Matrix.Matrix(2, 3, bits=5, value=[[1, 2, 3], [4, 5, 6]])
        m2 = Matrix.Matrix(1, 3, bits=10, value=[[7, 8, 9]])
        m3 = Matrix.Matrix(3, 3, bits=8, value=[[10, 11, 12], [13, 14, 15], [16, 17, 18]])
        m4 = Matrix.vstack(m1, m2, m3)

        self.assertEqual(m4.bits, 10)
        self.assertEqual(m4.max_bits, max(m1.max_bits, m2.max_bits, m3.max_bits))
        self.check_against_expected(
            m4,
            [[1, 2, 3],
             [4, 5, 6],
             [7, 8, 9],
             [10, 11, 12],
             [13, 14, 15],
             [16, 17, 18]]
        )

    def test_vstack_fail_on_inconsistent_cols(self):
        m1 = Matrix.Matrix(1, 1, bits=2, value=[[0]])
        m2 = Matrix.Matrix(2, 2, bits=4, value=[[1, 2], [3, 4]])
        m3 = Matrix.Matrix(3, 1, bits=3, value=[[0], [0], [0]])
        with self.assertRaises(pyrtl.PyrtlError):
            _v = Matrix.vstack(m1, m2, m3)

    def test_vstack_empty_args_fails(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _v = Matrix.vstack()

    def test_vstack_on_non_matrices_fails(self):
        w = pyrtl.WireVector(1)
        m = Matrix.Matrix(2, 1, bits=2, value=[[0], [1]])
        with self.assertRaises(pyrtl.PyrtlError):
            _v = Matrix.vstack(w, m)


class TestHelpers(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_list_to_int(self):
        self.assertEqual(Matrix.list_to_int([[0]], 1), 0b0)
        self.assertEqual(Matrix.list_to_int([[1, 2]], 2), 0b0110)
        self.assertEqual(Matrix.list_to_int([[1, 2, 3]], 2), 0b011011)
        self.assertEqual(Matrix.list_to_int([[4, 9, 11], [3, 5, 6]], 4),
                         0b010010011011001101010110)

    def test_list_to_int_truncates(self):
        self.assertEqual(Matrix.list_to_int([[4, 9, 27]], 3), 0b100001011)

    def test_list_to_int_negative(self):
        self.assertEqual(Matrix.list_to_int([[-4, -9, 11]], 5), 0b111001011101011)

    def test_list_to_int_negative_truncates(self):
        self.assertEqual(Matrix.list_to_int([[-4, -9, 11]], 3), 0b100111011)

    def test_list_to_int_non_positive_n_bits(self):
        with self.assertRaises(pyrtl.PyrtlError):
            Matrix.list_to_int([[3]], 0)


if __name__ == '__main__':
    unittest.main()
