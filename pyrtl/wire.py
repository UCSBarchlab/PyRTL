"""
wirevector has all of the basic extended types useful for creating logic.

Types defined in this file include:
WireVector: the base class for ordered collections of wires
Input: a wire vector that recieves an input for a block
Output: a wire vector that defines an output for a block
Const: a wire vector fed by an unsigned constant
Register: a wire vector that is latched each cycle
"""

import collections
import string
import core
import helperfuncs


#-----------------------------------------------------------------
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
    # Each class inhieriting from WireVector should overload accordingly
    code = 'W'

    def __init__(self, bitwidth=None, name=None, block=None):
        self.block = core.working_block(block)

        # figure out a name
        if name is None:
            name = core.Block.next_tempvar_name()
        if name.lower() in ['clk', 'clock']:
            raise core.PyrtlError(
                'Clock signals should never be explicitly instantiated')
        self.name = name

        # now handle the bitwidth
        if bitwidth is not None:
            if not isinstance(bitwidth, int):
                raise core.PyrtlError(
                    'error attempting to create wirevector with bitwidth of type "%s" '
                    'instead of integer' % type(bitwidth))
            if bitwidth <= 0:
                raise core.PyrtlError(
                    'error attempting to create wirevector with bitwidth of length "%d", '
                    'all bitwidths must be > 0' % bitwidth)
        self.bitwidth = bitwidth

        # finally, add the wirevector back in the mother block
        self.block.add_wirevector(self)

    def __str__(self):
        return ''.join([self.name, '/', str(self.bitwidth), self.code])

    def __ilshift__(self, other):
        other = helperfuncs.as_wires(other, block=self.block)

        if self.bitwidth is None:
            raise core.PyrtlError
        if self.bitwidth < other.bitwidth:
            # truncate the upper bits
            other = other[:self.bitwidth]
        if self.bitwidth > other.bitwidth:
            # extend appropriately
            other = other.extended(self.bitwidth)

        net = core.LogicNet(
            op='w',
            op_param=None,
            args=(other,),
            dests=(self,))
        self.block.add_net(net)
        return self

    def logicop(self, other, op):
        a, b = self, other
        # convert constants if necessary
        b = helperfuncs.as_wires(b, block=self.block)

        # check size of operands
        if len(a) < len(b):
            a = a.extended(len(b))
        elif len(b) < len(a):
            b = b.extended(len(a))
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

    # OPS
    def __and__(self, other):
        return self.logicop(other, '&')

    def __rand__(self, other):
        return self.logicop(other, '&')

    def __or__(self, other):
        return self.logicop(other, '|')

    def __ror__(self, other):
        return self.logicop(other, '|')

    def __xor__(self, other):
        return self.logicop(other, '^')

    def __rxor__(self, other):
        return self.logicop(other, '^')

    def __add__(self, other):
        return self.logicop(other, '+')

    def __radd__(self, other):
        return self.logicop(other, '+')

    def __sub__(self, other):
        return self.logicop(other, '-')

    def __rsub__(self, other):
        return self.logicop(other, '-')

    def __mul__(self, other):
        return self.logicop(other, '*')

    def __rmul__(self, other):
        return self.logicop(other, '*')

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

    def sign_extended(self, bitwidth):
        """ return a sign extended wirevector derived from self """
        return self._extend_with_bit(bitwidth, self[-1])

    def zero_extended(self, bitwidth):
        """ return a zero extended wirevector derived from self """
        return self._extend_with_bit(bitwidth, Const(0, bitwidth=1, block=self.block))

    def extended(self, bitwidth):
        """ return wirevector extended as the default rule for the class """
        return self.zero_extended(bitwidth)

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


#------------------------------------------------------------------------
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
    """ A WireVector representation of an unsigned integer constant """
    code = 'C'

    def __init__(self, val, bitwidth=None, block=None):
        """ Construct a constant implementation at initialization """

        if isinstance(val, int):
            num = val
            # infer bitwidth if it is not specified explicitly
            if bitwidth is None:
                bitwidth = len(bin(num))-2  # the -2 for the "0b" at the start of the string
        if isinstance(val, basestring):
            if bitwidth is not None:
                raise core.PyrtlError('error, bitwidth parameter of const should be'
                                      ' unspecified when the const is created from a string'
                                      ' (instead use verilog style specification)')
            split_string = string.split(val, "'")
            if len(split_string) != 2:
                raise core.PyrtlError('error, string for Const not in verilog style format')
            try:
                bitwidth = int(split_string[0])
                num = int(''.join(['0', split_string[1]]), 0)
            except ValueError:
                raise core.PyrtlError('error, string for Const not in verilog style format')

        if not isinstance(bitwidth, int):
            raise core.PyrtlError(
                'error, bitwidth must be from type int, instead Const was passed "%s" of type %s'
                % (str(bitwidth), type(bitwidth)))
        if num < 0:
            raise core.PyrtlError(
                'error, Const is only for unsigned numbers and must be positive')
        if bitwidth < 0:
            raise core.PyrtlError(
                'error, you are trying a negative bitwidth? awesome but wrong')
        if (num >> bitwidth) != 0:
            raise core.PyrtlError(
                'error constant "%s" cannot fit in the specified %d bits'
                % (str(num), bitwidth))

        name = core.Block.next_constvar_name(num)

        # initialize the WireVector
        super(Const, self).__init__(bitwidth=bitwidth, name=name, block=block)
        # add the member "val" to track the value of the constant
        self.val = num

    def __ilshift__(self, other):
        raise core.PyrtlError(
            'ConstWires, such as "%s", should never be assigned to with <<='
            % str(self.name))


class Register(WireVector):
    code = 'R'

    # When the register is called as such:  r.next <<= foo
    # the sequence of actions that happens is:
    # 1) The property .next is called to get the "value" of r.next
    # 2) The "value" is then passed to __ilshift__

    NextSetter = collections.namedtuple('NextSetter', 'rhs')

    def __init__(self, bitwidth, name=None, block=None):
        super(Register, self).__init__(bitwidth=bitwidth, name=name, block=block)
        self.reg_in = None  # wire vector setting self.next

    @property
    def next(self):
        return self

    def __ilshift__(self, other):
        other = helperfuncs.as_wires(other, block=self.block)
        # covert to proper bitwidth
        if self.bitwidth is None:
            raise core.PyrtlInternalError
        if self.bitwidth < other.bitwidth:
            # truncate the upper bits
            other = other[:self.bitwidth]
        if self.bitwidth > other.bitwidth:
            # extend appropriately
            other = other.extended(self.bitwidth)
        # pack into a special type to be handled by next.setter
        return Register.NextSetter(rhs=other)

    @next.setter
    def next(self, nextsetter):
        if not isinstance(nextsetter, Register.NextSetter):
            raise core.PyrtlError('error, .next values should only be set with the "<<=" operator')

        conditional = ConditionalUpdate.current
        if not conditional:
            if self.reg_in is not None:
                raise core.PyrtlError('error, .next value should be set once and only once')
            else:
                self.reg_in = nextsetter.rhs
                net = core.LogicNet('r', None, args=tuple([self.reg_in]), dests=tuple([self]))
                self.block.add_net(net)
        else:  # conditional
            # if this is the first assignment to the register
            if self.reg_in is None:
                # assume default update is "no change"
                self.reg_in = self
                net = core.LogicNet('r', None, args=tuple([self.reg_in]), dests=tuple([self]))
                self.block.add_net(net)
            else:
                net = core.LogicNet('r', None, args=tuple([self.reg_in]), dests=tuple([self]))
            # do the actual conditional update
            new_reg_in = conditional.add_conditional_update(net, nextsetter.rhs, self.block)
            self.reg_in = new_reg_in


#-----------------------------------------------------------------
#   __     __        ___  __           ___  __  ___  __   __   __
#  /__` | / _` |\ | |__  |  \    \  / |__  /  `  |  /  \ |__) /__`
#  .__/ | \__> | \| |___ |__/     \/  |___ \__,  |  \__/ |  \ .__/
#

class SignedWireVector(WireVector):
    code = 'SW'

    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


class SignedInput(Input):
    code = 'SI'

    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


class SignedOutput(Output):
    code = 'SO'

    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


class SignedConst(Const):
    code = 'SC'

    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


class SignedRegister(Register):
    code = 'SR'

    def extended(self, bitwidth):
        return self.sign_extended(bitwidth)


#------------------------------------------------------------------------
#    __   __        __    ___    __                  __
#   /  ` /  \ |\ | |  \ |  |  | /  \ |\ |  /\  |    /__`
#   \__, \__/ | \| |__/ |  |  | \__/ | \| /~~\ |___ .__/
#

# FIXME: Still need to add in the code to
# 1) keep track of the registers that fall under conditional update (to
# make sure that they are not assigned under any other conditional updates)
# 2) Handle memories and other crazy crap people might try to do inside
# these conditional statements

class ConditionalUpdate(object):
    """ Manages the conditional update of registers based on a predicate.

    The management of conditional updates is expected to happen through
    the "with" blocks which will ensure that the region of execution for
    which the condition should apply is well defined.  It is easiest
    to see with an example:

    >  condition = ConditionalUpdate()
    >  with condition(a):
    >      r.next <<= x  # set when a is true
    >      with condition(b):
    >          r2.next <<= y  # set when a and b are true
    >  with condition(c):
    >      r.next <<= z  # set when a is false and c is true
    >      r2.next <<= z
    >  with condition():
    >      r.next <<= w  # a is false and c is false
    """

    current = None  # the ConditionalUpdate instance in the current scope
    nesting_depth = 0  # the depth of nestin of the scopes

    def __init__(self, block=None):
        # A stack of all the lists of conditions is required, with
        # the most highy nested conditions near the top of the stack.
        # As we decend the nested conditions we push conditions onto the
        # list for that level of nesting, and we pop lists off when those
        # condition blocks are closed.
        self.conditions_list_stack = [[]]

        # predicate_on_deck stores the predicate passed by the last
        # call to the object (which is then used in __enter__).
        self.predicate_on_deck = None

    def __call__(self, predicate=None):
        self.predicate_on_deck = predicate
        return self

    def __enter__(self):
        # sanity checks on the scope
        if ConditionalUpdate.nesting_depth != 0:
            if ConditionalUpdate.current != self:
                raise core.PyrtlError('error, cannot nest different conditionals in one another')
        assert(ConditionalUpdate.nesting_depth >= 0)
        ConditionalUpdate.nesting_depth += 1
        ConditionalUpdate.current = self

        # make sure we did not add a condition after the "always true" clause
        if len(self.conditions_list_stack[-1]) >= 1:
            if self.conditions_list_stack[-1][-1] is None:
                raise core.PyrtlError('error, attempting to add unreachable condition')
        # append the predicate to the end of top list
        self.conditions_list_stack[-1].append(self.predicate_on_deck)
        # push a new empty list on the stack for sub-conditions
        self.conditions_list_stack.append([])
        self.predicate_on_deck = None
        return None

    def __exit__(self, etype, evalue, etraceback):
        # pop any sub-conditions off the top of the stacks
        self.conditions_list_stack.pop()

        # sanity checks on the scope
        ConditionalUpdate.nesting_depth -= 1
        if ConditionalUpdate.nesting_depth == 0:
            ConditionalUpdate.current = None
        assert(ConditionalUpdate.nesting_depth >= 0)

    def add_conditional_update(self, reg_net, valwire, block):
        """ Under the currently defined predicate, add an update rule to reg.

        Returns the new wire that should connect to the ".next" terminal
        of the register.
        """
        from helperfuncs import mux

        # calculate the predicate to use as a the select to a mux
        select = self._current_select()
        # copy the state out of reg_net that we need to build new net
        old_reg_next = reg_net.args[0]
        reg = reg_net.dests[0]

        # generate the mux selecting between old
        mux_out = mux(select, old_reg_next, valwire)
        new_reg_net = core.LogicNet('r', None, args=tuple([mux_out]), dests=tuple([reg]))

        # swap out the old register for the new conditioned one
        block.logic.remove(reg_net)
        block.add_net(new_reg_net)
        return mux_out

    def _current_select(self):
        """ Generates the conjuctions of the predicates required to control condition. """
        select = None

        # helper to create the conjuction of predicates
        def and_with_possible_none(a, b):
            assert(a is not None or b is not None)
            if a is None:
                return b
            if b is None:
                return a
            return a & b

        # for all conditions except the current children (which should be [])
        for predlist in self.conditions_list_stack[:-1]:
            # negate all of the predicates before the current one
            for predicate in predlist[:-1]:
                assert(predicate is not None)
                select = and_with_possible_none(select, ~predicate)
            # include the predicate for the current one (not negated)
            select = and_with_possible_none(select, predlist[-1])

        assert(select is not None)
        return select
