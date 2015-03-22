"""
wire has the basic extended types useful for creating logic.

Types defined in this file include:
WireVector: the base class for ordered collections of wires
Input: a wire vector that receives an input for a block
Output: a wire vector that defines an output for a block
Const: a wire vector fed by a constant
Register: a wire vector that is latched each cycle
"""

import collections
import string
import core
import helperfuncs
import conditional


# ----------------------------------------------------------------
#        ___  __  ___  __   __
#  \  / |__  /  `  |  /  \ |__)
#   \/  |___ \__,  |  \__/ |  \
#

class WireVector(object):
    """ The main class for describing the connections between operators.

    WireVectors act much like a list of wires, except that there is no
    "contained" type, each slice of a wirevector is itself a wirevector
    (even if it just contains a single "bit" of information).  The least
    significant bit of the wire is at index 0 and normal list slicing
    syntax applies (i.e. myvector[0:5] makes a new vector from the bottom
    5 bits of myvector, myvector[-1] takes the most significant bit, and
    myvector[-4:] takes the 4 most significant bits).
    """

    # "code" is a static variable used when output as string.
    # Each class inheriting from WireVector should overload accordingly
    code = 'W'

    def __init__(self, bitwidth=None, name=None, block=None):
        self.block = core.working_block(block)
        self.name = core.next_tempvar_name(name)
        if bitwidth is not None and isinstance(bitwidth, int) is False:
            raise core.PyrtlError('parameter "bitwidth" needs to be an int or left unspecificed')
        if bitwidth is not None and bitwidth <= 0:
            raise core.PyrtlError('error, bitwidth must be >= 1')
        self.bitwidth = bitwidth
        # finally, add the wirevector to the block
        self.block.add_wirevector(self)

    def __str__(self):
        return ''.join([self.name, '/', str(self.bitwidth), self.code])

    def _build_wirevector(self, other):
        # Actually create and add wirevector to logic block
        # This might be called immediately from ilshift, or delayed from ConditionalUpdate
        net = core.LogicNet(
            op='w',
            op_param=None,
            args=(other,),
            dests=(self,))
        self.block.add_net(net)

    def _prepare_for_assignment(self, rhs):
        # Convert right-hand-side to wires and propagate bitwidth if necessary
        rhs = helperfuncs.as_wires(rhs, bitwidth=self.bitwidth, block=self.block)
        if self.bitwidth is None:
            self.bitwidth = rhs.bitwidth
        return rhs

    def __ilshift__(self, other):
        """ Wire assignment operator (asign other to self). """
        other = self._prepare_for_assignment(other)
        self._build_wirevector(other)
        return self

    def __ior__(self, other):
        """ Conditional assignment operator (only valid under Conditional Update). """
        other = self._prepare_for_assignment(other)
        conditional.ConditionalUpdate._build_wirevector(self, other)
        return self

    def logicop(self, other, op):
        a, b = self, other
        # convert constants if necessary
        b = helperfuncs.as_wires(b, block=self.block)

        # check size of operands
        if len(a) < len(b):
            a = a.zero_extended(len(b))
        elif len(b) < len(a):
            b = b.zero_extended(len(a))
        resultlen = len(a)  # both are the same length now

        # some operations actually create more or less bits
        if op in ['+', '-']:
            resultlen += 1  # extra bit required for carry
        elif op in ['*']:
            resultlen = resultlen * 2  # more bits needed for mult
        elif op in ['<', '>', '=']:
            resultlen = 1

        s = WireVector(bitwidth=resultlen, block=self.block)
        net = core.LogicNet(
            op=op,
            op_param=None,
            args=(a, b),
            dests=(s,))
        self.block.add_net(net)
        return s

    def __bool__(self):
        """ Use of a wirevector in a statement like "a or b" is forbidden."""
        # python provides now way to overload these logical operations, and thus they
        # are very much not likely to be doing the thing that the programmer would be
        # expecting.
        raise core.PyrtlError('error, attempt to covert wirevector to compile-time boolean')

    __nonzero__ = __bool__  # for Python 2 and 3 compatibility

    def __and__(self, other):
        return self.logicop(other, '&')

    def __rand__(self, other):
        return self.logicop(other, '&')

    def __iand__(self, other):
        raise core.PyrtlError('error, operation not allowed on WireVectors')

    def __or__(self, other):
        return self.logicop(other, '|')

    def __ror__(self, other):
        return self.logicop(other, '|')

    # __ior__ used for conditional assignment above

    def __xor__(self, other):
        return self.logicop(other, '^')

    def __rxor__(self, other):
        return self.logicop(other, '^')

    def __ixor__(self, other):
        raise core.PyrtlError('error, operation not allowed on WireVectors')

    def __add__(self, other):
        return self.logicop(other, '+')

    def __radd__(self, other):
        return self.logicop(other, '+')

    def __iadd__(self, other):
        raise core.PyrtlError('error, operation not allowed on WireVectors')

    def __sub__(self, other):
        return self.logicop(other, '-')

    def __rsub__(self, other):
        other = helperfuncs.as_wires(other, block=self.block)
        return other.logicop(self, '-')

    def __isub__(self, other):
        raise core.PyrtlError('error, operation not allowed on WireVectors')

    def __mul__(self, other):
        return self.logicop(other, '*')

    def __rmul__(self, other):
        return self.logicop(other, '*')

    def __imul__(self, other):
        raise core.PyrtlError('error, operation not allowed on WireVectors')

    def __lt__(self, other):
        return self.logicop(other, '<')

    def __le__(self, other):
        # FIXME: Inefficient implementation of <=
        lt = self.logicop(other, '<')
        eq = self.logicop(other, '=')
        return lt | eq

    def __eq__(self, other):
        return self.logicop(other, '=')

    def __ne__(self, other):
        return ~ self.logicop(other, '=')

    def __gt__(self, other):
        return self.logicop(other, '>')

    def __ge__(self, other):
        # FIXME: Inefficient implementation of >=
        lt = self.logicop(other, '>')
        eq = self.logicop(other, '=')
        return lt | eq

    def __invert__(self):
        outwire = WireVector(bitwidth=len(self), block=self.block)
        net = core.LogicNet(
            op='~',
            op_param=None,
            args=(self,),
            dests=(outwire,))
        self.block.add_net(net)
        return outwire

    def __getitem__(self, item):
        assert self.bitwidth is not None  # should never be user visible
        allindex = [i for i in range(self.bitwidth)]
        if isinstance(item, int):
            selectednums = [allindex[item]]
        else:
            selectednums = allindex[item]  # slice
        outwire = WireVector(bitwidth=len(selectednums), block=self.block)
        net = core.LogicNet(
            op='s',
            op_param=tuple(selectednums),
            args=(self,),
            dests=(outwire,))
        self.block.add_net(net)
        return outwire

    def __len__(self):
        return self.bitwidth

    def __enter__(self):
        raise core.PyrtlError('error, WireVector cannot be used directly as a context.  '
                              '(you might be missing a ConditionalUpdate in your "with" block?)')

    def __exit__(self, type, value, tb):
        pass  # needed to allow the error raised in __enter__ to propagate up to the user

    # more functions for wires
    def nand(self, other):
        return self.logicop(other, 'n')

    def sign_extended(self, bitwidth):
        """ return a sign extended wirevector derived from self """
        return self._extend_with_bit(bitwidth, self[-1])

    def zero_extended(self, bitwidth):
        """ return a zero extended wirevector derived from self """
        return self._extend_with_bit(bitwidth, Const(0, bitwidth=1, block=self.block))

    def _extend_with_bit(self, bitwidth, extbit):
        numext = bitwidth - self.bitwidth
        if numext == 0:
            return self
        elif numext < 0:
            raise core.PyrtlError(
                'error, zero_extended cannot reduce the number of bits')
        else:
            from helperfuncs import concat
            extvector = WireVector(bitwidth=numext, block=self.block)
            net = core.LogicNet(
                op='s',
                op_param=(0,)*numext,
                args=(extbit,),
                dests=(extvector,))
            self.block.add_net(net)
            return concat(extvector, self)


# -----------------------------------------------------------------------
#  ___     ___  ___       __   ___  __           ___  __  ___  __   __   __
# |__  \_/  |  |__  |\ | |  \ |__  |  \    \  / |__  /  `  |  /  \ |__) /__`
# |___ / \  |  |___ | \| |__/ |___ |__/     \/  |___ \__,  |  \__/ |  \ .__/
#

class Input(WireVector):
    """ A WireVector type denoting inputs to a block (no writers) """
    code = 'I'

    def __init__(self, bitwidth=None, name=None, block=None):
        super(Input, self).__init__(bitwidth=bitwidth, name=name, block=block)

    def __ilshift__(self, _):
        raise core.PyrtlError(
            'Input, such as "%s", cannot have values generated internally'
            % str(self.name))


class Output(WireVector):
    """ A WireVector type denoting outputs of a block (no readers) """
    code = 'O'

    def __init__(self, bitwidth=None, name=None, block=None):
        super(Output, self).__init__(bitwidth, name, block)
    # todo: check that we can't read from this vector


class Const(WireVector):
    """ A WireVector representation of a constant value

    Converts from bool, integer, or verilog-style strings to a constant
    of the specified bitwidth.  If the bitwidth is too short to represent
    the specified constant then an error is raised.  If a possitive
    integer is specified the bitwidth can be infered from the constant.
    If a negative integer is provided it is converted to a two's complement
    representation of the specified bitwidth."""

    code = 'C'

    def __init__(self, val, bitwidth=None, block=None):
        """ Construct a constant implementation at initialization """
        if bitwidth is not None:
            if not isinstance(bitwidth, int):
                raise core.PyrtlError(
                    'bitwidth must be from type int, instead Const was passed "%s" of type %s'
                    % (str(bitwidth), type(bitwidth)))
            if bitwidth < 0:
                raise core.PyrtlError('you are trying a negative bitwidth? awesome but wrong')

        if isinstance(val, bool):
            num = int(val)
            if bitwidth is None:
                bitwidth = 1
            if bitwidth != 1:
                raise core.PyrtlError('error, boolean has bitwidth not equal to 1')
        elif isinstance(val, int):
            if val >= 0:
                num = val
                # infer bitwidth if it is not specified explicitly
                if bitwidth is None:
                    bitwidth = len(bin(num))-2  # the -2 for the "0b" at the start of the string
            else:  # val is negative
                if bitwidth is None:
                    raise core.PyrtlError(
                        'negative Const values must have bitwidth declared explicitly')
                if (val >> bitwidth-1) != -1:
                    raise core.PyrtlError('insufficient bits for negative number')
                mask = ((1 << bitwidth)-1)
                num = val & mask  # result is a twos complement value
        elif isinstance(val, basestring):
            if bitwidth is not None:
                raise core.PyrtlError('error, bitwidth parameter of const should be'
                                      ' unspecified when the const is created from a string'
                                      ' (instead use verilog style specification)')
            if val.startswith('-'):
                raise core.PyrtlError('verilog-style consts must be positive')
            split_string = string.split(val, "'")
            if len(split_string) != 2:
                raise core.PyrtlError('error, string for Const not in verilog style format')
            try:
                bitwidth = int(split_string[0])
                num = int(''.join(['0', split_string[1]]), 0)
            except ValueError:
                raise core.PyrtlError('error, string for Const not in verilog style format')
        else:
            raise core.PyrtlError('error, the value of Const is of an improper type, "%s"'
                                  'proper types are bool, int, and string' % type(val))

        if num < 0:
            raise core.PyrtlInternalError(
                'Const somehow evaluating to negative integer after checks')
        if (num >> bitwidth) != 0:
            raise core.PyrtlError(
                'error constant "%s" cannot fit in the specified %d bits'
                % (str(num), bitwidth))

        name = core.next_constvar_name(num)

        # initialize the WireVector
        super(Const, self).__init__(bitwidth=bitwidth, name=name, block=block)
        # add the member "val" to track the value of the constant
        self.val = num

    def __ilshift__(self, other):
        raise core.PyrtlError(
            'ConstWires, such as "%s", should never be assigned to with <<='
            % str(self.name))


class Register(WireVector):
    """ A WireVector with a register state element embedded.

    Registers only update their outputs on posedge of an implicit
    clk signal.  The "value" in the current cycle can be accessed
    by just referencing the Register itself.  To set the value for
    the next cycle (after the next posedge) you write to the
    property .next with the <<= operator.  For example, if you want
    to specify a counter it would look like: "a.next <<= a + 1"
    """
    code = 'R'

    # When the register is called as such:  r.next <<= foo
    # the sequence of actions that happens is:
    # 1) The property .next is called to get the "value" of r.next
    # 2) The "value" is then passed to __ilshift__
    #
    # The resulting behavior should enforce the following:
    # r.next <<= 5  -- good
    # a <<= r       -- good
    # r <<= 5       -- error
    # a <<= r.next  -- error
    # r.next = 5    -- error

    class _Next(object):
        """ This is the type returned by "r.next". """
        def __init__(self, reg):
            self.reg = reg

        def __ilshift__(self, other):
            return self.reg._next_ilshift(other)

        def __ior__(self, other):
            return self.reg._next_ior(other)

    class _NextSetter(object):
        """ This is the type returned by __ilshift__ which r.next will be assigned. """
        def __init__(self, rhs, is_conditional):
            self.rhs = rhs
            self.is_conditional = is_conditional

    def __init__(self, bitwidth, name=None, block=None):
        super(Register, self).__init__(bitwidth=bitwidth, name=name, block=block)
        self.reg_in = None  # wire vector setting self.next

    @property
    def next(self):
        return Register._Next(self)

    def __ilshift__(self, other):
        raise core.PyrtlError('error, you cannot set registers directly, net .next instead')

    def __ior__(self, other):
        raise core.PyrtlError('error, you cannot set registers directly, net .next instead')

    def _next_ilshift(self, other):
        other = helperfuncs.as_wires(other, bitwidth=self.bitwidth, block=self.block)
        if self.bitwidth is None:
            self.bitwidth = other.bitwidth
        return Register._NextSetter(other, is_conditional=False)

    def _next_ior(self, other):
        other = helperfuncs.as_wires(other, bitwidth=self.bitwidth, block=self.block)
        if self.bitwidth is None:
            self.bitwidth = other.bitwidth
        return Register._NextSetter(other, is_conditional=True)

    @next.setter
    def next(self, nextsetter):
        if not isinstance(nextsetter, Register._NextSetter):
            raise core.PyrtlError('error, .next should be set with "<<=" or "|=" operators')
        elif self.reg_in is not None:
            raise core.PyrtlError('error, .next value should be set once and only once')
        elif nextsetter.is_conditional:
            conditional.ConditionalUpdate._build_register(self, nextsetter.rhs)
        else:
            self._build_register(nextsetter.rhs)

    def _build_register(self, next):
        # this actually builds the register which might be from directly setting
        # the property "next" or delayed when there is a ConditionalUpdate
        self.reg_in = next
        net = core.LogicNet('r', None, args=(self.reg_in,), dests=(self,))
        self.block.add_net(net)
