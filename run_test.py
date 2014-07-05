#!/usr/bin/env python

import sys
sys.path.append("test")
import unittest
import StringIO

import adder

class TestAdder(unittest.TestCase):
  sim_trace = None

  @classmethod
  def setUpClass(cls):
    TestAdder.sim_trace = adder.run_adder()

  def test_adder(self):
    output = StringIO.StringIO()
    TestAdder.sim_trace.print_trace(output)
    self.assertEqual(output.getvalue(), open("test/adder_output.txt").read())

  def test_export(self):
    output = StringIO.StringIO()
    adder.ParseState.export(adder.TrivialGraphExporter(), output)
    with open("adder.vcd", "w") as vcd_fp:
      TestAdder.sim_trace.print_vcd(vcd_fp)
    #print output.getvalue()
    #with open("curr.txt", "w") as fp:
    #  fp.write(output.getvalue())
    #self.assertEqual(output.getvalue(), open("test/adder_export.txt", "r").read())

if __name__ == "__main__":
  unittest.main()
