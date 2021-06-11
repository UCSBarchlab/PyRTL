import unittest
import random
import io
import pyrtl
from .test_importexport import full_adder_blif


graphviz_string_detailed = """\
digraph g {
    graph [splines="spline", outputorder="edgesfirst"];
    node [shape=circle, style=filled, fillcolor=lightblue1,
        fontcolor=black, fontname=helvetica, penwidth=0,
        fixedsize=shape];
    edge [labelfloat=false, penwidth=2, color=deepskyblue, arrowsize=.5];
    n0 [label="a", shape=invhouse, fillcolor=coral];
    n1 [label="8", shape=circle, fillcolor=lightgrey];
    n2 [label="0", shape=circle, fillcolor=lightgrey];
    n3 [label="0", shape=circle, fillcolor=lightgrey];
    n4 [label=" (Fanout: 0)", height=.1, width=.1];
    n5 [label="d", shape=house, fillcolor=lawngreen];
    n6 [label="[0]*2 (Fanout: 1)", fillcolor=azure1, height=.25, width=.25];
    n7 [label="concat (Fanout: 1)", height=.1, width=.1];
    n8 [label="* (Fanout: 1)"];
    n9 [label="[7:2] (Fanout: 1)", fillcolor=azure1, height=.25, width=.25];
    n10 [label="[0]*4 (Fanout: 1)", fillcolor=azure1, height=.25, width=.25];
    n11 [label="concat (Fanout: 1)", height=.1, width=.1];
    n0 -> n7 [label="a/2 (Delay: 0.00)", penwidth="6", arrowhead="none"];
    n1 -> n8 [label="const_0_8/4 (Delay: 0.00)", penwidth="6", arrowhead="normal"];
    n2 -> n6 [label="const_1_0/1 (Delay: 0.00)", penwidth="2", arrowhead="none"];
    n3 -> n10 [label="const_2_0/1 (Delay: 0.00)", penwidth="2", arrowhead="none"];
    n4 -> n5 [label="d/10 (Delay: 706.50)", penwidth="6", arrowhead="normal"];
    n6 -> n7 [label="tmp0/2 (Delay: 0.00)", penwidth="6", arrowhead="none"];
    n7 -> n8 [label="tmp1/4 (Delay: 0.00)", penwidth="6", arrowhead="normal"];
    n8 -> n9 [label="tmp2/8 (Delay: 706.50)", penwidth="6", arrowhead="none"];
    n9 -> n11 [label="tmp3/6 (Delay: 706.50)", penwidth="6", arrowhead="none"];
    n10 -> n11 [label="tmp4/4 (Delay: 0.00)", penwidth="6", arrowhead="none"];
    n11 -> n4 [label="tmp5/10 (Delay: 706.50)", penwidth="6", arrowhead="normal"];
    {
        rank=same;
        edge[style=invis];
        n6 -> n0;
        rankdir=LR;
    }
    {
        rank=same;
        edge[style=invis];
        n10 -> n9;
        rankdir=LR;
    }
}

"""

graphviz_string_arg_ordered = """\
digraph g {
    graph [splines="spline", outputorder="edgesfirst"];
    node [shape=circle, style=filled, fillcolor=lightblue1,
        fontcolor=black, fontname=helvetica, penwidth=0,
        fixedsize=shape];
    edge [labelfloat=false, penwidth=2, color=deepskyblue, arrowsize=.5];
    n0 [label="0", shape=circle, fillcolor=lightgrey];
    n1 [label="0", shape=circle, fillcolor=lightgrey];
    n2 [label="0", shape=circle, fillcolor=lightgrey];
    n3 [label="i", shape=invhouse, fillcolor=coral];
    n4 [label="j", shape=invhouse, fillcolor=coral];
    n5 [label="", height=.1, width=.1];
    n6 [label="o", shape=house, fillcolor=lawngreen];
    n7 [label="", height=.1, width=.1];
    n8 [label="q", shape=house, fillcolor=lawngreen];
    n9 [label="[0]*4", fillcolor=azure1, height=.25, width=.25];
    n10 [label="concat", height=.1, width=.1];
    n11 [label="<"];
    n12 [label="[0]*7", fillcolor=azure1, height=.25, width=.25];
    n13 [label="concat", height=.1, width=.1];
    n14 [label="[0]*4", fillcolor=azure1, height=.25, width=.25];
    n15 [label="concat", height=.1, width=.1];
    n16 [label=">"];
    n0 -> n9 [label="", penwidth="2", arrowhead="none"];
    n1 -> n12 [label="", penwidth="2", arrowhead="none"];
    n2 -> n14 [label="", penwidth="2", arrowhead="none"];
    n3 -> n11 [label="", penwidth="6", arrowhead="normal"];
    n3 -> n16 [label="", penwidth="6", arrowhead="normal"];
    n4 -> n10 [label="", penwidth="6", arrowhead="none"];
    n4 -> n15 [label="", penwidth="6", arrowhead="none"];
    n5 -> n6 [label="", penwidth="6", arrowhead="normal"];
    n7 -> n8 [label="", penwidth="2", arrowhead="normal"];
    n9 -> n10 [label="", penwidth="6", arrowhead="none"];
    n10 -> n11 [label="", penwidth="6", arrowhead="normal"];
    n11 -> n13 [label="", penwidth="2", arrowhead="none"];
    n12 -> n13 [label="", penwidth="6", arrowhead="none"];
    n13 -> n5 [label="", penwidth="6", arrowhead="normal"];
    n14 -> n15 [label="", penwidth="6", arrowhead="none"];
    n15 -> n16 [label="", penwidth="6", arrowhead="normal"];
    n16 -> n7 [label="", penwidth="2", arrowhead="normal"];
    {
        rank=same;
        edge[style=invis];
        n9 -> n4;
        rankdir=LR;
    }
    {
        rank=same;
        edge[style=invis];
        n3 -> n10;
        rankdir=LR;
    }
    {
        rank=same;
        edge[style=invis];
        n12 -> n11;
        rankdir=LR;
    }
    {
        rank=same;
        edge[style=invis];
        n14 -> n4;
        rankdir=LR;
    }
    {
        rank=same;
        edge[style=invis];
        n15 -> n3;
        rankdir=LR;
    }
}

"""

graphviz_string_arg_unordered = """\
digraph g {
    graph [splines="spline", outputorder="edgesfirst"];
    node [shape=circle, style=filled, fillcolor=lightblue1,
        fontcolor=black, fontname=helvetica, penwidth=0,
        fixedsize=shape];
    edge [labelfloat=false, penwidth=2, color=deepskyblue, arrowsize=.5];
    n0 [label="0", shape=circle, fillcolor=lightgrey];
    n1 [label="0", shape=circle, fillcolor=lightgrey];
    n2 [label="0", shape=circle, fillcolor=lightgrey];
    n3 [label="i", shape=invhouse, fillcolor=coral];
    n4 [label="j", shape=invhouse, fillcolor=coral];
    n5 [label="", height=.1, width=.1];
    n6 [label="o", shape=house, fillcolor=lawngreen];
    n7 [label="", height=.1, width=.1];
    n8 [label="q", shape=house, fillcolor=lawngreen];
    n9 [label="[0]*4", fillcolor=azure1, height=.25, width=.25];
    n10 [label="concat", height=.1, width=.1];
    n11 [label="<"];
    n12 [label="[0]*7", fillcolor=azure1, height=.25, width=.25];
    n13 [label="concat", height=.1, width=.1];
    n14 [label="[0]*4", fillcolor=azure1, height=.25, width=.25];
    n15 [label="concat", height=.1, width=.1];
    n16 [label=">"];
    n0 -> n9 [label="", penwidth="2", arrowhead="none"];
    n1 -> n12 [label="", penwidth="2", arrowhead="none"];
    n2 -> n14 [label="", penwidth="2", arrowhead="none"];
    n3 -> n11 [label="", penwidth="6", arrowhead="normal"];
    n3 -> n16 [label="", penwidth="6", arrowhead="normal"];
    n4 -> n10 [label="", penwidth="6", arrowhead="none"];
    n4 -> n15 [label="", penwidth="6", arrowhead="none"];
    n5 -> n6 [label="", penwidth="6", arrowhead="normal"];
    n7 -> n8 [label="", penwidth="2", arrowhead="normal"];
    n9 -> n10 [label="", penwidth="6", arrowhead="none"];
    n10 -> n11 [label="", penwidth="6", arrowhead="normal"];
    n11 -> n13 [label="", penwidth="2", arrowhead="none"];
    n12 -> n13 [label="", penwidth="6", arrowhead="none"];
    n13 -> n5 [label="", penwidth="6", arrowhead="normal"];
    n14 -> n15 [label="", penwidth="6", arrowhead="none"];
    n15 -> n16 [label="", penwidth="6", arrowhead="normal"];
    n16 -> n7 [label="", penwidth="2", arrowhead="normal"];
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
            timing = pyrtl.TimingAnalysis()
            node_fan_in = {net: len(net.args) for net in pyrtl.working_block()}
            graph_namer = pyrtl.graphviz_detailed_namer(
                extra_node_info=node_fan_in,
                extra_edge_info=timing.timing_map
            )
            pyrtl.output_to_graphviz(vfile, namer=graph_namer)

    def test_output_to_graphviz_correct_detailed_output(self):
        pyrtl.wire._reset_wire_indexers()

        a = pyrtl.Input(2, 'a')
        b = a * 8
        c = b[2:]
        d = pyrtl.Output(10, 'd')
        d <<= c

        analysis = pyrtl.TimingAnalysis()
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
                namer=pyrtl.graphviz_detailed_namer(node_fanout, wire_delay),
                maintain_arg_order=True
            )
            self.assertEqual(vfile.getvalue(), graphviz_string_detailed)

    def test_output_to_graphviz_correct_output_with_arg_ordering(self):
        i = pyrtl.Input(8, 'i')
        j = pyrtl.Input(4, 'j')
        o = pyrtl.Output(8, 'o')
        q = pyrtl.Output(1, 'q')
        o <<= i < j
        q <<= j > i

        with io.StringIO() as vfile:
            pyrtl.output_to_graphviz(file=vfile, maintain_arg_order=True)
            self.assertEqual(vfile.getvalue(), graphviz_string_arg_ordered)

    def test_output_to_graphviz_correct_output_without_arg_ordering(self):
        i = pyrtl.Input(8, 'i')
        j = pyrtl.Input(4, 'j')
        o = pyrtl.Output(8, 'o')
        q = pyrtl.Output(1, 'q')
        o <<= i < j
        q <<= j > i

        with io.StringIO() as vfile:
            pyrtl.output_to_graphviz(file=vfile)
            self.assertEqual(vfile.getvalue(), graphviz_string_arg_unordered)


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

        self.assertEqual(len(g[inwire]), 1)
        self.assertEqual(list(g[inwire].keys())[0].op, '|')
        self.assertEqual(len(g[inwire].values()), 1)
        edges = list(g[inwire].values())[0]
        self.assertEqual(len(edges), 1)
        self.assertIs(edges[0], inwire)

    def test_netgraph_unused_wires(self):
        genwire = pyrtl.WireVector(8, "genwire")
        inwire = pyrtl.Input(8, "inwire")
        outwire = pyrtl.Output(8, "outwire")
        constwire = pyrtl.Const(8, 8)
        reg = pyrtl.Register(8, "reg")
        g = pyrtl.net_graph()
        self.assertEqual(len(g), 0)

    def test_netgraph_same_wire_multiple_edges_to_same_net(self):
        c = pyrtl.Const(1, 1)
        w = pyrtl.concat(c, c, c)
        g = pyrtl.net_graph()
        self.assertEqual(len(g[c]), 1)
        edges = list(g[c].values())[0]
        self.assertEqual(len(edges), 3)
        for w in edges:
            self.assertIs(w, c)


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
