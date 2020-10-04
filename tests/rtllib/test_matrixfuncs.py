import unittest
import random
import numpy as np

import pyrtl
import pyrtl.rtllib.matrixfuncs as funcs


class TestMultiply(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_multiply_scalar(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        first_matrix = pyrtl.Matrix(3, 3, 4, value=int_matrix)

        b_input = pyrtl.Input(bitwidth=2, name='b_input')

        result_matrix = funcs.multiply(first_matrix, b_input)

        self.assertEqual(result_matrix.rows, 3)
        self.assertEqual(result_matrix.columns, 3)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({b_input: 3})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, result_matrix.bits)
        expected_output = np.asarray(int_matrix) * 3

        for i in range(3):
            for j in range(3):
                self.assertEqual(given_output[i][j], expected_output[i][j])

    def test_multiply_matrix(self):
        int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
        first_matrix = pyrtl.Matrix(
            3, 3, 4, value=int_matrix)
        second_matrix = pyrtl.Matrix(
            3, 3, 4, value=int_matrix)

        result_matrix = funcs.multiply(first_matrix, second_matrix)

        self.assertEqual(result_matrix.rows, 3)
        self.assertEqual(result_matrix.columns, 3)

        output = pyrtl.Output(name='output', bitwidth=len(result_matrix))
        output <<= result_matrix.to_WireVector()

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = matrix_result(sim.inspect(
            "output"), 3, 3, result_matrix.bits)
        expected_output = np.asarray(
            int_matrix) * np.asarray(int_matrix)

        for i in range(3):
            for j in range(3):
                self.assertEqual(given_output[i][j], expected_output[i][j])

    def test_multiply_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            int_matrix = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
            second_matrix = pyrtl.Matrix(
                3, 3, 4, value=int_matrix)
            result_matrix = funcs.multiply(1, second_matrix)


class Testsum(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_sum_basic(self):
        self.sum([[0]], 1, 1, 2, None)

    def test_sum_basic_column(self):
        self.sum([[0]], 1, 1, 2, 0)

    def test_sum_basic_row(self):
        self.sum([[0]], 1, 1, 2, 1)

    def test_sum_3_by_3(self):
        self.sum([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, None)

    def test_sum_3_by_3_column(self):
        self.sum([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0)

    def test_sum_3_by_3_row(self):
        self.sum([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1)

    def test_sum_4_by_1(self):
        self.sum([[0], [1], [0], [1]], 4, 1, 4, None)

    def test_sum_4_by_1_column(self):
        self.sum([[0], [1], [0], [1]], 4, 1, 4, 0)

    def test_sum_4_by_1_row(self):
        self.sum([[0], [1], [0], [1]], 4, 1, 4, 1)

    def test_sum_1_by_4(self):
        self.sum([[0, 1, 0, 1]], 1, 4, 4, None)

    def test_sum_1_by_4_column(self):
        self.sum([[0, 1, 0, 1]], 1, 4, 4, 0)

    def test_sum_1_by_4_row(self):
        self.sum([[0, 1, 0, 1]], 1, 4, 4, 1)

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

    def test_sum_wire(self):
        wire = pyrtl.Const(3)
        sum_wire = pyrtl.Output(name="output", bitwidth=len(wire))
        sum_wire <<= funcs.sum(wire)

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        output = sim.inspect("output")

        self.assertEqual(output, 3)

    def test_sum_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            output = funcs.sum("1", 0)

    def test_sum_fail_negative_axis(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.sum(matrix, -1)

    def test_sum_fail_axis_out_of_bounds(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.sum(matrix, 2)

    def test_sum_fail_string_axis(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.sum(matrix, "0")

    def test_sum_fail_string_bits(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.sum(matrix, axis=0, bits="0")

    def test_sum_fail_negative_bits(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.sum(matrix, axis=0, bits=-1)

    def test_sum_fail_zero_bits(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.sum(matrix, axis=0, bits=0)

    def sum(self, int_matrix, rows, columns, bits, axis):
        matrix = pyrtl.Matrix(
            rows, columns, bits, value=int_matrix, max_bits=bits * rows)

        result = funcs.sum(
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
        expected_output = np.array(np.sum(
            np.array(int_matrix), axis), ndmin=2)

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
        self.min([[0]], 1, 1, 2, None)

    def test_min_basic_column(self):
        self.min([[0]], 1, 1, 2, 0)

    def test_min_basic_row(self):
        self.min([[0]], 1, 1, 2, 1)

    def test_min_3_by_3(self):
        self.min([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, None)

    def test_min_3_by_3_column(self):
        self.min([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0)

    def test_min_3_by_3_row(self):
        self.min([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1)

    def test_min_4_by_1(self):
        self.min([[0], [1], [0], [1]], 4, 1, 4, None)

    def test_min_4_by_1_column(self):
        self.min([[0], [1], [0], [1]], 4, 1, 4, 0)

    def test_min_4_by_1_row(self):
        self.min([[0], [1], [0], [1]], 4, 1, 4, 1)

    def test_min_1_by_4(self):
        self.min([[0, 1, 0, 1]], 1, 4, 4, None)

    def test_min_1_by_4_column(self):
        self.min([[0, 1, 0, 1]], 1, 4, 4, 0)

    def test_min_1_by_4_row(self):
        self.min([[0, 1, 0, 1]], 1, 4, 4, 1)

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

    def test_min_wire(self):
        wire = pyrtl.Const(3)
        sum_wire = pyrtl.Output(name="output", bitwidth=len(wire))
        sum_wire <<= funcs.min(wire)

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        output = sim.inspect("output")

        self.assertEqual(output, 3)

    def test_min_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            output = funcs.min("1", 0)

    def test_min_fail_axis_out_of_bounds(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.min(matrix, 4)

    def test_min_fail_axis_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.min(matrix, -1)

    def test_min_fail_axis_string(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.min(matrix, "0")

    def test_min_fail_bits_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.min(matrix, axis=0, bits="1")

    def test_min_fail_bits_zero(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.min(matrix, axis=0, bits=0)

    def test_min_fail_bits_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.min(matrix, axis=0, bits=-2)

    def min(self, int_matrix, rows, columns, bits, axis):
        matrix = pyrtl.Matrix(
            rows, columns, bits, value=int_matrix, max_bits=bits * rows)

        result = funcs.min(
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
        expected_output = np.array(np.min(np.array(int_matrix), axis), ndmin=2)

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
        self.max([[0]], 1, 1, 2, None)

    def test_max_basic_columns(self):
        self.max([[0]], 1, 1, 2, 0)

    def test_max_basic_rows(self):
        self.max([[0]], 1, 1, 2, 1)

    def test_max_3_by_3(self):
        self.max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, None)

    def test_max_3_by_3_columns(self):
        self.max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0)

    def test_max_3_by_3_rows(self):
        self.max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1)

    def test_max_4_by_1(self):
        self.max([[0], [1], [0], [1]], 4, 1, 4, None)

    def test_max_4_by_1_columns(self):
        self.max([[0], [1], [0], [1]], 4, 1, 4, 0)

    def test_max_4_by_1_rows(self):
        self.max([[0], [1], [0], [1]], 4, 1, 4, 1)

    def test_max_1_by_4(self):
        self.max([[0, 1, 0, 1]], 1, 4, 4, None)

    def test_max_1_by_4_columns(self):
        self.max([[0, 1, 0, 1]], 1, 4, 4, 0)

    def test_max_1_by_4_rows(self):
        self.max([[0, 1, 0, 1]], 1, 4, 4, 1)

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

    def test_max_wire(self):
        wire = pyrtl.Const(3)
        max_wire = pyrtl.Output(name="output", bitwidth=len(wire))
        max_wire <<= funcs.max(wire)

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        output = sim.inspect("output")

        self.assertEqual(output, 3)

    def test_max_fail_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            output = funcs.max("1", 0)

    def test_max_fail_axis_out_of_bounds(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.max(matrix, 4)

    def test_max_fail_axis_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.max(matrix, -1)

    def test_max_fail_axis_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.max(matrix, "0")

    def test_max_fail_bits_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.max(matrix, axis=0, bits="1")

    def test_max_fail_bits_zero(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.max(matrix, axis=0, bits=0)

    def test_max_fail_bits_negative(self):
        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.max(matrix, axis=0, bits=-1)

    def max(self, int_matrix, rows, columns, bits, axis):
        matrix = pyrtl.Matrix(
            rows, columns, bits, value=int_matrix, max_bits=bits * rows)

        result = funcs.max(
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
        expected_output = np.array(np.max(np.array(int_matrix), axis), ndmin=2)

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
        self.argument_max([[0]], 1, 1, 2, None)

    def test_argument_max_basic_columns(self):
        self.argument_max([[0]], 1, 1, 2, 0)

    def test_argument_max_basic_rows(self):
        self.argument_max([[0]], 1, 1, 2, 1)

    def test_argument_max_3_by_3(self):
        self.argument_max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, None)

    def test_argument_max_3_by_3_columns(self):
        self.argument_max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 0)

    def test_argument_max_3_by_3_rows(self):
        self.argument_max([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4, 1)

    def test_argument_max_4_by_1(self):
        self.argument_max([[0], [1], [0], [1]], 4, 1, 4, None)

    def test_argument_max_4_by_1_columns(self):
        self.argument_max([[0], [1], [0], [1]], 4, 1, 4, 0)

    def test_argument_max_4_by_1_rows(self):
        self.argument_max([[0], [1], [0], [1]], 4, 1, 4, 1)

    def test_argument_max_1_by_4(self):
        self.argument_max([[0, 1, 0, 1]], 1, 4, 4, None)

    def test_argument_max_1_by_4_columns(self):
        self.argument_max([[0, 1, 0, 1]], 1, 4, 4, 0)

    def test_argument_max_1_by_4_rows(self):
        self.argument_max([[0, 1, 0, 1]], 1, 4, 4, 1)

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

    def test_argument_max_wire(self):
        wire = pyrtl.Const(3)
        sum_wire = pyrtl.Output(name="output", bitwidth=len(wire))
        sum_wire <<= funcs.argmax(wire)

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        output = sim.inspect("output")

        self.assertEqual(output, 0)

    def test_argument_max_string(self):

        with self.assertRaises(pyrtl.PyrtlError):
            output = funcs.argmax("1", axis=0)

    def test_argument_max_axis_out_of_bounds(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.argmax(matrix, axis=4)

    def test_argument_max_axis_negative(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.argmax(matrix, axis=-1)

    def test_argument_max_axis_string(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.argmax(matrix, "1")

    def test_argument_max_bits_string(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.argmax(matrix, axis=1, bits="1")

    def test_argument_max_bits_negative(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.argmax(matrix, axis=1, bits=-1)

    def test_argument_max_bits_zero(self):

        with self.assertRaises(pyrtl.PyrtlError):
            matrix = pyrtl.Matrix(
                3, 3, 3)
            output = funcs.argmax(matrix, axis=1, bits=0)

    def argument_max(self, int_matrix, rows, columns, bits, axis):
        matrix = pyrtl.Matrix(
            rows, columns, bits, value=int_matrix, max_bits=bits * rows)

        result = funcs.argmax(
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

        expected_output = np.array(
            np.argmax(np.array(int_matrix), axis), ndmin=2)

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
        self.dot([[0]], 1, 1, 2, [[0]], 1, 1, 3)

    def test_dot_1_by_2_multiply_2_by_1(self):
        self.dot([[1, 2]], 1, 2, 2, [[1], [2]], 2, 1, 3)

    def test_dot_1_by_2_multiply_1_by_2(self):
        self.dot([[1, 2]], 1, 2, 2, [[1, 2]], 1, 2, 3)

    def test_dot_2_by_1_multiply_2_by_1(self):
        self.dot([[1], [2]], 2, 1, 3, [[1], [2]], 2, 1, 3)

    def test_dot_2_by_1_multiply_1_by_2(self):
        self.dot([[1], [2]], 2, 1, 3, [[1, 2]], 1, 2, 3)

    def test_dot_3_by_3_multiply_3_by_3_same(self):
        self.dot([[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_dot_3_by_3_multiply_3_by_3_different(self):
        self.dot([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                 [[0, 1, 2], [3, 4, 5], [6, 7, 8]], 3, 3, 4)

    def test_dot_both_wires(self):
        first = pyrtl.Const(5)
        second = pyrtl.Const(3)

        dot_product = funcs.dot(first, second)

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
        second = pyrtl.Matrix(
            1, 1, 3, value=[[3]])

        dot_product = funcs.dot(first, second)

        output = pyrtl.Output(name='output', bitwidth=len(dot_product))
        output <<= dot_product

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        sim.step({})

        given_output = sim.inspect('output')
        expected_output = 15

        self.assertEqual(given_output, expected_output)

    def test_dot_second_wire(self):
        first = pyrtl.Matrix(
            1, 1, 3, value=[[5]])
        second = pyrtl.Const(3)

        dot_product = funcs.dot(first, second)

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
            first_matrix = pyrtl.Matrix(
                3, 2, 3)
            result = funcs.dot(first_matrix, 1)

    def test_dot_fail_int_first(self):
        with self.assertRaises(pyrtl.PyrtlError):
            first_matrix = pyrtl.Matrix(
                3, 2, 3)
            result = funcs.dot(1, first_matrix)

    def test_dot_fail_1_by_2_multiply_1_by_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.dot([[1, 2]], 1, 2, 2, [[1, 2, 3]], 1, 3, 3)

    def test_dot_fail_3_by_3_multiply_2_by_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.dot([[2, 4, 3], [5, 4, 7], [2, 5, 1]], 3, 3, 4,
                     [[0, 1], [0, 1]], 2, 2, 4)

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

    def dot(self, first_int_matrix, rows1, columns1, bits1,
            second_int_matrix, rows2, columns2, bits2):
        first_matrix = pyrtl.Matrix(
            rows1, columns1, bits1, value=first_int_matrix)
        second_matrix = pyrtl.Matrix(
            rows2, columns2, bits2, value=second_int_matrix)

        result_matrix = funcs.dot(first_matrix, second_matrix)

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

        first_int_matrix = np.array(first_int_matrix, ndmin=2)
        second_int_matrix = np.array(second_int_matrix, ndmin=2)

        if first_int_matrix.shape[0] == 1 or first_int_matrix.shape[1] == 1:
            if second_int_matrix.shape[0] == 1 or second_int_matrix.shape[1] == 1:
                first_int_matrix = np.squeeze(first_int_matrix)
                second_int_matrix = np.squeeze(second_int_matrix)

        expected_output = np.dot(
            first_int_matrix, second_int_matrix).astype(int)

        if isinstance(given_output, int):
            self.assertEqual(given_output, expected_output)
        else:
            for i in range(expected_output.shape[0]):
                for j in range(expected_output.shape[1]):
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
    # unittest.main(
    #    defaultTest='TestDot', verbosity=2)
    unittest.main(verbosity=2)
