"""
rtlcore contains the minumum necessary elements for PyRTL

The classes PyrtlError and PyrtlInternalError are the two main exeptions to 
be thrown when things go wrong.  Block is the netlist storing module for a
chunk of hardware with well defined inputs and outputs, it contains both the 
basic logic elements and references to the wires that connect them together.
Wirevector is the the named element that connect nets together and is mutually
dependent on Block.
"""


import collections
import sys
import re

# All ASCII Art in "JS Stick Letters"



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

LogicNet = collections.namedtuple(
    'LogicNet',
    ['op', 'op_param', 'args', 'dests']
    )


class Block(object):
    """Data structure for holding a hardware connectivity graph.
    Structure is primarily contained in self.logic which holds a set of
    "LogicNet"s. Each LogicNet is describes a primitive unit (such as an adder
    or memory).  The primitive is described by a 4-tuple of the op (a single
    character describing the operation such as '+' or 'm'), a set of hard
    parameters to that primitives (such as the number of read ports for a
    memory), and two tuples (args and dests) that list the wirevectors hooked
    up as inputs and outputs to that primitive respectively.

    * Most logical and arithmetic ops ('&','|','^','+','-') are pretty self
      explanitory, they should perform the operation specified.
    * The op (None) is simply a directional wire and has no logic function.
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
      Writes have two args (addr and data).  Reads are specified first and then
      writes.

    The connecting elements (args and dests) should be WireVectors or derived
    from WireVector, and registered seperately with the block using
    the method add_wirevector.
    """
    def __init__(self):
        """Creates and empty hardware block."""
        self.logic = set([])  # set of nets, each is a LogicNet named tuple
        self.wirevector_set = set([])  # set of all wirevectors
        self.wirevector_by_name = {}  # map from name->wirevector
        self.legal_ops = set('~&|^+-csrm') | set([None])

    def __str__(self):
        """String form has one LogicNet per line."""
        return '\n'.join(str(l) for l in self.logic)

    def add_wirevector(self, wirevector):
        """ Add a wirevector object to the block."""
        self.wirevector_set.add(wirevector)
        self.wirevector_by_name[wirevector.name] = wirevector

    def add_net(self, net):
        """ Connect new net to wirevectors previously added to the block."""
        for w in net.args + net.dests:
            if not isinstance(w, WireVector):
                raise PyrtlError(
                    'error attempting to create logic with input of type "%s" '
                    'instead of WireVector' % type(w))
            if w not in self.wirevector_set:
                raise PyrtlError(
                    'error making net with unknown source "%s"'
                    % w.name)
            if w.motherblock is not self:
                raise PyrtlError(
                    'error, cannot make net between two different blocks')
        if net.op not in self.legal_ops:
            raise PyrtlError(
                'error adding op "%s" not from known set %s'
                % (net.op, self.legal_ops))
        # after all that sanity checking, actually update the data structure
        self.logic.add(net)

    def wirevector_subset(self, cls=None):
        """Return set of wirevectors, filtered by the types provided as cls."""
        if cls is None:
            return self.wirevector_set
        else:
            return set([x for x in self.wirevector_set if isinstance(x, cls)])

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
            raise PyrtlError('Duplicate wire names found: %s' % repr(dup_list))

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


#-----------------------------------------------------------------
#        ___  __  ___  __   __     
#  \  / |__  /  `  |  /  \ |__)   
#   \/  |___ \__,  |  \__/ |  \ 
#

class WireVector(object):
    def __init__(self, bitwidth=None, name=None, block=None):

        # figure out what block this wirevector should be part of
        if isinstance(block, Block):
            self.block = block
        elif block is None:
            import rtlhelper
            self.block = rtlhelper._working_block;
        else:
            raise PyrtlError(
                'Attempt to link WireVector to block not derived of type Block')
        

        # figure out a name
        if name is None:
            name = Block.next_tempvar_name()
        if name.lower() in ['clk', 'clock']:
            raise PyrtlError(
                'Clock signals should never be explicitly instantiated')
        self.name = name

        # now handle the bitwidth
        if bitwidth is not None:
            if not isinstance(bitwidth, int):
                raise PyrtlError(
                    'error attempting to create wirevector with bitwidth of type "%s" '
                    'instead of integer' % type(w))
            if bitwidth <= 0:
                raise PyrtlError(
                    'error attempting to create wirevector with bitwidth of length "%s", '
                    'all bitwidths must be > 0' % type(w))
        self.bitwidth = bitwidth

        # finally, register the wirevector back with the mother block
        self.block.add_wirevector(self)

    def __repr__(self):
        return ''.join([
            type(self).__name__,
            ':',
            self.name,
            '/',
            str(self.bitwidth)
            ])

    def __ilshift__(self, other):
        if not isinstance(other, WireVector):
            import rtlhelper
            other = rtlhelper.Const(other)
        if self.bitwidth is None:
            self.bitwidth = len(other)
        else:
            if len(self) != len(other):
                raise PyrtlError(
                    'error attempting to assign a wirevector to an existing wirevector with a different bitwidth')

        net = LogicNet(
            op=None,
            op_param=None,
            args=(other,),
            dests=(self,))
        self.block.add_net(net)
        return self

    def logicop(self, other, op):
        a, b = self, other
        # convert constants if necessary
        if not isinstance(b, WireVector):
            b = Const(b)
        # check size of operands
        if len(a) < len(b):
            a = a.sign_extended(len(b))
        elif len(b) < len(a):
            b = b.sign_extended(len(a))
        # if len(a) != len(b):
        #    raise PyrtlError(
        #       'error, cannot apply op "%s" to wirevectors'
        #       ' of different length' % op)
        s = WireVector(bitwidth=len(a))  # both are same length now
        net = LogicNet(
            op=op,
            op_param=None,
            args=(a, b),
            dests=(s,))
        self.block.add_net(net)
        return s

    def __and__(self, other):
        return self.logicop(other, '&')

    def __or__(self, other):
        return self.logicop(other, '|')

    def __xor__(self, other):
        return self.logicop(other, '^')

    def __add__(self, other):
        return self.logicop(other, '+')

    def __sub__(self, other):
        return self.logicop(other, '-')

    def __invert__(self):
        outwire = WireVector(bitwidth=len(self))
        net = LogicNet(
            op='~',
            op_param=None,
            args=(self,),
            dests=(outwire,))
        self.block.add_net(net)
        return outwire

    def __getitem__(self, item):
        assert self.bitwidth is not None # should never be user visible
        allindex = [i for i in range(self.bitwidth)]
        if isinstance(item, int):
            selectednums = [allindex[item]]
        else:
            selectednums = allindex[item]  # slice
        outwire = WireVector(bitwidth=len(selectednums))
        net = LogicNet(
            op='s',
            op_param=tuple(selectednums),
            args=(self,),
            dests=(outwire,))
        self.block.add_net(net)
        return outwire

    def __len__(self):
        return self.bitwidth

    def sign_extended(self, bitwidth):
        """ return a sign extended wirevector derived from self """
        return self._extended(bitwidth, self[-1])

    def zero_extended(self, bitwidth):
        """ return a zero extended wirevector derived from self """
        import rtlhelper
        return self._extended(bitwidth, rtlhelper.Const(0, bitwidth=1))

    def _extended(self, bitwidth, extbit):
        import rtlhelper
        numext = bitwidth - self.bitwidth
        if numext == 0:
            return self
        elif numext < 0:
            raise PyrtlError(
                'error, zero_extended cannot reduce the number of bits')
        else:
            extvector = WireVector(bitwidth=numext)
            net = LogicNet(
                op='s',
                op_param=(0,)*numext,
                args=(extbit,),
                dests=(extvector,))
            self.block.add_net(net)
            return rtlhelper.concat(extvector, self)


 


