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
        self.assertEquals(estimate.area_estimation(), (0.00734386752, 0.01879779717361501))

    def test_area_est_unchanged_with_rom(self):
        a = pyrtl.Const(2, 8)
        b = pyrtl.Const(85, 8)
        zero = pyrtl.Const(0, 1)
        reg = pyrtl.Register(8)
        mem = pyrtl.RomBlock(8, 8, romdata=list(range(0, 256)))
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
        memread <<= mem[reg]
        self.assertEquals(estimate.area_estimation(), (0.00734386752, 0.001879779717361501))


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
        self.assertEqual(timing.max_freq(), 610.2770657878676)
        self.assertEquals(timing.max_length(), 1255.6000000000001)


class TestYosysInterface(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
