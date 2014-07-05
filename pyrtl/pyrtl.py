"""
PyRTL is a framework for synthesizable logic specification in Python.

The module contains a collection of classes that are intended to work together
to provide RTL specification, simulation, tracing, and testing suitable for
teaching and research.  Simplicity, usability, clarity, and extendability
rather than performance or optimization is the overarching goal.
"""

import collections
import sys
import re

from export_base import ExportBase

# todo list:
# * all user visible assert calls should be replaced with "raise PyrtlError"
# * all PyrtlError calls should have useful error message
# * all classes should have useful docstrings
# * all public functions and methods should have useful docstrings
# * all private methods and members should use "_" at the start of their names
# * should have set of unit tests for main abstractions
# * should be PEP8 compliant
# * multiple nested blocks should be supported
# * add verilog export option to block

# ASCII Art in "JS Stick Letters"


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
        """ Add a wirevector object to the module."""
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
        if net.op not in self.legal_ops:
            raise PyrtlError(
                'error adding op "%s" not from known set %s'
                % (net.op, self.legal_ops))
        self.logic.add(net)

    def wirevector_subset(self, cls=None):
        """Return set of wirevectors, filtered by the types provided as cls."""
        if cls is None:
            return self.wirevector_set
        else:
            return set([x for x in self.wirevector_set if isinstance(x, cls)])

    def typecheck(self):
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


#-----------------------------------------------------------------
#        ___  __  ___  __   __   __               ___
#  \  / |__  /  `  |  /  \ |__) /__`   -|-  |\/| |__   |\/|
#   \/  |___ \__,  |  \__/ |  \ .__/        |  | |___  |  |
#

class WireVector(object):
    def __init__(self, bitwidth=None, name=None):
        # now figure out a name
        if name is None:
            name = ParseState.next_tempvar_name()
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
        ParseState.current_block.add_wirevector(self)

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
            other = Const(other)
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
        ParseState.current_block.add_net(net)
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
        ParseState.current_block.add_net(net)
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
        ParseState.current_block.add_net(net)
        return outwire

    def __len__(self):
        return self.bitwidth

    def sign_extended(self, bitwidth):
        """ return a sign extended wirevector derived from self """
        return self._extended(bitwidth, self[-1])

    def zero_extended(self, bitwidth):
        """ return a zero extended wirevector derived from self """
        return self._extended(bitwidth, Const(0, bitwidth=1))

    def _extended(self, bitwidth, extbit):
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
            ParseState.current_block.add_net(net)
            return concat(extvector, self)


class Input(WireVector):
    def __init__(self, bitwidth=None, name=None):
        WireVector.__init__(self, bitwidth, name)

    def __ilshift__(self, _):
        raise PyrtlError(
            'Input, such as "%s", cannot have values generated internally'
            % str(self.name))


class Output(WireVector):
    def __init__(self, bitwidth=None, name=None):
        WireVector.__init__(self, bitwidth, name)
    # todo: check that we can't read from this vector


class Const(WireVector):
    def __init__(self, val, bitwidth=None):
        self.name = ParseState.next_constvar_name(val)
        if bitwidth is None:
            self.bitwidth = len(bin(val))-2
        else:
            self.bitwidth = bitwidth
        self.val = val
        if (self.val >> self.bitwidth) != 0:
            raise PyrtlError(
                'error constant "%s" cannot fit in the specified %d bits'
                % (str(self.val),self.bitwidth) )
            
        ParseState.current_block.add_wirevector(self)

    def __ilshift__(self, other):
        raise PyrtlError(
            'ConstWires, such as "%s", should never be assigned to with <<='
            % str(self.name))


class Register(WireVector):
    def __init__(self, bitwidth, name=None):
        WireVector.__init__(self, bitwidth=bitwidth, name=name)
        self.reg_in = None

    def _makereg(self):
        if self.reg_in is None:
            n = WireVector(bitwidth=self.bitwidth, name=self.name+"'")
            net = LogicNet(
                op='r',
                op_param=None,
                args=(n,),
                dests=(self,))
            ParseState.current_block.add_net(net)
            self.reg_in = n
        return self.reg_in

    def __ilshift__(self, other):
        raise PyrtlError(
            'Registers, such as "%s", should never be assigned to with <<='
            % str(self.name))

    @property
    def next(self):
        return self._makereg()

    @next.setter
    def next(self, value):
        # The .next feild can be set with either "<<=" or "=", and
        # they do the same thing.
        if self.reg_in == value:
            return
        if self.reg_in is not None:
            raise PyrtlError
        if len(self) != len(value):
            raise PyrtlError
        n = self._makereg()
        n <<= value


class MemBlock(object):
    # data = memory[addr]  (infer read port)
    # memory[addr] = data  (infer write port)
    # Not currently implemented:  memory[addr] <<= data (infer write port)
    def __init__(self,  bitwidth, addrwidth, name=None):
        if bitwidth <= 0:
            raise PyrtlError
        if addrwidth <= 0:
            raise PyrtlError
        if name is None:
            name = ParseState.next_tempvar_name()

        self.bitwidth = bitwidth
        self.name = name
        self.addrwidth = addrwidth
        self.stored_net = None
        self.id = ParseState.next_memid()
        self.read_addr = []  # arg
        self.read_data = []  # dest
        self.write_addr = []  # arg
        self.write_data = []  # arg

    def __getitem__(self, item):
        if not isinstance(item, WireVector):
            raise PyrtlError
        if len(item) != self.addrwidth:
            raise PyrtlError

        data = WireVector(bitwidth=self.bitwidth)
        self.read_data.append(data)
        self.read_addr.append(item)
        self._update_net()
        return data

    def _update_net(self):
        if self.stored_net:
            ParseState.current_block.logic.remove(self.stored_net)
        assert len(self.write_addr) == len(self.write_data) # not sure about this one

        net = LogicNet(
            op='m',
            op_param=(self.id, len(self.read_addr), len(self.write_addr)),
            args=tuple(self.read_addr + self.write_addr + self.write_data),
            dests=tuple(self.read_data))
        ParseState.current_block.add_net(net)
        self.stored_net = net

    def __setitem__(self, item, val):
        if not isinstance(item, WireVector):
            raise PyrtlError
        if len(item) != self.addrwidth:
            raise PyrtlError
        if not isinstance(val, WireVector):
            raise PyrtlError
        if len(val) != self.bitwidth:
            raise PyrtlError
        self.write_data.append(val)
        self.write_addr.append(item)
        self._update_net()


#-----------------------------------------------------------------
#        ___       __   ___  __   __
#  |__| |__  |    |__) |__  |__) /__`
#  |  | |___ |___ |    |___ |  \ .__/
#

def as_wires(val):
    if isinstance(val, int):
        return Const(val)
    if not isinstance(val, WireVector):
        raise PyrtlError
    return val


def concat(*args):
    if len(args) <= 0:
        raise PyrtlError
    if len(args) == 1:
        return args[0]
    else:
        final_width = sum([len(arg) for arg in args])
        outwire = WireVector(bitwidth=final_width)
        net = LogicNet(
            op='c',
            op_param=None,
            args=tuple(args),
            dests=(outwire,))
        ParseState.current_block.add_net(net)
        return outwire


class PyrtlError(Exception):
    pass  # raised on any user-facing error in this module


class PyrtlInternalError(Exception):
    pass  # raised on any internal failure


#-----------------------------------------------------------------
#   __        __   __   ___     __  ___      ___  ___
#  |__)  /\  |__) /__` |__     /__`  |   /\   |  |__
#  |    /~~\ |  \ .__/ |___    .__/  |  /~~\  |  |___
#

class ParseState(object):
    current_block = Block()
    _tempvar_count = 1
    _memid_count = 0

    @classmethod
    def export(cls, exporter, file=sys.stdout):
        if not isinstance(exporter, ExportBase):
          raise PyrtlError
        exporter.import_from_block(cls.current_block)
        exporter.dump(file)

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

