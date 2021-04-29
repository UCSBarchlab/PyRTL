""" The core abstraction for hardware in PyRTL.

Included in this file you will find:

* `LogicNet` -- the core class holding a "net" in the netlist
* `Block` -- a collection of nets with associated access and error checking
* `working_block` -- the "current" Block to which, by default, all created nets are added
* `modes` -- access methods for "modes" such as debug

"""
from __future__ import print_function, unicode_literals
import collections
import re
import keyword

from .pyrtlexceptions import PyrtlError, PyrtlInternalError


# -----------------------------------------------------------------
#    __        __   __
#   |__) |    /  \ /  ` |__/
#   |__) |___ \__/ \__, |  \
#

class LogicNet(collections.namedtuple('LogicNet', ['op', 'op_param', 'args', 'dests'])):
    """ The basic immutable datatype for storing a "net" in a netlist.

    This is used for the Internal representation that Python stores
    Knowledge of what this is, and how it is used is only required for
    advanced users of PyRTL.

    A 'net' is a structure in Python that is representative of hardware
    logic operations. These include binary operations, such as 'and'
    'or' and 'not', arithmetic operations such as '+' and '-', as well
    as other operations such as Memory ops, and concat, split, wire,
    and reg logic.

    The details of what is allowed in each of these fields is defined
    in the comments of Block, and is checked by `block.sanity_check`


    `Logical Operations`::

        ('&', None, (a1, a2), (out)) => AND two wires together, put result into out
        ('|', None, (a1, a2), (out)) => OR two wires together, put result into out
        ('^', None, (a1, a2), (out)) => XOR two wires together, put result into out
        ('n', None, (a1, a2), (out)) => NAND two wires together, put result into out
        ('~', None, (a1), (out)) => invert one wire, put result into out
        ('+', None, (a1, a2), (out)) => add a1 and a2, put result into out
                                        len(out) = max(len(a1), len(a2)) + 1
                                        works with both unsigned and two's complement
        ('-', None, (a1, a2), (out)) => subtract a2 from a1, put result into out
                                        len(out) = max(len(a1), len(a2)) + 1
                                        works with both unsigned and two's complement
        ('*', None, (a1, a2), (out)) => multiply a1 & a2, put result into out
                                        len(out) = len(a1) + len(a2)
                                        assumes unsigned, but "signed_mult" provides wrapper
        ('=', None, (a1, a2), (out)) => check a1 & a2 equal, put result into out (0 | 1)
        ('<', None, (a1, a2), (out)) => check a2 greater than a1, put result into out (0 | 1)
        ('>', None, (a1, a2), (out)) => check a1 greater than a2, put result into out (0 | 1)
        ('w', None, (w1), (w2) => directional wire w/ no logical operation: connects w1 to w2
        ('x', None, (x, a1, a2), (out)) => mux: connect a1 (x=0), a2 (x=1) to out;
                                           x must be one bit; len(a1) = len(a2)
        ('c', None, (*args), (out)) => concatenates *args (wires) into single WireVector;
                                       puts first arg at MSB, last arg at LSB
        ('s', (sel), (wire), (out)) => selects bits from wire based on sel (std slicing syntax),
                                       puts into out
        ('r', None, (next), (r1)) => on positive clock edge: copies next to r1
        ('m', (memid, mem), (addr), (data)) => read address addr of mem (w/ id memid),
                                               put it into data
        ('@', (memid, mem), (addr, data, wr_en), ()) => write data to mem (w/ id memid) at
                                                        address addr; req. write enable (wr_en)

    """

    def __str__(self):
        rhs = ', '.join(str(x) for x in self.args)
        lhs = ', '.join(str(x) for x in self.dests)
        options = '' if self.op_param is None else '(' + str(self.op_param) + ')'

        from .helperfuncs import _currently_in_jupyter_notebook

        if _currently_in_jupyter_notebook():
            # Output the working block as a Latex table
            # Escape all Underscores
            rhs = rhs.replace('_', "\\_")
            lhs = lhs.replace('_', "\\_")
            options = options.replace('_', "\\_")
            if self.op in '&|':
                return "{} & \\leftarrow \\{} \\, - & {} {} \\\\".format(
                       lhs, self.op, rhs, options)
            elif self.op in "wn+-*<>xcsr":
                return "{} & \\leftarrow {} \\, - & {} {} \\\\".format(
                       lhs, self.op, rhs, options)
            elif self.op in "=":
                return "{} & \\leftarrow \\, {} \\, - & {} {} \\\\".format(
                       lhs, self.op, rhs, options)
            elif self.op in "^":
                return "{} & \\leftarrow \\oplus \\, - & {} {} \\\\".format(
                       lhs, rhs, options)
            elif self.op in "~":
                return "{} & \\leftarrow \\sim \\, - & {} {} \\\\".format(
                       lhs, rhs, options)

            elif self.op in 'm@':
                memid, memblock = self.op_param
                extrainfo = 'memid=' + str(memid)
                extrainfo = extrainfo.replace("_", "\\_")
                name = memblock.name
                name = name.replace("_", "\\_")
                if self.op == 'm':
                    return "{} & \\leftarrow m \\, - &  {}[{}]({}) \\\\".format(
                           lhs, name, rhs, extrainfo)
                else:
                    addr, data, we = (str(x) for x in self.args)
                    addr = addr.replace("_", "\\_")
                    data = data.replace("_", "\\_")
                    we = we.replace("_", "\\_")
                    return "{}[{}] & \\leftarrow @ \\, - & {} we={} ({}) \\\\".format(
                        name, addr, data, we, extrainfo)
            else:
                raise PyrtlInternalError('error, unknown op "%s"' % str(self.op))

        else:  # not in ipython
            if self.op in 'w~&|^n+-*<>=xcsr':
                return "{} <-- {} -- {} {}".format(lhs, self.op, rhs, options)
            elif self.op in 'm@':
                memid, memblock = self.op_param
                extrainfo = 'memid=' + str(memid)
                if self.op == 'm':
                    return "{} <-- m --  {}[{}]({})".format(lhs, memblock.name, rhs, extrainfo)
                else:
                    addr, data, we = (str(x) for x in self.args)
                    return "{}[{}] <-- @ -- {} we={} ({})".format(
                        memblock.name, addr, data, we, extrainfo)
            else:
                raise PyrtlInternalError('error, unknown op "%s"' % str(self.op))

    def __hash__(self):
        # it seems that namedtuple is not always hashable
        return hash(tuple(self))

    def __eq__(self, other):
        # We can't be going and calling __eq__ recursively on the logic nets for all of
        # the args and dests because that will actually *create* new logic nets which is
        # very much not what people would expect to happen.  Instead we define equality
        # as the immutable fields being equal and the list of args and dests being
        # references to the same objects.
        return (self.op == other.op
                and self.op_param == other.op_param
                and len(self.args) == len(other.args)
                and len(self.dests) == len(other.dests)
                and all(self.args[i] is other.args[i] for i in range(len(self.args)))
                and all(self.dests[i] is other.dests[i] for i in range(len(self.dests))))

    def __ne__(self, other):
        return not self.__eq__(other)

    def _compare_error(self, other):
        """ Throw error when LogicNets are compared.

        Comparisons get you in a bad place between while you can compare op and op_param
        safely, the args and dests are references to mutable objects with comparison
        operators overloaded.
        """
        raise PyrtlError('Greater than and less than comparisons between'
                         ' LogicNets are not supported')

    __lt__ = _compare_error
    __gt__ = _compare_error
    __le__ = _compare_error
    __ge__ = _compare_error


class Block(object):
    """ Block encapsulates a netlist.

    A Block in PyRTL is the class that stores a netlist and provides basic access
    and error checking members.  Each block has well defined inputs and outputs,
    and contains both the basic logic elements and references to the wires and
    memories that connect them together.

    The logic structure is primarily contained in self.logic which holds a set of
    "LogicNet"s. Each LogicNet describes a primitive operation (such as an adder
    or memory).  The primitive is described by a 4-tuple of:

    1) the op (a single character describing the operation such as '+' or 'r'),
    2) a set of hard parameters to that primitives (such as the constants to
       select from the "selection" op).
    3) the tuple "args" which list the wirevectors hooked up as inputs to
       this particular net.
    4) the tuple "dests" which list the wirevectors hooked up as output for
       this particular net.

    Below is a list of the basic operations.  These properties (more formally
    specified) should all be checked by the class method 'sanity_check'.

    * Most logical and arithmetic ops are pretty self explanatory. Each takes
      exactly two arguments, and they should perform the arithmetic or logical
      operation specified. OPS: ('&','|','^','n','~','+','-','*').  All inputs must
      be the same bitwidth.  Logical operations produce as many bits as are in
      the input, while '+' and '-' produce n+1 bits, and '*' produces 2n bits.

    * In addition there are some operations for performing comparisons
      that should perform the operation specified.  The '=' op is checking
      to see if the bits of the vectors are equal, while '<' and '>' do
      unsigned arithmetic comparison.  All comparisons generate a single bit
      of output (1 for true, 0 for false).

    * The 'w' operator is simply a directional wire and has no logic function.

    * The 'x' operator is a mux which takes a select bit and two signals.
      If the value of the select bit is 0 it selects the second argument; if
      it is 1 it selects the third argument.  Select must be a single bit, while
      the other two arguments must be the same length.

    * The 'c' operator is the concatenation operator and combines any number of
      wirevectors (a,b,...,z) into a single new wirevector with "a" in the MSB
      and "z" (or whatever is last) in the LSB position.

    * The 's' operator is the selection operator and chooses, based on the
      op_param specified, a subset of the logic bits from a WireVector to
      select.  Repeats are accepted.

    * The 'r' operator is a register and on posedge, simply copies the value
      from the input to the output of the register.

    * The 'm' operator is a memory block read port, which supports async reads (acting
      like combinational logic). Multiple read (and write) ports are possible to
      the same memory but each 'm' defines only one of those. The op_param
      is a tuple containing two references: the mem id, and a reference to the
      MemBlock containing this port. The MemBlock should only be used for debug and
      sanity checks. Each read port has one addr (an arg) and one data (a dest).

    * The '@' (update) operator is a memory block write port, which supports synchronous writes
      (writes are "latched" at posedge).  Multiple write (and read) ports are possible
      to the same memory but each '@' defines only one of those. The op_param
      is a tuple containing two references: the mem id, and a reference to the MemoryBlock.
      Writes have three args (addr, data, and write enable).  The dests should be an
      empty tuple.  You will not see a written value change until the following cycle.
      If multiple writes happen to the same address in the same cycle the behavior is currently
      undefined.

    The connecting elements (args and dests) should be WireVectors or derived
    from WireVector, and should be registered with the block using
    the method 'add_wirevector'.  Nets should be registered using 'add_net'.

    In addition, there is a member 'legal_ops' which defines the set of operations
    that can be legally added to the block.  By default it is set to all of the above
    defined operations, but it can be useful in certain cases to only allow a
    subset of operations (such as when transforms are being done that are "lowering"
    the blocks to more primitive ops).
    """

    def __init__(self):
        """Creates an empty hardware block."""
        self.logic = set()  # set of nets, each is a LogicNet named tuple
        self.wirevector_set = set()  # set of all wirevectors
        self.wirevector_by_name = {}  # map from name->wirevector, used for performance
        # pre-synthesis wirevectors to post-synthesis vectors
        self.legal_ops = set('w~&|^n+-*<>=xcsrm@')  # set of legal OPS
        self.rtl_assert_dict = {}   # map from wirevectors -> exceptions, used by rtl_assert
        self.memblock_by_name = {}  # map from name->memblock, for easy access to memblock objs

    def __str__(self):
        """String form has one LogicNet per line."""
        from .helperfuncs import _currently_in_jupyter_notebook, _print_netlist_latex

        if _currently_in_jupyter_notebook():
            _print_netlist_latex(list(self))
            return ' '
        else:
            return '\n'.join(str(net) for net in self)

    def add_wirevector(self, wirevector):
        """ Add a wirevector object to the block."""
        self.sanity_check_wirevector(wirevector)
        self.wirevector_set.add(wirevector)
        self.wirevector_by_name[wirevector.name] = wirevector

    def remove_wirevector(self, wirevector):
        """ Remove a wirevector object to the block."""
        self.wirevector_set.remove(wirevector)
        del self.wirevector_by_name[wirevector.name]

    def add_net(self, net):
        """ Add a net to the logic of the block.

        The passed net, which must be of type LogicNet, is checked and then
        added to the block.  No wires are added by this member, they must be
        added seperately with add_wirevector."""

        self.sanity_check_net(net)
        self.logic.add(net)

    def _add_memblock(self, mem):
        """ Registers a memory to the block.

        Note that this is done automatically when a memory block is
        created and isn't intended for use by PyRTL end users.
        This is so non-local memories can be accessed later on
        (e.g. for instantiating during a simulation).
        """
        self.sanity_check_memblock(mem)
        self.memblock_by_name[mem.name] = mem

    def get_memblock_by_name(self, name, strict=False):
        """ Get a reference to a memory stored in this block by name.

        By fallthrough, if a matching memblock cannot be found the value None is
        returned.  However, if the argument strict is set to True, then this will
        instead throw a PyrtlError when no match is found.

        This useful for when a block defines its own internal memory block, and
        during simulation you want to instantiate that memory with certain values
        for testing. Since the Simulation constructor requires a reference to the
        memory object itself, but the block you're testing defines the memory internally,
        this allows you to get the object reference.

        Note that this requires you know the name of the memory block, meaning that
        you most likely need to have named it yourself.

        For example:

            def special_memory(read_addr, write_addr, data, wen):
                mem = pyrtl.MemBlock(bitwidth=32, addrwidth=5, name='special_mem')
                mem[write_addr] <<= pyrtl.MemBlock.EnabledWrite(data, wen & (write_addr > 0))
                return mem[read_addr]

            read_addr = pyrtl.Input(5, 'read_addr')
            write_addr = pyrtl.Input(5, 'write_addr')
            data = pyrtl.Input(32, 'data')
            wen = pyrtl.Input(1, 'wen')
            res = pyrtl.Output(32, 'res')

            res <<= special_memory(read_addr, write_addr, data, wen)

            # Can only access it after the `special_memory` block has been instantiated/called
            special_mem = pyrtl.working_block().get_memblock_by_name('special_mem')

            sim = pyrtl.Simulation(memory_value_map={
                special_mem: {
                    0: 5,
                    1: 6,
                    2: 7,
                }
            })

            inputs = {
                'read_addr':  '012012',
                'write_addr': '012012',
                'data':       '890333',
                'wen':        '111000',
            }
            expected = {
                'res': '567590',
            }
            sim.step_multiple(inputs, expected)
        """
        if name in self.memblock_by_name:
            return self.memblock_by_name[name]
        elif strict:
            raise PyrtlError('error, block does not have a memblock named %s' % name)
        else:
            return None

    def wirevector_subset(self, cls=None, exclude=tuple()):
        """Return set of wirevectors, filtered by the type or tuple of types provided as cls.

        If no cls is specified, the full set of wirevectors associated with the Block are
        returned.  If cls is a single type, or a tuple of types, only those wirevectors of
        the matching types will be returned.  This is helpful for getting all inputs, outputs,
        or registers of a block for example.
        """
        if cls is None:
            initial_set = self.wirevector_set
        else:
            initial_set = (x for x in self.wirevector_set if isinstance(x, cls))
        if exclude == tuple():
            return set(initial_set)
        else:
            return set(x for x in initial_set if not isinstance(x, exclude))

    def logic_subset(self, op=None):
        """Return set of logicnets, filtered by the type(s) of logic op provided as op.

        If no op is specified, the full set of logicnets associated with the Block are
        returned.  This is helpful for getting all memories of a block for example.
        """
        if op is None:
            return self.logic
        else:
            return set(x for x in self.logic if x.op in op)

    def get_wirevector_by_name(self, name, strict=False):
        """Return the wirevector matching name.

        By fallthrough, if a matching wirevector cannot be found the value None is
        returned.  However, if the argument strict is set to True, then this will
        instead throw a PyrtlError when no match is found.
        """
        if name in self.wirevector_by_name:
            return self.wirevector_by_name[name]
        elif strict:
            raise PyrtlError('error, block does not have a wirevector named %s' % name)
        else:
            return None

    def net_connections(self, include_virtual_nodes=False):
        """ Returns a representation of the current block useful for creating a graph.

        :param include_virtual_nodes: if enabled, the wire itself will be used to
          signal an external source or sink (such as the source for an Input net).
          If disabled, these nodes will be excluded from the adjacency dictionaries
        :return wire_src_dict, wire_sink_dict
          Returns two dictionaries: one that maps WireVectors to the logic
          net that creates their signal and one that maps WireVectors to
          a list of logic nets that use the signal

        These dictionaries make the creation of a graph much easier, as
        well as facilitate other places in which one would need wire source
        and wire sink information.

        Look at inputoutput.net_graph for one such graph that uses the information
        from this function.
        """
        src_list = {}
        dst_list = {}

        def add_wire_src(edge, node):
            if edge in src_list:
                raise PyrtlError('Wire "{}" has multiple drivers: [{}] and [{}] (check for '
                                 'multiple assignments with "<<=" or accidental mixing of '
                                 '"|=" and "<<=")'
                                 .format(edge, str(src_list[edge]).strip(), str(node).strip()))
            src_list[edge] = node

        def add_wire_dst(edge, node):
            if edge in dst_list:
                # if node in dst_list[edge]:
                #     raise PyrtlError("The net already exists in the graph")
                dst_list[edge].append(node)
            else:
                dst_list[edge] = [node]

        if include_virtual_nodes:
            from .wire import Input, Output, Const
            for wire in self.wirevector_subset((Input, Const)):
                add_wire_src(wire, wire)

            for wire in self.wirevector_subset(Output):
                add_wire_dst(wire, wire)

        for net in self.logic:
            for arg in set(net.args):  # prevents unexpected duplicates when doing b <<= a & a
                add_wire_dst(arg, net)
            for dest in net.dests:
                add_wire_src(dest, net)
        return src_list, dst_list

    def _repr_svg_(self):
        """ IPython display support for Block. """
        from .visualization import block_to_svg
        return block_to_svg(self)

    def __iter__(self):
        """ BlockIterator iterates over the block passed on init in topographic order.
        The input is a Block, and when a LogicNet is returned it is always the case
        that all of its "parents" have already been returned earlier in the iteration.

        Note: this method will throw an error if there are loops in the
        logic that do not involve registers.
        Also, the order of the nets is not guaranteed to be the same
        over multiple iterations.
        """
        from .wire import Input, Const, Register
        src_dict, dest_dict = self.net_connections()
        to_clear = self.wirevector_subset((Input, Const, Register))
        cleared = set()
        remaining = self.logic.copy()
        try:
            while len(to_clear):
                wire_to_check = to_clear.pop()
                cleared.add(wire_to_check)
                if wire_to_check in dest_dict:
                    for gate in dest_dict[wire_to_check]:  # loop over logicnets not yet returned
                        if all(arg in cleared for arg in gate.args):  # if all args ready
                            yield gate
                            remaining.remove(gate)
                            if gate.op != 'r':
                                to_clear.update(gate.dests)
        except KeyError as e:
            import six
            six.raise_from(PyrtlError("Cannot Iterate through malformed block"), e)

        if len(remaining) != 0:
            from pyrtl.helperfuncs import find_and_print_loop
            find_and_print_loop(self)
            raise PyrtlError("Failure in Block Iterator due to non-register loops")

    def sanity_check(self):
        """ Check block and throw PyrtlError or PyrtlInternalError if there is an issue.

        Should not modify anything, only check data structures to make sure they have been
        built according to the assumptions stated in the Block comments.
        """

        # TODO: check that the wirevector_by_name is sane
        from .wire import Input, Const, Output
        from .helperfuncs import get_stack, get_stacks

        # check for valid LogicNets (and wires)
        for net in self.logic:
            self.sanity_check_net(net)

        for w in self.wirevector_subset():
            if w.bitwidth is None:
                raise PyrtlError(
                    'error, missing bitwidth for WireVector "%s" \n\n %s' % (w.name, get_stack(w)))

        # check for unique names
        wirevector_names_set = set(x.name for x in self.wirevector_set)
        if len(self.wirevector_set) != len(wirevector_names_set):
            wirevector_names_list = [x.name for x in self.wirevector_set]
            for w in wirevector_names_set:
                wirevector_names_list.remove(w)
            raise PyrtlError('Duplicate wire names found for the following '
                             'different signals: %s (make sure you are not using "tmp" '
                             'or "const_" as a signal name because those are reserved for '
                             'internal use)' % repr(wirevector_names_list))

        # check for dead input wires (not connected to anything)
        all_input_and_consts = self.wirevector_subset((Input, Const))

        # The following line also checks for duplicate wire drivers
        wire_src_dict, wire_dst_dict = self.net_connections()
        dest_set = set(wire_src_dict.keys())
        arg_set = set(wire_dst_dict.keys())
        full_set = dest_set | arg_set
        connected_minus_allwires = full_set.difference(self.wirevector_set)
        if len(connected_minus_allwires) > 0:
            bad_wire_names = '\n    '.join(str(x) for x in connected_minus_allwires)
            raise PyrtlError('Unknown wires found in net:\n %s \n\n %s' % (bad_wire_names,
                             get_stacks(*connected_minus_allwires)))
        allwires_minus_connected = self.wirevector_set.difference(full_set)
        allwires_minus_connected = allwires_minus_connected.difference(all_input_and_consts)
        #   ^ allow inputs and consts to be unconnected
        if len(allwires_minus_connected) > 0:
            bad_wire_names = '\n    '.join(str(x) for x in allwires_minus_connected)
            raise PyrtlError('Wires declared but not connected:\n %s \n\n %s' % (bad_wire_names,
                             get_stacks(*allwires_minus_connected)))

        # Check for wires that are inputs to a logicNet, but are not block inputs and are never
        # driven.
        ins = arg_set.difference(dest_set)
        undriven = ins.difference(all_input_and_consts)
        if len(undriven) > 0:
            raise PyrtlError('Wires used but never driven: %s \n\n %s' %
                             ([w.name for w in undriven], get_stacks(*undriven)))

        # Check for async memories not specified as such
        self.sanity_check_memory_sync(wire_src_dict)

        if debug_mode:
            # Check for wires that are destinations of a logicNet, but are not outputs and are never
            # used as args.
            outs = dest_set.difference(arg_set)
            unused = outs.difference(self.wirevector_subset(Output))
            if len(unused) > 0:
                names = [w.name for w in unused]
                print('Warning: Wires driven but never used { %s } ' % names)
                print(get_stacks(*unused))

    def sanity_check_memory_sync(self, wire_src_dict=None):
        """ Check that all memories are synchronous unless explicitly specified as async.

        While the semantics of 'm' memories reads is asynchronous, if you want your design
        to use a block ram (on an FPGA or otherwise) you want to make sure the index is
        available at the beginning of the clock edge.  This check will walk the logic structure
        and throw an error on any memory if finds that has an index that is not ready at the
        beginning of the cycle.
        """
        sync_mems = set(m for m in self.logic_subset('m') if not m.op_param[1].asynchronous)
        if not len(sync_mems):
            return  # nothing to check here

        if wire_src_dict is None:
            wire_src_dict, wdd = self.net_connections()

        from .wire import Input, Const
        sync_src = 'r'
        sync_prop = 'wcs'
        for net in sync_mems:
            wires_to_check = list(net.args)
            while len(wires_to_check):
                wire = wires_to_check.pop()
                if isinstance(wire, (Input, Const)):
                    continue
                src_net = wire_src_dict[wire]
                if src_net.op == sync_src:
                    continue
                elif src_net.op in sync_prop:
                    wires_to_check.extend(src_net.args)
                else:
                    raise PyrtlError(
                        'memory "%s" is not specified as asynchronous but has an index '
                        '"%s" that is not ready at the start of the cycle due to net "%s"'
                        % (net.op_param[1].name, net.args[0].name, str(src_net)))

    def sanity_check_wirevector(self, w):
        """ Check that w is a valid wirevector type. """
        from .wire import WireVector
        if not isinstance(w, WireVector):
            raise PyrtlError(
                'error attempting to pass an input of type "%s" '
                'instead of WireVector' % type(w))

    def sanity_check_memblock(self, m):
        """ Check that m is a valid memblock type. """
        from .memory import MemBlock
        if not isinstance(m, MemBlock):
            raise PyrtlError(
                'error attempting to pass an input of type "%s" '
                'instead of MemBlock' % type(m))

    def sanity_check_net(self, net):
        """ Check that net is a valid LogicNet. """
        from .wire import Input, Output, Const, Register
        from .memory import MemBlock

        # general sanity checks that apply to all operations
        if not isinstance(net, LogicNet):
            raise PyrtlInternalError('error, net must be of type LogicNet')
        if not isinstance(net.args, tuple):
            raise PyrtlInternalError('error, LogicNet args must be tuple')
        if not isinstance(net.dests, tuple):
            raise PyrtlInternalError('error, LogicNet dests must be tuple')
        for w in net.args + net.dests:
            self.sanity_check_wirevector(w)
            if w._block is not self:
                raise PyrtlInternalError('error, net references different block')
            if w not in self.wirevector_set:
                raise PyrtlInternalError('error, net with unknown source "%s"' % w.name)

        # checks that input and output wirevectors are not misused
        bad_dests = set(filter(lambda w: isinstance(w, (Input, Const)), net.dests))
        if bad_dests:
            raise PyrtlInternalError('error, Inputs, Consts cannot be destinations to a net (%s)' %
                                     ','.join(map(str, bad_dests)))
        bad_args = set(filter(lambda w: isinstance(w, (Output)), net.args))
        if bad_args:
            raise PyrtlInternalError('error, Outputs cannot be arguments for a net (%s)' %
                                     ','.join(map(str, bad_args)))

        if net.op not in self.legal_ops:
            raise PyrtlInternalError('error, net op "%s" not from acceptable set %s' %
                                     (net.op, self.legal_ops))

        # operation-specific checks on arguments
        if net.op in 'w~rsm' and len(net.args) != 1:
            raise PyrtlInternalError('error, op only allowed 1 argument')
        if net.op in '&|^n+-*<>=' and len(net.args) != 2:
            raise PyrtlInternalError('error, op only allowed 2 arguments')
        if net.op == 'x':
            if len(net.args) != 3:
                raise PyrtlInternalError('error, op only allowed 3 arguments')
            if net.args[1].bitwidth != net.args[2].bitwidth:
                raise PyrtlInternalError('error, args have mismatched bitwidths')
            if net.args[0].bitwidth != 1:
                raise PyrtlInternalError('error, mux select must be a single bit')
        if net.op == '@' and len(net.args) != 3:
            raise PyrtlInternalError('error, op only allowed 3 arguments')
        if net.op in '&|^n+-*<>=' and net.args[0].bitwidth != net.args[1].bitwidth:
            raise PyrtlInternalError('error, args have mismatched bitwidths')
        if net.op in 'm@' and net.args[0].bitwidth != net.op_param[1].addrwidth:
            raise PyrtlInternalError('error, mem addrwidth mismatch')
        if net.op == '@' and net.args[1].bitwidth != net.op_param[1].bitwidth:
            raise PyrtlInternalError('error, mem bitwidth mismatch')
        if net.op == '@' and net.args[2].bitwidth != 1:
            raise PyrtlInternalError('error, mem write enable must be 1 bit')

        # operation-specific checks on op_params
        if net.op in 'w~&|^n+-*<>=xcr' and net.op_param is not None:
            raise PyrtlInternalError('error, op_param should be None')
        if net.op == 's':
            if not isinstance(net.op_param, tuple):
                raise PyrtlInternalError('error, select op requires tuple op_param')
            for p in net.op_param:
                if not isinstance(p, int):
                    raise PyrtlInternalError('error, select op_param requires ints')
                if p < 0 or p >= net.args[0].bitwidth:
                    raise PyrtlInternalError('error, op_param out of bounds')
        if net.op in 'm@':
            if not isinstance(net.op_param, tuple):
                raise PyrtlInternalError('error, mem op requires tuple op_param')
            if len(net.op_param) != 2:
                raise PyrtlInternalError('error, mem op requires 2 op_params in tuple')
            if not isinstance(net.op_param[0], int):
                raise PyrtlInternalError('error, mem op requires first operand as int')
            if not isinstance(net.op_param[1], MemBlock):
                raise PyrtlInternalError('error, mem op requires second operand of a memory type')

        # operation-specific checks on destinations
        if net.op in 'w~&|^n+-*<>=xcsrm' and len(net.dests) != 1:
            raise PyrtlInternalError('error, op only allowed 1 destination')
        if net.op == '@' and net.dests != ():
            raise PyrtlInternalError('error, mem write dest should be empty tuple')
        if net.op == 'r' and not isinstance(net.dests[0], Register):
            raise PyrtlInternalError('error, dest of next op should be a Register')

        # check destination validity
        if net.op in 'w~&|^nr' and net.dests[0].bitwidth > net.args[0].bitwidth:
            raise PyrtlInternalError('error, upper bits of destination unassigned')
        if net.op in '<>=' and net.dests[0].bitwidth != 1:
            raise PyrtlInternalError('error, destination should be of bitwidth=1')
        if net.op in '+-' and net.dests[0].bitwidth > net.args[0].bitwidth + 1:
            raise PyrtlInternalError('error, upper bits of destination unassigned')
        if net.op == '*' and net.dests[0].bitwidth > 2 * net.args[0].bitwidth:
            raise PyrtlInternalError('error, upper bits of destination unassigned')
        if net.op == 'x' and net.dests[0].bitwidth > net.args[1].bitwidth:
            raise PyrtlInternalError('error, upper bits of mux output undefined')
        if net.op == 'c' and net.dests[0].bitwidth > sum(x.bitwidth for x in net.args):
            raise PyrtlInternalError('error, upper bits of concat output undefined')
        if net.op == 's' and net.dests[0].bitwidth > len(net.op_param):
            raise PyrtlInternalError('error, upper bits of select output undefined')
        if net.op == 'm' and net.dests[0].bitwidth != net.op_param[1].bitwidth:
            raise PyrtlInternalError('error, mem read dest bitwidth mismatch')


class PostSynthBlock(Block):
    """ This is a block with extra metadata required to maintain the
    pre-synthesis interface during post-synthesis.

    It currently holds the following instance attributes:

    * *.io_map*: a map from old IO wirevector to a list of new IO wirevectors it maps to;
        this is a list because for unmerged io vectors, each old N-bit IO wirevector maps
        to N new 1-bit IO wirevectors.
    * *.reg_map*: a map from old register to a list of new registers; a list because post-synthesis,
        each N-bit register has been mapped to N 1-bit registers
    * *.mem_map*: a map from old memory block to the new memory block
    """

    def __init__(self):
        super(PostSynthBlock, self).__init__()
        self.io_map = collections.defaultdict(list)
        self.reg_map = collections.defaultdict(list)
        self.mem_map = {}


# -----------------------------------------------------------------------
#          __   __               __      __        __   __
#    |  | /  \ |__) |__/ | |\ | / _`    |__) |    /  \ /  ` |__/
#    |/\| \__/ |  \ |  \ | | \| \__>    |__) |___ \__/ \__, |  \
#

# Right now we use singleton_block to store the one global
# block, but in the future we should support multiple Blocks.
# The argument "singleton_block" should never be passed.
_singleton_block = Block()

# settings help tweak the behavior of pyrtl as needed, especially
# when there is a trade off between speed and debugability.  These
# are useful for developers to adjust behaviors in the different modes
# but should not be set directly by users.
debug_mode = False
_setting_keep_wirevector_call_stack = False
_setting_slower_but_more_descriptive_tmps = False


def _get_debug_mode():
    return debug_mode


def _get_useful_callpoint_name():
    """ Attempts to find the lowest user-level call into the PyRTL module.

    :return (string, int) or None: the file name and line number respectively

    This function walks back the current frame stack attempting to find the
    first frame that is not part of the pyrtl module.  The filename (stripped
    of path and .py extention) and line number of that call are returned.
    This point should be the point where the user-level code is making the
    call to some pyrtl intrisic (for example, calling "mux").   If the
    attempt to find the callpoint fails for any reason, None is returned.
    """
    if not _setting_slower_but_more_descriptive_tmps:
        return None

    import inspect
    loc = None
    frame_stack = inspect.stack()
    try:
        for frame in frame_stack:
            modname = inspect.getmodule(frame[0]).__name__
            if not modname.startswith('pyrtl.'):
                full_filename = frame[0].f_code.co_filename
                filename = full_filename.split('/')[-1].rstrip('.py')
                lineno = frame[0].f_lineno
                loc = (filename, lineno)
                break
    except Exception:
        loc = None
    finally:
        del frame_stack
    return loc


def working_block(block=None):
    """ Convenience function for capturing the current working block.

    If a block is not passed, or if the block passed is None, then
    this will return the "current working block".  However, if a block
    is passed in it will simply return that block instead.  This feature
    is useful in allowing functions to "override" the current working block.
    """

    if block is None:
        return _singleton_block
    elif not isinstance(block, Block):
        raise PyrtlError('error, expected instance of Block as block argument')
    else:
        return block


def reset_working_block():
    """ Reset the working block to be empty. """
    global _singleton_block
    _singleton_block = Block()


class set_working_block(object):
    """ Set the working block to be the block passed as argument.
    Compatible with the 'with' statement.

    Sanity checks will only be run if the new block is different
    from the original block.
    """

    @staticmethod
    def _set_working_block(block, no_sanity_check=False):
        global _singleton_block
        if not isinstance(block, Block):
            raise PyrtlError('error, expected instance of Block as block argument')
        if block is not _singleton_block:  # don't update if the blocks are the same
            if not no_sanity_check:
                block.sanity_check()
            _singleton_block = block

    def __init__(self, block, no_sanity_check=False):
        self.old_block = working_block()  # for with statement compatibility
        self._set_working_block(working_block(block), no_sanity_check)

    def __enter__(self):
        return self.old_block

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._set_working_block(self.old_block, no_sanity_check=True)


def temp_working_block():
    """ Set the working block to be new temporary block.

    If used with the 'with' statement the block will be reset to the
    original value (at the time of call) at exit of the context.
    """
    return set_working_block(Block())


def set_debug_mode(debug=True):
    """ Set the global debug mode.

    :param debug: Optional boolean paramter to which debug mode will be set

    This function will set the debug mode to the specified value.  Debug mode
    is, by default, set to off to keep the performance of the system.  With debug
    mode set to true, all temporary WireVectors created will be given a name based
    on the line of code on which they were created and a snapshot of the call-stack
    for those WireVectors will be kept as well.
    """
    global debug_mode
    global _setting_keep_wirevector_call_stack
    global _setting_slower_but_more_descriptive_tmps
    debug_mode = debug
    _setting_keep_wirevector_call_stack = debug
    _setting_slower_but_more_descriptive_tmps = debug


_py_regex = r'^[^\d\W]\w*\Z'


class _NameIndexer(object):
    """ Provides internal names that are based on a prefix and an index. """
    def __init__(self, internal_prefix='_sani_temp'):
        self.internal_prefix = internal_prefix
        self.internal_index = 0

    def make_valid_string(self):
        """ Build a valid string based on the prefix and internal index. """
        return self.internal_prefix + str(self.next_index())

    def next_index(self):
        index = self.internal_index
        self.internal_index += 1
        return index


class _NameSanitizer(_NameIndexer):
    """ Sanitizes the names so that names can be used in places that don't allow
    for arbitrary names while not mangling valid names.

    Put the values you want to validate into make_valid_string the first time
    you want to sanitize a particular string (or before the first time), and
    retrieve from the _NameSanitizer through indexing directly thereafter
    eg: sani["__&sfhs"] for retrieval after the first time

    """
    def __init__(self, identifier_regex_str, internal_prefix='_sani_temp',
                 map_valid_vals=True, extra_checks=lambda x: True, allow_duplicates=False):
        if identifier_regex_str[-1] != '$':
            identifier_regex_str += '$'
        self.identifier = re.compile(identifier_regex_str)
        self.val_map = {}
        self.map_valid = map_valid_vals
        self.extra_checks = extra_checks
        self.allow_dups = allow_duplicates
        super(_NameSanitizer, self).__init__(internal_prefix)

    def __getitem__(self, item):
        """ Get a value from the sanitizer """
        if not self.map_valid and self.is_valid_str(item):
            return item
        return self.val_map[item]

    def is_valid_str(self, string):
        return self.identifier.match(string) and self.extra_checks(string)

    def make_valid_string(self, string=''):
        """ Inputting a value for the first time. """
        if not self.is_valid_str(string):
            if string in self.val_map and not self.allow_dups:
                raise IndexError("Value {} has already been given to the sanitizer".format(string))
            internal_name = super(_NameSanitizer, self).make_valid_string()
            self.val_map[string] = internal_name
            return internal_name
        else:
            if self.map_valid:
                self.val_map[string] = string
            return string


class _PythonSanitizer(_NameSanitizer):
    """ Name Sanitizer specifically built for Python identifers. """
    def __init__(self, internal_prefix='_sani_temp', map_valid_vals=True):
        super(_PythonSanitizer, self).__init__(_py_regex, internal_prefix, map_valid_vals)
        self.extra_checks = lambda s: not keyword.iskeyword(s)
