import sys
sys.path.append("..")
sys.path.append("test")
import unittest
import StringIO

from pyrtl.pyrtl import *
from pyrtl.simulation import *
from pyrtl.export import *
import adder

class TestAdder(unittest.TestCase):
  def setUp(self):
    self.sim_trace = adder.run_adder()

  def test_adder(self):
    output = StringIO.StringIO()
    self.sim_trace.print_trace(output)
    self.assertEqual(output.getvalue(), open("test/adder_output.txt").read())

if __name__ == "__main__":
  unittest.main()
