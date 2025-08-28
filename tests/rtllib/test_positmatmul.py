import doctest
import random
import unittest

import pyrtl
import pyrtl.rtllib.testingutils as utils
from pyrtl.rtllib.matrix import Matrix, matrix_wv_to_list
from pyrtl.rtllib.positmatmul import posit_matmul
from pyrtl.positutils import decimal_to_posit


class TestDocTests(unittest.TestCase):
    """Test documentation examples."""

    def test_doctests(self):
        failures, tests = doctest.testmod(m=pyrtl.rtllib.positadder)
        self.assertGreater(tests, 0)
        self.assertEqual(failures, 0)


class PositMatrixTestBase(unittest.TestCase):
    def check_against_expected(self, result, expected_output, rows, cols, nbits):
        expected = Matrix(rows, cols, bits=nbits, value=expected_output)

        result_wv = pyrtl.Output(name='result')
        expected_wv = pyrtl.Output(name='expected')

        result_wv <<= result.to_wirevector()
        expected_wv <<= expected.to_wirevector()

        sim = pyrtl.Simulation()
        sim.step({})

        result_vals = matrix_wv_to_list(
            sim.inspect('result'), rows, cols, nbits
        )
        expected_vals = matrix_wv_to_list(
            sim.inspect('expected'), rows, cols, nbits
        )

        for i in range(len(result_vals)):
            for j in range(len(result_vals[0])):
                self.assertLessEqual(
                    abs(result_vals[i][j] - expected_vals[i][j]), 2
                )

    def generate_and_check(self, m, n, p, identity=False):
        nbits_list = [8, 16]
        es_list = [0, 1, 2]
        nbits, es = random.choice(nbits_list), random.choice(es_list)

        useed = 2 ** (2 ** es)
        maxpos = useed ** (nbits - 2)

        matrix_x_raw = [
            [random.randint(0, maxpos) for _ in range(n)] for _ in range(m)
        ]
        matrix_x = [
            [decimal_to_posit(val, nbits, es) for val in row]
            for row in matrix_x_raw
        ]
        test_x = Matrix(m, n, bits=nbits, value=matrix_x)

        if identity:
            matrix_y_raw = [
                [1 if i == j else 0 for j in range(n)] for i in range(n)
            ]
            p = n
        else:
            matrix_y_raw = [
                [random.randint(0, maxpos) for _ in range(p)]
                for _ in range(n)
            ]

        matrix_y = [
            [decimal_to_posit(val, nbits, es) for val in row]
            for row in matrix_y_raw
        ]
        test_y = Matrix(n, p, bits=nbits, value=matrix_y)

        result = posit_matmul(test_x, test_y, nbits, es)

        expected_output_raw = [[0 for _ in range(p)] for _ in range(m)]
        for i in range(m):
            for j in range(p):
                for k in range(n):
                    expected_output_raw[i][j] += (
                        matrix_x_raw[i][k] * matrix_y_raw[k][j]
                    )

        expected_output = [
            [decimal_to_posit(val, nbits, es) for val in row]
            for row in expected_output_raw
        ]

        self.check_against_expected(result, expected_output, m, p, nbits)


class TestPositMatmul(PositMatrixTestBase):
    @classmethod
    def setUpClass(cls):
        random.seed(42)

    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_posit_matmul_identity(self):
        m = random.randint(1, 5)
        n = random.randint(1, 5)
        self.generate_and_check(m, n, p=None, identity=True)

    def test_posit_matmul(self):
        m = random.randint(1, 5)
        n = random.randint(1, 5)
        p = random.randint(1, 5)
        self.generate_and_check(m, n, p, identity=False)


if __name__ == "__main__":
    unittest.main()
