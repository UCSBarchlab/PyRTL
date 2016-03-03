from __future__ import print_function, unicode_literals, absolute_import
from .test_transform import NetWireNumTestCases
from pyrtl.wire import Const,  Output

import unittest
import pyrtl
import io


class TestAreaEstimate(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()


class TestTimingEstimate(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()


class TestYosysInterface(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

