import unittest
import io
import pyrtl

firrtl_output_concat_test = """\
circuit Example :
  module Example :
    input clock : Clock
    input reset : UInt<1>
    output o : UInt<13>
    wire tmp0 : UInt<13>
    wire tmp1 : UInt<7>
    wire tmp2 : UInt<13>
    node const_0_12 = UInt<4>(12)
    node const_1_3 = UInt<3>(3)
    node const_2_38 = UInt<6>(38)

    o <= tmp0
    tmp0 <= tmp2
    tmp1 <= cat(const_0_12, const_1_3)
    tmp2 <= cat(tmp1, const_2_38)
"""

firrtl_output_select_test = """\
circuit Example :
  module Example :
    input clock : Clock
    input reset : UInt<1>
    output b : UInt<6>
    wire tmp0 : UInt<6>
    wire tmp1 : UInt<1>
    wire tmp2 : UInt<1>
    wire tmp3 : UInt<1>
    wire tmp4 : UInt<1>
    wire tmp5 : UInt<1>
    wire tmp6 : UInt<1>
    wire tmp7 : UInt<6>
    wire tmp8 : UInt<2>
    wire tmp9 : UInt<3>
    wire tmp10 : UInt<4>
    wire tmp11 : UInt<5>
    wire tmp12 : UInt<6>
    node const_0_2893 = UInt<12>(2893)

    b <= tmp0
    tmp0 <= tmp7
    tmp1 <= bits(const_0_2893, 0, 0)
    tmp2 <= bits(const_0_2893, 2, 2)
    tmp3 <= bits(const_0_2893, 4, 4)
    tmp4 <= bits(const_0_2893, 6, 6)
    tmp5 <= bits(const_0_2893, 8, 8)
    tmp6 <= bits(const_0_2893, 10, 10)
    tmp7 <= tmp12
    tmp8 <= cat(tmp6, tmp5)
    tmp9 <= cat(tmp8, tmp4)
    tmp10 <= cat(tmp9, tmp3)
    tmp11 <= cat(tmp10, tmp2)
    tmp12 <= cat(tmp11, tmp1)
"""


class TestOutputFirrtl(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        pyrtl.wire._reset_wire_indexers()
        pyrtl.memory._reset_memory_indexer()

    def test_textual_consistency_concats(self):
        i = pyrtl.Const(0b1100)
        j = pyrtl.Const(0b011, bitwidth=3)
        k = pyrtl.Const(0b100110)
        o = pyrtl.Output(13, 'o')
        o <<= pyrtl.concat(i, j, k)

        buffer = io.StringIO()
        pyrtl.output_to_firrtl(buffer)

        self.assertEqual(buffer.getvalue(), firrtl_output_concat_test)

    def test_textual_consistency_selects(self):
        a = pyrtl.Const(0b101101001101)
        b = pyrtl.Output(6, 'b')
        b <<= a[::2]

        buffer = io.StringIO()
        pyrtl.output_to_firrtl(buffer)

        self.assertEqual(buffer.getvalue(), firrtl_output_select_test)


if __name__ == "__main__":
    unittest.main()
