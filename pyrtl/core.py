
import collections
import sys
import re
import wire


# -----------------------------------------------------------------
#   ___  __   __   __   __  ___      __   ___  __
#  |__  |__) |__) /  \ |__)  |  \ / |__) |__  /__`
#  |___ |  \ |  \ \__/ |  \  |   |  |    |___ .__/
#

class PyrtlError(Exception):
    """ Raised on any user-facing error in this module """
    pass


class PyrtlInternalError(Exception):
    """ Raised on any PyRTL internal failure """
    pass


# -----------------------------------------------------------------
#    __        __   __
#   |__) |    /  \ /  ` |__/
#   |__) |___ \__/ \__, |  \
#

class LogicNet(collections.namedtuple('LogicNet', ['op', 'op_param', 'args', 'dests'])):
    """ The basic immutable datatype for storing a "net" in a netlist.

    The details of what is allowed in each of these fields is defined
    in the comments of Block, and is checked by block.sanity_check
    """
    def __str__(self):
        rhs = ', '.join([str(x) for x in self.args])
        lhs = ', '.join([str(x) for x in self.dests])
        options = '' if self.op_param is None else '(' + str(self.op_param) + ')'
        return ' '.join([lhs, '<--', self.op, '--', rhs, options])

    def __eq__(self, other):
        # We can't be going and calling __eq__ recursively on the logic nets for all of
        # the args and dests because that will actually *create* new logic nets which is
        # very much not what people would expect to happen.  Instead we define equality
        # as the immutable feilds as being equal and the list of args and dests as being
        # references to the same objects.
        return (self.op == other.op and
                self.op_param == other.op_param and
                len(self.args) == len(other.args) and
                len(self.dests) == len(other.dests) and
                all(self.args[i] is other.args[i] for i in range(len(self.args))) and
                all(self.dests[i] is other.dests[i] for i in range(len(self.dests))))

    def __ne__(self, other):
        return not self.__eq__(other)

    def _compare_error(self):
        # comparisons get you in a bad place between while you can compare op and op_param
        # safely, the args and dests are references to mutable objects.
        raise PyrtlError('Comparison between LogicNets is not supported')

    def __lt__(self, other):
        self._compare_error()

    def __le__(self, other):
        self._compare_error()

    def __gt__(self, other):
        self._compare_error()

    def __ge__(self, other):
        self._compare_error()


class Block(object):
    """ Block encapsulates a netlist.

    A Block in PyRTL is the class that stores a netlist and provides basic access
    and error checking members.  Each block has well defined inputs and outputs,
    and contains both the basic logic elements and references to the wires that
    connect them together.

    The logic structure is primarily contained in self.logic which holds a set of
    "LogicNet"s. Each LogicNet describes a primitive operation (such as an adder
    or memory).  The primitive is described by a 4-tuple of:

    1) the op (a single character describing the operation such as '+' or 'm'),
    2) a set of hard parameters to that primitives (such as the number of read
       ports for a memory),
    3) the tuple "args" which list the wirevectors hooked up as inputs to
       this particular net.
    4) the tuple "dests" which list the wirevectors hooked up as output for
       this particular net.

    Below is a list of the basic operations.  These properties (more formally
    specified) should all be checked by the class method sanity_check.

    * Most logical and arithmetic ops are pretty self explanatory, each takes
      exactly two arguments and they should perform the arithmetic or logical
      operation specified. OPS: ('&','|','^','+','-','*').  All inputs must
      be the same bitwidth.  Logical operations produce as many bits as are in
      the input, while '+' and '-' produce n+1 bits, and '*' produced 2n bits.
    * In addition there are some operations for performing comparisons
      that should perform the operation specified.  The '=' op is checking
      to see if the bits of the vectors are equal, while '<' and '>' do
      unsigned arithmetic comparison.  All comparisons generate a single bit
      of output (1 for true, 0 for false).
    * The 'w' operator is simply a directional wire and has no logic function.
    * The 'x' operator is a mux which takes a select bit and two signals.
      If the value of the select bit is 0 it selects the second argument, if
      it is 1 it selects the third argument.  Select must be a single bit, while
      the other two arguments must be the same length.
    * The 'c' operator is the concatiation operator and combines any number of
      wirevectors (a,b,...,z) into a single new wirevector with "a" in the MSB
      and "z" (or whatever is last) in the LSB position.
    * The 's' operator is the selection operator and chooses, based in the
      op_param specificied, a subset of the logic bits from a wire vector to
      select.  Repeats are accepted.
    * The 'r' operator is a register and on posedge, simply copies the value
      from the input to the output of the register
    * The 'm' operator is a memory block, which supports async reads (acting
      like combonational logic), and syncronous writes (writes are "latched"
      at posedge).  Multiple read and write ports are possible, and op_param
      requires three numbers (memory id, num reads, num writes). It assumes
      that operator reads have one addr (an arg) and one data (a dest).
      Writes have three args (addr, data, and write enable).  Reads are
      specified first and then writes.  You will not see a written value change
      until the following cycle.

    The connecting elements (args and dests) should be WireVectors or derived
    from WireVector, and should be registered with the block using
    the method add_wirevector.  Nets should be registered using add_net.

    In addition, there is a member legal_ops which defines the set of operations
    that can be legally added to the block.  By default it is set to all of the above
    defined operations, but it can be useful in certain cases to only allow a
    subset of operations (such as when transforms are being done that are "lowering"
    the blocks to more primitive ops.
    """

    def __init__(self):
        """Creates an empty hardware block."""
        self.logic = set()  # set of nets, each is a LogicNet named tuple
        self.wirevector_set = set()  # set of all wirevectors
        self.wirevector_by_name = {}  # map from name->wirevector, used for performance
        self.wirevector_map = {}  # map from (wirevector, number) -> wirevector, used for mapping
        # pre-synthesis wirevectors to post-synthesis vectors
        self.legal_ops = set('w~&|^+-*<>=xcsrm')  # set of legal OPS

    def __str__(self):
        """String form has one LogicNet per line."""
        return '\n'.join(str(l) for l in self.logic)

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

    def wirevector_subset(self, cls=None):
        """Return set of wirevectors, filtered by the type or tuple of types provided as cls.

        If no cls is specified, the full set of wirevectors associated with the Block are
        returned.  If cls is a single type, or a tuple of types, only those wirevectors of
        the matching types will be returned.  This is helpful for getting all inputs, outputs,
        or registers of a block for example."""
        if cls is None:
            return self.wirevector_set
        else:
            return set(x for x in self.wirevector_set if isinstance(x, cls))

    def logic_subset(self, op=None):
        """Return set of logicnets, filtered by the type of logic op provided as op.

        If no op is specified, the full set of logicnets associated with the Block are
        returned.  This is helpful for getting all memories of a block for example."""
        if op is None:
            return self.logic
        else:
            return set(x for x in self.logic if op in x.op)

    def get_wirevector_by_name(self, name, strict=False):
        """Return the wirevector matching name.

        By default, if a matching wirevector cannot be found the value None is
        returned.  However, if the argument strict is set to True, then this will
        instead throw a PyrtlError when no match is found."""
        if name in self.wirevector_by_name:
            return self.wirevector_by_name[name]
        elif strict:
            raise PyrtlError('error, block does not have a wirevector named %s' % name)
        else:
            return None

    def __iter__(self):
        """Return a generator object that yields the block's LogicNets in topological order.

        A LogicNet is never returned before all of its dependent LogicNets have been seen;
        this is the only guarantee on the order of the returned LogicNets."""
        return BlockIterator(self)

    def sanity_check(self):
        """ Check block and throw PyrtlError or PyrtlInternalError if there is an issue.

        Should not modify anything, only check datastructures to make sure they have been
        built according to the assumptions stated in the Block comments."""

        # TODO: check that the wirevector_by_name is sane

        # check for valid LogicNets (and wires)
        for net in self.logic:
            self.sanity_check_net(net)

        for w in self.wirevector_subset():
            if w.bitwidth is None:
                raise PyrtlError(
                    'error, missing bitwidth for WireVector "%s" ', w.name)

        # check for unique names
        wirevector_names_list = [x.name for x in self.wirevector_set]
        wirevector_names_set = set(wirevector_names_list)
        if len(wirevector_names_list) != len(wirevector_names_set):
            for w in wirevector_names_set:
                wirevector_names_list.remove(w)
            raise PyrtlError('Duplicate wire names found for the following '
                             'different signals: %s' % repr(wirevector_names_list))

        # check for dead input wires (not connected to anything)
        dest_set = set(wire for net in self.logic for wire in net.dests)
        arg_set = set(wire for net in self.logic for wire in net.args)
        full_set = dest_set | arg_set
        connected_minus_allwires = full_set.difference(self.wirevector_set)
        if len(connected_minus_allwires) > 0:
            bad_wire_names = '\n    '.join(str(x) for x in connected_minus_allwires)
            raise PyrtlError('Unknown wires found in net:\n    %s' % bad_wire_names)
        allwires_minus_connected = self.wirevector_set.difference(full_set)
        allwires_minus_connected = allwires_minus_connected.difference(
            self.wirevector_subset(wire.Input))
        #   ^ allow inputs to be unconnected
        if len(allwires_minus_connected) > 0:
            bad_wire_names = '\n    '.join(str(x) for x in allwires_minus_connected)
            raise PyrtlError('Wires declared but not connected:\n    %s' % bad_wire_names)

        # Check for wires that are inputs to a logicNet, but are not block inputs and are never
        # driven.
        ins = arg_set.difference(dest_set)
        ins = ins.difference(self.wirevector_subset(wire.Input))
        undriven = ins.difference(self.wirevector_subset(wire.Const))
        if len(undriven) > 0:
            raise PyrtlError('Wires used but never driven: %s' % [w.name for w in undriven])

        if debug_mode:
            # Check for wires that are destinations of a logicNet, but are not outputs and are never
            # used as args.
            outs = dest_set.difference(arg_set)
            unused = outs.difference(self.wirevector_subset(wire.Output))
            if len(unused) > 0:
                print 'Warning: Wires driven but never used { %s }' % [w.name for w in unused]

    def sanity_check_wirevector(self, w):
        """ Check that w is a valid wirevector type. """
        if not isinstance(w, wire.WireVector):
            raise PyrtlError(
                'error attempting to pass an input of type "%s" '
                'instead of WireVector' % type(w))

    def sanity_check_net(self, net):
        """ Check that net is a valid LogicNet. """

        # general sanity checks that apply to all operations
        if not isinstance(net, LogicNet):
            raise PyrtlInternalError('error, net must be of type LogicNet')
        if not isinstance(net.args, tuple):
            raise PyrtlInternalError('error, LogicNet args must be tuple')
        if not isinstance(net.dests, tuple):
            raise PyrtlInternalError('error, LogicNet dests must be tuple')
        for w in net.args + net.dests:
            self.sanity_check_wirevector(w)
            if w not in self.wirevector_set:
                raise PyrtlInternalError('error, net with unknown source "%s"' % w.name)
            if w.block is not self:
                raise PyrtlInternalError('error, net references different block')

        # checks that input and output wirevectors are not misused
        for w in net.dests:
            if isinstance(w, wire.Input):
                raise PyrtlInternalError('error, Inputs cannot be destinations to a net')
        for w in net.args:
            if isinstance(w, wire.Output):
                raise PyrtlInternalError('error, Outputs cannot be arguments for a net')

        if net.op not in self.legal_ops:
            raise PyrtlInternalError('error, net op "%s" not from acceptable set %s' %
                                     (net.op, self.legal_ops))

        # operation specific checks on arguments
        if net.op in 'w~rs' and len(net.args) != 1:
            raise PyrtlInternalError('error, op only allowed 1 argument')
        if net.op in '&|^+-*<>=' and len(net.args) != 2:
            raise PyrtlInternalError('error, op only allowed 2 arguments')
        if net.op in 'x' and len(net.args) != 3:
            raise PyrtlInternalError('error, op only allowed 3 arguments')
        if net.op in '&|^+-*<>=' and len(set(x.bitwidth for x in net.args)) > 1:
            raise PyrtlInternalError('error, args have mismatched bitwidths')
        if net.op == 'x' and net.args[1].bitwidth != net.args[2].bitwidth:
            raise PyrtlInternalError('error, args have mismatched bitwidths')
        if net.op == 'x' and net.args[0].bitwidth != 1:
            raise PyrtlInternalError('error, mux select must be a single bit')

        # operation specific checks on op_params
        if net.op in 'w~&|^+-*<>=xcr' and net.op_param is not None:
            raise PyrtlInternalError('error, op_param should be None')
        if net.op == 's':
            if not isinstance(net.op_param, tuple):
                raise PyrtlInternalError('error, select op requires op_param')
            for p in net.op_param:
                if p < 0 or p >= net.args[0].bitwidth:
                    raise PyrtlInternalError('error, op_param out of bounds')

        # check destination validity
        if net.op in 'w~&|^r' and net.dests[0].bitwidth > net.args[0].bitwidth:
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
        # TODO: Add Memory to the above checks

    # some unique name class methods useful internally
    _tempvar_count = 1
    _memid_count = 0

    def next_tempvar_name(self, name=None):
        cls = type(self)
        if name is None:
            wire_name = ''.join(['tmp', str(cls._tempvar_count)])
            cls._tempvar_count += 1
        else:
            if name.lower() in ['clk', 'clock']:
                raise PyrtlError('Clock signals should never be explicit')
            wire_name = name
        if wire_name in self.wirevector_by_name:
            raise PyrtlError('duplicate name "%s" added' % wire_name)
        return wire_name

    @classmethod
    def next_constvar_name(cls, val):
        wire_name = ''.join(['const', str(cls._tempvar_count), '_', str(val)])
        cls._tempvar_count += 1
        return wire_name

    @classmethod
    def next_memid(cls):
        cls._memid_count += 1
        return cls._memid_count


class BlockIterator():
    """ BlockIterator iterates over the block passed on init in topographic order.
        The input is a Block, and when a LogicNet is returned it is always the case
        that all of it's "parents" have already been returned earlier in the iteration.

        Note: this method will throw an error if there are loops in the
        logic that do not involve registers"""

    def __init__(self, block):
        self.block = block

    def __iter__(self):
        return self

    def next(self):
        cleared = self.block.wirevector_subset(wire.Input)\
            .union(self.block.wirevector_subset(wire.Register))
        remaining = self.block.logic.copy()
        prev_remain = len(self.block.logic)
        while len(remaining) > prev_remain:
            prev_remain = len(remaining)
            for gate in remaining:  # loop over logicnets not yet returned
                if all([arg in cleared for arg in gate.args]):  # if all args ready
                    cleared.update(set(gate.dests))  # add dests to set of ready wires
                    remaining.remove(gate)  # remove gate from set of to return
                    yield gate

        if remaining:
            raise PyrtlError("Failure in Block Iterator due to non-register loops")

        raise StopIteration

# -----------------------------------------------------------------------
#          __   __               __      __        __   __
#    |  | /  \ |__) |__/ | |\ | / _`    |__) |    /  \ /  ` |__/
#    |/\| \__/ |  \ |  \ | | \| \__>    |__) |___ \__/ \__, |  \
#

# Right now we use singleton_block to store the one global
# block, but in the future we should support multiple Blocks.
# The argument "singleton_block" should never be passed.
_singleton_block = Block()
debug_mode = False


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


def set_working_block(block):
    """ Set the working block to be the block passed as argument. """
    global _singleton_block
    if not isinstance(block, Block):
        raise PyrtlError('error, expected instance of Block as block argument')
    block.sanity_check()
    _singleton_block = block


def set_debug_mode(debug=True):
    """ Set the global debug mode. """
    global debug_mode
    debug_mode = debug
