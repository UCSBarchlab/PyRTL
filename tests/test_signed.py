import unittest
import six
import pyrtl


class TestComparisonBasicOperationsMSB1(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        # test with '101' in binary, which should be
        # 5 for an unsigned comparison and should be
        # -3 for an signed comparison
        self.c = pyrtl.Const(0b101, bitwidth=3)
        self.r = pyrtl.Register(bitwidth=3)
        self.o = pyrtl.Output(bitwidth=1, name='o')
        self.r.next <<= self.r + 1

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = six.StringIO()
        sim_trace.print_trace(output, compact=True)
        spaced_output = '  '.join(output.getvalue())  # add spaces to string
        self.assertEqual(spaced_output, correct_string)

    def test_basic_unsigned_lt(self):
        self.o <<= self.r < self.c
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     1  1  1  1  1  0  0  0  \n')

    def test_basic_unsigned_lte(self):
        self.o <<= self.r <= self.c
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     1  1  1  1  1  1  0  0  \n')

    def test_basic_unsigned_gt(self):
        self.o <<= self.r > self.c
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     0  0  0  0  0  0  1  1  \n')

    def test_basic_unsigned_gte(self):
        self.o <<= self.r >= self.c
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     0  0  0  0  0  1  1  1  \n')

    def test_basic_signed_lt(self):
        self.o <<= pyrtl.signed_lt(self.r, self.c)
        #                       0  1  2  3 -4 -3 -2 -1
        self.check_trace('o     0  0  0  0  1  0  0  0  \n')

    def test_basic_signed_lte(self):
        self.o <<= pyrtl.signed_le(self.r, self.c)
        #                       0  1  2  3 -4 -3 -2 -1
        self.check_trace('o     0  0  0  0  1  1  0  0  \n')

    def test_basic_signed_gt(self):
        self.o <<= pyrtl.signed_gt(self.r, self.c)
        #                       0  1  2  3 -4 -3 -2 -1
        self.check_trace('o     1  1  1  1  0  0  1  1  \n')

    def test_basic_signed_gte(self):
        self.o <<= pyrtl.signed_ge(self.r, self.c)
        #                       0  1  2  3 -4 -3 -2 -1
        self.check_trace('o     1  1  1  1  0  1  1  1  \n')


class TestComparisonBasicOperations_MSB0(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        # test with '0101' in binary, which should be
        # 5 for an unsigned comparison and should be
        # 5 for an signed comparison
        self.c = pyrtl.Const(0b101, bitwidth=4)
        self.r = pyrtl.Register(bitwidth=4)
        self.o = pyrtl.Output(bitwidth=1, name='o')
        self.r.next <<= self.r + 1

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = six.StringIO()
        sim_trace.print_trace(output, compact=True)
        spaced_output = '  '.join(output.getvalue())  # add spaces to string
        self.assertEqual(spaced_output, correct_string)

    def test_basic_unsigned_lt(self):
        self.o <<= self.r < self.c
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     1  1  1  1  1  0  0  0  \n')

    def test_basic_unsigned_lte(self):
        self.o <<= self.r <= self.c
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     1  1  1  1  1  1  0  0  \n')

    def test_basic_unsigned_gt(self):
        self.o <<= self.r > self.c
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     0  0  0  0  0  0  1  1  \n')

    def test_basic_unsigned_gte(self):
        self.o <<= self.r >= self.c
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     0  0  0  0  0  1  1  1  \n')

    def test_basic_signed_lt(self):
        self.o <<= pyrtl.signed_lt(self.r, self.c)
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     1  1  1  1  1  0  0  0  \n')

    def test_basic_signed_lte(self):
        self.o <<= pyrtl.signed_le(self.r, self.c)
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     1  1  1  1  1  1  0  0  \n')

    def test_basic_signed_gt(self):
        self.o <<= pyrtl.signed_gt(self.r, self.c)
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     0  0  0  0  0  0  1  1  \n')

    def test_basic_signed_gte(self):
        self.o <<= pyrtl.signed_ge(self.r, self.c)
        #                       0  1  2  3  4  5  6  7
        self.check_trace('o     0  0  0  0  0  1  1  1  \n')


class TestSignedArithBasicOperations(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        # test with '101' in binary, which should be
        # 5 for an unsigned operation and should be
        # -3 for an signed operation
        self.c = pyrtl.Const(0b101, bitwidth=3)
        self.r = pyrtl.Register(bitwidth=3)
        self.o = pyrtl.Output(bitwidth=4, name='o')
        self.r.next <<= self.r + 1

    def check_trace(self, correct_string):
        sim = pyrtl.Simulation()
        output_list = []
        for i in range(8):
            sim.step({})
            output_list.append(sim.value[self.o])
        bw = len(self.o)
        spaced_output = '  '.join(str(pyrtl.val_to_signed_integer(x, bw)) for x in output_list)
        self.assertEqual(spaced_output, correct_string)

    def test_basic_signed_add(self):
        self.o <<= pyrtl.signed_add(self.r, self.c)
        #                  0   1   2  3  -4  -3  -2  -1
        self.check_trace('-3  -2  -1  0  -7  -6  -5  -4')

    def test_basic_signed_add_signed_const(self):
        self.o <<= pyrtl.signed_add(self.r, pyrtl.Const(-3, signed=True))
        self.check_trace('-3  -2  -1  0  -7  -6  -5  -4')

    def test_basic_signed_add_neg_integer(self):
        self.o <<= pyrtl.signed_add(self.r, -3)
        self.check_trace('-3  -2  -1  0  -7  -6  -5  -4')

    def test_basic_signed_mult(self):
        self.o <<= pyrtl.signed_mult(self.r, self.c)
        #                 0   1   2  3  -4  -3  -2  -1
        self.check_trace('0  -3  -6  7  -4  -7  6  3')
        # the above numbers don't look like multiplication but when you sign
        # extend the inputs, truncate to the last 4 digits and then sign extend,
        # the output I assure that they are indeed correct. :)

    def test_basic_signed_mult_const_with_bitwidth(self):
        self.o <<= pyrtl.signed_mult(self.r, pyrtl.Const(-2, bitwidth=3))
        #                 0   1   2   3  -4 -3 -2 -1
        self.check_trace('0  -2  -4  -6  -8  6  4  2')
        # this one is multiplies by -2 and the trend is easier to see (-4 x -3 does
        # overflow the 4 bits though).

    def test_basic_signed_mult_signed_const(self):
        self.o <<= pyrtl.signed_mult(self.r, pyrtl.Const(-2, signed=True))
        self.check_trace('0  -2  -4  -6  -8  6  4  2')

    def test_basic_signed_mult_neg_integer(self):
        self.o <<= pyrtl.signed_mult(self.r, -2)
        self.check_trace('0  -2  -4  -6  -8  6  4  2')

    def test_basic_signed_mult_commutative(self):
        self.o <<= pyrtl.signed_mult(-2, self.r)
        self.check_trace('0  -2  -4  -6  -8  6  4  2')
