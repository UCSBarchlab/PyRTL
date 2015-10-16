from pyrtl.rtllib import strlib
import unittest


class TestStringConversion(unittest.TestCase):

    def test_simple_conversion(self):
        self.assertEqual([0xa7, 0x23], strlib.str_to_int_array("a7 23"))

    def test_binary_conversion(self):
        result = strlib.str_to_int_array("0100 0110 010", base=2)
        self.assertEqual(result, [4, 6, 2])

    def test_empty(self):
        result = strlib.str_to_int_array("")
        self.assertEqual(result, [])

    def test_multiline(self):
        text = """
        374 1c
        a
        34 76"""
        result = strlib.str_to_int_array(text)
        self.assertEqual([0x374, 0x1c, 0xa, 0x34, 0x76], result)

    def test_invalid_str(self):
        with self.assertRaises(ValueError):
            strlib.str_to_int_array("hello")

    def test_invalid_bin_str(self):
        with self.assertRaises(ValueError):
            strlib.str_to_int_array("0313", 2)

    def test_no_override(self):
        with self.assertRaises(ValueError):
            strlib.str_to_int_array("0x0313", 2)
