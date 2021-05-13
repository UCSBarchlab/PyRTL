from __future__ import print_function, unicode_literals, absolute_import

import unittest
import pyrtl


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
        self.assertEquals(pyrtl.area_estimation(), (0.00734386752, 0.01879779717361501))

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
        self.assertEquals(pyrtl.area_estimation(), (0.00734386752, 0.001879779717361501))


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
        timing = pyrtl.TimingAnalysis()
        self.assertEqual(timing.max_freq(), 610.2770657878676)
        self.assertEquals(timing.max_length(), 1255.6000000000001)


class TestYosysInterface(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()


class TestPaths(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    def test_one_path_to_one_output(self):
        a = pyrtl.Input(4, 'a')
        o = pyrtl.Output(name='o')
        o <<= a * 2

        paths = pyrtl.paths(a, o)
        paths_a_to_o = paths[a][o]
        self.assertEqual(len(paths_a_to_o), 1)
        path_a_to_o = paths_a_to_o[0]
        self.assertEqual(len(path_a_to_o), 2)
        self.assertEqual(path_a_to_o[0].op, '*')
        self.assertEqual(path_a_to_o[1].op, 'w')

    def test_two_paths_to_one_output(self):
        a = pyrtl.Input(4, 'a')
        w1 = a * 2
        w2 = a + 1
        o = pyrtl.Output(name='o')
        o <<= w1 - w2

        paths = pyrtl.paths(a, o)
        self.assertEqual(len(paths[a][o]), 2)
        for path in paths[a][o]:
            if path[0].op == '*':
                self.assertEqual(len(path), 3)
            else:
                # Has an extra 'c'
                self.assertEqual(path[0].op, '+')
                self.assertEqual(len(path), 4)

    def test_two_paths_to_two_outputs(self):
        a = pyrtl.Input(4, 'a')
        o1, o2 = pyrtl.output_list('o1/5 o1/8')
        o1 <<= a + 1
        o2 <<= a * 2

        paths = pyrtl.paths(a)
        paths_from_a = paths[a]
        self.assertEqual(len(paths_from_a), 2)
        path_to_o1 = paths_from_a[o1]
        self.assertEqual(len(path_to_o1), 1)
        path_to_o2 = paths_from_a[o2]
        self.assertEqual(len(path_to_o2), 1)

    def test_all_paths(self):
        a, b, c = pyrtl.input_list('a/2 b/4 c/1')
        o, p = pyrtl.output_list('o/4 p/2')
        o <<= a + (b ^ (b + 1))
        p <<= c * 2 - a

        paths = pyrtl.paths()

        # We have entries for every input, output pair
        for start in (a, b, c):
            self.assertEqual(len(paths[start]), 2)
            self.assertTrue([w.name for w in paths[start].keys()], [o.name, p.name])

        paths_a_to_o = paths[a][o]
        self.assertEqual(len(paths_a_to_o), 1)
        path_a_to_o = paths_a_to_o[0]
        self.assertEqual(path_a_to_o[0].op, 'c')
        self.assertEqual(path_a_to_o[1].op, '+')
        self.assertEqual(path_a_to_o[2].op, 's')

        paths_a_to_p = paths[a][p]
        self.assertEqual(len(paths_a_to_p), 1)
        path_a_to_p = paths_a_to_p[0]
        self.assertEqual(path_a_to_p[0].op, 'c')
        self.assertEqual(path_a_to_p[1].op, '-')
        self.assertEqual(path_a_to_p[2].op, 's')

        paths_b_to_o = paths[b][o]
        self.assertEqual(len(paths_b_to_o), 2)
        paths_b_to_p = paths[b][p]
        self.assertEqual(len(paths_b_to_p), 0)

        paths_c_to_o = paths[c][o]
        self.assertEqual(len(paths_c_to_o), 0)
        paths_c_to_p = paths[c][p]
        self.assertEqual(len(paths_c_to_p), 1)


class TestDistance(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    def test_simple_distance(self):
        for b in (None, pyrtl.working_block()):
            a = pyrtl.Input(4, 'a')
            o = pyrtl.Output(name='o')
            o <<= a * 2

            distances = pyrtl.distance(a, o, lambda _: 1, b)
            self.assertEqual(len(distances), 1)
            self.assertEqual(list(distances.values())[0], 2)

    def test_several_distances(self):
        a = pyrtl.Input(4, 'a')
        o = pyrtl.Output(name='o')
        w1 = a * 2
        w2 = w1 & 0b1101 + a
        o <<= ~w2

        distances = pyrtl.distance(a, o, lambda _: 1)
        self.assertEqual(len(distances), 2)
        for path, distance in distances.items():
            self.assertEqual(distance, len(path))

    def test_special_cost(self):
        a = pyrtl.Input(4, 'a')
        o = pyrtl.Output(name='o')
        w1 = a * 2
        w2 = w1 - 4
        o <<= ~w2

        def cost(net):
            if net.op in 'wcs':
                return 0
            elif net.op in '*+-':
                return 2
            else:
                return 1

        distances = pyrtl.distance(a, o, cost)
        self.assertEqual(len(distances), 1)
        self.assertEqual(list(distances.values())[0], 5)


class TestFanout(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_fanout_simple(self):
        i = pyrtl.Input(1, 'i')
        o = pyrtl.Output(3, 'o')
        w = i ^ 1
        y = i | 1
        z = i & 0
        o <<= w + y + z
        self.assertEqual(pyrtl.fanout(i), 3)
        for wire in (w, y, z):
            self.assertEqual(pyrtl.fanout(wire), 1)
        self.assertEqual(pyrtl.fanout(o), 0)

    def test_fanout_wire_repeated_as_arg(self):
        i = pyrtl.Input(1, 'i')
        _w = i * i
        self.assertEqual(pyrtl.fanout(i), 2)

    def test_fanout_wire_repeated_in_concat(self):
        w = pyrtl.WireVector(2)
        _c = pyrtl.concat(w, w, w, w)
        self.assertEqual(pyrtl.fanout(w), 4)


if __name__ == "__main__":
    unittest.main()
