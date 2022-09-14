from __future__ import print_function, absolute_import

import unittest
import io
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
        self.assertEqual(pyrtl.area_estimation(), (0.00734386752, 0.01879779717361501))

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
        self.assertEqual(pyrtl.area_estimation(), (0.00734386752, 0.001879779717361501))


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
        self.assertEqual(timing.max_length(), 1255.6000000000001)


class TestYosysInterface(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()


paths_print_output = """\
From i
  To o
    Path 0
      tmp5/3W <-- - -- i/2I, tmp4/2W
      tmp6/3W <-- | -- tmp2/3W, tmp5/3W
      o/3O <-- w -- tmp6/3W
    Path 1
      tmp1/3W <-- c -- tmp0/1W, i/2I
      tmp2/3W <-- & -- tmp1/3W, j/3I
      tmp6/3W <-- | -- tmp2/3W, tmp5/3W
      o/3O <-- w -- tmp6/3W
  To p
    Path 0
      tmp8/4W <-- c -- tmp7/2W, i/2I
      tmp9/5W <-- - -- k/4I, tmp8/4W
      p/5O <-- w -- tmp9/5W
From j
  To o
    Path 0
      tmp2/3W <-- & -- tmp1/3W, j/3I
      tmp6/3W <-- | -- tmp2/3W, tmp5/3W
      o/3O <-- w -- tmp6/3W
  To p
    (No paths)
From k
  To o
    (No paths)
  To p
    Path 0
      tmp9/5W <-- - -- k/4I, tmp8/4W
      p/5O <-- w -- tmp9/5W
"""


class TestPaths(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
        # To compare textual consistency, need to make
        # sure we're starting at the same index for all
        # automatically created names.
        pyrtl.wire._reset_wire_indexers()
        pyrtl.memory._reset_memory_indexer()

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

    def test_subset_of_all_paths(self):
        i, j, k = pyrtl.input_list('i/2 j/3 k/4')
        o, p = pyrtl.Output(), pyrtl.Output()
        o <<= i & j
        p <<= k - i

        # Make sure passing in both set and list works
        paths = pyrtl.paths([i, k], {o})
        paths_from_i = paths[i]
        self.assertNotIn(p, paths_from_i)  # Because p was not provided as target output
        self.assertEqual(len(paths_from_i[o]), 1)  # One path from i to o
        self.assertEqual(paths_from_i[o][0][0].op, 'c')
        self.assertEqual(paths_from_i[o][0][1].op, '&')
        self.assertEqual(paths_from_i[o][0][2].op, 'w')

        paths_from_k = paths[k]
        self.assertNotIn(p, paths_from_k)  # Because p was not provided as target output
        self.assertEqual(len(paths_from_k[o]), 0)  # 0 paths from k to o

    def test_paths_empty_src_and_dst_equal_with_no_other_logic(self):
        i = pyrtl.Input(4, 'i')
        paths = pyrtl.paths(i, i)
        self.assertEqual(len(paths[i][i]), 0)

    def test_paths_with_loop(self):
        r = pyrtl.Register(1, 'r')
        r.next <<= r & ~r
        paths = pyrtl.paths(r, r)
        self.assertEqual(len(paths[r][r]), 2)
        p1, p2 = sorted(paths[r][r], key=lambda p: len(p), reverse=True)
        self.assertEqual(len(p1), 3)
        self.assertEqual(p1[0].op, '~')
        self.assertEqual(p1[1].op, '&')
        self.assertEqual(p1[2].op, 'r')
        self.assertEqual(len(p2), 2)
        self.assertEqual(p2[0].op, '&')
        self.assertEqual(p2[1].op, 'r')

    def test_paths_loop_and_input(self):
        i = pyrtl.Input(1, 'i')
        o = pyrtl.Output(1, 'o')
        r = pyrtl.Register(1, 'r')
        r.next <<= i & r
        o <<= r
        paths = pyrtl.paths(r, o)
        self.assertEqual(len(paths[r][o]), 1)

    def test_paths_loop_get_arbitrary_inner_wires(self):
        w = pyrtl.WireVector(1, 'w')
        y = w & pyrtl.Const(1)
        w <<= ~y
        paths = pyrtl.paths(w, y)
        self.assertEqual(len(paths[w][y]), 1)
        self.assertEqual(paths[w][y][0][0].op, '&')

    def test_paths_no_path_exists(self):
        i = pyrtl.Input(1, 'i')
        o = pyrtl.Output(1, 'o')
        o <<= ~i

        w = pyrtl.WireVector(1, 'w')
        y = w & pyrtl.Const(1)
        w <<= ~y

        paths = pyrtl.paths(w, o)
        self.assertEqual(len(paths[w][o]), 0)

    def test_paths_with_memory(self):
        i = pyrtl.Input(4, 'i')
        o = pyrtl.Output(8, 'o')
        mem = pyrtl.MemBlock(8, 32, 'mem')
        waddr = pyrtl.Input(32, 'waddr')
        raddr = pyrtl.Input(32, 'raddr')
        data = mem[raddr]
        mem[waddr] <<= (i + ~data).truncate(8)
        o <<= data

        paths = pyrtl.paths(i, o)
        path = paths[i][o][0]
        self.assertEqual(path[0].op, 'c')
        self.assertEqual(path[1].op, '+')
        self.assertEqual(path[2].op, 's')
        self.assertEqual(path[3].op, '@')
        self.assertEqual(path[4].op, 'm')
        self.assertEqual(path[5].op, 'w')

        # TODO Once issue with _MemIndexed lookups is resolved,
        #      these should be `data` instead of `data.wire`.
        paths = pyrtl.paths(data.wire, data.wire)
        path = paths[data.wire][data.wire][0]
        self.assertEqual(path[0].op, '~')
        self.assertEqual(path[1].op, '+')
        self.assertEqual(path[2].op, 's')
        self.assertEqual(path[3].op, '@')
        self.assertEqual(path[4].op, 'm')

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

    def test_pretty_print(self):
        i, j, k = pyrtl.input_list('i/2 j/3 k/4')
        o, p = pyrtl.Output(name='o'), pyrtl.Output(name='p')
        o <<= (i & j) | (i - 1)
        p <<= k - i

        paths = pyrtl.paths()
        output = io.StringIO()
        paths.print(file=output)
        self.assertEqual(output.getvalue(), paths_print_output)


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
