import unittest
import random
import io
import pyrtl
from pyrtl import analysis
from .test_blif import full_adder_blif


graphviz_string = """
              digraph g {

              graph [splines="spline"];
              node [shape=circle, style=filled, fillcolor=lightblue1,
                    fontcolor=black, fontname=helvetica, penwidth=0,
                    fixedsize=true];
              edge [labelfloat=false, penwidth=2, color=deepskyblue, arrowsize=.5];
                  n0 [label="bits(0,0) (Fanout: 1)", height=.1, width=.1];
    n1 [label="bits(7,2) (Fanout: 1)", height=.1, width=.1];
    n2 [label="bits(0,0) (Fanout: 1)", height=.1, width=.1];
    n3 [label="concat (Fanout: 1)", height=.1, width=.1];
    n4 [label=" (Fanout: 0)", height=.1, width=.1];
    n5 [label="concat (Fanout: 1)", height=.1, width=.1];
    n6 [label="* (Fanout: 1)"];
    n7 [label="8", shape=circle, fillcolor=lightgrey];
    n8 [label="d", shape=house, fillcolor=lawngreen];
    n9 [label="0", shape=circle, fillcolor=lightgrey];
    n10 [label="0", shape=circle, fillcolor=lightgrey];
    n11 [label="a", shape=invhouse, fillcolor=coral];
   n0 -> n3 [label="tmp0/2 (Delay: 0.00)", penwidth="6", arrowhead="none"];
   n1 -> n5 [label="tmp3/6 (Delay: 706.50)", penwidth="6", arrowhead="none"];
   n2 -> n5 [label="tmp4/4 (Delay: 0.00)", penwidth="6", arrowhead="none"];
   n3 -> n6 [label="tmp1/4 (Delay: 0.00)", penwidth="6", arrowhead="normal"];
   n4 -> n8 [label="d/10 (Delay: 706.50)", penwidth="6", arrowhead="normal"];
   n5 -> n4 [label="tmp5/10 (Delay: 706.50)", penwidth="6", arrowhead="normal"];
   n6 -> n1 [label="tmp2/8 (Delay: 706.50)", penwidth="6", arrowhead="none"];
   n7 -> n6 [label="const_0_8/4 (Delay: 0.00)", penwidth="6", arrowhead="normal"];
   n9 -> n0 [label="const_1_0/1 (Delay: 0.00)", penwidth="2", arrowhead="none"];
   n10 -> n2 [label="const_2_0/1 (Delay: 0.00)", penwidth="2", arrowhead="none"];
   n11 -> n3 [label="a/2 (Delay: 0.00)", penwidth="6", arrowhead="none"];
}


"""


class TestOutputGraphs(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_output_to_tgf_does_not_throw_error(self):
        with io.StringIO() as vfile:
            pyrtl.input_from_blif(full_adder_blif)
            pyrtl.output_to_trivialgraph(vfile)

    def test_output_to_graphviz_does_not_throw_error(self):
        with io.StringIO() as vfile:
            pyrtl.input_from_blif(full_adder_blif)
            pyrtl.output_to_graphviz(vfile)

    def test_output_to_graphviz_with_custom_namer_does_not_throw_error(self):
        with io.StringIO() as vfile:
            pyrtl.input_from_blif(full_adder_blif)
            timing = analysis.TimingAnalysis()
            node_fan_in = {net: len(net.args) for net in pyrtl.working_block()}
            graph_namer = pyrtl.graphviz_detailed_namer(
                extra_node_info=node_fan_in,
                extra_edge_info=timing.timing_map
            )
            pyrtl.output_to_graphviz(vfile, namer=graph_namer)

    @unittest.skip("Need to make Graphviz output order deterministic via sorting")
    def test_output_to_graphviz_correct_detailed_output(self):
        from pyrtl.analysis.estimate import TimingAnalysis

        a = pyrtl.Input(2, 'a')
        b = a * 8
        c = b[2:]
        d = pyrtl.Output(10, 'd')
        d <<= c

        analysis = TimingAnalysis()
        _, dst_map = pyrtl.working_block().net_connections()

        def get_fanout(n):
            if isinstance(n, pyrtl.LogicNet):
                if n.op == '@':
                    return 0
                w = n.dests[0]
            else:
                w = n

            if isinstance(w, pyrtl.Output):
                return 0
            else:
                return len(dst_map[w])

        node_fanout = {n: "Fanout: %d" % get_fanout(n) for n in pyrtl.working_block().logic}
        wire_delay = {
            w: "Delay: %.2f" % analysis.timing_map[w] for w in pyrtl.working_block().wirevector_set
        }

        with io.StringIO() as vfile:
            pyrtl.output_to_graphviz(
                file=vfile,
                namer=pyrtl.graphviz_detailed_namer(node_fanout, wire_delay)
            )
            self.assertEqual(vfile.getvalue(), graphviz_string)


class TestNetGraph(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_as_graph(self):
        inwire = pyrtl.Input(bitwidth=1, name="inwire1")
        inwire2 = pyrtl.Input(bitwidth=1)
        inwire3 = pyrtl.Input(bitwidth=1)
        tempwire = pyrtl.WireVector()
        tempwire2 = pyrtl.WireVector()
        outwire = pyrtl.Output()

        tempwire <<= inwire | inwire2
        tempwire2 <<= ~tempwire
        outwire <<= tempwire2 & inwire3

        g = pyrtl.net_graph()
        # note for future: this might fail if we change
        # the way that temp wires are inserted, but that
        # should not matter for this test and so the number
        # can be safely updated.
        self.assertEqual(len(g), 10)

    def test_netgraph_unused_wires(self):
        genwire = pyrtl.WireVector(8, "genwire")
        inwire = pyrtl.Input(8, "inwire")
        outwire = pyrtl.Output(8, "outwire")
        constwire = pyrtl.Const(8, 8)
        reg = pyrtl.Register(8, "reg")
        g = pyrtl.net_graph()
        self.assertEquals(len(g), 0)


class TestOutputIPynb(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.maxDiff = None

    def test_one_bit_adder_matches_expected(self):
        temp1 = pyrtl.WireVector(bitwidth=1, name='temp1')
        temp2 = pyrtl.WireVector()

        a, b, c = pyrtl.Input(1, 'a'), pyrtl.Input(1, 'b'), pyrtl.Input(1, 'c')
        sum, carry_out = pyrtl.Output(1, 'sum'), pyrtl.Output(1, 'carry_out')

        sum <<= a ^ b ^ c

        temp1 <<= a & b  # connect the result of a & b to the pre-allocated wirevector
        temp2 <<= a & c
        temp3 = b & c  # temp3 IS the result of b & c (this is the first mention of temp3)
        carry_out <<= temp1 | temp2 | temp3

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(15):
            sim.step({
                'a': random.choice([0, 1]),
                'b': random.choice([0, 1]),
                'c': random.choice([0, 1])
            })

        htmlstring = pyrtl.trace_to_html(sim_trace)  # tests if it compiles or not


if __name__ == "__main__":
    unittest.main()
