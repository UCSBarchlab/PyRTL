import functools
import io
import os
import random
import sys
import unittest

import pyrtl
import pyrtl.corecircuits
import pyrtl.helperfuncs
from pyrtl.rtllib import testingutils as utils

# ---------------------------------------------------------------


class TestWireVectorList(unittest.TestCase):
    def setUp(self):
        pass

    def test_input_list_type(self):
        inputs = pyrtl.helperfuncs.input_list('one, two, three')
        self.assertTrue(all(isinstance(inp, pyrtl.Input) for inp in inputs))

    def test_output_list_type(self):
        outputs = pyrtl.helperfuncs.output_list('one, two, three')
        self.assertTrue(all(isinstance(outp, pyrtl.Output) for outp in outputs))

    def test_register_list_type(self):
        registers = pyrtl.helperfuncs.register_list('one, two, three')
        self.assertTrue(all(isinstance(reg, pyrtl.Register) for reg in registers))

    def test_wirevector_list_type(self):
        # Single string of names
        wirevectors = pyrtl.helperfuncs.wirevector_list('one, two, three')
        self.assertTrue(all(isinstance(wire, pyrtl.WireVector) for wire in wirevectors))
        self.assertListEqual([wire.bitwidth for wire in wirevectors], [1, 1, 1])

        # List of names
        wirevectors = pyrtl.helperfuncs.wirevector_list('one, two, three')
        self.assertTrue(all(isinstance(wire, pyrtl.WireVector) for wire in wirevectors))
        self.assertListEqual([wire.bitwidth for wire in wirevectors], [1, 1, 1])

    def test_wirevector_list_bitwidth(self):
        wirevectors = pyrtl.helperfuncs.wirevector_list('one, two, three')
        self.assertListEqual([wire.bitwidth for wire in wirevectors], [1, 1, 1])

        wirevectors = pyrtl.helperfuncs.wirevector_list('one, two, three', 8)
        self.assertListEqual([wire.bitwidth for wire in wirevectors], [8, 8, 8])

    def test_wirevector_list_per_wire_width(self):
        wirevectors = pyrtl.helperfuncs.wirevector_list('one/2, two/4, three/8')
        self.assertListEqual([wire.bitwidth for wire in wirevectors], [2, 4, 8])

        wirevectors = pyrtl.helperfuncs.wirevector_list(['one', 'two', 'three'], [2, 4, 8])
        self.assertListEqual([wire.bitwidth for wire in wirevectors], [2, 4, 8])

    def test_wirevector_list_raise_errors(self):

        with self.assertRaises(ValueError):
            pyrtl.helperfuncs.wirevector_list(['one', 'two', 'three'], [2, 4])

        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.helperfuncs.wirevector_list('one/2, two/4, three/8', 16)

        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.helperfuncs.wirevector_list(['one/2', 'two/4', 'three/8'], [8, 4, 2])


class TestNonCoreHelpers(unittest.TestCase):
    def setUp(self):
        pass

    def test_log2(self):
        self.assertEqual(pyrtl.log2(1), 0)
        self.assertEqual(pyrtl.log2(2), 1)
        self.assertEqual(pyrtl.log2(8), 3)
        self.assertEqual(pyrtl.log2(16), 4)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.log2(-1)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.log2(1.5)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.log2(0)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.log2(7)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.log2(9)

    def test_truncate_function(self):
        self.assertEqual(pyrtl.truncate(5, 3), 5)
        self.assertEqual(pyrtl.truncate(9, 3), 1)
        self.assertEqual(pyrtl.truncate(-1, 3), 7)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.truncate(5, -1)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.truncate(29, 0)

    def test_val_to_signed_integer(self):
        self.assertEqual(pyrtl.val_to_signed_integer(0b000, 3), 0)
        self.assertEqual(pyrtl.val_to_signed_integer(0b001, 3), 1)
        self.assertEqual(pyrtl.val_to_signed_integer(0b010, 3), 2)
        self.assertEqual(pyrtl.val_to_signed_integer(0b011, 3), 3)
        self.assertEqual(pyrtl.val_to_signed_integer(0b100, 3), -4)
        self.assertEqual(pyrtl.val_to_signed_integer(0b101, 3), -3)
        self.assertEqual(pyrtl.val_to_signed_integer(0b110, 3), -2)
        self.assertEqual(pyrtl.val_to_signed_integer(0b111, 3), -1)

    def test_infer_val_and_bitwidth(self):
        self.assertEqual(pyrtl.infer_val_and_bitwidth(2, bitwidth=5), (2, 5))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(3), (3, 2))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(True), (1, 1))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(False), (0, 1))
        self.assertEqual(pyrtl.infer_val_and_bitwidth("5'd12"), (12, 5))
        self.assertEqual(pyrtl.infer_val_and_bitwidth("5'b10"), (2, 5))
        self.assertEqual(pyrtl.infer_val_and_bitwidth("5'b10"), (2, 5))
        self.assertEqual(pyrtl.infer_val_and_bitwidth("8'B 0110_1100"), (108, 8))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(-3, bitwidth=5), (0b11101, 5))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(3, signed=True), (3, 3))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(-3, signed=True), (5, 3))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(-4, signed=True), (4, 3))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(-3, bitwidth=5, signed=True), (29, 5))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(3, bitwidth=2), (3, 2))

        self.assertEqual(pyrtl.infer_val_and_bitwidth(0), (0, 1))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(1), (1, 1))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(2), (2, 2))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(3), (3, 2))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(4), (4, 3))

        self.assertEqual(pyrtl.infer_val_and_bitwidth(0, signed=True), (0, 1))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(1, signed=True), (1, 2))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(2, signed=True), (2, 3))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(3, signed=True), (3, 3))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(4, signed=True), (4, 4))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(-1, signed=True), (1, 1))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(-2, signed=True), (2, 2))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(-3, signed=True), (5, 3))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(-4, signed=True), (4, 3))
        self.assertEqual(pyrtl.infer_val_and_bitwidth(-5, signed=True), (11, 4))

        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.infer_val_and_bitwidth(-3)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.infer_val_and_bitwidth(True, signed=True)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.infer_val_and_bitwidth(3, bitwidth=2, signed=True)


class TestMatchBitpattern(unittest.TestCase):
    def setUp(self):
        random.seed(8492049)
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output, compact=True)
        self.assertEqual(output.getvalue(), correct_string)

    def test_pattern_type_or_length_mismatch(self):
        instr = pyrtl.WireVector(name='instr', bitwidth=8)
        with self.assertRaises(pyrtl.PyrtlError):
            o, _ = pyrtl.match_bitpattern(instr, '000100010')
        with self.assertRaises(pyrtl.PyrtlError):
            o, _ = pyrtl.match_bitpattern(instr, '0001000')
        with self.assertRaises(pyrtl.PyrtlError):
            o, _ = pyrtl.match_bitpattern(instr, '0b00010001')
        with self.assertRaises(pyrtl.PyrtlError):
            o, _ = pyrtl.match_bitpattern(instr, 0b000100010)
        with self.assertRaises(pyrtl.PyrtlError):
            o, _ = pyrtl.match_bitpattern(instr, '')
        with self.assertRaises(pyrtl.PyrtlError):
            o, _ = pyrtl.match_bitpattern(instr, None)
        with self.assertRaises(pyrtl.PyrtlError):
            o, _ = pyrtl.match_bitpattern(instr, instr)

    def test_match_bitwidth_does_simulation_correct(self):
        r = pyrtl.Register(6, 'r')
        r.next <<= r + 3
        # 000000 -> 000011 -> 000110 -> 001001 -> 001100 -> 001111 -> 010010 -> 010101
        a, matches = pyrtl.match_bitpattern(r, '00_?0 ?1')
        o = pyrtl.Output(name='o')
        o <<= a
        self.assertEqual(matches, ())  # '?' wildcard doesn't bind to a field
        self.check_trace('o 01010000\nr 036912151821\n')

    def test_match_bitwidth_simulates_no_ones_in_pattern(self):
        r = pyrtl.Register(6, 'r')
        r.next <<= r + 3
        # 000000 -> 000011 -> 000110 -> 001001 -> 001100 -> 001111 -> 010010 -> 010101
        a, _ = pyrtl.match_bitpattern(r, '00??00')
        o = pyrtl.Output(name='o')
        o <<= a
        self.check_trace('o 10001000\nr 036912151821\n')

    def test_match_bitwidth_simulates_no_zeroes_in_pattern(self):
        r = pyrtl.Register(6, 'r')
        r.next <<= r + 3
        # 000000 -> 000011 -> 000110 -> 001001 -> 001100 -> 001111 -> 010010 -> 010101
        a, _ = pyrtl.match_bitpattern(r, '?1??1?')
        o = pyrtl.Output(name='o')
        o <<= a
        self.check_trace('o 00000010\nr 036912151821\n')

    def test_match_bitwidth_simulates_only_wildcards(self):
        r = pyrtl.Register(6, 'r')
        r.next <<= r + 3
        # 000000 -> 000011 -> 000110 -> 001001 -> 001100 -> 001111 -> 010010 -> 010101
        a, _ = pyrtl.match_bitpattern(r, '??????')
        o = pyrtl.Output(name='o')
        o <<= a
        self.check_trace('o 11111111\nr 036912151821\n')

    def test_match_bitwidth_with_consecutive_fields(self):
        r = pyrtl.Register(6, 'r')
        r.next <<= r + 3
        # 000000 -> 000011 -> 000110 -> 001001 -> 001100 -> 001111 -> 010010 -> 010101
        m, (b, a) = pyrtl.match_bitpattern(r, 'bb0a?1')
        pyrtl.probe(b, 'b')
        pyrtl.probe(a, 'a')
        o = pyrtl.Output(name='o')
        o <<= m
        self.check_trace(
            'a 00101101\n'
            'b 00000011\n'
            'o 01000001\n'
            'r 036912151821\n'
        )

    def test_match_bitwidth_with_non_consecutive_field(self):
        r = pyrtl.Register(6, 'r')
        r.next <<= r + 3
        # 000000 -> 000011 -> 000110 -> 001001 -> 001100 -> 001111 -> 010010 -> 010101
        m, (b, a) = pyrtl.match_bitpattern(r, 'bb0ab1')
        pyrtl.probe(b, 'b')
        pyrtl.probe(a, 'a')
        o = pyrtl.Output(name='o')
        o <<= m
        self.check_trace(
            'a 00101101\n'
            'b 01100132\n'
            'o 01000001\n'
            'r 036912151821\n'
        )

    def test_match_bitwidth_with_several_non_consecutive_fields(self):
        r = pyrtl.Register(6, 'r')
        r.next <<= r + 3
        # 000000 -> 000011 -> 000110 -> 001001 -> 001100 -> 001111 -> 010010 -> 010101
        m, (a, b) = pyrtl.match_bitpattern(r, 'ab0aba')
        pyrtl.probe(a, 'a')
        pyrtl.probe(b, 'b')
        o = pyrtl.Output(name='o')
        o <<= m
        self.check_trace(
            'a 01212303\n'
            'b 01100132\n'
            'o 11100011\n'
            'r 036912151821\n'
        )

    def test_match_bitwidth_with_all_fields(self):
        r = pyrtl.Register(6, 'r')
        r.next <<= r + 3
        # 000000 -> 000011 -> 000110 -> 001001 -> 001100 -> 001111 -> 010010 -> 010101
        m, (a, b, c, d, e, f) = pyrtl.match_bitpattern(r, 'abcdef')
        pyrtl.probe(a, 'a')
        pyrtl.probe(b, 'b')
        pyrtl.probe(c, 'c')
        pyrtl.probe(d, 'd')
        pyrtl.probe(e, 'e')
        pyrtl.probe(f, 'f')
        o = pyrtl.Output(name='o')
        o <<= m
        self.check_trace(
            'a 00000000\n'
            'b 00000011\n'
            'c 00011100\n'
            'd 00101101\n'
            'e 01100110\n'
            'f 01010101\n'
            'o 11111111\n'
            'r 036912151821\n'
        )

    def check_all_accesses_valid(self):
        sim = pyrtl.Simulation()
        sim.step_multiple({'i': [0b11010, 0b00011, 0b01101]})
        output = io.StringIO()
        sim.tracer.print_trace(output, compact=True)
        self.assertEqual(
            output.getvalue(),
            '  i 26313\n'
            'out 313\n'
        )

    def test_match_bitwidth_with_pattern_matched_fields(self):
        i = pyrtl.Input(5, 'i')
        out = pyrtl.Output(2, 'out')

        with pyrtl.conditional_assignment:
            with pyrtl.match_bitpattern(i, '1a?a0') as (a,):
                out |= a
            with pyrtl.match_bitpattern(i, 'b0?1b') as (b,):
                out |= b
            with pyrtl.match_bitpattern(i, 'ba1ab') as (b, a):
                out |= a + b

        self.check_all_accesses_valid()

    def test_match_bitwidth_with_pattern_matched_fields_by_name(self):
        i = pyrtl.Input(5, 'i')
        out = pyrtl.Output(2, 'out')

        with pyrtl.conditional_assignment:
            with pyrtl.match_bitpattern(i, '1a?a0') as x:
                out |= x.a
            with pyrtl.match_bitpattern(i, 'b0?1b') as x:
                out |= x.b
            with pyrtl.match_bitpattern(i, 'ba1ab') as x:
                out |= x.a + x.b

        self.check_all_accesses_valid()

    def test_match_bitwidth_with_pattern_matched_fields_with_field_map(self):
        i = pyrtl.Input(5, 'i')
        out = pyrtl.Output(2, 'out')

        field_map = {'a': 'field1', 'b': 'field2'}
        with pyrtl.conditional_assignment:
            with pyrtl.match_bitpattern(i, '1a?a0', field_map) as x:
                out |= x.field1
            with pyrtl.match_bitpattern(i, 'b0?1b', field_map) as x:
                out |= x.field2
            with pyrtl.match_bitpattern(i, 'ba1ab', field_map) as x:
                out |= x.field1 + x.field2

        self.check_all_accesses_valid()

    def test_match_bitwidth_with_pattern_matched_fields_with_bad_field_map(self):
        i = pyrtl.Input(5, 'i')
        out = pyrtl.Output(2, 'out')

        field_map = {'a': 'field1', 'c': 'field2'}
        with self.assertRaises(pyrtl.PyrtlError):
            with pyrtl.conditional_assignment:
                with pyrtl.match_bitpattern(i, 'b0?1b', field_map) as x:
                    out |= x.field2


class TestBitpatternToVal(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    @staticmethod
    def r5_br_immed(x):
        # i is the 12th bit, k is the 11th bit, and j is the bottom 10 bits of the immediate field
        return {'i': (x >> 11) & 0x1, 'k': (x >> 10) & 0x1, 'j': x & ((1 << 10) - 1)}

    def test_ordered_fields(self):
        self.assertEqual(
            pyrtl.bitpattern_to_val('0000000sssssrrrrr000ddddd0110011', 1, 2, 3),  # RISC-V ADD
            0b00000000000100010000000110110011
        )

        self.assertEqual(
            pyrtl.bitpattern_to_val('iiiiiiisssssrrrrr010iiiii0100011', 1, 3, 4),  # RISC-V SW
            0b00000000001100100010000010100011
        )

        m = TestBitpatternToVal.r5_br_immed(-5)
        self.assertEqual(
            pyrtl.bitpattern_to_val(
                'ijjjjjjsssssrrrrr100jjjjk1100011', m['i'], m['j'], 2, 3, m['k']
            ),  # RISC-V BLT
            0b11111110001000011100101111100011
        )

    def test_named_fields(self):
        self.assertEqual(
            pyrtl.bitpattern_to_val(
                '0000000sssssrrrrr000ddddd0110011', s=1, r=2, d=3
            ),  # RISC-V ADD
            0b00000000000100010000000110110011
        )

        self.assertEqual(
            pyrtl.bitpattern_to_val('iiiiiiisssssrrrrr010iiiii0100011', i=1, s=3, r=4),  # RISC-V SW
            0b00000000001100100010000010100011
        )

        self.assertEqual(
            pyrtl.bitpattern_to_val(
                'ijjjjjjsssssrrrrr100jjjjk1100011',
                s=2, r=3, **TestBitpatternToVal.r5_br_immed(-5)
            ),  # RISC-V BLT
            0b11111110001000011100101111100011
        )

    def test_named_fields_with_field_map(self):
        field_map = {
            's': 'rs2',
            'r': 'rs1',
            'd': 'rd',
            'i': 'imm',
        }
        self.assertEqual(
            pyrtl.bitpattern_to_val(
                '0000000sssssrrrrr000ddddd0110011', rs2=1, rs1=2, rd=3, field_map=field_map
            ),  # RISC-V ADD
            0b00000000000100010000000110110011
        )

        self.assertEqual(
            pyrtl.bitpattern_to_val(
                'iiiiiiisssssrrrrr010iiiii0100011', imm=1, rs2=3, rs1=4, field_map=field_map
            ),  # RISC-V SW
            0b00000000001100100010000010100011
        )

    def test_fields_all_different(self):
        self.assertEqual(
            pyrtl.bitpattern_to_val('abcdefg', a=1, b=0, c=1, d=0, e=0, f=1, g=0),
            0b1010010
        )

    def test_no_fields(self):
        self.assertEqual(
            pyrtl.bitpattern_to_val('1010010'),
            0b1010010
        )

    def test_error_both_ordered_and_named_fields(self):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.bitpattern_to_val('iiiiiiirrrrrsssss010iiiii0100011', 1, r=3, s=4)

    def test_error_invalid_num_unique_patterns(self):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.bitpattern_to_val('iiiiiiirrrrrsssss010iiiii0100011', 1, 3)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.bitpattern_to_val('iiiiiiirrrrrsssss010iiiii0100011', i=1, r=3)

    def test_error_bitpattern_field_not_provided(self):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.bitpattern_to_val('iiiiiiirrrrrsssss010iiiii0100011', i=1, r=3, t=4)

    def test_error_unnamed_fields_in_bitpattern(self):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.bitpattern_to_val('iiiiiii?????sssss010iiiii0100011', 1, 3, 4)

    def test_error_value_doesnt_fit_in_field(self):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.bitpattern_to_val('iiiiiiirrrrrsssss010iiiii0100011', 1, 65, 4)

    def test_error_empty_bitpattern(self):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.bitpattern_to_val('')


class TestChop(unittest.TestCase):
    def setUp(self):
        random.seed(8492049)
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output, compact=True)
        self.assertEqual(output.getvalue(), correct_string)

    def test_fields_mismatch(self):
        instr = pyrtl.WireVector(name='instr', bitwidth=32)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.chop(instr, 10, 10, 10)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.chop(instr, 10, 10, 14)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.chop(instr, 33)

    def test_wrong_input_types_fail(self):
        instr = pyrtl.WireVector(name='instr', bitwidth=32)
        x = pyrtl.WireVector(name='x', bitwidth=10)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.chop(instr, x, 10, 12)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.chop(instr, 10, x, 12)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.chop(instr, x)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.chop(10, 5, 5)

    def test_chop_does_simulation_correct(self):
        r = pyrtl.Register(5, 'r')
        r.next <<= r + 1
        a, b, c = pyrtl.helperfuncs.chop(r, 2, 2, 1)
        o = pyrtl.Output(name='o')
        o <<= c
        self.check_trace('o 01010101\nr 01234567\n')


class TestBitField_Update(unittest.TestCase):
    def setUp(self):
        random.seed(8492049)
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output, compact=True)
        self.assertEqual(output.getvalue(), correct_string)

    def test_field_too_big(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.bitfield_update(a, 1, 2, b)

    def test_field_too_big_truncate(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=3)
        o = pyrtl.bitfield_update(a, 1, 2, b, truncating=True)

    def test_no_bits_to_update(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.bitfield_update(a, 1, 1, b, truncating=True)

    def bitfield_update_checker(self, input_width, range_start, range_end,
                                update_width, test_amt=20):
        def ref(i, s, e, u):
            mask = ((1 << (e)) - 1) - ((1 << s) - 1)
            return (i & ~mask) | ((u << s) & mask)
        inp, inp_vals = utils.an_input_and_vals(input_width, test_vals=test_amt, name='inp')
        upd, upd_vals = utils.an_input_and_vals(update_width, test_vals=test_amt, name='upd')
        out = pyrtl.Output(input_width, "out")
        bfu_out = pyrtl.bitfield_update(inp, range_start, range_end, upd)
        self.assertEqual(len(out), len(bfu_out))  # output should have width of input
        out <<= bfu_out
        true_result = [ref(i, range_start, range_end, u) for i, u in zip(inp_vals, upd_vals)]
        upd_result = utils.sim_and_ret_out(out, [inp, upd], [inp_vals, upd_vals])
        self.assertEqual(upd_result, true_result)

    def test_bitfield(self):
        self.bitfield_update_checker(10, 3, 6, 3)

    def test_bitfield_msb(self):
        a = pyrtl.Const(0, 8)
        pyrtl.probe(pyrtl.bitfield_update(a, -1, None, 1), 'out')
        sim = pyrtl.Simulation()
        sim.step({})
        self.assertEqual(sim.inspect('out'), 0b10000000)

    def test_bitfield_all_but_msb(self):
        a = pyrtl.Const(0, 8)
        pyrtl.probe(pyrtl.bitfield_update(a, None, -1, 0b101110), 'out')
        sim = pyrtl.Simulation()
        sim.step({})
        self.assertEqual(sim.inspect('out'), 0b0101110)

    def test_bitfield_lsb(self):
        a = pyrtl.Const(0, 8)
        pyrtl.probe(pyrtl.bitfield_update(a, None, 1, 1), 'out')
        sim = pyrtl.Simulation()
        sim.step({})
        self.assertEqual(sim.inspect('out'), 0b00000001)

    def test_bitfield_all_but_lsb(self):
        a = pyrtl.Const(0, 8)
        pyrtl.probe(pyrtl.bitfield_update(a, 1, None, 0b1011101), 'out')  # TODO
        sim = pyrtl.Simulation()
        sim.step({})
        self.assertEqual(sim.inspect('out'), 0b10111010)


class TestBitField_Update_Set(unittest.TestCase):
    def setUp(self):
        random.seed(8492049)
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output, compact=True)
        self.assertEqual(output.getvalue(), correct_string)

    def test_field_too_big(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.bitfield_update_set(a, {(1, 2): b})

    def test_field_too_big_truncate(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=3)
        o = pyrtl.bitfield_update_set(a, {(1, 2): b}, truncating=True)

    def test_no_bits_to_update(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.bitfield_update_set(a, {(1, 1): b}, truncating=True)

    def test_overlapping_ranges(self):
        a = pyrtl.WireVector(name='a', bitwidth=10)
        b = pyrtl.WireVector(name='b', bitwidth=10)
        c = pyrtl.WireVector(name='c', bitwidth=10)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.bitfield_update_set(a, {(1, 4): b, (3, 6): c}, truncating=True)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.bitfield_update_set(a, {(8, 10): b, (-1, None): c}, truncating=True)
        with self.assertRaises(pyrtl.PyrtlError):
            o = pyrtl.bitfield_update_set(a, {(None, 3): b, (0, 1): c}, truncating=True)

    def bitfield_update_set_checker(self, input_width, update_set_constraints, test_amt=20):
        from functools import reduce
        from collections import namedtuple
        Update_Info = namedtuple('Update_Info', ['range_start', 'range_end',
                                                 'update_wire', 'update_vals'])

        def ref(i, s, e, u):
            mask = ((1 << (e)) - 1) - ((1 << s) - 1)
            return (i & ~mask) | ((u << s) & mask)
        inp, inp_vals = utils.an_input_and_vals(input_width, test_vals=test_amt, name='inp')
        update_set_list = []
        for ix, (range_start, range_end, update_width) in enumerate(update_set_constraints):
            upd, upd_vals = utils.an_input_and_vals(update_width, test_vals=test_amt,
                                                    name='upd%d' % ix)
            update_set_list.append(Update_Info(range_start, range_end, upd, upd_vals))
        out = pyrtl.Output(input_width, "out")
        bfu_out = pyrtl.bitfield_update_set(
            inp,
            {(ui.range_start, ui.range_end): ui.update_wire for ui in update_set_list}
        )
        self.assertEqual(len(out), len(bfu_out))  # output should have width of input
        out <<= bfu_out
        true_result = []
        for ix, iv in enumerate(inp_vals):
            true_result.append(
                reduce(lambda w, ui: ref(w, ui.range_start, ui.range_end, ui.update_vals[ix]),
                       update_set_list, iv)
            )
        upd_result = utils.sim_and_ret_out(
            out,
            [inp] + [ui.update_wire for ui in update_set_list],
            [inp_vals] + [ui.update_vals for ui in update_set_list],
        )
        self.assertEqual(upd_result, true_result)

    def test_bitfield(self):
        self.bitfield_update_set_checker(10, [(3, 6, 3), (0, 2, 2)])


class TestAnyAll(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output, compact=True)
        self.assertEqual(output.getvalue(), correct_string)

    def test_any_only_on_1_bit_vectors(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.rtl_any(a, b)

    def test_all_only_on_1_bit_vectors(self):
        a = pyrtl.WireVector(name='a', bitwidth=1)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.rtl_all(a, b, c)

    def test_any_works_with_consts(self):
        a = pyrtl.WireVector(name='a', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        r = pyrtl.corecircuits.rtl_any(a, 1, c)

    def test_all_works_with_consts(self):
        a = pyrtl.WireVector(name='a', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        r = pyrtl.corecircuits.rtl_all(a, 1, c)

    def test_any_does_simulation_correct(self):
        r = pyrtl.Register(3, 'r')
        r.next <<= r + 1
        a, b, c = r[0], r[1], r[2]
        o = pyrtl.Output(name='o')
        o <<= pyrtl.corecircuits.rtl_any(a, b, c)
        self.check_trace('o 01111111\nr 01234567\n')

    def test_all_does_simulation_correct(self):
        r = pyrtl.Register(3, 'r')
        r.next <<= r + 1
        a, b, c = r[0], r[1], r[2]
        o = pyrtl.Output(name='o')
        o <<= pyrtl.corecircuits.rtl_all(a, b, c)
        self.check_trace('o 00000001\nr 01234567\n')


class TestTreeReduce(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_xor(self):
        wires, vals = utils.make_inputs_and_values(7, exact_bitwidth=8, dist=utils.uniform_dist)
        outwire = pyrtl.Output(name="test")

        import operator
        outwire <<= pyrtl.tree_reduce(operator.xor, wires)

        out_vals = utils.sim_and_ret_out(outwire, wires, vals)
        true_result = [functools.reduce(operator.xor, v) for v in zip(*vals)]
        self.assertEqual(out_vals, true_result)

    def test_empty(self):
        with self.assertRaises(pyrtl.PyrtlError):
            import operator
            pyrtl.tree_reduce(operator.add, [])


class TestXorAllBits(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output, compact=True)
        self.assertEqual(output.getvalue(), correct_string)

    def test_one_wirevector(self):
        r = pyrtl.Register(3, 'r')
        r.next <<= r + 1
        o = pyrtl.Output(name='o')
        o <<= pyrtl.corecircuits.xor_all_bits(r)
        self.check_trace('o 01101001\nr 01234567\n')

    def test_list_of_one_bit_wires(self):
        r = pyrtl.Register(2, 'r')
        r.next <<= r + 1
        o = pyrtl.Output(name='o')
        o <<= pyrtl.corecircuits.xor_all_bits([r[0], r[1]])
        self.check_trace('o 01100110\nr 01230123\n')

    def test_list_of_long_wires(self):
        in_wires, vals = utils.make_inputs_and_values(4, exact_bitwidth=13)
        out = pyrtl.Output(name='o')
        out <<= pyrtl.corecircuits.xor_all_bits(in_wires)
        expected = [v1 ^ v2 ^ v3 ^ v4 for v1, v2, v3, v4 in zip(*vals)]
        self.assertEqual(expected, utils.sim_and_ret_out(out, in_wires, vals))


class TestMux(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_mux_too_many_inputs(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.mux(s, a, b, c)

    def test_mux_not_enough_inputs(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.mux(s, a, b, c)

    def test_mux_not_enough_inputs_but_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        r = pyrtl.corecircuits.mux(s, a, b, default=0)

    def test_mux_enough_inputs_with_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        d = pyrtl.WireVector(name='d', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        r = pyrtl.corecircuits.mux(s, a, b, c, d, default=0)

    def test_mux_too_many_inputs_with_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        d = pyrtl.WireVector(name='d', bitwidth=1)
        e = pyrtl.WireVector(name='e', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.mux(s, a, b, c, d, e, default=0)

    def test_mux_too_many_inputs_with_extra_kwarg(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.mux(s, a, b, default=0, foo=1)


class TestMuxSimulation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        random.seed(8492049)

    def setUp(self):
        pyrtl.reset_working_block()

    def test_simple_mux_1(self):
        self.mux_t_subprocess(4, 16)

    def test_simple_mux_2(self):
        self.mux_t_subprocess(6, 7)

    def mux_t_subprocess(self, addr_width, val_width):
        mux_ins, vals = utils.make_consts(num_wires=2**addr_width, exact_bitwidth=val_width)
        control, testctrl = utils.an_input_and_vals(addr_width, 40, "mux_ctrl")

        out = pyrtl.Output(val_width, "mux_out")
        out <<= pyrtl.corecircuits.mux(control, *mux_ins)

        true_result = [vals[i] for i in testctrl]
        mux_result = utils.sim_and_ret_out(out, (control,), (testctrl,))
        self.assertEqual(mux_result, true_result)

    def test_mux_with_default(self):
        addr_width = 5
        val_width = 9
        default_val = 170  # arbitrary value under 2**val_width
        num_defaults = 5
        mux_ins, vals = utils.make_consts(num_wires=2**addr_width - num_defaults,
                                          exact_bitwidth=val_width, random_dist=utils.uniform_dist)
        control, testctrl = utils.an_input_and_vals(addr_width, 40, "mux_ctrl", utils.uniform_dist)

        for i in range(5):
            vals.append(default_val)

        out = pyrtl.Output(val_width, "mux_out")
        out <<= pyrtl.corecircuits.mux(control, *mux_ins, default=pyrtl.Const(default_val))

        true_result = [vals[i] for i in testctrl]
        mux_result = utils.sim_and_ret_out(out, (control,), (testctrl,))
        self.assertEqual(mux_result, true_result)

    def test_select(self):
        vals = 12, 27
        mux_ins = [pyrtl.Const(x) for x in vals]
        control, testctrl = utils.an_input_and_vals(1, 40, "sel_ctrl", utils.uniform_dist)

        out = pyrtl.Output(5, "mux_out")
        out <<= pyrtl.corecircuits.select(control, falsecase=mux_ins[0], truecase=mux_ins[1])

        true_result = [vals[i] for i in testctrl]
        mux_result = utils.sim_and_ret_out(out, (control,), (testctrl,))
        self.assertEqual(mux_result, true_result)

    def test_select_no_pred(self):
        vals = 12, 27
        mux_ins = [pyrtl.Const(x) for x in vals]
        control, testctrl = utils.an_input_and_vals(1, 40, "sel_ctrl", utils.uniform_dist)

        out = pyrtl.Output(5, "mux_out")
        out <<= pyrtl.corecircuits.select(control, mux_ins[1], mux_ins[0])

        true_result = [vals[i] for i in testctrl]
        mux_result = utils.sim_and_ret_out(out, (control,), (testctrl,))
        self.assertEqual(mux_result, true_result)


class TestRtlProbe(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_bad_probe_wire(self):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.probe(5)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.probe('a')

    def test_simple_probe(self):
        i = pyrtl.Input(1)
        o = pyrtl.Output(1)
        o <<= pyrtl.probe(i + 1)

    def test_probe_wire(self):
        i = pyrtl.Input(1)
        x = pyrtl.probe(i)
        self.assertIs(x, i)

    def test_simple_probe_debug(self):
        pyrtl.set_debug_mode()
        i = pyrtl.Input(1)
        o = pyrtl.Output(1)
        output = io.StringIO()
        sys.stdout = output
        o <<= pyrtl.probe(i + 1, name="probe0")
        sys.stdout = sys.__stdout__
        self.assertTrue(output.getvalue().startswith("Probe: probe0"))
        pyrtl.set_debug_mode(False)


class TestShiftSimulation(unittest.TestCase):

    def setUp(self):
        random.seed(8492049)
        pyrtl.reset_working_block()

    def shift_checker(self, shift_func, ref_func, input_width, shift_width,
                      shift_amount=None, test_amt=20):
        inputs, all_inp_vals = [], []
        inp, inp_vals = utils.an_input_and_vals(input_width, test_vals=test_amt, name='inp')
        inputs.append(inp)
        all_inp_vals.append(inp_vals)
        if shift_amount is not None:
            shf, shf_vals = shift_amount, [shift_amount] * test_amt
        else:
            shf, shf_vals = utils.an_input_and_vals(shift_width, test_vals=test_amt, name='shf')
            inputs.append(shf)
            all_inp_vals.append(shf_vals)
        out = pyrtl.Output(input_width, "out")
        shf_out = shift_func(inp, shf)
        self.assertEqual(len(out), len(shf_out))  # output should have width of input
        out <<= shf_out
        true_result = [ref_func(i, s) for i, s in zip(inp_vals, shf_vals)]
        shift_result = utils.sim_and_ret_out(out, inputs, all_inp_vals)
        self.assertEqual(shift_result, true_result)

    def sll_checker(self, input_width, shift_width, shift_amount=None):
        mask = (1 << input_width) - 1

        def ref(i, s):
            return (i << s) & mask

        self.shift_checker(pyrtl.shift_left_logical, ref, input_width, shift_width, shift_amount)

    def sla_checker(self, input_width, shift_width, shift_amount=None):
        mask = (1 << input_width) - 1

        def ref(i, s):
            return (i << s) & mask

        self.shift_checker(pyrtl.shift_left_arithmetic, ref, input_width,
                           shift_width, shift_amount)

    def srl_checker(self, input_width, shift_width, shift_amount=None):
        mask = (1 << input_width) - 1

        def ref(i, s):
            return (i >> s) & mask

        self.shift_checker(pyrtl.shift_right_logical, ref, input_width, shift_width, shift_amount)

    def sra_checker(self, input_width, shift_width, shift_amount=None):
        # a little more work is required to take the positive number and treat it
        # as a twos complement number for the purpose of testing the shifter
        def ref(i, s):
            mask = (1 << input_width) - 1
            if (i >> input_width - 1) & 0x1 == 0x1:
                return ((~mask | i) >> s) & mask  # negative number
            else:
                return (i >> s) & mask  # positive number
        self.shift_checker(pyrtl.shift_right_arithmetic, ref, input_width,
                           shift_width, shift_amount)

    def test_sll(self):
        self.sll_checker(5, 2)

    def test_sla(self):
        self.sla_checker(5, 2)

    def test_srl(self):
        self.srl_checker(5, 2)

    def test_sra(self):
        self.sra_checker(5, 2)

    def test_sll_big(self):
        self.sll_checker(10, 3)

    def test_sla_big(self):
        self.sla_checker(10, 3)

    def test_srl_big(self):
        self.srl_checker(10, 3)

    def test_sra_big(self):
        self.sra_checker(10, 3)

    def test_sll_over(self):
        self.sll_checker(4, 4)

    def test_sla_over(self):
        self.sla_checker(4, 4)

    def test_srl_over(self):
        self.srl_checker(4, 4)

    def test_sra_over(self):
        self.sra_checker(4, 4)

    def test_sll_integer_shift_amount(self):
        self.sll_checker(5, 2, 1)

    def test_sla_integer_shift_amount(self):
        self.sla_checker(5, 2, 1)

    def test_srl_integer_shift_amount(self):
        self.srl_checker(5, 2, 1)

    def test_sra_integer_shift_amount(self):
        self.sra_checker(5, 2, 1)


class TestBasicMult(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def mult_t_base(self, len_a, len_b):
        # Creating the logic nets
        a, b = pyrtl.Input(len_a, "a"), pyrtl.Input(len_b, "b")
        product = pyrtl.Output(name="product")
        product <<= pyrtl.corecircuits._basic_mult(a, b)

        self.assertEqual(len(product), len_a + len_b)

        # creating the testing values and the correct results
        xvals = [int(random.uniform(0, 2 ** len_a - 1)) for i in range(20)]
        yvals = [int(random.uniform(0, 2 ** len_b - 1)) for i in range(20)]
        true_result = [i * j for i, j in zip(xvals, yvals)]

        # Setting up and running the tests
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(len(xvals)):
            sim.step({a: xvals[cycle], b: yvals[cycle]})

        # Extracting the values and verifying correctness
        multiplier_result = sim_trace.trace[product.name]
        self.assertEqual(multiplier_result, true_result)

    def test_mult_1(self):
        self.mult_t_base(1, 7)

    def test_mult_1_1(self):
        self.mult_t_base(2, 1)

    def test_mult_2(self):
        self.mult_t_base(5, 4)

    def test_mult_3(self):
        self.mult_t_base(5, 2)


class TestRtlAssert(unittest.TestCase):

    class RTLSampleException(Exception):
        pass

    def setUp(self):
        pyrtl.reset_working_block()

    def bad_rtl_assert(self, *args, **kwargs):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.rtl_assert(*args, **kwargs)

    def test_bad_type(self):
        self.bad_rtl_assert(True, self.RTLSampleException())
        self.bad_rtl_assert(1, self.RTLSampleException())

    def test_wrong_len(self):
        w = pyrtl.Input(2)
        w2 = pyrtl.Input()

        self.bad_rtl_assert(w, self.RTLSampleException())
        self.bad_rtl_assert(w2, self.RTLSampleException())

    def test_invalid_exception_type(self):
        w = pyrtl.Input(1)

        self.bad_rtl_assert(w, 1)
        self.bad_rtl_assert(w, "")
        self.bad_rtl_assert(w, w)
        self.bad_rtl_assert(w, KeyError())

    def test_duplicate_assert(self):
        w = pyrtl.Input(1)
        pyrtl.rtl_assert(w, self.RTLSampleException())
        pyrtl.rtl_assert(w, self.RTLSampleException())

    def test_wire_from_another_block(self):
        w = pyrtl.Input(1)
        pyrtl.reset_working_block()
        self.bad_rtl_assert(w, self.RTLSampleException())

    def test_wire_outside_block(self):
        w = pyrtl.Input(1)
        block = pyrtl.working_block()
        block.wirevector_set.clear()
        self.bad_rtl_assert(w, self.RTLSampleException())

    def test_create_assert(self):
        w = pyrtl.WireVector(1)
        pyrtl.rtl_assert(w, self.RTLSampleException('testing rtl assert'))

    def test_assert_simulation(self):
        i = pyrtl.Input(1)
        o = pyrtl.rtl_assert(i, self.RTLSampleException('test assertion failed'))

        sim = pyrtl.Simulation()
        sim.step({i: 1})
        self.assertEqual(sim.inspect(o), 1)

        with self.assertRaises(self.RTLSampleException):
            sim.step({i: 0})

    def test_assert_fastsimulation(self):
        i = pyrtl.Input(1)
        o = pyrtl.rtl_assert(i, self.RTLSampleException('test assertion failed'))

        sim = pyrtl.FastSimulation()
        sim.step({i: 1})
        self.assertEqual(sim.inspect(o), 1)

        with self.assertRaises(self.RTLSampleException):
            sim.step({i: 0})


class TestLoopDetection(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        # Redirect stdout because we don't care to see the specific messages about
        # wires being deemed useless by optimization sent to stdout.
        f = open(os.devnull, 'w')
        sys.stdout = f

    def tearDown(self):
        sys.stdout.close()
        sys.stdout = sys.__stdout__

    def assert_no_loop(self):
        self.assertEqual(pyrtl.find_loop(), None)
        pyrtl.synthesize()
        self.assertEqual(pyrtl.find_loop(), None)
        pyrtl.optimize()
        self.assertEqual(pyrtl.find_loop(), None)

    def assert_has_loop(self):
        self.assertNotEqual(pyrtl.find_loop(), None)
        pyrtl.synthesize()
        self.assertNotEqual(pyrtl.find_loop(), None)
        pyrtl.optimize()
        self.assertNotEqual(pyrtl.find_loop(), None)

    def test_no_loop_1(self):
        ins = [pyrtl.Input(8) for i in range(8)]
        outs = [pyrtl.Output(8) for i in range(3)]
        x_1 = ins[0] & ins[1]
        x_2 = ins[3] & ins[4]
        x_3 = ins[0] | ins[4]
        x_4 = ins[6] ^ ins[7]
        x_5 = ~ ins[2]
        x_6 = ~ x_2
        x_7 = x_1 ^ x_3 & x_6
        outs[0] <<= x_4
        outs[2] <<= x_5 | x_7
        outs[1] <<= (x_1 & x_7) ^ x_3

        self.assert_no_loop()

    def test_loop_1(self):
        ins = [pyrtl.Input(8) for i in range(8)]
        outs = [pyrtl.Output(8) for i in range(3)]
        x_1 = ins[0] & ins[1]
        x_2 = ins[3] & ins[4]
        x_3 = ins[0] | ins[4]
        x_4 = ins[6] ^ ins[7]
        x_5 = ~ ins[2]
        x_6 = ~ x_2
        l_1 = pyrtl.WireVector(8)
        l_0 = x_6 & l_1
        l_1 <<= (l_0 | x_5) & x_2

        x_7 = x_1 ^ x_3 & l_0
        outs[0] <<= x_4
        outs[2] <<= x_5 | l_1
        outs[1] <<= (x_1 & x_7) ^ x_3

        self.assert_has_loop()

    def test_no_loop_special_ops(self):
        mem1 = pyrtl.MemBlock(4, 4)
        ins = [pyrtl.Input(4) for i in range(8)]
        outs = [pyrtl.Output(4) for i in range(3)]
        reg = pyrtl.Register(4)

        x_1 = ins[4] < reg
        x_2 = ins[1] * x_1
        x_3 = pyrtl.corecircuits.mux(x_1, ins[1], ins[2])
        # x_4 = pyrtl.as_wires(mem1[ins[6]])
        x_4 = mem1[ins[6]]
        x_5 = reg + ins[7]
        x_9 = pyrtl.as_wires(x_4)
        mem1[pyrtl.as_wires(x_4)] <<= x_9
        outs[0] <<= x_2 == x_1
        reg.next <<= x_5 & ins[1]
        outs[1] <<= reg
        outs[2] <<= pyrtl.corecircuits.concat(x_1, x_5[:7])

        self.assert_no_loop()

    def test_edge_case_1(self):
        in_1 = pyrtl.Input(10)
        in_2 = pyrtl.Input(9)
        fake_loop_wire = pyrtl.WireVector(1)
        comp_wire = pyrtl.corecircuits.concat(in_2[0:4], fake_loop_wire, in_2[4:9])
        r_wire = in_1 & comp_wire
        fake_loop_wire <<= r_wire[3]
        out = pyrtl.Output(10)
        out <<= fake_loop_wire

        # Yes, because we only check loops on a net level, this will still be
        # a loop pre synth
        self.assertNotEqual(pyrtl.find_loop(), None)
        pyrtl.synthesize()

        # Because synth separates the individual wires, it also resolves the loop
        self.assertEqual(pyrtl.find_loop(), None)
        pyrtl.optimize()
        self.assertEqual(pyrtl.find_loop(), None)

    def test_loop_2(self):
        in_1 = pyrtl.Input(10)
        in_2 = pyrtl.Input(9)
        fake_loop_wire = pyrtl.WireVector(1)
        # Note the slight difference from the last test case on the next line
        comp_wire = pyrtl.corecircuits.concat(in_2[0:6], fake_loop_wire, in_2[6:9])
        r_wire = in_1 & comp_wire
        fake_loop_wire <<= r_wire[3]
        out = pyrtl.Output(10)
        out <<= fake_loop_wire

        # It causes there to be a real loop
        self.assert_has_loop()

    def test_no_loop_reg_1(self):
        reg = pyrtl.Register(8)
        in_w = pyrtl.Input(8)
        res = reg + in_w
        reg.next <<= res
        self.assert_no_loop()


@pyrtl.wire_struct
class Byte:
    # A Byte can be decomposed into high and low nibbles, or composed from
    # high and low nibbles.
    high: 4
    low: 4


@pyrtl.wire_struct
class Pixel:
    # A Pixel can be decomposed into red, green and blue bytes, or composed
    # from red, green and blue bytes.
    red: Byte
    green: Byte
    blue: Byte


class TestWireStruct(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_concatenate(self):
        '''Drive high and low, observe concatenated high+low.'''
        # Concatenates to 'byte'.
        byte = Byte(name='byte', high=0xA, low=0xB)
        self.assertEqual(len(byte), 2)
        self.assertEqual(byte.bitwidth, 8)
        self.assertEqual(len(pyrtl.as_wires(byte)), 8)
        self.assertEqual(len(byte.high), 4)
        self.assertEqual(len(byte.low), 4)

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        # Because the Byte has the name 'byte', its components are
        # automatically assigned the names 'byte.high' and 'byte.low'.
        self.assertEqual(sim.inspect('byte'), 0xAB)
        self.assertEqual(sim.inspect('byte.high'), 0xA)
        self.assertEqual(sim.inspect('byte.low'), 0xB)

    def test_exceptions(self):
        # Slicing exceptions.
        with self.assertRaises(pyrtl.PyrtlError):
            bad_byte = Byte(Byte=0xAB, high=0xC)
        with self.assertRaises(pyrtl.PyrtlError):
            bad_byte = Byte(Byte=0xAB, foo=0xC)

        # Concatenating exceptions.
        with self.assertRaises(pyrtl.PyrtlError):
            bad_byte = Byte()
        with self.assertRaises(pyrtl.PyrtlError):
            bad_byte = Byte(high=0xA)
        with self.assertRaises(pyrtl.PyrtlError):
            bad_byte = Byte(low=0xB)
        with self.assertRaises(pyrtl.PyrtlError):
            bad_byte = Byte(high=0xA, low=0xB, foo=0xC)

    def test_slice(self):
        '''Drive concatenated high+low, observe high and low.'''
        # Slices to 'byte.high' and 'byte.low'.
        byte = Byte(name='byte', Byte=0xCD)

        # Constants are sliced immediately.
        self.assertTrue(isinstance(pyrtl.as_wires(byte), pyrtl.Const))
        self.assertEqual(byte.val, 0xCD)
        self.assertTrue(isinstance(byte.high, pyrtl.Const))
        self.assertEqual(byte.high.val, 0xC)
        self.assertTrue(isinstance(byte.low, pyrtl.Const))
        self.assertEqual(byte.low.val, 0xD)

    def test_input_slice(self):
        '''Given Input concatenated high+low, observe high and low.'''
        byte = Byte(name='byte', concatenated_type=pyrtl.Input)

        self.assertTrue(isinstance(pyrtl.as_wires(byte), pyrtl.Input))

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={'byte': 0xAB})
        self.assertEqual(sim.inspect('byte'), 0xAB)
        self.assertEqual(sim.inspect('byte.high'), 0xA)
        self.assertEqual(sim.inspect('byte.low'), 0xB)

    def test_input_concatenate(self):
        '''Given Input high and low, observe concatenated high+low.'''
        byte = Byte(name='byte', component_type=pyrtl.Input)

        self.assertTrue(isinstance(byte.high, pyrtl.Input))
        self.assertTrue(isinstance(byte.low, pyrtl.Input))

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={'byte.low': 0xB, 'byte.high': 0xA})
        self.assertEqual(sim.inspect('byte'), 0xAB)
        self.assertEqual(sim.inspect('byte.high'), 0xA)
        self.assertEqual(sim.inspect('byte.low'), 0xB)

    def test_output_slice(self):
        '''Drive concatenated high+low, observe high and low as Outputs.'''
        byte = Byte(name='byte', component_type=pyrtl.Output, Byte=0xCD)

        self.assertTrue(isinstance(byte.high, pyrtl.Output))
        self.assertTrue(isinstance(byte.low, pyrtl.Output))

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('byte'), 0xCD)
        self.assertEqual(sim.inspect('byte.high'), 0xC)
        self.assertEqual(sim.inspect('byte.low'), 0xD)

    def test_output_concatenate(self):
        '''Drive high and low, observe concatenated high+low as Output.'''
        byte = Byte(name='byte', concatenated_type=pyrtl.Output,
                    high=0xA, low=0xB)

        self.assertTrue(isinstance(pyrtl.as_wires(byte), pyrtl.Output))

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('byte'), 0xAB)
        self.assertEqual(sim.inspect('byte.high'), 0xA)
        self.assertEqual(sim.inspect('byte.low'), 0xB)

    def test_register_slice(self):
        '''Given Register concatenated high+low, observe high and low.'''
        byte = Byte(name='byte', concatenated_type=pyrtl.Register)
        next_value = pyrtl.Input(name='next_value', bitwidth=8)
        byte.next <<= next_value

        self.assertTrue(isinstance(pyrtl.as_wires(byte), pyrtl.Register))

        sim = pyrtl.Simulation()
        # On the first cycle, set the register's value to 0xAB, but it will
        # take one cycle for that value to propagate to the register's outputs.
        sim.step(provided_inputs={'next_value': 0xAB})
        self.assertEqual(sim.inspect('byte'), 0x0)
        self.assertEqual(sim.inspect('byte.high'), 0x0)
        self.assertEqual(sim.inspect('byte.low'), 0x0)

        # On the second cycle, the register's output is visible.
        sim.step(provided_inputs={'next_value': 0x00})
        self.assertEqual(sim.inspect('byte'), 0xAB)
        self.assertEqual(sim.inspect('byte.high'), 0xA)
        self.assertEqual(sim.inspect('byte.low'), 0xB)

    def test_anonymous_concatenate(self):
        '''Drive high and low, observe concatenated high+low, without names.'''
        byte = Byte(low=0xB, high=0xA)

        out = pyrtl.WireVector(bitwidth=8, name='out')
        out <<= byte

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('out'), 0xAB)

        # The other wires are not named, so 'out' should be the only traced
        # wire.
        self.assertEqual(list(sim.tracer.trace.keys()), ['out'])

    def test_anonymous_slice(self):
        '''Drive concatenated high+low, observe high and low, without names.'''
        byte = Byte(Byte=0xCD)

        low = pyrtl.WireVector(bitwidth=4, name='l')
        low <<= byte.low
        high = pyrtl.WireVector(bitwidth=4, name='h')
        high <<= byte.high

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('h'), 0xC)
        self.assertEqual(sim.inspect('l'), 0xD)

        # The other wires are not named, so 'h' and 'l' should be the only
        # traced wires.
        self.assertEqual(list(sorted(sim.tracer.trace.keys())), ['h', 'l'])

    def test_pixel_slice(self):
        pixel = Pixel(name='pixel', Pixel=0xABCDEF)
        self.assertEqual(len(pixel), 3)
        self.assertEqual(pixel.bitwidth, 24)
        self.assertEqual(len(pyrtl.as_wires(pixel)), 24)

        # Constants are sliced immediately.
        self.assertTrue(isinstance(pyrtl.as_wires(pixel), pyrtl.Const))
        self.assertEqual(pixel.val, 0xABCDEF)

        self.assertTrue(isinstance(pyrtl.as_wires(pixel.red), pyrtl.Const))
        self.assertEqual(pixel.red.val, 0xAB)
        self.assertTrue(isinstance(pixel.red.high, pyrtl.Const))
        self.assertEqual(pixel.red.high.val, 0xA)
        self.assertTrue(isinstance(pixel.red.low, pyrtl.Const))
        self.assertEqual(pixel.red.low.val, 0xB)

        self.assertTrue(isinstance(pyrtl.as_wires(pixel.green), pyrtl.Const))
        self.assertEqual(pixel.green.val, 0xCD)
        self.assertTrue(isinstance(pixel.green.high, pyrtl.Const))
        self.assertEqual(pixel.green.high.val, 0xC)
        self.assertTrue(isinstance(pixel.green.low, pyrtl.Const))
        self.assertEqual(pixel.green.low.val, 0xD)

        self.assertTrue(isinstance(pyrtl.as_wires(pixel.blue), pyrtl.Const))
        self.assertEqual(pixel.blue.val, 0xEF)
        self.assertTrue(isinstance(pixel.blue.high, pyrtl.Const))
        self.assertEqual(pixel.blue.high.val, 0xE)
        self.assertTrue(isinstance(pixel.blue.low, pyrtl.Const))
        self.assertEqual(pixel.blue.low.val, 0xF)

    def test_pixel_concatenate(self):
        pixel = Pixel(name='pixel',
                      red=Byte(name='foo', high=0xA, low=0xB),
                      green=0xCD,
                      blue=0xEF)

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('pixel'), 0xABCDEF)
        self.assertEqual(sim.inspect('pixel.red'), 0xAB)
        self.assertEqual(sim.inspect('pixel.red.high'), 0xA)
        self.assertEqual(sim.inspect('pixel.red.low'), 0xB)
        self.assertEqual(sim.inspect('pixel.green'), 0xCD)
        self.assertEqual(sim.inspect('pixel.green.high'), 0xC)
        self.assertEqual(sim.inspect('pixel.green.low'), 0xD)
        self.assertEqual(sim.inspect('pixel.blue'), 0xEF)
        self.assertEqual(sim.inspect('pixel.blue.high'), 0xE)
        self.assertEqual(sim.inspect('pixel.blue.low'), 0xF)

    def test_anonymous_pixel_slice(self):
        pixel = Pixel(Pixel=0xABCDEF)
        rh = pyrtl.WireVector(bitwidth=4, name='rh')
        rh <<= pixel.red.high
        rl = pyrtl.WireVector(bitwidth=4, name='rl')
        rl <<= pixel.red.low
        gh = pyrtl.WireVector(bitwidth=4, name='gh')
        gh <<= pixel.green.high
        gl = pyrtl.WireVector(bitwidth=4, name='gl')
        gl <<= pixel.green.low
        bh = pyrtl.WireVector(bitwidth=4, name='bh')
        bh <<= pixel.blue.high
        bl = pyrtl.WireVector(bitwidth=4, name='bl')
        bl <<= pixel.blue.low

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('rh'), 0xA)
        self.assertEqual(sim.inspect('rl'), 0xB)
        self.assertEqual(sim.inspect('gh'), 0xC)
        self.assertEqual(sim.inspect('gl'), 0xD)
        self.assertEqual(sim.inspect('bh'), 0xE)
        self.assertEqual(sim.inspect('bl'), 0xF)

        self.assertEqual(list(sorted(sim.tracer.trace.keys())),
                         ['bh', 'bl', 'gh', 'gl', 'rh', 'rl'])

    def test_anonymous_pixel_concatenate(self):
        pixel = Pixel(red=Byte(high=0xA, low=0xB),
                      green=0xCD,
                      blue=0xEF)
        out = pyrtl.WireVector(bitwidth=24, name='out')
        out <<= pixel

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('out'), 0xABCDEF)

        # The other wires are not named, so 'out' should be the only traced
        # wire.
        self.assertEqual(list(sim.tracer.trace.keys()), ['out'])


# BitPair is an array of two single wires.
BitPair = pyrtl.wire_matrix(component_schema=1, size=2)


# Word is an array of two Bytes. This checks that a @wire_struct (Byte) can be
# a component of a wire_matrix (Word).
Word = pyrtl.wire_matrix(component_schema=Byte, size=2)


# ByteMatrix tests the corner case of a single-element wire_matrix.
ByteMatrix = pyrtl.wire_matrix(component_schema=Byte, size=1)


# DWord is an array of two Words, or effectively a 2x2 array of Bytes. This
# check that a wire_matrix (Word) can be a component of a wire_matrix (DWord).
DWord = pyrtl.wire_matrix(component_schema=Word, size=2)


# CachedData is valid bit paired with some data. This checks that a wire_matrix
# (Word) can be a component of a @wire_struct (CachedData).
@pyrtl.wire_struct
class CachedData:
    valid: 1
    data: Word


class TestWireMatrix(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_wire_matrix_slice(self):
        bitpair = BitPair(name='bitpair', values=[2])
        self.assertEqual(len(bitpair), 2)
        self.assertEqual(bitpair.bitwidth, 2)
        self.assertEqual(len(pyrtl.as_wires(bitpair)), 2)
        self.assertEqual(len(bitpair[0]), 1)
        self.assertEqual(len(bitpair[1]), 1)

        # Constants are sliced immediately.
        self.assertEqual(bitpair.val, 2)
        self.assertEqual(bitpair[0].val, 1)
        self.assertEqual(bitpair[1].val, 0)

    def test_wire_matrix_concatenate(self):
        bitpair = BitPair(name='bitpair', values=[1, 0])

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('bitpair'), 2)
        self.assertEqual(sim.inspect('bitpair[0]'), 1)
        self.assertEqual(sim.inspect('bitpair[1]'), 0)

    def test_wire_matrix_exceptions(self):
        with self.assertRaises(pyrtl.PyrtlError):
            bad_bitpair = BitPair()
        with self.assertRaises(pyrtl.PyrtlError):
            bad_bitpair = BitPair(values=[])
        with self.assertRaises(pyrtl.PyrtlError):
            bad_bitpair = BitPair(values=[99, 100, 101])

    def test_wire_matrix_word_slice(self):
        word = Word(name='word', values=[0xABCD])
        self.assertEqual(len(word), 2)
        self.assertEqual(word.bitwidth, 16)
        self.assertEqual(len(pyrtl.as_wires(word)), 16)

        # Constants are sliced immediately.
        self.assertEqual(word.val, 0xABCD)
        self.assertEqual(word[0].val, 0xAB)
        self.assertEqual(word[0].high.val, 0xA)
        self.assertEqual(word[0].low.val, 0xB)
        self.assertEqual(word[1].val, 0xCD)
        self.assertEqual(word[1].high.val, 0xC)
        self.assertEqual(word[1].low.val, 0xD)

    def test_wire_matrix_word_concatenate(self):
        word = Word(name='word', values=[0xAB, 0xCD])

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('word'), 0xABCD)
        self.assertEqual(sim.inspect('word[0]'), 0xAB)
        self.assertEqual(sim.inspect('word[0].high'), 0xA)
        self.assertEqual(sim.inspect('word[0].low'), 0xB)
        self.assertEqual(sim.inspect('word[1]'), 0xCD)
        self.assertEqual(sim.inspect('word[1].high'), 0xC)
        self.assertEqual(sim.inspect('word[1].low'), 0xD)

    def test_anonymous_wire_matrix_slice(self):
        word = Word(values=[0xABCD])
        w0 = pyrtl.WireVector(bitwidth=8, name='w0')
        w0 <<= word[0]
        w0h = pyrtl.WireVector(bitwidth=4, name='w0h')
        w0h <<= word[0].high
        w1 = pyrtl.WireVector(bitwidth=8, name='w1')
        w1 <<= word[1]
        w1l = pyrtl.WireVector(bitwidth=4, name='w1l')
        w1l <<= word[1].low

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('w0'), 0xAB)
        self.assertEqual(sim.inspect('w0h'), 0xA)
        self.assertEqual(sim.inspect('w1'), 0xCD)
        self.assertEqual(sim.inspect('w1l'), 0xD)

        self.assertEqual(list(sorted(sim.tracer.trace.keys())),
                         ['w0', 'w0h', 'w1', 'w1l'])

    def test_anonymous_wire_matrix_concatenate(self):
        word = Word(values=[0xAB, Byte(high=0xC, low=0xD)])
        w = pyrtl.WireVector(bitwidth=16, name='w')
        w <<= word

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('w'), 0xABCD)

        self.assertEqual(list(sorted(sim.tracer.trace.keys())), ['w'])

    def test_wire_matrix_input(self):
        word = Word(name='word', component_type=pyrtl.Input)

        self.assertTrue(isinstance(pyrtl.as_wires(word[0]), pyrtl.Input))
        self.assertTrue(isinstance(pyrtl.as_wires(word[1]), pyrtl.Input))

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={'word[0]': 0xAB, 'word[1]': 0xCD})
        self.assertEqual(sim.inspect('word'), 0xABCD)
        self.assertEqual(sim.inspect('word[0]'), 0xAB)
        self.assertEqual(sim.inspect('word[0].high'), 0xA)
        self.assertEqual(sim.inspect('word[0].low'), 0xB)
        self.assertEqual(sim.inspect('word[1]'), 0xCD)
        self.assertEqual(sim.inspect('word[1].high'), 0xC)
        self.assertEqual(sim.inspect('word[1].low'), 0xD)

    def test_wire_matrix_register(self):
        word = Word(name='word', concatenated_type=pyrtl.Register)
        word.next <<= 0xABCD

        self.assertTrue(isinstance(pyrtl.as_wires(word), pyrtl.Register))

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('word'), 0)
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('word'), 0xABCD)
        self.assertEqual(sim.inspect('word[0]'), 0xAB)
        self.assertEqual(sim.inspect('word[1]'), 0xCD)

    def test_wire_matrix_composition_dword(self):
        dword = DWord(name='dword', values=[0x89ABCDEF])

        # Constants are sliced immediately.
        self.assertEqual(dword.val, 0x89ABCDEF)
        self.assertEqual(dword[0].val, 0x89AB)
        self.assertEqual(dword[0][0].val, 0x89)
        self.assertEqual(dword[0][0].high.val, 0x8)
        self.assertEqual(dword[0][0].low.val, 0x9)
        self.assertEqual(dword[0][1].val, 0xAB)
        self.assertEqual(dword[0][1].high.val, 0xA)
        self.assertEqual(dword[0][1].low.val, 0xB)
        self.assertEqual(dword[1].val, 0xCDEF)
        self.assertEqual(dword[1][0].val, 0xCD)
        self.assertEqual(dword[1][0].high.val, 0xC)
        self.assertEqual(dword[1][0].low.val, 0xD)
        self.assertEqual(dword[1][1].val, 0xEF)
        self.assertEqual(dword[1][1].high.val, 0xE)
        self.assertEqual(dword[1][1].low.val, 0xF)

    def test_wire_matrix_composition_cached_data(self):
        cached_data = CachedData(name='cached_data', valid=True, data=0xABCD)
        self.assertTrue(isinstance(cached_data, CachedData))

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={})
        self.assertEqual(sim.inspect('cached_data'), 0x1ABCD)
        self.assertEqual(sim.inspect('cached_data.valid'), 1)
        self.assertEqual(sim.inspect('cached_data.data'), 0xABCD)
        self.assertEqual(sim.inspect('cached_data.data[0]'), 0xAB)
        self.assertEqual(sim.inspect('cached_data.data[0].high'), 0xA)
        self.assertEqual(sim.inspect('cached_data.data[0].low'), 0xB)
        self.assertEqual(sim.inspect('cached_data.data[1]'), 0xCD)
        self.assertEqual(sim.inspect('cached_data.data[1].high'), 0xC)
        self.assertEqual(sim.inspect('cached_data.data[1].low'), 0xD)

    def test_byte_matrix_const(self):
        byte_matrix = ByteMatrix(name='byte_matrix', values=[0xAB])
        self.assertEqual(len(byte_matrix), 1)
        self.assertEqual(byte_matrix.bitwidth, 8)
        self.assertEqual(len(pyrtl.as_wires(byte_matrix)), 8)

        # Constants are sliced immediately.
        self.assertEqual(byte_matrix.val, 0xAB)
        self.assertEqual(byte_matrix[0].val, 0xAB)
        self.assertEqual(byte_matrix[0].high.val, 0xA)
        self.assertEqual(byte_matrix[0].low.val, 0xB)

    def test_byte_matrix_input_slice(self):
        byte_matrix = ByteMatrix(name='byte_matrix',
                                 component_type=pyrtl.Input)

        self.assertTrue(isinstance(pyrtl.as_wires(byte_matrix[0]),
                                   pyrtl.Input))

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={'byte_matrix[0]': 0xAB})
        self.assertEqual(sim.inspect('byte_matrix'), 0xAB)
        self.assertEqual(sim.inspect('byte_matrix[0]'), 0xAB)
        self.assertEqual(sim.inspect('byte_matrix[0].high'), 0xA)
        self.assertEqual(sim.inspect('byte_matrix[0].low'), 0xB)

    def test_byte_matrix_input_concatenate(self):
        byte_matrix = ByteMatrix(name='byte_matrix',
                                 concatenated_type=pyrtl.Input)

        self.assertTrue(isinstance(pyrtl.as_wires(byte_matrix),
                                   pyrtl.Input))

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={'byte_matrix': 0xAB})
        self.assertEqual(sim.inspect('byte_matrix'), 0xAB)
        self.assertEqual(sim.inspect('byte_matrix[0]'), 0xAB)
        self.assertEqual(sim.inspect('byte_matrix[0].high'), 0xA)
        self.assertEqual(sim.inspect('byte_matrix[0].low'), 0xB)


class TestOneHotToBinary(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_simple_onehot(self):
        i = pyrtl.Input(bitwidth=8, name='i')
        o = pyrtl.Output(bitwidth=3, name='o')
        o <<= pyrtl.one_hot_to_binary(i)

        sim = pyrtl.Simulation()
        sim.step({i: 0b00000001})
        self.assertEqual(sim.inspect('o'), 0)
        sim.step({i: 0b10000000})
        self.assertEqual(sim.inspect('o'), 7)
        sim.step({i: 32})
        self.assertEqual(sim.inspect('o'), 5)
        sim.step({i: 16})
        self.assertEqual(sim.inspect('o'), 4)

    def test_multiple_ones(self):
        i = pyrtl.Input(bitwidth=8, name='i')
        o = pyrtl.Output(bitwidth=3, name='o')
        o <<= pyrtl.one_hot_to_binary(i)

        sim = pyrtl.Simulation()
        sim.step({i: 0b00000101})
        self.assertEqual(sim.inspect('o'), 0)
        sim.step({i: 0b11000000})
        self.assertEqual(sim.inspect('o'), 6)
        sim.step({i: 0b10010010})
        self.assertEqual(sim.inspect('o'), 1)

    def test_no_ones(self):
        i = pyrtl.Input(bitwidth=8, name='i')
        o = pyrtl.Output(bitwidth=3, name='o')
        o <<= pyrtl.one_hot_to_binary(i)

        sim = pyrtl.Simulation()
        sim.step({i: 0b00000000})
        self.assertEqual(sim.inspect('o'), 0)


class TestBinaryToOneHot(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_simple_binary_to_one_hot(self):
        bit_position = pyrtl.Input(bitwidth=8, name='bit_position')
        one_hot = pyrtl.Output(name='one_hot')
        one_hot <<= pyrtl.binary_to_one_hot(bit_position)

        self.assertEqual(one_hot.bitwidth, 256)

        sim = pyrtl.Simulation()
        sim.step({bit_position: 0})
        self.assertEqual(sim.inspect('one_hot'), 0b01)
        sim.step({bit_position: 2})
        self.assertEqual(sim.inspect('one_hot'), 0b0100)
        sim.step({bit_position: 5})
        self.assertEqual(sim.inspect('one_hot'), 0b00100000)
        sim.step({bit_position: 12})
        self.assertEqual(sim.inspect('one_hot'), 0b0001000000000000)
        sim.step({bit_position: 15})
        self.assertEqual(sim.inspect('one_hot'), 0b1000000000000000)

    # Tests with the max_bitwidth set
    def test_with_max_bitwidth(self):
        bit_position = pyrtl.Input(bitwidth=8, name='bit_position')
        one_hot = pyrtl.Output(name='one_hot')
        one_hot <<= pyrtl.binary_to_one_hot(bit_position, max_bitwidth=4)

        self.assertEqual(one_hot.bitwidth, 4)

        sim = pyrtl.Simulation()
        sim.step({bit_position: 0})
        self.assertEqual(sim.inspect('one_hot'), 0b0001)
        sim.step({bit_position: 3})
        self.assertEqual(sim.inspect('one_hot'), 0b1000)

        # The max_bitwidth set is not enough for a bit position of 4
        sim.step({bit_position: 4})
        self.assertEqual(sim.inspect('one_hot'), 0b0000)


if __name__ == "__main__":
    unittest.main()
