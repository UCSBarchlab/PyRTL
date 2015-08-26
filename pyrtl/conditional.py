"""
conditional contains the class for ConditionUpdate.
"""

import core
import wire


# -----------------------------------------------------------------------
#    __   __        __    ___    __                  __
#   /  ` /  \ |\ | |  \ |  |  | /  \ |\ |  /\  |    /__`
#   \__, \__/ | \| |__/ |  |  | \__/ | \| /~~\ |___ .__/
#

class ConditionalUpdate(object):
    """ Manages the conditional update of registers based on a predicate.

    The management of conditional updates is expected to happen through
    the "with" blocks which will ensure that the region of execution for
    which the condition should apply is well defined.  It is easiest
    to see with an example:

    >   r1 = Register()
    >   r2 = Register()
    >   with ConditionalUpdate() as condition:
    >       with condition(a):
    >           r.next |= x  # set when a is true
    >           with condition(b):
    >               r2.next |= y  # set when a and b are true
    >       with condition(c):
    >           r.next |= z  # set when a is false and c is true
    >           r2.next |= z
    >       with condition.fallthrough:
    >           r.next |= w  # a is false and c is false

    In addition to this longer form, there is a shortcut version for
    dealing with just a single condition (there is no fallthrough or nesting
    of conditions possible in this shorter form.

    >   r = Register()
    >   with ConditionalUpdate(a == b):
    >       r.next |= x  # set when a is true
    """

    depth = 0
    current = None

    def __init__(self, shortcut_condition=None):
        if self.depth != 0:
            raise core.PyrtlError('error, no nesting ConditionalUpdates')
        # predicate_on_deck is used to shuffle the "call" on condition, which
        # is where the predicate is specified, to the actual "enter" that happens
        # as we enter the context.  A "none" is used if we are specifying a larger
        # context that will be home to many smaller subcontexts.
        self.predicate_on_deck = shortcut_condition
        self.conditions_list_stack = [[]]
        self.register_predicate_map = {}  # map reg -> [(pred, rhs), ...]
        self.wirevector_predicate_map = {}  # map wirevector -> [(pred, rhs), ...]
        self.memblock_write_predicate_map = {}  # map mem -> [(pred, addr, data, enable), ...]

    def __enter__(self):
        # if we are entering a context to contain multiple conditions
        if self.predicate_on_deck is None:
            if self.depth != 0:
                raise core.PyrtlError('error, you did something wrong with conditionals')
            retval = self  # return self to "condtional"
        # else we are entering a specific condition
        else:
            self.conditions_list_stack[-1].append(self.predicate_on_deck)
            # push a new empty list on the stack for sub-conditions
            self.conditions_list_stack.append([])
            retval = None  # no reference to the returned "with ... as ..." object

        ConditionalUpdate.current = self
        ConditionalUpdate.depth += 1
        self.predicate_on_deck = None
        return retval

    def __exit__(self, etype, evalue, etraceback):
        self.conditions_list_stack.pop()
        ConditionalUpdate.depth -= 1
        if self.depth == 0:
            self._finalize_wirevectors()
            self._finalize_registers()
            self._finalize_memblocks()
            ConditionalUpdate.current = None
        if self.depth < 0:
            raise core.PyrtlInternalError()

    def __call__(self, predicate):
        self.predicate_on_deck = predicate
        return self

    @property
    def fallthrough(self):
        """Property used to enter the context of the fallthrough case. This is the case
        where all the other cases evaluated to false"""
        self.predicate_on_deck = True
        return self

    @property
    def default(self):
        """Property used to specify values that are not assigned a value by a matched up case
        (Note that only one condition (other than this) gets matched up with any given
        wirevector) """

    @classmethod
    def currently_under_condition(cls):
        """Returns True if execution is currently in the context of a ConditionalUpdate."""
        return cls.depth > 0

    @classmethod
    def _build_wirevector(cls, wirevector, rhs):
        """Stores the wire assignment details until finalize is called."""
        if cls.depth < 1:
            raise core.PyrtlError('error, conditional assignment "|=" only valid under a condition')
        p = cls.current._current_select()
        # if map entry not there, set to [], then append the tuple (p, rhs)
        cls.current.wirevector_predicate_map.setdefault(wirevector, []).append((p, rhs))

    def _finalize_wirevectors(self):
        """Build the required muxes and call back to WireVector to finalize the wirevector build."""
        from helperfuncs import mux
        for wirevector in self.wirevector_predicate_map:
            result = wire.Const(0)  # default value
            wirevector_predlist = self.wirevector_predicate_map[wirevector]
            for p, rhs in wirevector_predlist:
                result = mux(p, truecase=rhs, falsecase=result)
            wirevector._build_wirevector(result)

    @classmethod
    def _build_register(cls, reg, rhs):
        """Stores the register details until finalize is called."""
        if cls.depth < 1:
            raise core.PyrtlError('error, conditional assignment "|=" only valid under a condition')
        p = cls.current._current_select()
        # if map entry not there, set to [], then append the tuple (p, rhs)
        cls.current.register_predicate_map.setdefault(reg, []).append((p, rhs))

    def _finalize_registers(self):
        """Build the required muxes and call back to Register to finalize the register build."""
        from helperfuncs import mux
        for reg in self.register_predicate_map:
            result = reg
            # TODO: right now this is totally not optimzied, should use muxes
            # in conjuction with predicates to encode efficiently.
            regpredlist = self.register_predicate_map[reg]
            for p, rhs in regpredlist:
                result = mux(p, truecase=rhs, falsecase=result)
            reg._build_register(result)

    @classmethod
    def _build_read_port(cls, mem, addr):
        # TODO: reduce number of ports through collapsing reads
        return mem._build_read_port(addr)

    @classmethod
    def _build_write_port(cls, mem, addr, data, enable):
        """Stores the write-port details until finalize is called."""
        if cls.depth == 0:
            raise core.PyrtlError('attempting to use conditional assign "|="'
                                  ' while not in a ConditionalUpdate context')
        p = cls.current._current_select()
        # if map entry not there, set to [], then append the tuple (p, ...)
        cls.current.memblock_write_predicate_map.setdefault(mem, []).append((p, addr, data, enable))

    def _finalize_memblocks(self):
        """Build the required muxes and call back to MemBlock to finalize the write port build."""
        from helperfuncs import mux
        for mem in self.memblock_write_predicate_map:
            is_first = True
            for p, addr, data, enable in self.memblock_write_predicate_map[mem]:
                if is_first:
                    combined_enable = mux(p, truecase=enable, falsecase=wire.Const(0))
                    combined_addr = addr
                    combined_data = data
                    is_first = False
                else:
                    combined_enable = mux(p, truecase=enable, falsecase=combined_enable)
                    combined_addr = mux(p, truecase=addr, falsecase=combined_addr)
                    combined_data = mux(p, truecase=data, falsecase=combined_data)
            mem._build_write_port(combined_addr, combined_data, combined_enable)

    def _current_select(self):
        """Function to calculate the current "predicate" in the current context."""
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

        if select is None:
            raise core.PyrtlError('error, update inside ConditionalUpdate not covered by condition')
        return select
