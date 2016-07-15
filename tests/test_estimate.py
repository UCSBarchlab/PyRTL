from __future__ import print_function, unicode_literals, absolute_import
from .test_transform import NetWireNumTestCases
from pyrtl.wire import Const, Output
from pyrtl.analysis import estimate

import unittest
import pyrtl
import io


class TestAreaEstimate(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    def test_area_est_unchanged(self):
        a = pyrtl.Const(2, 8)
        b = pyrtl.Const(85, 8)
        zero = pyrtl.Const(0, 1)
        reg = pyrtl.Register(8)
        mem = pyrtl.MemBlock(8, 8)
        out = pyrtl.Output(8)
        nota, aLSB, athenb, aORb, aANDb, aNANDb, \
        aXORb, aequalsb, altb, agtb, aselectb, \
        aplusb, bminusa, atimesb, memread = [pyrtl.Output() for i in range(15)]
        out <<= zero
        nota <<= ~a
        aLSB <<= a[0]
        athenb <<= pyrtl.concat(a, b)
        aORb <<= a | b
        aANDb <<= a & b
        aNANDb <<= a.nand(b)
        aXORb <<= a ^ b
        aequalsb <<= a==b
        altb <<= a < b
        agtb <<= a > b
        aselectb <<= pyrtl.select(zero, a, b)
        reg.next <<= a
        aplusb <<= a + b
        bminusa <<= a - b
        atimesb <<= a*b
        memread <<= mem[0]
        mem[1] <<= a
        curr_area = estimate.area_estimation()
        for i in range(10):
            self.assertEquals(curr_area, estimate.area_estimation())


class TestTimingEstimate(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    def test_time_est_unchanged(self):
        a = pyrtl.Const(2, 8)
        b = pyrtl.Const(85, 8)
        zero = pyrtl.Const(0, 1)
        reg = pyrtl.Register(8)
        mem = pyrtl.MemBlock(8, 8)
        out = pyrtl.Output(8)
        nota, aLSB, athenb, aORb, aANDb, aNANDb, \
        aXORb, aequalsb, altb, agtb, aselectb, \
        aplusb, bminusa, atimesb, memread = [pyrtl.Output() for i in range(15)]
        out <<= zero
        nota <<= ~a
        aLSB <<= a[0]
        athenb <<= pyrtl.concat(a, b)
        aORb <<= a | b
        aANDb <<= a & b
        aNANDb <<= a.nand(b)
        aXORb <<= a ^ b
        aequalsb <<= a == b
        altb <<= a < b
        agtb <<= a > b
        aselectb <<= pyrtl.select(zero, a, b)
        reg.next <<= a
        aplusb <<= a + b
        bminusa <<= a - b
        atimesb <<= a * b
        memread <<= mem[0]
        mem[1] <<= a
        timing = estimate.TimingAnalysis()
        maxlength = timing.max_length()
        self.assertEquals(maxlength, timing.max_length())
        timing2 = estimate.TimingAnalysis()
        self.assertEqual(maxlength, timing2.max_length())

class TestYosysInterface(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

