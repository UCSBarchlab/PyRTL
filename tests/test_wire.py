import unittest
import random
import pyrtl

from helperfunctions import *


class TestWireVector(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_assignment_small(self):
        c = pyrtl.Register(bitwidth=3)
        c.next <<= pyrtl.Const(1, bitwidth=3)

    def test_assignment_unspec_width(self):
        c = pyrtl.Register(bitwidth=3)
        c.next <<= pyrtl.Const(1)

    def test_assignment_raw(self):
        c = pyrtl.Register(bitwidth=3)
        c.next <<= 1

    def test_assignment_large(self):
        c = pyrtl.Register(bitwidth=3)
        c.next <<= pyrtl.Const(202)

    def test_register_assignment_direct(self):
        with self.assertRaises(pyrtl.PyrtlError):
            c = pyrtl.Register(bitwidth=3)
            c.next = 1

    def test_register_assignment_not_next(self):
        with self.assertRaises(pyrtl.PyrtlError):
            c = pyrtl.Register(bitwidth=3)
            c <<= 1

    def test_logic_operatons(self):
        with self.assertRaises(pyrtl.PyrtlError):
            c = pyrtl.Register(bitwidth=1)
            c.next <<= c or True

    def test_slice(self):
        testmissing()

    def test_zero_extend(self):
        testmissing()

    def test_sign_extend(self):
        testmissing()


# -------------------------------------------------------------------
class TestConst(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_const_integers(self):
        c = pyrtl.Const(1)
        self.assertTrue(c.val == 1)
        self.assertTrue(c.bitwidth == 1)

        c = pyrtl.Const(5)
        self.assertTrue(c.val == 5)
        self.assertTrue(c.bitwidth == 3)

        c = pyrtl.Const(1, bitwidth=5)
        self.assertTrue(c.val == 1)
        self.assertTrue(c.bitwidth == 5)

    def test_const_string(self):
        c = pyrtl.Const("1'1")
        self.assertTrue(c.val == 1)
        self.assertTrue(c.bitwidth == 1)

        c = pyrtl.Const("5'3")
        self.assertTrue(c.val == 3)
        self.assertTrue(c.bitwidth == 5)

        c = pyrtl.Const("5'b11")
        self.assertTrue(c.val == 3)
        self.assertTrue(c.bitwidth == 5)

        c = pyrtl.Const("16'xff")
        self.assertTrue(c.val == 0xff)
        self.assertTrue(c.bitwidth == 16)

        c = pyrtl.Const("17'xff")
        self.assertTrue(c.val == 0xff)
        self.assertTrue(c.bitwidth == 17)

        c = pyrtl.Const("5'b011")
        self.assertTrue(c.val == 3)
        self.assertTrue(c.bitwidth == 5)

    def test_const_badstring(self):
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1")
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "-1")
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1bx")
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1ba")
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1'bx")
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1'ba")
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1'b10")
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1'-b10")
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "-1'b10")
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "5'b111111'")

# -------------------------------------------------------------------
class TestRTLAdderDesign(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_complete_adders(self):
        for bitwidth in range(9, 10):
            r = pyrtl.Register(bitwidth=bitwidth, name='r')
            const_one = pyrtl.Const(1)
            addby = const_one.zero_extended(bitwidth)
            sum, cout = generate_full_adder(r, addby)
            r.next <<= sum

            self.assertTrue(isinstance(r, pyrtl.Register))
            self.assertTrue(isinstance(cout, pyrtl.WireVector))
            pyrtl.reset_working_block()

