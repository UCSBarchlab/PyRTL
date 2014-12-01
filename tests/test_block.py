import unittest
import random
import pyrtl

from helperfunctions import testmissing


class TestBlock(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_add_wirevector_simple(self):
        w = pyrtl.WireVector(name='testwire', bitwidth=3)
        pyrtl.working_block().add_wirevector(w)
        self.assertTrue(w in pyrtl.working_block().wirevector_set)
        self.assertTrue('testwire' in pyrtl.working_block().wirevector_by_name)

    def test_add_net(self):
        self.assertRaises(pyrtl.PyrtlInternalError, pyrtl.working_block().add_net, None)
        self.assertRaises(pyrtl.PyrtlInternalError, pyrtl.working_block().add_net, 1)
        self.assertRaises(pyrtl.PyrtlInternalError, pyrtl.working_block().add_net, "hi")

    def test_undriven_net(self):
        w = pyrtl.WireVector(name='testwire', bitwidth=3)
        self.assertRaises(pyrtl.PyrtlError, pyrtl.working_block().sanity_check)

    def test_sanity_check(self):
        testmissing()


if __name__ == "__main__":
    unittest.main()


