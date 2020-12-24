import random
import math
import unittest

import pyrtl
import pyrtl.rtllib.matrix as Matrix


class TestMatrixInit(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        with self.assertRaises(pyrtl.PyrtlError):
            matrix_input = pyrtl.Input(1 * 1, 'matrix_input')
            matrix = Matrix.Matrix(1, 1, 3, value=matrix_input)

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
        matrix_input = pyrtl.Input(rows * columns * bits, 'matrix_input')
        matrix = Matrix.Matrix(rows, columns, bits, value=matrix_input)

        self.assertEqual(rows, matrix.rows)
        self.assertEqual(columns, matrix.columns)
        self.assertEqual(bits, matrix.bits)
        self.assertEqual(len(matrix), (rows * columns * bits))

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({matrix_input: matrix_to_int(matrix_value, bits)})

        given_output = matrix_result(
            sim.inspect("output"), rows, columns, bits)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], matrix_value[i][j])

    def init_int_matrix(self, int_matrix, rows, columns, bits):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)

        self.assertEqual(rows, matrix.rows)
        self.assertEqual(columns, matrix.columns)
        self.assertEqual(bits, matrix.bits)
        self.assertEqual(len(matrix), (rows * columns * bits))

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(
            sim.inspect("output"), rows, columns, bits)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], int_matrix[i][j])


class TestMatrixBits(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_bits_no_change(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(
            3, 3, 4, value=int_matrix)

        self.assertEqual(matrix.bits, 4)

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(
            sim.inspect("output"), 3, 3, 4)

        for i in range(3):
            for j in range(3):
                self.assertEqual(given_output[i][j], int_matrix[i][j])

    def test_bits_basic_change_bits(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(
            3, 3, 4, value=int_matrix)

        matrix.bits = 5

        self.assertEqual(matrix.bits, 5)

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})
        given_output = matrix_result(
            sim.inspect("output"), 3, 3, 5)

        for i in range(3):
            for j in range(3):
                self.assertEqual(given_output[i][j], int_matrix[i][j])

    def test_bits_basic_change_bits_trunicate(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(
            3, 3, 4, value=int_matrix)

        matrix.bits = 2

        self.assertEqual(matrix.bits, 2)

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})
        given_output = matrix_result(
            sim.inspect("output"), 3, 3, 2)

        int_matrix = [[0, 1, 2], [3, 0, 1], [2, 3, 0]]

        for i in range(3):
            for j in range(3):
                self.assertEqual(given_output[i][j], int_matrix[i][j])

    def test_bits_fail_change_bits_zero(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 4, value=[[0, 1, 2], [3, 4, 5], [6, 7, 8]])

            matrix.bits = 0

    def test_bits_fail_change_bits_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 4, value=[[0, 1, 2], [3, 4, 5], [6, 7, 8]])

            matrix.bits = -1

    def test_bits_fail_change_bits_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 4, value=[[0, 1, 2], [3, 4, 5], [6, 7, 8]])

            matrix.bits = "1"


class TestMatrixGetItem(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            output = matrix["2", 3]

    def test_getitem_fail_string_columns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            output = matrix[2, "2"]

    def test_getitem_fail_out_of_bounds_rows(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            output = matrix[4, 2]

    def test_getitem_fail_out_of_bounds_rows_negative(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            output = matrix[-4, 2]

    def test_getitem_fail_out_of_bounds_columns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            output = matrix[1, 4]

    def test_getitem_fail_out_of_bounds_columns_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            output = matrix[1, -4]

    def test_getitem_fail_out_of_bounds_rows_slice(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            output = matrix[1:4, 1]

    def test_getitem_fail_out_of_bounds_columns_slice(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            output = matrix[1, 1:4]

    def test_getitem_fail_string_column_only(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            output = matrix["1"]

    def get_item(self, value_array, rows, columns, bits, x_slice, y_slice, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=value_array)

        item = matrix[x_slice, y_slice]

        output = pyrtl.Output(name="output", bitwidth=len(item))

        out_rows, out_columns = x_slice.stop - x_slice.start, \
            y_slice.stop - y_slice.start
        if isinstance(item, Matrix.Matrix):
            output <<= item.to_WireVector()
            self.assertEqual(out_rows, item.rows)
            self.assertEqual(out_columns, item.columns)
            self.assertEqual(bits, item.bits)
            self.assertEqual(len(item), out_rows * out_columns * bits)
        else:
            output <<= item

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), out_rows, out_columns, bits)

        if isinstance(item, Matrix.Matrix):
            for row in range(len(given_output)):
                for column in range(len(given_output[0])):
                    self.assertEqual(
                        given_output[row][column], expected_output[row][column])
        else:
            self.assertEqual(given_output[0][0], expected_output)

    def test_getitem_full(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)

        item = matrix[:, :]

        output = pyrtl.Output(name="output", bitwidth=len(item))
        output <<= item.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect("output"), 3, 3, 4)
        for i in range(3):
            for j in range(3):
                self.assertEqual(given_output[i][j], int_matrix[i][j])

    def test_getitem_full_row(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)

        item = matrix[1]

        output = pyrtl.Output(name="output", bitwidth=len(item))
        output <<= item.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        expected_output = [[3], [4], [5]]

        given_output = matrix_result(sim.inspect("output"), 3, 1, 4)
        for column in range(len(given_output[0])):
            self.assertEqual(
                given_output[0][column], expected_output[0][column])

    def test_getitem_negative(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)

        item = matrix[-2:-1, -2:-1]

        output = pyrtl.Output(name="output", bitwidth=len(item))
        output <<= item

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = sim.inspect("output")
        expected_output = 4

        self.assertEqual(given_output, expected_output)


class TestMatrixSetItem(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix["2", 3] = pyrtl.Const(0)

    def test_setitem_fail_string_column(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix[2, "2"] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_rows(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix[4, 2] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_rows_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix[-4, 2] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_columns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix[1, 4] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_columns_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix[1, -4] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_rows_slice(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix[1:4, 2] = pyrtl.Const(0, bitwidth=9)

    def test_getitem_fail_out_of_bounds_columns_slice(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix[1:4, 2] = pyrtl.Const(0, bitwidth=9)

    def test_getitem_fail_string_rows_only(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix["1"] = pyrtl.Const(0, bitwidth=9)

    def test_getitem_fail_wire_for_matrix(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix[1, 0:2] = pyrtl.Const(0, bitwidth=3)

    def test_getitem_fail_int_value(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            matrix[1, 1] = 1

    def test_getitem_fail_value_matrix_incorrect_rows(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            value_matrix = Matrix.Matrix(2, 1, 3)
            matrix[0:1, 0:1] = value_matrix

    def test_getitem_fail_value_matrix_incorrect_columns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(3, 3, 3)
            value_matrix = Matrix.Matrix(1, 2, 3)
            matrix[0:1, 0:1] = value_matrix

    def set_item(self, int_matrix, rows, columns, bits,
                 x_slice, y_slice, value, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)
        value_matrix = Matrix.Matrix(
            x_slice.stop - x_slice.start, y_slice.stop - y_slice.start,
            bits, value=value)

        matrix[x_slice, y_slice] = value_matrix

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows, columns, bits)

        for row in range(len(given_output)):
            for column in range(len(given_output[0])):
                self.assertEqual(
                    given_output[row][column], expected_output[row][column])

    def test_setitem_negative(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)

        matrix[-2:-1, -2:-1] = pyrtl.Const(0)

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, 4)

        expected_output = [[0, 1, 2], [3, 0, 5], [6, 7, 8]]

        for row in range(len(given_output)):
            for column in range(len(given_output[0])):
                self.assertEqual(
                    given_output[row][column], expected_output[row][column])

    def test_setitem_full(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[8, 7, 6], [5, 4, 3], [2, 1, 0]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = Matrix.Matrix(3, 3, 4, value=value_int_matrix)

        matrix[:, :] = value_matrix

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, 4)

        expected_output = value_int_matrix

        for row in range(len(given_output)):
            for column in range(len(given_output[0])):
                self.assertEqual(
                    given_output[row][column], expected_output[row][column])

    def test_setitem_full_row_item(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[8, 7, 6]]
        matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = Matrix.Matrix(1, 3, 4, value=value_int_matrix)

        matrix[1] = value_matrix

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, 4)

        expected_output = [[0, 1, 2], [8, 7, 6], [6, 7, 8]]

        for row in range(len(given_output)):
            for column in range(len(given_output[0])):
                self.assertEqual(
                    given_output[row][column], expected_output[row][column])


class TestPyRTLCopy(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        change_matrix = Matrix.Matrix(
            rows, columns, bits, value=second_value)
        copy_matrix = matrix.copy()

        self.assertEqual(copy_matrix.rows, matrix.rows)
        self.assertEqual(copy_matrix.columns, matrix.columns)
        self.assertEqual(copy_matrix.bits, matrix.bits)
        self.assertEqual(len(copy_matrix), len(matrix))

        copy_output = pyrtl.Output(
            name="copy_output", bitwidth=len(copy_matrix))
        copy_output <<= copy_matrix.to_WireVector()

        matrix_output = pyrtl.Output(
            name="matrix_output", bitwidth=len(matrix))
        matrix_output <<= matrix.to_WireVector()

        copy_matrix[:, :] = change_matrix[:, :]

        matrix_output_1 = pyrtl.Output(
            name="matrix_output_1", bitwidth=len(matrix))
        matrix_output_1 <<= matrix.to_WireVector()

        copy_output_1 = pyrtl.Output(
            name="copy_output_1", bitwidth=len(copy_matrix))
        copy_output_1 <<= copy_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "matrix_output"), rows, columns, bits)
        expected_output = matrix_result(sim.inspect(
            "copy_output"), rows, columns, bits)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], expected_output[i][j])

        given_output = matrix_result(sim.inspect(
            "matrix_output_1"), rows, columns, bits)

        expected_output = matrix_result(sim.inspect(
            "copy_output_1"), rows, columns, bits)

        for i in range(rows):
            for j in range(columns):
                self.assertNotEqual(first_value[i][j], second_value[i][j])
                self.assertNotEqual(given_output[i][j], expected_output[i][j])


class TestPyRTLTranspose(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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

        output = pyrtl.Output(name="output", bitwidth=len(transpose_matrix))
        output <<= transpose_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(
            sim.inspect("output"), columns, rows, bits)

        for i in range(columns):
            for j in range(rows):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixReverse(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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

        output = pyrtl.Output(name="output", bitwidth=len(reversed_matrix))
        output <<= reversed_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(
            sim.inspect("output"), rows, columns, bits)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixAdd(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_add_basic_case(self):
        self.add([[0]], 1, 1, 2, [[0]], 1, 1, 3, [[0]])

    def test_add_2_by_3(self):
        self.add([[0, 1, 2], [3, 4, 5]], 2, 3, 4,
                 [[0, 1, 2], [3, 4, 5]], 2, 3, 4, [[0, 2, 4],
                                                   [6, 8, 10]])

    def test_add_3_by_2(self):
        self.add([[2, 4], [5, 4], [2, 5]], 3, 2, 4,
                 [[0, 1], [3, 4], [6, 7]], 3, 2, 4, [[2,  5],
                                                     [8,  8],
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
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = Matrix.Matrix(
                1, 3, 3)
            result = first_matrix + 1

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
        first_matrix = Matrix.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        result_matrix = first_matrix + second_matrix

        self.assertEqual(result_matrix.rows, rows1)
        self.assertEqual(result_matrix.columns, columns1)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns1, result_matrix.bits)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixInplaceAdd(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        first_matrix = Matrix.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        first_matrix += second_matrix

        self.assertEqual(first_matrix.rows, rows1)
        self.assertEqual(first_matrix.columns, columns1)

        output = pyrtl.Output(name='output', bitwidth=len(first_matrix))
        output <<= first_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns1, first_matrix.bits)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixSub(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = Matrix.Matrix(
                1, 3, 3)
            result = first_matrix - 1

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
        first_matrix = Matrix.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        result_matrix = first_matrix - second_matrix

        self.assertEqual(result_matrix.rows, rows1)
        self.assertEqual(result_matrix.columns, columns1)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns1, result_matrix.bits)

        for i in range(rows1):
            for j in range(columns1):
                if expected_output[i][j] > 0:
                    self.assertEqual(given_output[i][j], expected_output[i][j])
                else:
                    self.assertEqual(given_output[i][j], 0)


class TestMatrixInplaceSub(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        first_matrix = Matrix.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        first_matrix -= second_matrix

        self.assertEqual(first_matrix.rows, rows1)
        self.assertEqual(first_matrix.columns, columns1)

        output = pyrtl.Output(name='output', bitwidth=len(first_matrix))
        output <<= first_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns1, first_matrix.bits)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
            self.element_wise_multiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3,
                                       4,
                                       [[0, 1], [0, 1], [0, 1]], 3, 2, 4, [[]])

    def test_element_wise_multiply_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_multiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3,
                                       4,
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
        first_matrix = Matrix.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        result_matrix = first_matrix * second_matrix

        self.assertEqual(result_matrix.rows, rows1)
        self.assertEqual(result_matrix.columns, columns1)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns1, result_matrix.bits)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])

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
        bits = 1
        if number != 0:
            bits = int(math.log(number, 2)) + 1

        b_input = pyrtl.Input(bitwidth=int(bits), name='b_input')

        result_matrix = first_matrix * b_input

        self.assertEqual(result_matrix.rows, rows)
        self.assertEqual(result_matrix.columns, columns)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({b_input: number})

        given_output = matrix_result(sim.inspect(
            "output"), rows, columns, result_matrix.bits)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], expected_output[i][j])

    def test_multiply_fail_int(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = Matrix.Matrix(
                3, 2, 3)
            result = first_matrix * 1


class TestMatrixInplaceMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
            self.element_wise_imultiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3,
                                        4,
                                        [[0, 1], [0, 1], [0, 1]], 2, 3, 4, [[]])

    def test_element_wise_imultiply_fail_3_by_3_multiply_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_imultiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3,
                                        4,
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
        first_matrix = Matrix.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        first_matrix *= second_matrix

        self.assertEqual(first_matrix.rows, rows1)
        self.assertEqual(first_matrix.columns, columns1)

        output = pyrtl.Output(name='output', bitwidth=len(first_matrix))
        output <<= first_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns1, first_matrix.bits)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixMatrixMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = Matrix.Matrix(
                3, 2, 3)
            result = first_matrix.__matmul__(1)

    def test_mat_mul_fail_3_by_3_multiply_2_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                        [[0, 1], [0, 1], [0, 1]], 2, 3, 4, [[]])

    def test_mat_mul_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                        [[0, 1, 1], [0, 1, 1]], 2, 3, 4, [[]])

    def test_mat_mul_fail_3_by_2_multiply_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = Matrix.Matrix(
                3, 2, 3)
            second_matrix = Matrix.Matrix(
                3, 2, 3)
            result = first_matrix.__matmul__(second_matrix)

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
        first_matrix = Matrix.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        result_matrix = first_matrix.__matmul__(second_matrix)

        self.assertEqual(result_matrix.rows, rows1)
        self.assertEqual(result_matrix.columns, columns2)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns2, result_matrix.bits)

        for i in range(rows1):
            for j in range(columns2):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixInplaceMatrixMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        first_matrix = Matrix.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        first_matrix.__imatmul__(second_matrix)

        self.assertEqual(first_matrix.rows, rows1)
        self.assertEqual(first_matrix.columns, columns2)

        output = pyrtl.Output(name='output', bitwidth=len(first_matrix))
        output <<= first_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns2, first_matrix.bits)

        for i in range(rows1):
            for j in range(columns2):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixMatrixPower(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = Matrix.Matrix(
                3, 3, 3)
            result = first_matrix ** "1"

    def test_matrix_power_fail_negative_power(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matrix_power(
                [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, -1, [[]])

    '''
    def test_matrix_power_random_case(self):
        self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]],
                          3, 3, 4, random.randint(0, 2))
    '''

    def matrix_power(self, int_matrix, rows, columns, bits, exp, expected_output):
        matrix = Matrix.Matrix(rows, columns, bits, value=int_matrix)

        result_matrix = matrix ** exp

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows, columns, result_matrix.bits)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixInplaceMatrixPower(unittest.TestCase):
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

        output = pyrtl.Output(name='output', bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows, columns, matrix.bits)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_multiply_scalar(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        first_matrix = Matrix.Matrix(3, 3, 4, value=int_matrix)

        b_input = pyrtl.Input(bitwidth=2, name='b_input')

        result_matrix = Matrix.multiply(first_matrix, b_input)

        self.assertEqual(result_matrix.rows, 3)
        self.assertEqual(result_matrix.columns, 3)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({b_input: 3})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, result_matrix.bits)
        expected_output = [[0, 3, 6], [9, 12, 15], [18, 21, 24]]

        for i in range(3):
            for j in range(3):
                self.assertEqual(given_output[i][j], expected_output[i][j])

    def test_multiply_matrix(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        first_matrix = Matrix.Matrix(
            3, 3, 4, value=int_matrix)
        second_matrix = Matrix.Matrix(
            3, 3, 4, value=int_matrix)

        result_matrix = Matrix.multiply(first_matrix, second_matrix)

        self.assertEqual(result_matrix.rows, 3)
        self.assertEqual(result_matrix.columns, 3)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, result_matrix.bits)
        expected_output = [[0, 1, 4], [9, 16, 25], [36, 49, 64]]

        for i in range(3):
            for j in range(3):
                self.assertEqual(given_output[i][j], expected_output[i][j])

    def test_multiply_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
            second_matrix = Matrix.Matrix(
                3, 3, 4, value=int_matrix)
            result_matrix = Matrix.multiply(1, second_matrix)


class TestSum(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_sum_basic(self):
        self.sum([[0]], 1, 1, 2, None, 0)

    def test_sum_basic_column(self):
        self.sum([[0]], 1, 1, 2, 0, [[0]])

    def test_sum_basic_row(self):
        self.sum([[0]], 1, 1, 2, 1, [[0]])

    def test_sum_3_by_3(self):
        self.sum([[0, 1, 2], [3, 4, 5], [6, 7, 8]],
                 3, 3, 4, None, 36)

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
        wire = pyrtl.Const(3)
        sum_wire = pyrtl.Output(name="output", bitwidth=len(wire))
        sum_wire <<= Matrix.sum(wire)

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        output = sim.inspect("output")

        self.assertEqual(output, 3)

    def test_sum_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            output = Matrix.sum("1", 0)

    def test_sum_fail_negative_axis(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.sum(matrix, -1)

    def test_sum_fail_axis_out_of_bounds(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.sum(matrix, 2)

    def test_sum_fail_string_axis(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.sum(matrix, "0")

    def test_sum_fail_string_bits(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.sum(matrix, axis=0, bits="0")

    def test_sum_fail_negative_bits(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.sum(matrix, axis=0, bits=-1)

    def test_sum_fail_zero_bits(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.sum(matrix, axis=0, bits=0)

    def sum(self, int_matrix, rows, columns, bits, axis, expected_output):
        matrix = Matrix.Matrix(
            rows, columns, bits, value=int_matrix, max_bits=bits * rows)

        result = Matrix.sum(
            matrix, axis=axis, bits=bits * max(rows, columns))
        output = pyrtl.Output(name="output", bitwidth=len(result))
        if axis is None:
            output <<= result
        else:
            output <<= result.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = None
        if axis is None:
            given_output = sim.inspect("output")
        else:
            given_output = matrix_result(sim.inspect(
                "output"), result.rows, result.columns, result.bits)

        if axis is None:
            self.assertEqual(given_output, expected_output)
        else:
            for i in range(result.rows):
                for j in range(result.columns):
                    self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMin(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        wire = pyrtl.Const(3)
        sum_wire = pyrtl.Output(name="output", bitwidth=len(wire))
        sum_wire <<= Matrix.min(wire)

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        output = sim.inspect("output")

        self.assertEqual(output, 3)

    def test_min_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            output = Matrix.min("1", 0)

    def test_min_fail_axis_out_of_bounds(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.min(matrix, 4)

    def test_min_fail_axis_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.min(matrix, -1)

    def test_min_fail_axis_string(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.min(matrix, "0")

    def test_min_fail_bits_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.min(matrix, axis=0, bits="1")

    def test_min_fail_bits_zero(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.min(matrix, axis=0, bits=0)

    def test_min_fail_bits_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.min(matrix, axis=0, bits=-2)

    def min(self, int_matrix, rows, columns, bits, axis, expected_output):
        matrix = Matrix.Matrix(
            rows, columns, bits, value=int_matrix, max_bits=bits * rows)

        result = Matrix.min(
            matrix, axis=axis, bits=bits * max(rows, columns))
        output = pyrtl.Output(name="output", bitwidth=len(result))
        if axis is None:
            output <<= result
        else:
            output <<= result.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = None
        if axis is None:
            given_output = sim.inspect("output")
        else:
            given_output = matrix_result(sim.inspect(
                "output"), result.rows, result.columns, result.bits)

        if axis is None:
            self.assertEqual(given_output, expected_output)
        else:
            for i in range(result.rows):
                for j in range(result.columns):
                    self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMax(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        wire = pyrtl.Const(3)
        max_wire = pyrtl.Output(name="output", bitwidth=len(wire))
        max_wire <<= Matrix.max(wire)

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        output = sim.inspect("output")

        self.assertEqual(output, 3)

    def test_max_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            output = Matrix.max("1", 0)

    def test_max_fail_axis_out_of_bounds(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.max(matrix, 4)

    def test_max_fail_axis_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.max(matrix, -1)

    def test_max_fail_axis_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.max(matrix, "0")

    def test_max_fail_bits_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.max(matrix, axis=0, bits="1")

    def test_max_fail_bits_zero(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.max(matrix, axis=0, bits=0)

    def test_max_fail_bits_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.max(matrix, axis=0, bits=-1)

    def max(self, int_matrix, rows, columns, bits, axis, expected_output):
        matrix = Matrix.Matrix(
            rows, columns, bits, value=int_matrix, max_bits=bits * rows)

        result = Matrix.max(
            matrix, axis=axis, bits=bits * max(rows, columns))
        output = pyrtl.Output(name="output", bitwidth=len(result))
        if axis is None:
            output <<= result
        else:
            output <<= result.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = None
        if axis is None:
            given_output = sim.inspect("output")
        else:
            given_output = matrix_result(sim.inspect(
                "output"), result.rows, result.columns, result.bits)

        if axis is None:
            self.assertEqual(given_output, expected_output)
        else:
            for i in range(result.rows):
                for j in range(result.columns):
                    self.assertEqual(given_output[i][j], expected_output[i][j])


class TestArgMax(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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
        self.argument_max([[0, 1, 2], [3, 4, 5], [6, 7, 8]],
                          3, 3, 4, 0, [[2, 2, 2]])

    def test_argument_max_3_by_3_rows(self):
        self.argument_max([[0, 1, 2], [3, 4, 5], [6, 7, 8]],
                          3, 3, 4, 1, [[2, 2, 2]])

    def test_argument_max_4_by_1(self):
        self.argument_max([[0], [1], [0], [1]], 4, 1, 4, None, 1)

    def test_argument_max_4_by_1_columns(self):
        self.argument_max([[0], [1], [0], [1]], 4, 1, 4, 0, [[1]])

    def test_argument_max_4_by_1_rows(self):
        self.argument_max([[0], [1], [0], [1]], 4, 1, 4,
                          1, [[0, 0, 0, 0]])

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
        wire = pyrtl.Const(3)
        sum_wire = pyrtl.Output(name="output", bitwidth=len(wire))
        sum_wire <<= Matrix.argmax(wire)

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        output = sim.inspect("output")

        self.assertEqual(output, 0)

    def test_argument_max_string(self):

        with self.assertRaises(pyrtl.PyrtlError):
            output = Matrix.argmax("1", axis=0)

    def test_argument_max_axis_out_of_bounds(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.argmax(matrix, axis=4)

    def test_argument_max_axis_negative(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.argmax(matrix, axis=-1)

    def test_argument_max_axis_string(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.argmax(matrix, "1")

    def test_argument_max_bits_string(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.argmax(matrix, axis=1, bits="1")

    def test_argument_max_bits_negative(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.argmax(matrix, axis=1, bits=-1)

    def test_argument_max_bits_zero(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = Matrix.Matrix(
                3, 3, 3)
            output = Matrix.argmax(matrix, axis=1, bits=0)

    def argument_max(self, int_matrix, rows, columns, bits, axis, expected_output):
        matrix = Matrix.Matrix(
            rows, columns, bits, value=int_matrix, max_bits=bits * rows)

        result = Matrix.argmax(
            matrix, axis=axis, bits=bits * max(rows, columns))
        output = pyrtl.Output(name="output", bitwidth=len(result))
        if axis is None:
            output <<= result
        else:
            output <<= result.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = None
        if axis is None:
            given_output = sim.inspect("output")
        else:
            given_output = matrix_result(sim.inspect(
                "output"), result.rows, result.columns, result.bits)

        if axis is None:
            self.assertEqual(given_output, int(expected_output))
        else:
            for i in range(result.rows):
                for j in range(result.columns):
                    self.assertEqual(given_output[i][j], expected_output[i][j])


class TestDot(unittest.TestCase):
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

        output = pyrtl.Output(name='output', bitwidth=len(dot_product))
        output <<= dot_product

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = sim.inspect('output')
        expected_output = 15

        self.assertEqual(given_output, expected_output)

    def test_dot_first_wire(self):
        first = pyrtl.Const(5)
        second = Matrix.Matrix(
            1, 1, 3, value=[[3]])

        dot_product = Matrix.dot(first, second)

        output = pyrtl.Output(name='output', bitwidth=len(dot_product))
        output <<= dot_product

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = sim.inspect('output')
        expected_output = 15

        self.assertEqual(given_output, expected_output)

    def test_dot_second_wire(self):
        first = Matrix.Matrix(
            1, 1, 3, value=[[5]])
        second = pyrtl.Const(3)

        dot_product = Matrix.dot(first, second)

        output = pyrtl.Output(name='output', bitwidth=len(dot_product))
        output <<= dot_product

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = sim.inspect('output')
        expected_output = 15

        self.assertEqual(given_output, expected_output)

    def test_dot_fail_int_second(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = Matrix.Matrix(
                3, 2, 3)
            result = Matrix.dot(first_matrix, 1)

    def test_dot_fail_int_first(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = Matrix.Matrix(
                3, 2, 3)
            result = Matrix.dot(1, first_matrix)

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
        first_matrix = Matrix.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = Matrix.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        result_matrix = Matrix.dot(first_matrix, second_matrix)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        if isinstance(result_matrix, pyrtl.WireVector):
            output <<= result_matrix
        else:
            output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = None
        if isinstance(result_matrix, pyrtl.WireVector):
            given_output = sim.inspect("output")
        else:
            given_output = matrix_result(sim.inspect(
                "output"), result_matrix.rows, result_matrix.columns, result_matrix.bits)

        if isinstance(given_output, int):
            self.assertEqual(given_output, expected_output)
        else:
            for i in range(len(expected_output)):
                for j in range(len(expected_output[0])):
                    self.assertEqual(given_output[i][j], expected_output[i][j])


'''
These are helpful functions to use in testing
'''


def matrix_to_int(matrix, n_bits):
    result = ''

    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            result = result + bin(matrix[i][j])[2:].zfill(n_bits)

    return int(result, 2)


def matrix_result(start_value, rows, columns, bits):
    value = bin(start_value)[2:].zfill(rows * columns * bits)

    result = [[0 for _ in range(columns)]
              for _ in range(rows)]

    bit_pointer = 0
    for i in range(rows):
        for j in range(columns):
            int_value = int(value[bit_pointer: bit_pointer + bits], 2)
            result[i][j] = int_value
            bit_pointer += bits
    return result


def check_matrix_matches(first, second):
    if len(first) != len(second) or len(first[0]) != len(second[0]):
        return False
    for row in len(first):
        for column in len(first[0]):
            if first[row][column] != second[row][column]:
                return False
    return True


if __name__ == '__main__':
    # unittest.main(
    #    defaultTest='TestDot', verbosity=2)
    unittest.main(verbosity=2)
