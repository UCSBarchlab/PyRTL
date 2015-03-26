import unittest
import random
import io
import pyrtl

from helperfunctions import testmissing


class TestVerilog(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def checkname(self, name):
        t_in = pyrtl.WireVector(name=name, bitwidth=3)
        t_out = pyrtl.WireVector(name='t_out', bitwidth=3)
        t_out <<= t_in + 1
        with io.BytesIO() as testbuffer:
            pyrtl.output_to_verilog(testbuffer)
        self.assert_(True)

    def test_verilog_check_valid_name_good(self):
        self.checkname('abc')

    def test_verilog_check_valid_name_good2(self):
        self.checkname('a')

    def test_verilog_check_valid_name_good2(self):
        self.checkname('B')

    def test_verilog_check_valid_name_good3(self):
        self.checkname('BC')

    def test_verilog_check_valid_name_good4(self):
        self.checkname('Kabc')

    def test_verilog_check_valid_name_good5(self):
        self.checkname('B_ac')

    def test_verilog_check_valid_name_good6(self):
        self.checkname('_asdvqa')

    def test_verilog_check_valid_name_good7(self):
        self.checkname('_Bs_')

    def test_verilog_check_valid_name_good8(self):
        self.checkname('fd$oeoe')

    def test_verilog_check_valid_name_good9(self):
        self.checkname('_B$$s')

    def test_verilog_check_valid_name_bad(self):
        self.assertRaises(pyrtl.PyrtlError, self.checkname, 'carne asda')
        self.assertRaises(pyrtl.PyrtlError, self.checkname, 'asd%kask')
        self.assertRaises(pyrtl.PyrtlError, self.checkname, "flipin'")
        self.assertRaises(pyrtl.PyrtlError, self.checkname, ' jklol')

if __name__ == "__main__":
    unittest.main()
