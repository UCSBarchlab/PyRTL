import sys
from pyrtl import *
from export_base import *

#-----------------------------------------------------------------
#   ___      __   __   __  ___
#  |__  \_/ |__) /  \ |__)  |
#  |___ / \ |    \__/ |  \  |
#

class TrivialGraphExporter(ExportBase):
    def __init__(self):
        self.uid = 1
        self.nodes = {}
        self.edges = set([])
        self.edge_names = {}
        self._block = None

    def producer(self, wire):
        assert isinstance(wire, WireVector)
        for net in sorted(self._block.logic):
            for dest in sorted(net.dests):
                if dest == wire:
                    return net
        self.add_node(wire, '???')
        return wire

    def consumer(self, wire):
        assert isinstance(wire, WireVector)
        for net in sorted(self._block.logic):
            for arg in sorted(net.args):
                if arg == wire:
                    return net
        self.add_node(wire, '???')
        return wire

    def add_node(self, x, label):
        self.nodes[x] = (self.uid, label)
        self.uid += 1

    def add_edge(self, frm, to):
        if hasattr(frm, 'name') and not frm.name.startswith('tmp'):
            edge_label = frm.name
        else:
            edge_label = ''
        if frm not in self.nodes:
            frm = self.producer(frm)
        if to not in self.nodes:
            to = self.consumer(to)
        (frm_id, _) = self.nodes[frm]
        (to_id, _) = self.nodes[to]
        self.edges.add((frm_id, to_id))
        if edge_label:
            self.edge_names[(frm_id, to_id)] = edge_label

    def import_from_block(self, block):
        self._block = block
        # build edge and node sets
        for net in sorted(self._block.logic):
            label = str(net.op)
            label += str(net.op_param) if net.op_param is not None else ''
            self.add_node(net, label)
        for input in sorted(self._block.wirevector_subset(Input)):
            label = 'in' if input.name is None else input.name
            self.add_node(input, label)
        for output in sorted(self._block.wirevector_subset(Output)):
            label = 'out' if output.name is None else output.name
            self.add_node(output, label)
        for const in sorted(self._block.wirevector_subset(Const)):
            label = str(const.val)
            self.add_node(const, label)
        for net in sorted(self._block.logic):
            for arg in sorted(net.args):
                self.add_edge(arg, net)
            for dest in sorted(net.dests):
                self.add_edge(net, dest)

    def dump(self, file=sys.stdout):
        for (id, label) in sorted(self.nodes.values()):
            print >> file, id, label
        print >> file, '#'
        for (frm, to) in sorted(self.edges):
            print >> file, frm, to, self.edge_names.get((frm, to), '')
