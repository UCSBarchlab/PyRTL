#!/usr/bin/env python

import sys
import unittest
import StringIO
import pyrtl

sys.path.append("test")
import adder

class TestAdder(unittest.TestCase):
  sim_trace = None

  @classmethod
  def setUpClass(cls):
    cls.sim_trace = adder.run_adder()

  def test_adder(self):
    output = StringIO.StringIO()
    self.sim_trace.print_trace(output)
    self.assertEqual(output.getvalue(), open("test/adder_output.txt").read())

  def test_export(self):
    output = StringIO.StringIO()
    #pyrtl.ParseState.export(pyrtl.TrivialGraphExporter(), output)

    #with open("adder.vcd", "w") as vcd_fp:
    #  TestAdder.sim_trace.print_vcd(vcd_fp)

if __name__ == "__main__":
  unittest.main()
