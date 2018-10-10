import unittest
import six
import pyrtl

class TestComparisonBasicOperationsMSB1(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        # test with '101' in binary, which should be
        # 5 for an unsigned comparison and should be
        # -3 for an signed comparison
        self.c = pyrtl.Const(0b101,bitwidth=3)
        self.r = pyrtl.Register(bitwidth=3)
        self.o = pyrtl.Output(bitwidth=1, name='o')
        self.r.next <<= self.r+1

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
        self.o <<= pyrtl.signed_le( self.r, self.c)
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
        self.c = pyrtl.Const(0b101,bitwidth=4)
        self.r = pyrtl.Register(bitwidth=4)
        self.o = pyrtl.Output(bitwidth=1, name='o')
        self.r.next <<= self.r+1

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
        self.o <<= pyrtl.signed_le( self.r, self.c)
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


class TestSignedAddBasicOperations(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        # test with '101' in binary, which should be
        # 5 for an unsigned operation and should be
        # -3 for an signed operation
        self.c = pyrtl.Const(0b101,bitwidth=3)
        self.r = pyrtl.Register(bitwidth=3)
        self.o = pyrtl.Output(bitwidth=4, name='o')
        self.r.next <<= self.r+1

    def check_trace(self, correct_string):
        sim = pyrtl.Simulation()
        output_list = []
        for i in range(8):
            sim.step({})
            output_list.append(sim.value[self.o])
        bw = len(self.o)
        spaced_output = '  '.join(str(pyrtl.val_to_signed_integer(x,bw)) for x in output_list)
        self.assertEqual(spaced_output, correct_string)

    def test_basic_signed_add(self):
        self.o <<= pyrtl.signed_add(self.r, self.c)
        #                  0   1   2  3  -4  -3  -2  -1
        self.check_trace('-3  -2  -1  0  -7  -6  -5  -4')
