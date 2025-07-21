"""
Helper functions for viewing the block visually.

Each of the functions in visualization take a block and a file descriptor. The functions
provided write the block as a given visual format to the file.
"""

from __future__ import annotations

import collections
from typing import TYPE_CHECKING, Callable

from pyrtl.core import Block, LogicNet, working_block
from pyrtl.pyrtlexceptions import PyrtlError, PyrtlInternalError
from pyrtl.wire import Const, Input, Output, Register, WireVector

if TYPE_CHECKING:
    from pyrtl.simulation import SimulationTrace


def net_graph(block: Block = None, split_state: bool = False):
    """Return a graph representation of the given :class:`Block`.

    The graph has the following form::

        {
          node1: { nodeA: [edge1A_1, edge1A_2], nodeB: [edge1B]},
          node2: { nodeB: [edge2B],             nodeC: [edge2C_1, edge2C_2]},
          ...
        }

    aka: ``edges = graph[source][dest]``

    Each node can be either a :class:`LogicNet` or a :class:`WireVector` (e.g. an
    :class:`Input`, an :class:`Output`, a :class:`Const` or even an undriven
    :class:`WireVector` (which acts as a source or sink in the network). Each edge is a
    :class:`WireVector` or derived type (:class:`Input`, :class:`Output`,
    :class:`Register`, etc.). Note that :class:`Inputs<Input>`, :class:`Consts<Const>`,
    and :class:`Outputs<Output>` will be both "node" and "edge".
    :class:`WireVectors<WireVector>` that are not connected to any nets are not returned
    as part of the graph.

    .. note::

        Consider using :ref:`gate_graphs` instead.

    :param block: :class:`Block` to use (defaults to current :ref:`working_block`).
    :param split_state: If ``True``, split connections to/from a register update net;
        this means that registers will be appear as source nodes of the network, and
        ``r`` nets (i.e. the logic for setting :attr:`Register.next`) will be treated as
        sink nodes of the network.
    """
    # FIXME: make it not try to add unused wires (issue #204)
    block = working_block(block)

    # self.sanity_check()
    graph = {}

    # add all of the nodes
    for net in block.logic:
        graph[net] = {}

    wire_src_dict, wire_dst_dict = block.net_connections()
    dest_set = set(wire_src_dict.keys())
    arg_set = set(wire_dst_dict.keys())
    dangle_set = dest_set.symmetric_difference(arg_set)
    for w in dangle_set:
        graph[w] = {}
    if split_state:
        for w in block.wirevector_subset(Register):
            graph[w] = {}

    # add all of the edges
    for w in dest_set | arg_set:
        try:
            _from = wire_src_dict[w]
        except Exception:
            _from = w  # e.g. an Input/Const
        if split_state and isinstance(w, Register):
            _from = w

        try:
            _to_list = wire_dst_dict[w]
        except Exception:
            graph[_from][w] = [w]  # e.g. an Output
        else:
            for _to in _to_list:
                graph[_from][_to] = list(filter(lambda arg: arg is w, _to.args))

    return graph


# -----------------------------------------------------------------
#    ___  __   ___
#     |  / _` |___
#     |  \__> |


def _trivialgraph_default_namer(thing, is_edge=True):
    """Returns a "good" string for thing in printed graphs."""
    if is_edge:
        if thing.name is None or thing.name.startswith("tmp"):
            return ""
        return "/".join([thing.name, str(len(thing))])
    if isinstance(thing, Const):
        return str(thing.val)
    if isinstance(thing, WireVector):
        return thing.name or "??"
    try:
        return thing.op + str(thing.op_param or "")
    except AttributeError as exc:
        msg = f'no naming rule for "{thing}"'
        raise PyrtlError(msg) from exc


def output_to_trivialgraph(
    file,
    namer: Callable[[WireVector | LogicNet, bool], str] = _trivialgraph_default_namer,
    block: Block = None,
    split_state: bool = False,
):
    """Walk the block and output it in `trivial graph format
    <https://en.wikipedia.org/wiki/Trivial_Graph_Format>`_ to the open file.

    :param file: Open file to write to.
    :param namer: A function that takes in an object (a :class:`WireVector` or
        :class:`LogicNet`) as the first argument and a boolean ``is_edge`` as the second
        that is set ``True`` if the object is a :class:`WireVector`, and returns a
        string representing that object.
    :param block: :class:`Block` to use (defaults to current :ref:`working_block`).
    :param split_state: If ``True``, split connections to/from a register update net;
        this means that registers will be appear as source nodes of the network, and
        ``r`` :class:`LogicNets<LogicNet>` (i.e. the logic for setting
        :attr:`Register.next`) will be treated as sink nodes of the network.
    """
    graph = net_graph(block, split_state)
    node_index_map = {}  # map node -> index

    # print the list of nodes
    for index, node in enumerate(graph):
        print(index, namer(node, is_edge=False), file=file)
        node_index_map[node] = index

    print("#", file=file)

    # print the list of edges
    for _from in graph:
        for _to in graph[_from]:
            from_index = node_index_map[_from]
            to_index = node_index_map[_to]
            for edge in graph[_from][_to]:
                print(from_index, to_index, namer(edge), file=file)


# -----------------------------------------------------------------
#     __   __        __              __
#    / _` |__)  /\  |__) |__| \  / |  /
#    \__> |  \ /~~\ |    |  |  \/  | /__


def _default_edge_namer(
    edge: WireVector,
    is_to_splitmerge: bool = False,
    extra_edge_info: dict[WireVector, str] | None = None,
):
    """
    A function for naming an edge for use in the ``graphviz`` graph.

    :param edge: the edge (i.e. :class:`WireVector` or deriving class)
    :param is_to_splitmerge: if the node to which the edge points
        is a ``select`` or ``concat`` operation
    :param extra_edge_info: a map from edge to any additional data you want
        to print associated with it (e.g. timing data)
    :return: a function that can be called by graph namer function you pass
        in to ``block_to_graphviz_string``
    """

    name = "" if edge.name is None else "/".join([edge.name, str(len(edge))])
    if extra_edge_info and edge in extra_edge_info:
        # Always label an edge if present in the extra_edge_info map
        name = name + " (" + str(extra_edge_info[edge]) + ")"
    elif (
        edge.name is None
        or edge.name.startswith("tmp")
        or isinstance(edge, (Input, Output, Const, Register))
    ):
        name = ""

    penwidth = 2 if len(edge) == 1 else 6
    arrowhead = "none" if is_to_splitmerge else "normal"
    return f'[label="{name}", penwidth="{penwidth}", arrowhead="{arrowhead}"]'


def _default_node_namer(
    node: WireVector,
    split_state: bool = False,
    extra_node_info: dict[WireVector, str] | None = None,
):
    """
    A function for naming a node for use in the ``graphviz`` graph.

    :param node: the node (i.e. :class:`WireVector` or deriving class, or a logic net)
    :param split_state: if ``True``, split connections to/from a register update net;
        this means that registers will be appear as source nodes of the network, and 'r'
        nets (i.e. the logic for setting a register's next value) will be treated as
        sink nodes of the network.
    :param extra_node_info: a map from node to any additional data you want to print
        associated with it (e.g. delay data)

    :return: a function that can be called by graph namer function you pass in to
             :func:`block_to_graphviz_string`
    """

    def label(v):
        if extra_node_info and node in extra_node_info:
            v = v + " (" + str(extra_node_info[node]) + ")"
        return v

    if isinstance(node, Const):
        name = node.name + ": " if not node.name.startswith("const_") else ""
        return (
            f'[label="{label(name + str(node.val))}", shape=circle, '
            "fillcolor=lightgrey]"
        )
    if isinstance(node, Input):
        return f'[label="{label(node.name)}", shape=invhouse, fillcolor=coral]'
    if isinstance(node, Output):
        return f'[label="{label(node.name)}", shape=house, fillcolor=lawngreen]'
    if isinstance(node, Register):
        return f'[label="{label(node.name)}", shape=square, fillcolor=gold]'
    if isinstance(node, WireVector):
        return f'[label="{label(node.name)}", shape=circle, fillcolor=none]'
    try:
        if node.op == "&":
            return '[label="{}"]'.format(label("and"))
        if node.op == "|":
            return '[label="{}"]'.format(label("or"))
        if node.op == "^":
            return '[label="{}"]'.format(label("xor"))
        if node.op == "~":
            return '[label="{}", shape=invtriangle]'.format(label("not"))
        if node.op == "x":
            return '[label="{}", shape=invtrapezium]'.format(label("mux"))
        if node.op == "s":
            # node.op_param is a tuple of the selected bits to pull from the argument
            # wire, so it could look something like (0,0,0,0,0,0,0), meaning dest wire
            # is going to be a concatenation of the zero-th bit of the argument wire, 7
            # times.
            selLower = node.op_param[0]
            selUpper = node.op_param[-1]
            if len(node.op_param) == 1:
                bits = f"[{selLower}]"
            elif node.op_param == tuple(range(selLower, selUpper + 1)):  # consecutive
                bits = f"[{selUpper}:{selLower}]"
            elif all(
                ix == node.op_param[0] for ix in node.op_param[1:]
            ):  # all the same
                bits = f"[{node.op_param[0]}]*{len(node.op_param)}"
            else:
                bits = "bits" + str(tuple(reversed(node.op_param)))
            return f'[label="{label(bits)}", fillcolor=azure1, height=.25, width=.25]'
        if node.op in "c":
            return '[label="{}", height=.1, width=.1]'.format(label("concat"))
        if node.op == "r":
            name = node.dests[0].name or ""
            name = (f"{name}.next") if split_state else name
            return f'[label="{label(name)}", shape=square, fillcolor=gold]'
        if node.op == "w":
            return '[label="{}", height=.1, width=.1]'.format(label(""))
        if node.op in "m@":
            name = node.op_param[1].name
            if name.startswith("tmp"):
                name = ""
            else:
                name = "(" + name + ")"
            return f'[label="{label(node.op + name)}"]'
        return '[label="{}"]'.format(label(node.op + str(node.op_param or "")))
    except AttributeError as exc:
        msg = f'no naming rule for "{node}"'
        raise PyrtlError(msg) from exc


def _graphviz_default_namer(
    thing: WireVector | LogicNet,
    is_edge: bool,
    is_to_splitmerge: bool,
    split_state: bool,
    node_namer=_default_node_namer,
    edge_namer=_default_edge_namer,
):
    """Returns a "good" Graphviz label for thing.

    :param thing: The edge (:class:`WireVector`) or node (:class:`LogicNet` or
        :class:`Input`/:class:`Output`/:class:`Const`) to name
    :param is_edge: ``True`` if thing is an edge
    :param is_to_splitmerge: if the node to which the edge points is a ``select`` or
        concat operation
    :param split_state: If ``True``, visually split the connections to/from a register
        update net.
    :param node_namer: A function mapping a node to a label; one of its arguments is a
        dict mapping nodes to nodes to additional user-supplied information.
    :param edge_namer: A function mapping an edge to a label; one of its arguments is a
        dict mapping nodes to nodes to additional user-supplied information.

    :return: A function that knows how to label each element in the graph, which can be
             passed to :func:`output_to_graphviz` or :func:`block_to_graphviz_string`
    """
    if is_edge:
        return edge_namer(thing, is_to_splitmerge=is_to_splitmerge)
    return node_namer(thing, split_state=split_state)


def graphviz_detailed_namer(
    extra_node_info: dict | None = None, extra_edge_info: dict | None = None
):
    """Returns a detailed Graphviz namer that prints extra information about nodes/edges
    in the given maps.

    If both :class:`dict` arguments are ``None``, the returned namer behaves identically
    to the default Graphviz namer.

    :param extra_node_info: A :class:`dict` from node to additional data about that
        node. The additional data will be converted to :class:`str` and printed next to
        the node's label.
    :param extra_edge_info: A :class:`dict` from edge to additional data about that
        edge. The additional data will be converted to :class:`str` and printed next to
        the edge's label.

    :return: A function to label each element in the graph, which can be used as
             :func:`output_to_graphviz` or :func:`block_to_graphviz_string`'s ``namer``.
    """

    def node_namer(node, split_state):
        return _default_node_namer(node, split_state, extra_node_info)

    def edge_namer(edge, is_to_splitmerge):
        return _default_edge_namer(edge, is_to_splitmerge, extra_edge_info)

    def namer(thing, is_edge, is_to_splitmerge, split_state):
        return _graphviz_default_namer(
            thing,
            is_edge,
            is_to_splitmerge,
            split_state,
            node_namer=node_namer,
            edge_namer=edge_namer,
        )

    return namer


def output_to_graphviz(
    file,
    block: Block = None,
    namer=_graphviz_default_namer,
    split_state: bool = True,
    maintain_arg_order: bool = False,
):
    """Walk the :class:`Block` and output it in `Graphviz <https://graphviz.org/>`_
    format to the open file.

    ``output_to_graphviz`` writes a file containing a directed graph in the format
    expected by `Graphviz <https://graphviz.org/>`_, specifically in the :command:`dot`
    format. Once Graphviz is installed, the resulting graph file can be rendered to a
    ``.pdf`` file with::

        dot -Tpdf output.dot > output.pdf

    :param file: Open file to write to.
    :param block: :class:`Block` to use (defaults to current :ref:`working_block`)
    :param namer: Function used to label each edge and node; see
        :func:`block_to_graphviz_string` for more information.
    :param split_state: If ``True``, visually split the connections to/from a
        :class:`Register` update net.
    :param maintain_arg_order: If ``True``, add ordering constraints so incoming edges
        are ordered left-to-right for nets where argument order matters (e.g. ``<``).
        Keeping this as ``False`` results in a cleaner, though less visually precise,
        graphical output.
    """
    print(
        block_to_graphviz_string(block, namer, split_state, maintain_arg_order),
        file=file,
    )


def block_to_graphviz_string(
    block: Block = None,
    namer=_graphviz_default_namer,
    split_state: bool = True,
    maintain_arg_order: bool = False,
):
    """Return a Graphviz string for the ``block``.

    The normal namer function will label user-named wires with their names and label the
    nodes (:class:`LogicNets<LogicNet>` or :class:`Input`/:class:`Output`/:class:`Const`
    terminals) with their operator symbol or name/value, respectively. If custom
    information about each node in the graph is desired, you can pass in a custom namer
    function which must have the same signature as the default namer,
    :func:`_graphviz_default_namer`.

    However, we recommend you instead pass in a call to :func:`graphviz_detailed_namer`,
    supplying it with your own :class:`dicts<dict>` mapping wires and nodes to labels.
    For any wire/node found in these maps, that additional information will be printed
    in parentheses alongside the node in the ``graphviz`` graph.

    For example, if you wanted to print the delay of each wire and the fanout of each
    gate, you could pass in two maps to the :func:`graphviz_detailed_namer` call, which
    returns a namer function that can subsequently be passed to
    :func:`output_to_graphviz` or :func:`block_to_graphviz_string`::

        node_fanout = {n: f"Fanout: {my_fanout_func(n)}"
                       for n in working_block().logic}
        wire_delay = {w: f"Delay: {my_delay_func(w):.2f}"
                      for w in working_block().wirevector_set}

        with open("out.gv", "w") as f:
            output_to_graphviz(
                f, namer=graphviz_detailed_namer(node_fanout, wire_delay))

    :param namer: A function mapping graph objects (wires/logic nets) to labels. If you
        want a more detailed namer, pass in a call to :func:`graphviz_detailed_namer`.
    :param block: :class:`Block` to use (defaults to current :ref:`working_block`)
    :param bool split_state: If ``True``, split connections to/from a :class:`Register`
        update net; this means that registers will be appear as source nodes of the
        network, and ``r`` nets (i.e. the logic for setting :attr:`Register.next`) will
        be treated as sink nodes of the network.
    :param bool maintain_arg_order: If ``True``, will add ordering constraints so
        incoming edges are ordered left-to-right for nets where argument order matters
        (e.g. ``<``). Keeping this as ``False`` results in a cleaner, though less
        visually precise, graphical output.
    """
    graph = net_graph(block, split_state)
    node_index_map = {}  # map node -> index

    rstring = """\
digraph g {
    graph [splines="spline", outputorder="edgesfirst"];
    node [shape=circle, style=filled, fillcolor=lightblue1,
        fontcolor=black, fontname=helvetica, penwidth=0,
        fixedsize=shape];
    edge [labelfloat=false, penwidth=2, color=deepskyblue, arrowsize=.5];
"""
    from pyrtl.importexport import _natural_sort_key

    def _node_sort_key(node):
        # If a LogicNet and a wire share the same name, we want the LogicNet to sort
        # first, so we arbitrarily 'A' and 'B' suffixes to break ties.
        if isinstance(node, LogicNet):
            if node.op == "@":
                key = str(node.args[2]) + "A"
            else:
                key = node.dests[0].name + "A"
        else:
            key = node.name + "B"
        return _natural_sort_key(key)

    # print the list of nodes
    for index, node in enumerate(sorted(graph.keys(), key=_node_sort_key)):
        label = namer(node, False, False, split_state)
        rstring += f"    n{index} {label};\n"
        node_index_map[node] = index

    # print the list of edges
    srcs = collections.defaultdict(list)
    for _from in sorted(graph.keys(), key=_node_sort_key):
        for _to in sorted(graph[_from].keys(), key=_node_sort_key):
            from_index = node_index_map[_from]
            to_index = node_index_map[_to]
            for edge in graph[_from][_to]:
                is_to_splitmerge = hasattr(_to, "op") and _to.op in "cs"
                label = namer(edge, True, is_to_splitmerge, False)
                rstring += f"    n{from_index} -> n{to_index} {label};\n"
                srcs[_to].append((_from, edge))

    # Maintain left-to-right order of incoming wires for nets where order matters. This
    # won't be visually perfect sometimes (especially for a wire used twice in a net's
    # argument list), but for the majority of cases this will improve the visualization.
    def index_of(w, args):
        # Special helper so we compare id rather than using builtin operators
        for i, arg in enumerate(args):
            if w is arg:
                return i
        msg = "Expected to find wire in set of args"
        raise PyrtlInternalError(msg)

    if maintain_arg_order:
        block = working_block(block)
        for net in sorted(block.logic_subset(op="c-<>x@"), key=_node_sort_key):
            args = [(node_index_map[n], wire) for (n, wire) in srcs[net]]
            args.sort(key=lambda t: index_of(t[1], net.args))
            s = " -> ".join([f"n{n}" for n, _ in args])
            rstring += "    {\n"
            rstring += "        rank=same;\n"
            rstring += "        edge[style=invis];\n"
            rstring += "        " + s + ";\n"
            rstring += "        rankdir=LR;\n"
            rstring += "    }\n"

    rstring += "}\n"
    return rstring


# -----------------------------------------------------------------
#     __        __
#    /__` \  / / _`
#    .__/  \/  \__>


def output_to_svg(file, block: Block = None, split_state: bool = True):
    """Output the block as an SVG to the open file.

    :param file: Open file to write to.
    :param block: :class:`Block` to use (defaults to current :ref:`working_block`).
    :param split_state: If ``True``, visually split the connections to/from a register
        update net.
    """
    print(block_to_svg(block, split_state), file=file)


def block_to_svg(
    block: Block = None, split_state: bool = True, maintain_arg_order: bool = False
):
    """Return an SVG for the block.

    :param block: :class:`Block` to use (defaults to current :ref:`working_block`).
    :param split_state: If ``True``, visually split the connections to/from a register
        update net.
    :param maintain_arg_order: If ``True``, will add ordering constraints so incoming
        edges are ordered left-to-right for nets where argument order matters (e.g.
        ``<``). Keeping this as ``False`` results in a cleaner, though less visually
        precise, graphical output.

    :return: The SVG representation of the :class:`Block`.
    """
    try:
        from graphviz import Source

        src = Source(
            block_to_graphviz_string(
                block, split_state=split_state, maintain_arg_order=maintain_arg_order
            )
        )
        try:
            svg = src._repr_image_svg_xml()
        except AttributeError:
            # py-graphviz 0.18.3 or earlier
            return src._repr_svg_()
        else:
            # py-graphviz 0.19 or later
            return svg
    except ImportError as exc:
        msg = 'need graphviz installed (try "pip install graphviz")'
        raise PyrtlError(msg) from exc


# -----------------------------------------------------------------
#         ___
#    |__|  |  |\/| |
#    |  |  |  |  | |___


def trace_to_html(
    simtrace: SimulationTrace,
    trace_list: list[str] | None = None,
    sortkey=None,
    repr_func: Callable[[int], str] = hex,
    repr_per_name: dict[str, Callable[[int], str]] | None = None,
) -> str:
    """Return a HTML block showing the trace.

    :param simtrace: A trace to render in HTML.
    :param trace_list: (optional) A list of wires to display.
    :param sortkey: (optional) The key with which to sort the ``trace_list``.
    :param repr_func: Function to use for representing each value in the trace. Examples
        include :func:`hex`, :func:`oct`, :func:`bin`, and :class:`str` (for decimal),
        :func:`val_to_signed_integer` (for signed decimal) or the function returned by
        :func:`enum_name` (for :class:`~enum.IntEnum`). Defaults to :func:`hex`.
    :param repr_per_name: Map from signal name to a function that takes in the signal's
        value and returns a user-defined representation. If a signal name is not found
        in the map, the argument ``repr_func`` will be used instead.

    :return: An HTML block showing the trace.
    """

    from pyrtl.simulation import SimulationTrace, _trace_sort_key

    if repr_per_name is None:
        repr_per_name = {}
    if not isinstance(simtrace, SimulationTrace):
        msg = "first arguement must be of type SimulationTrace"
        raise PyrtlError(msg)

    trace = simtrace.trace
    if sortkey is None:
        sortkey = _trace_sort_key

    if trace_list is None:
        trace_list = sorted(trace, key=sortkey)

    wave_template = """\
<script type="WaveDrom">
{
  signal : [
%s
  ],
  config: { hscale: %d }
}
</script>
"""

    vallens = []  # For determining longest value length

    def extract(w):
        wavelist = []
        datalist = []
        last = None

        for value in trace[w]:
            if last == value:
                wavelist.append(".")
            else:
                f = repr_per_name.get(w)
                if f is not None:
                    wavelist.append("=")
                    datalist.append(str(f(value)))
                elif len(simtrace._wires[w]) == 1:
                    # int() to convert True/False to 0/1
                    wavelist.append(str(int(value)))
                else:
                    wavelist.append("=")
                    datalist.append(str(repr_func(value)))

                last = value

        wavestring = "".join(wavelist)
        datastring = ", ".join([f'"{data}"' for data in datalist])
        if repr_per_name.get(w) is None and len(simtrace._wires[w]) == 1:
            vallens.append(1)  # all are the same length
            return bool_signal_template % (w, wavestring)
        vallens.extend([len(data) for data in datalist])
        return int_signal_template % (w, wavestring, datastring)

    bool_signal_template = '    { name: "%s",  wave: "%s" },'
    int_signal_template = '    { name: "%s",  wave: "%s", data: [%s] },'
    signals = [extract(w) for w in trace_list]
    all_signals = "\n".join(signals)
    maxvallen = max(vallens)
    scale = (maxvallen // 5) + 1
    return wave_template % (all_signals, scale)
    # print(wave)
