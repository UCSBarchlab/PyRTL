import inspect
import os
import sys
import unittest
import math
import random
import numpy as np


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
            matrix = pyrtl.Matrix(1, 1, 3, value=matrix_input)

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
        matrix = pyrtl.Matrix(rows, columns, bits, value=matrix_input)

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
        matrix = pyrtl.Matrix(rows, columns, bits, value=int_matrix)

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
        matrix = pyrtl.Matrix(
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
        matrix = pyrtl.Matrix(
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
        matrix = pyrtl.Matrix(
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
            matrix = pyrtl.Matrix(
                3, 3, 4, value=[[0, 1, 2], [3, 4, 5], [6, 7, 8]])

            matrix.bits = 0

    def test_bits_fail_change_bits_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 4, value=[[0, 1, 2], [3, 4, 5], [6, 7, 8]])

            matrix.bits = -1

    def test_bits_fail_change_bits_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 4, value=[[0, 1, 2], [3, 4, 5], [6, 7, 8]])

            matrix.bits = "1"


class TestMatrixGetItem(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_getitem_basic_case(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 1, None), slice(0, 1, None))

    def test_getitem_2_by_2_slice(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 2, None), slice(0, 2, None))

    def test_getitem_3_by_3_slice(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 3, None), slice(0, 3, None))

    def test_getitem_2_3_slice(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 2, None), slice(0, 3, None))

    def test_getitem_3_2_slice(self):
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 2, None), slice(0, 3, None))

    def test_getitem_random(self):
        x_start = random.randint(0, 2)
        x_stop = random.randint(x_start + 1, 3)

        y_start = random.randint(0, 2)
        y_stop = random.randint(y_start + 1, 3)
        self.get_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(x_start, x_stop, None),
                      slice(y_start, y_stop, None))

    def test_getitem_fail_string_rows(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            output = matrix["2", 3]

    def test_getitem_fail_string_columns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            output = matrix[2, "2"]

    def test_getitem_fail_out_of_bounds_rows(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            output = matrix[4, 2]

    def test_getitem_fail_out_of_bounds_rows_negative(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            output = matrix[-4, 2]

    def test_getitem_fail_out_of_bounds_columns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            output = matrix[1, 4]

    def test_getitem_fail_out_of_bounds_columns_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            output = matrix[1, -4]

    def test_getitem_fail_out_of_bounds_rows_slice(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            output = matrix[1:4, 1]

    def test_getitem_fail_out_of_bounds_columns_slice(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            output = matrix[1, 1:4]

    def test_getitem_fail_string_column_only(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            output = matrix["1"]

    def get_item(self, value_array, rows, columns, bits, x_slice, y_slice):
        matrix = pyrtl.Matrix(rows, columns, bits, value=value_array)

        item = matrix[x_slice, y_slice]

        output = pyrtl.Output(name="output", bitwidth=len(item))

        out_rows, out_columns = x_slice.stop - x_slice.start, \
            y_slice.stop - y_slice.start
        if isinstance(item, pyrtl.Matrix):
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

        array = np.asarray(value_array)
        expected_output = array[x_slice, y_slice]

        if isinstance(item, pyrtl.Matrix):
            for i in range(out_rows):
                for j in range(out_columns):
                    self.assertEqual(
                        given_output[i][j], expected_output[i][j])
        else:
            self.assertEqual(given_output, expected_output)

    def test_getitem_full(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = pyrtl.Matrix(3, 3, 4, value=int_matrix)

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
        matrix = pyrtl.Matrix(3, 3, 4, value=int_matrix)

        item = matrix[1]

        output = pyrtl.Output(name="output", bitwidth=len(item))
        output <<= item.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        expected_output = np.asarray(int_matrix)[1]

        given_output = matrix_result(sim.inspect("output"), 3, 1, 4)
        for i in range(len(expected_output)):
            self.assertEqual(given_output[i], expected_output[i])

    def test_getitem_negative(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = pyrtl.Matrix(3, 3, 4, value=int_matrix)

        item = matrix[-2:-1, -2:-1]

        output = pyrtl.Output(name="output", bitwidth=len(item))
        output <<= item

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = sim.inspect("output")
        array = np.asarray(int_matrix)
        expected_output = array[-2:-1, -2:-1][0][0]

        self.assertEqual(given_output, expected_output)


class TestMatrixSetItem(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_setitem_basic_case(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 1, None), slice(0, 1, None), [[1]])

    def test_setitem_2_by_2(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 2, None), slice(0, 2, None),
                      [[1, 0], [1, 0]])

    def test_setitem_3_by_3(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 3, None), slice(0, 3, None),
                      [[8, 7, 6], [5, 4, 3], [2, 1, 0]])

    def test_setitem_2_by_3(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 2, None), slice(0, 3, None),
                      [[8, 7, 6], [5, 4, 3]])

    def test_setitem_3_by_2(self):
        self.set_item([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3,
                      3, 4, slice(0, 3, None), slice(0, 2, None),
                      [[8, 7], [5, 4], [2, 1]])

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

    def test_setitem_fail_string_row(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix["2", 3] = pyrtl.Const(0)

    def test_setitem_fail_string_column(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix[2, "2"] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_rows(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix[4, 2] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_rows_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix[-4, 2] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_columns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix[1, 4] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_columns_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix[1, -4] = pyrtl.Const(0)

    def test_getitem_fail_out_of_bounds_rows_slice(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix[1:4, 2] = pyrtl.Const(0, bitwidth=9)

    def test_getitem_fail_out_of_bounds_columns_slice(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix[1:4, 2] = pyrtl.Const(0, bitwidth=9)

    def test_getitem_fail_string_rows_only(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix["1"] = pyrtl.Const(0, bitwidth=9)

    def test_getitem_fail_wire_for_matrix(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix[1, 0:2] = pyrtl.Const(0, bitwidth=3)

    def test_getitem_fail_int_value(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            matrix[1, 1] = 1

    def test_getitem_fail_value_matrix_incorrect_rows(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            value_matrix = pyrtl.Matrix(2, 1, 3)
            matrix[0:1, 0:1] = value_matrix

    def test_getitem_fail_value_matrix_incorrect_columns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(3, 3, 3)
            value_matrix = pyrtl.Matrix(1, 2, 3)
            matrix[0:1, 0:1] = value_matrix

    def set_item(self, int_matrix, rows, columns, bits,
                 x_slice, y_slice, value):
        matrix = pyrtl.Matrix(rows, columns, bits, value=int_matrix)
        value_matrix = pyrtl.Matrix(
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

        expected_output = np.asarray(int_matrix)
        expected_output[x_slice, y_slice] = np.asarray(value)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(
                    given_output[i][j], expected_output[i][j])

    def test_setitem_negative(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        matrix = pyrtl.Matrix(3, 3, 4, value=int_matrix)

        matrix[-2:-1, -2:-1] = pyrtl.Const(0)

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, 4)

        expected_output = np.asarray(int_matrix)
        expected_output[-2:-1, -2:-1] = 0

        for i in range(3):
            for j in range(3):
                self.assertEqual(
                    given_output[i][j], expected_output[i][j])

    def test_setitem_full(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[8, 7, 6], [5, 4, 3], [2, 1, 0]]
        matrix = pyrtl.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = pyrtl.Matrix(3, 3, 4, value=value_int_matrix)

        matrix[:, :] = value_matrix

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, 4)

        expected_output = np.asarray(int_matrix)
        expected_output[:, :] = value_int_matrix

        for i in range(3):
            for j in range(3):
                self.assertEqual(
                    given_output[i][j], expected_output[i][j])

    def test_setitem_full_row_item(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        value_int_matrix = [[8, 7, 6]]
        matrix = pyrtl.Matrix(3, 3, 4, value=int_matrix)
        value_matrix = pyrtl.Matrix(1, 3, 4, value=value_int_matrix)

        matrix[1] = value_matrix

        output = pyrtl.Output(name="output", bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, 4)

        expected_output = np.asarray(int_matrix)
        expected_output[1] = np.asarray(value_int_matrix)

        for i in range(3):
            for j in range(3):
                self.assertEqual(
                    given_output[i][j], expected_output[i][j])


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
        matrix = pyrtl.Matrix(rows, columns, bits, value=first_value)
        change_matrix = pyrtl.Matrix(
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
        self.transpose([[0]], 1, 1, 2)

    def test_transpose_3_by_3(self):
        self.transpose([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_transpose_1_by_4(self):
        self.transpose([[0, 1, 0, 2]], 1, 4, 4)

    def test_transpose_4_by_1(self):
        self.transpose([[0], [1], [0], [2]], 4, 1, 4)

    def test_transpose_random_case(self):
        rows, columns, bits = random.randint(
            1, 20), random.randint(1, 20), random.randint(1, 20)

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.transpose(matrix, rows, columns, bits)

    def transpose(self, int_matrix, rows, columns, bits):
        matrix = pyrtl.Matrix(rows, columns, bits, value=int_matrix)

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
        expected_output = np.asarray(int_matrix).transpose()

        for i in range(columns):
            for j in range(rows):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixReverse(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_reverse_basic(self):
        self.reverse([[0]], 1, 1, 2)

    def test_reverse_3_by_3(self):
        self.reverse([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_reverse_1_by_4(self):
        self.reverse([[0, 1, 3, 2]], 1, 4, 4)

    def test_reverse_4_by_1(self):
        self.reverse([[0], [1], [3], [2]], 4, 1, 4)

    def test_reverse_random(self):
        rows, columns, bits = random.randint(
            1, 20), random.randint(1, 20), random.randint(1, 20)

        matrix = [[0 for _ in range(columns)]
                  for _ in range(rows)]

        for i in range(rows):
            for j in range(columns):
                matrix[i][j] = random.randint(1, 2**bits - 1)

        self.reverse(matrix, rows, columns, bits)

    def reverse(self, int_matrix, rows, columns, bits):
        matrix = pyrtl.Matrix(rows, columns, bits, value=int_matrix)

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
        expected_output = np.asarray(int_matrix)[::-1, ::-1]

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixAdd(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_add_basic_case(self):
        self.add([[0]], 1, 1, 2, [[0]], 1, 1, 3)

    def test_add_2_by_3(self):
        self.add([[0, 1, 2], [3, 4, 5]], 2, 3, 4,
                 [[0, 1, 2], [3, 4, 5]], 2, 3, 4)

    def test_add_3_by_2(self):
        self.add([[2, 4], [5, 4], [2, 5]], 3, 2, 4,
                 [[0, 1], [3, 4], [6, 7]], 3, 2, 4)

    def test_add_3_by_3_same(self):
        self.add([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_add_3_by_3_different(self):
        self.add([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_add_fail_2_by_2_add_3_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.add([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1], [0, 1], [0, 1]], 2, 3, 4)

    def test_add_fail_3_by_3_add_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.add([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1, 1], [0, 1, 1]], 2, 3, 4)

    def test_add_fail_3_by_3_add_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.add([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1], [0, 1], [1, 1]], 3, 2, 4)

    def test_add_fail_add_one(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = pyrtl.Matrix(
                1, 3, 3)
            result = first_matrix + 1

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

    def add(self, first_int_matrix, rows1, columns1, bits1, second_int_matrix,
            rows2, columns2, bits2):
        first_matrix = pyrtl.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = pyrtl.Matrix(
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
        expected_output = np.asarray(
            first_int_matrix) + np.asarray(second_int_matrix)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixInplaceAdd(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_iadd_basic(self):
        self.iadd([[0]], 1, 1, 2, [[0]], 1, 1, 3)

    def test_iadd_3_by_3_same(self):
        self.iadd([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                  [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_iadd_3_by_3_different(self):
        self.iadd([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                  [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_iadd_fail_3_by_3_add_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.iadd([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                      [[0, 1], [0, 1], [0, 1]], 2, 3, 4)

    def test_iadd_fail_3_by_3_add_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.iadd([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                      [[0, 1, 1], [0, 1, 1]], 3, 2, 4)

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

    def iadd(self, first_int_matrix, rows1, columns1, bits1, second_int_matrix,
             rows2, columns2, bits2):
        first_matrix = pyrtl.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = pyrtl.Matrix(
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
        expected_output = np.asarray(
            first_int_matrix) + np.asarray(second_int_matrix)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixSub(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_sub_basic(self):
        self.sub([[0]], 1, 1, 2, [[0]], 1, 1, 3)

    def test_sub_3_by_3_same(self):
        self.sub([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_sub_3_by_3_different_postive_result(self):
        self.sub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_sub_fail_int(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = pyrtl.Matrix(
                1, 3, 3)
            result = first_matrix - 1

    def test_sub_fail_3_by_3_sub_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.sub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1], [0, 1], [0, 1]], 3, 2, 4)

    def test_sub_fail_3_by_3_sub_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.sub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1, 1], [0, 1, 1]], 2, 3, 4)

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

    def sub(self, first_int_matrix, rows1, columns1, bits1, second_int_matrix,
            rows2, columns2, bits2):
        first_matrix = pyrtl.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = pyrtl.Matrix(
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
        expected_output = np.asarray(
            first_int_matrix) - np.asarray(second_int_matrix)

        for i in range(rows1):
            for j in range(columns1):
                if expected_output[i][j] > 0:
                    self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixInplaceSub(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_isub_basic(self):
        self.isub([[0]], 1, 1, 2, [[0]], 1, 1, 3)

    def test_isub_3_by_3_same(self):
        self.isub([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                  [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_isub_3_by_3_different_positive_result(self):
        self.isub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                  [[0, 1, 2], [3, 4, 5], [1, 4, 0]], 3, 3, 4)

    def test_isub_fail_3_by_3_sub_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.isub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                      [[0, 1], [0, 1], [0, 1]], 2, 3, 4)

    def test_isub_fail_3_by_3_sub_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.isub([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                      [[0, 1, 1], [0, 1, 1]], 3, 2, 4)

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

    def isub(self, first_int_matrix, rows1, columns1, bits1, second_int_matrix,
             rows2, columns2, bits2):
        first_matrix = pyrtl.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = pyrtl.Matrix(
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
        expected_output = np.asarray(
            first_int_matrix) - np.asarray(second_int_matrix)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_element_wise_multiply_basic(self):
        self.element_wise_multiply([[0]], 1, 1, 2, [[0]], 1, 1, 3)

    def test_element_wise_multiply_2_by_3(self):
        self.element_wise_multiply([[2, 4, 3], [5, 4, 7]], 2, 3, 4,
                                   [[0, 1, 2], [3, 4, 5]], 2, 3, 4)

    def test_element_wise_multiply_3_by_2(self):
        self.element_wise_multiply([[2, 4], [5, 7], [2, 5]], 3, 2, 4,
                                   [[0, 2], [3, 4], [6, 7]], 3, 2, 4)

    def test_element_wise_multiply_3_by_3_same(self):
        self.element_wise_multiply([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                                   [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_element_wise_multiply_3_by_3_different(self):
        self.element_wise_multiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                                   [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_element_wise_multiply_fail_3_by_3_multiply_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_multiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3,
                                       4,
                                       [[0, 1], [0, 1], [0, 1]], 3, 2, 4)

    def test_element_wise_multiply_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_multiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3,
                                       4,
                                       [[0, 1, 1], [0, 1, 1]], 2, 3, 4)

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

    def element_wise_multiply(self, first_int_matrix, rows1, columns1, bits1,
                              second_int_matrix, rows2, columns2, bits2):
        first_matrix = pyrtl.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = pyrtl.Matrix(
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
        expected_output = np.asarray(
            first_int_matrix) * np.asarray(second_int_matrix)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])

    def test_multiply_scalar_basic(self):
        self.multiply_number([[0]], 1, 1, 2, 1)

    def test_multiply_scalar_basic_zero(self):
        self.multiply_number([[1]], 1, 1, 2, 0)

    def test_multiply_scalar_basic_one(self):
        self.multiply_number([[1]], 1, 1, 2, 1)

    def test_multiply_scalar_3_by_3(self):
        self.multiply_number([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 3)

    def test_multiply_scalar_4_by_1(self):
        self.multiply_number([[0, 1, 0, 2]], 1, 4, 4, 5)

    def test_multiply_scalar_1_by_4(self):
        self.multiply_number([[0], [1], [0], [2]], 4, 1, 4, 5)

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

    def multiply_number(self, int_matrix, rows, columns, bits, number):
        first_matrix = pyrtl.Matrix(rows, columns, bits, value=int_matrix)
        bits = 1
        if number != 0:
            bits = math.floor(math.log(number, 2)) + 1

        b_input = pyrtl.Input(bitwidth=bits, name='b_input')

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
        expected_output = np.asarray(int_matrix) * number

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], expected_output[i][j])

    def test_multiply_fail_int(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = pyrtl.Matrix(
                3, 2, 3)
            result = first_matrix * 1


class TestMatrixInplaceMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_element_wise_imultiply_basic(self):
        self.element_wise_imultiply([[0]], 1, 1, 2, [[0]], 1, 1, 3)

    def test_element_wise_imultiply_3_by_3_same(self):
        self.element_wise_imultiply([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                                    [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_element_wise_imultiply_3_by_3_different(self):
        self.element_wise_imultiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                                    [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_element_wise_imultiply_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_imultiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3,
                                        4,
                                        [[0, 1], [0, 1], [0, 1]], 2, 3, 4)

    def test_element_wise_imultiply_fail_3_by_3_multiply_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.element_wise_imultiply([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3,
                                        4,
                                        [[0, 1, 1], [0, 1, 1]], 3, 2, 4)

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

    def element_wise_imultiply(self, first_int_matrix, rows1, columns1, bits1,
                               second_int_matrix, rows2, columns2, bits2):
        first_matrix = pyrtl.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = pyrtl.Matrix(
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
        expected_output = np.asarray(
            first_int_matrix) * np.asarray(second_int_matrix)

        for i in range(rows1):
            for j in range(columns1):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixMatrixMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_mat_mul_basic(self):
        self.matmul([[0]], 1, 1, 2, [[0]], 1, 1, 3)

    def test_mat_mul_1_by_2_multiply_2_by_1(self):
        self.matmul([[1, 2]], 1, 2, 2, [[1], [2]], 2, 1, 3)

    def test_mat_mul_3_by_3_multiply_3_by_3_same(self):
        self.matmul([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                    [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_mat_mul_3_by_3_multiply_3_by_3_different(self):
        self.matmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                    [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_mat_mul_fail_int(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = pyrtl.Matrix(
                3, 2, 3)
            result = first_matrix @ 1

    def test_mat_mul_fail_3_by_3_multiply_2_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                        [[0, 1], [0, 1], [0, 1]], 2, 3, 4)

    def test_mat_mul_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                        [[0, 1, 1], [0, 1, 1]], 2, 3, 4)

    def test_mat_mul_fail_3_by_2_multiply_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = pyrtl.Matrix(
                3, 2, 3)
            second_matrix = pyrtl.Matrix(
                3, 2, 3)
            result = first_matrix @ second_matrix

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

    def matmul(self, first_int_matrix, rows1, columns1, bits1,
               second_int_matrix, rows2, columns2, bits2):
        first_matrix = pyrtl.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = pyrtl.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        result_matrix = first_matrix @ second_matrix

        self.assertEqual(result_matrix.rows, rows1)
        self.assertEqual(result_matrix.columns, columns2)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns2, result_matrix.bits)
        expected_output = np.asarray(
            first_int_matrix) @ np.asarray(second_int_matrix)

        for i in range(rows1):
            for j in range(columns2):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixInplaceMatrixMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_imat_mul_basic(self):
        self.imatmul([[0]], 1, 1, 2, [[0]], 1, 1, 3)

    def test_imat_mul_1_by_2_multiply_2_by_1(self):
        self.imatmul([[1, 2]], 1, 2, 2, [[1], [2]], 2, 1, 3)

    def test_imat_mul_3_by_3_multiply_3_by_3_same(self):
        self.imatmul([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                     [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_imat_mul_3_by_3_multiply_3_by_3_different(self):
        self.imatmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_imat_mul_fail_3_by_3_multiply_2_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.imatmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                         [[0, 1], [0, 1], [0, 1]], 2, 3, 4)

    def test_imat_mul_fail_3_by_3_multiply_3_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.imatmul([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                         [[0, 1, 1], [0, 1, 1]], 3, 2, 4)

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

    def imatmul(self, first_int_matrix, rows1, columns1, bits1,
                second_int_matrix, rows2, columns2, bits2):
        first_matrix = pyrtl.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = pyrtl.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        first_matrix @= second_matrix

        self.assertEqual(first_matrix.rows, rows1)
        self.assertEqual(first_matrix.columns, columns2)

        output = pyrtl.Output(name='output', bitwidth=len(first_matrix))
        output <<= first_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows1, columns2, first_matrix.bits)
        expected_output = np.asarray(
            first_int_matrix) @ np.asarray(second_int_matrix)

        for i in range(rows1):
            for j in range(columns2):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixMatrixPower(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_matrix_power_3_by_3_power_0(self):
        self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0)

    def test_matrix_power_3_by_3_power_1(self):
        self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1)

    def test_matrix_power_3_by_3_power_2(self):
        self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 2)

    def test_matrix_power_fail_nonsquare(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matrix_power([[0, 0, 0, 0]], 1, 4, 4, 3)

    def test_matrix_power_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = pyrtl.Matrix(
                3, 3, 3)
            result = first_matrix ** "1"

    def test_matrix_power_fail_negative_power(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, -1)

    def test_matrix_power_random_case(self):
        self.matrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]],
                          3, 3, 4, random.randint(0, 2))

    def matrix_power(self, int_matrix, rows, columns, bits, exp):
        matrix = pyrtl.Matrix(rows, columns, bits, value=int_matrix)

        result_matrix = matrix ** exp

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows, columns, result_matrix.bits)
        expected_output = np.linalg.matrix_power(np.asarray(int_matrix), exp)

        for i in range(rows):
            for j in range(columns):
                self.assertEqual(given_output[i][j], expected_output[i][j])


class TestMatrixInplaceMatrixPower(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_imatrix_power_3_by_3_power_0(self):
        self.imatrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0)

    def test_imatrix_power_3_by_3_power_1(self):
        self.imatrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1)

    def test_imatrix_power_3_by_3_power_2(self):
        self.imatrix_power([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 2)

    def imatrix_power(self, int_matrix, rows, columns, bits, exp):
        matrix = pyrtl.Matrix(rows, columns, bits, value=int_matrix)

        matrix **= exp

        output = pyrtl.Output(name='output', bitwidth=len(matrix))
        output <<= matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), rows, columns, matrix.bits)
        expected_output = np.linalg.matrix_power(np.asarray(int_matrix), exp)

        for i in range(rows):
            for j in range(columns):
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

if __name__ == '__main__':
    currentdir = os.path.dirname(os.path.abspath(
        inspect.getfile(inspect.currentframe())))
    parentdir = os.path.dirname(currentdir)
    sys.path.insert(0, parentdir)

    import pyrtl
    # unittest.main(
    #    defaultTest='TestDot', verbosity=2)
    unittest.main(verbosity=2)
