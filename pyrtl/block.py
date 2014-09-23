
"""
Block contains the core netlist data structure for PyRTL

The classes PyrtlError and PyrtlInternalError are the two main exceptions to
be thrown when things go wrong.  Block is the netlist storing module for a
chunk of hardware with well defined inputs and outputs, it contains both the
basic logic elements and references to the wires that connect them together.
The functions working_block and reset_working_block provide an easy way to
manage the current "working" block (i.e. the block that all hardware, by
default, is added in to).
"""


import collections
import sys
import re

from collections import namedtuple


#-----------------------------------------------------------------
#   ___  __   __   __   __  ___      __   ___  __
#  |__  |__) |__) /  \ |__)  |  \ / |__) |__  /__`
#  |___ |  \ |  \ \__/ |  \  |   |  |    |___ .__/
#

class PyrtlError(Exception):
    pass  # raised on any user-facing error in this module


class PyrtlInternalError(Exception):
    pass  # raised on any internal failure


#-----------------------------------------------------------------
#    __        __   __
#   |__) |    /  \ /  ` |__/
#   |__) |___ \__/ \__, |  \
#

class LogicNet(namedtuple('LogicNet', ['op', 'op_param', 'args', 'dests'])):
    """ The basic immutable datatype for storing a "net" in a netlist."""
    def __str__(self):
        lhs = str(self.args[0]) if len(self.args) == 1 else str(self.args)
        rhs = str(self.dests[0]) if len(self.dests) == 1 else str(self.dests)
        op_str = '' if self.op is None else self.op
        return ' '.join([lhs, '<<=', op_str, rhs])


class Block(object):
    """Data structure for holding a hardware connectivity graph.
    Structure is primarily contained in self.logic which holds a set of
    "LogicNet"s. Each LogicNet is describes a primitive unit (such as an adder
    or memory).  The primitive is described by a 4-tuple of the op (a single
    character describing the operation such as '+' or 'm'), a set of hard
    parameters to that primitives (such as the number of read ports for a
    memory), and two tuples (args and dests) that list the wirevectors hooked
    up as inputs and outputs to that primitive respectively.

    * Most logical and arithmetic ops are pretty self explanitory,
      OPS: ('&','|','^','+','-','*','<','>','=')
      they should perform the operation specified.  The '=' is checking
      to see if the bits of the vectors are equal
    * The op (None) is simply a directional wire and has no logic function.
    * The 'x' operator is a mux which takes a select bit and two signals.
      If the value of the select bit is 0 it selects the second argument, if
      it is 1 it selects the third argument..
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
      specified first and then writes.

    The connecting elements (args and dests) should be WireVectors or derived
    from WireVector, and registered seperately with the block using
    the method add_wirevector.
    """
    def __init__(self):
        """Creates and empty hardware block."""
        self.logic = set([])  # set of nets, each is a LogicNet named tuple
        self.wirevector_set = set([])  # set of all wirevectors
        self.wirevector_by_name = {}  # map from name->wirevector
        self.legal_ops = set('~&|^+-*<>=xcsrm') | set([None])  # OPS

    def __str__(self):
        """String form has one LogicNet per line."""
        return '\n'.join(str(l) for l in self.logic)

    def add_wirevector(self, wirevector):
        """ Add a wirevector object to the block."""
        _check_type_wirevector(wirevector)
        self.wirevector_set.add(wirevector)
        self.wirevector_by_name[wirevector.name] = wirevector

    def add_net(self, net):
        """ Connect new net to wirevectors previously added to the block."""
        if not isinstance(net, LogicNet):
            raise PyrtlError(
                'error attempting to create logic net from "%s" '
                'instead of LogicNet' % type(net))
        for w in net.args + net.dests:
            _check_type_wirevector(w)
            if w not in self.wirevector_set:
                raise PyrtlError(
                    'error making net with unknown source "%s"'
                    % w.name)
            if w.block is not self:
                raise PyrtlInternalError(
                    'error, cannot make net between two different blocks')
        if net.op in set('&|^+-*<>='):
            widths = set(x.bitwidth for x in net.args)
            if len(widths) > 1:
                raise PyrtlInternalError(
                    'error operands have mismatched bitwidths')
        if net.op not in self.legal_ops:
            raise PyrtlInternalError(
                'error adding op "%s" not from known set %s'
                % (net.op, self.legal_ops))
        # after all that sanity checking, actually update the data structure
        self.logic.add(net)

    def wirevector_subset(self, cls=None):
        """Return set of wirevectors, filtered by the type or tuple of types provided as cls."""
        if cls is None:
            return self.wirevector_set
        else:
            return set([x for x in self.wirevector_set if isinstance(x, cls)])

    def get_wirevector_by_name(self, name, strict=False):
        """Return the wirevector matching name."""
        try:
            retval = self.wirevector_by_name[name]
        except KeyError:
            retval = None
            if strict:
                raise PyrtlError('error, block does not have a wirevector named %s' % name)
        return retval

    def sanity_check(self):
        """ Check logic and wires and throw PyrtlError if there is an issue."""
        # check for unique names
        wirevector_names = [x.name for x in self.wirevector_set]
        dup_list = [
            x
            for x, y in collections.Counter(wirevector_names).items()
            if y > 1
            ]
        if len(dup_list) > 0:
            raise PyrtlError('Duplicate wire names found for the following '
                             'different signals: %s' % repr(dup_list))

        # check for dead input wires (not connected to anything)
        dest_set = set(wire for net in self.logic for wire in net.dests)
        arg_set = set(wire for net in self.logic for wire in net.args)
        full_set = dest_set | arg_set
        connected_minus_allwires = full_set.difference(self.wirevector_set)
        if len(connected_minus_allwires) > 0:
            raise PyrtlError(
                'Unknown wires found in net: %s'
                % repr(connected_minus_allwires))
        allwires_minus_connected = self.wirevector_set.difference(full_set)
        if len(allwires_minus_connected) > 0:
            raise PyrtlError(
                'Wires declared but never connected: %s'
                % repr([w.name for w in allwires_minus_connected]))

    # some unique name class methods useful internally
    _tempvar_count = 1
    _memid_count = 0

    @classmethod
    def next_tempvar_name(cls):
        wire_name = ''.join(['tmp', str(cls._tempvar_count)])
        cls._tempvar_count += 1
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


def _check_type_wirevector(w):
    from wirevector import WireVector
    if not isinstance(w, WireVector):
        raise PyrtlError(
            'error attempting to pass an input of type "%s" '
            'instead of WireVector' % type(w))


#------------------------------------------------------------------------
#          __   __               __      __        __   __
#    |  | /  \ |__) |__/ | |\ | / _`    |__) |    /  \ /  ` |__/
#    |/\| \__/ |  \ |  \ | | \| \__>    |__) |___ \__/ \__, |  \
#


# Right now we use singlton_block to store the one global
# block, but in the future we should support multiple Blocks.
# The argument "singlton_block" should never be passed.
_singleton_block = Block()


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
        raise PyrtlError('error, expected instance of Block as block arguement')
    else:
        return block


def reset_working_block():
    global _singleton_block
    _singleton_block = Block()
