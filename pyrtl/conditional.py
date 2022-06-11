""" Conditional assignment of registers and WireVectors based on a predicate.

The management of selected assignments is expected to happen through
the "with" blocks which will ensure that the region of execution for
which the condition should apply is well defined.  It is easiest
to see with an example:

Example::

   r1 = Register()
   r2 = Register()
   w3 = WireVector()
   with conditional_assignment:
       with a:
           r1.next |= i  # set when a is true
           with b:
               r2.next |= j  # set when a and b are true
       with c:
           r1.next |= k  # set when a is false and c is true
           r2.next |= k
       with otherwise:
           r2.next |= l  # a is false and c is false

       with d:
           w3.next |= m  # d is true (assignments must be independent)

This is equivalent to::

    r1.next <<= select(a, i, select(c, k, default))
    r2.next <<= select(a, select(b, j, default), select(c, k, l))
    w3 <<= select(d, m, 0)

This functionality is provided through two instances: "conditional_update", which
is a context manager (under which conditional assignements can be made), and "otherwise",
which is an instance that stands in for a 'fall through' case.  The details of how these
should be used, and the difference between normal assignments and condtional assignments,
described in more detail in the state machine example in examples/example3-statemachine.py.

There are instances where you might want a wirevector to be set to a certain value in all
but certain with blocks. For example, say you have a processor with a PC register that is
normally updated to PC + 1 after each cycle, except when the current instruction is
a branch or jump. You could represent that as follows::

    pc = pyrtl.Register(32)
    instr = pyrtl.WireVector(32)
    res = pyrtl.WireVector(32)

    op = instr[:7]
    ADD = 0b0110011
    JMP = 0b1101111

    with conditional_assignment(
        defaults={
            pc: pc + 1,
            res: 0
        }
    ):
        with op == ADD:
            res |= instr[15:20] + instr[20:25]
            # pc will be updated to pc + 1
        with op == JMP:
            pc.next |= pc + instr[7:]
            # res will be set to 0

In addition to the conditional context, there is a helper function "currently_under_condition"
which will test if the code where it is called is currently elaborating hardware
under a condition.

"""
# Access should be done through instances "conditional_update" and "otherwise",
# as described above, not through the classes themselves.

from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .wire import WireVector, Const, Register


# -----------------------------------------------------------------------
#    __   __        __    ___    __                  __
#   /  ` /  \ |\ | |  \ |  |  | /  \ |\ |  /\  |    /__`
#   \__, \__/ | \| |__/ |  |  | \__/ | \| /~~\ |___ .__/
#


def currently_under_condition():
    """ Returns True if execution is currently in the context of a _ConditionalAssignment. """
    return _depth > 0


# -----------------------------------------------------------------------
# conditional_assignment and otherwise, both visible in the pyrtl module, are defineded as
# instances (hopefully the only and unchanging instances) of the following two types.

class _ConditionalAssignment:
    def __init__(self):
        self.defaults = {}

    def __call__(self, defaults):
        self.defaults = defaults
        return self

    """ Context providing funcitionality of "conditional_assignment". """
    def __enter__(self):
        global _depth
        _check_no_nesting()
        _depth = 1

    def __exit__(self, *exc_info):
        try:
            _finalize(self.defaults)
        finally:
            # even if the above finalization throws an error we need to
            # reset the state to prevent errors from bleeding over
            _reset_conditional_state()  # sets _depth back to 0


class _Otherwise:
    """ Context providing functionality of pyrtl "otherwise". """
    def __enter__(self):
        _push_condition(otherwise)

    def __exit__(self, *exc_info):
        _pop_condition()


def _reset_conditional_state():
    """ Set or reset all the module state required for conditionals. """
    global _conditions_list_stack
    global _conflicts_map
    global _predicate_map
    global _depth
    _depth = 0
    _conditions_list_stack = [[]]  # stack of lists of current conditions
    # _predicate_map: map wirevector or mem -> [(final_pred, rhs), ...]
    _predicate_map = {}
    # _conflicts_map: map wirevector or mem -> [ set([(pred,bool), (pred,bool)]), set([(pred,bool)..
    # * each element maps to a list of sets of tuples of (predicate id, bool)
    # * each time a value is written (lhs) we add the predicate set to the list
    # * each new write happens we have to check that the new predicate has at least one negated
    #   term with the value we are now trying to write.  Otherwise it is an error.
    _conflicts_map = {}


_reset_conditional_state()
conditional_assignment = _ConditionalAssignment()
otherwise = _Otherwise()


# -----------------------------------------------------------------------
# The following functions should not be PyRTL programmer visible, but are called in other
# places in the pyrtl module.

def _push_condition(predicate):
    """As we enter new conditions, this pushes them on the predicate stack."""
    global _depth
    _check_under_condition()
    _depth += 1
    if predicate is not otherwise and len(predicate) > 1:
        raise PyrtlError('all predicates for conditional assignments must be wirevectors of len 1')
    _conditions_list_stack[-1].append(predicate)
    _conditions_list_stack.append([])


def _pop_condition():
    """As we exit conditions, this pops them off the stack."""
    global _depth
    _check_under_condition()
    _conditions_list_stack.pop()
    _depth -= 1


def _build(lhs, rhs):
    """Stores the wire assignment details until finalize is called."""
    _check_under_condition()
    final_predicate, pred_set = _current_select()
    _check_and_add_pred_set(lhs, pred_set)
    _predicate_map.setdefault(lhs, []).append((final_predicate, rhs))


def _build_read_port(mem, addr):
    # TODO: reduce number of ports through collapsing reads
    return mem._build_read_port(addr)


# -----------------------------------------------------------------------
# The following helper functions are used only internally

def _check_no_nesting():
    if _depth != 0:
        raise PyrtlError('no nesting of conditional assignments allowed')


def _check_under_condition():
    if not currently_under_condition():
        raise PyrtlError('conditional assignment "|=" only valid under a condition')


def _check_and_add_pred_set(lhs, pred_set):
    for test_set in _conflicts_map.setdefault(lhs, []):
        if _pred_sets_are_in_conflict(pred_set, test_set):
            raise PyrtlError('conflicting conditions for %s' % lhs)
    _conflicts_map[lhs].append(pred_set)


def _pred_sets_are_in_conflict(pred_set_a, pred_set_b):
    """ Find conflict in sets, return conflict if found, else None. """
    # pred_sets conflict if we cannot find one shared predicate that is "negated" in one
    # and "non-negated" in the other
    for pred_a, bool_a in pred_set_a:
        for pred_b, bool_b in pred_set_b:
            if pred_a is pred_b and bool_a != bool_b:
                return False
    return True


def _finalize(defaults):
    """Build the required muxes and call back to WireVector to finalize the wirevector build."""
    from .memory import MemBlock
    from pyrtl.corecircuits import select
    for lhs in _predicate_map:
        # handle memory write ports
        if isinstance(lhs, MemBlock):
            p, (addr, data, enable) = _predicate_map[lhs][0]
            combined_enable = select(p, truecase=enable, falsecase=Const(0))
            combined_addr = addr
            combined_data = data

            for p, (addr, data, enable) in _predicate_map[lhs][1:]:
                combined_enable = select(p, truecase=enable, falsecase=combined_enable)
                combined_addr = select(p, truecase=addr, falsecase=combined_addr)
                combined_data = select(p, truecase=data, falsecase=combined_data)

            lhs._build(combined_addr, combined_data, combined_enable)

        # handle wirevector and register assignments
        else:
            if isinstance(lhs, Register):
                if lhs in defaults:
                    result = defaults[lhs]
                else:
                    result = lhs  # default for registers is "self"
            elif isinstance(lhs, WireVector):
                if lhs in defaults:
                    result = defaults[lhs]
                else:
                    result = 0  # default for wire is "0"
            else:
                raise PyrtlInternalError('unknown assignment in finalize')
            predlist = _predicate_map[lhs]
            for p, rhs in predlist:
                result = select(p, truecase=rhs, falsecase=result)
            lhs._build(result)


def _current_select():
    """ Function to calculate the current "predicate" in the current context.

    Returns a tuple of information: (predicate, pred_set).
    The value pred_set is a set([ (predicate, bool), ... ]) as described in
    the _reset_conditional_state
    """

    # helper to create the conjuction of predicates
    def and_with_possible_none(a, b):
        assert(a is not None or b is not None)
        if a is None:
            return b
        if b is None:
            return a
        return a & b

    def between_otherwise_and_current(predlist):
        lastother = None
        for i, p in enumerate(predlist[:-1]):
            if p is otherwise:
                lastother = i
        if lastother is None:
            return predlist[:-1]
        else:
            return predlist[lastother + 1:-1]

    select = None
    pred_set = set()

    # for all conditions except the current children (which should be [])
    for predlist in _conditions_list_stack[:-1]:
        # negate all of the predicates between "otherwise" and the current one
        for predicate in between_otherwise_and_current(predlist):
            select = and_with_possible_none(select, ~predicate)
            pred_set.add((predicate, True))
        # include the predicate for the current one (not negated)
        if predlist[-1] is not otherwise:
            predicate = predlist[-1]
            select = and_with_possible_none(select, predicate)
            pred_set.add((predicate, False))

    if select is None:
        raise PyrtlError('problem with conditional assignment')
    if len(select) != 1:
        raise PyrtlInternalError('conditional predicate with length greater than 1')

    return select, pred_set

# Some examples that were helpful in the design and testing of conditional

#  1  with a:  # a
#  2  with b:  # not(a) and b
#  3    with x:  # not(a) and b and x
#  4    with otherwise:  # not(a) and b and not(x)
#  5    with y:  # not(a) and b and y;  check(3,4)
#  6        with i:  # not(a) and b and y and i;  check(3,4)
#  7        with j:  # not(a) and b and y and not(i) and j;  check(3,4)
#  8        with otherwise:  # not(a) and b and y and not(i) and not(j):  check(3,4)
#  9        with k:  # not(a) and b and y and k;  check(3,4,6,7,8)
# 10        with m:  # not(a) and b and y and not(k) and m;  check(3,4,6,7,8)
# 11  with otherwise:  #not(a) and not(b)
# 12  with c:  #c;  check(1,2,3,4,5,6,7,8,9,10,11)

#  0  with a:  # a
#  1  with otherwise:  # a;
#  2  with b:  # not(a) and b;  check(0,1)
#  3    with x:  # not(a) and b and x;  check(0,1)
#  4    with otherwise:  # not(a) and b and not(x);  check(0,1)
#  5    with y:  # not(a) and b and y;  check(0,1,3,4)
#  6        with i:  # not(a) and b and y and i;  check(0,1,3,4)
#  7        with j:  # not(a) and b and y and not(i) and j;  check(0,1,3,4)
#  8        with otherwise:  # not(a) and b and y and not(i) and not(j):  check(0,1,3,4)
#  9        with k:  # not(a) and b and y and k;  check(0,1,3,4,6,7,8)
# 10        with m:  # not(a) and b and y and not(k) and m;  check(0,1,3,4,6,7,8)
#       with z: check(0,1,3,4)
#       with otherwise: check(0,1,3,4)
#       with g: check(0,1,3,4,5,6,7,8,9,10)
# 11  with otherwise:  #not(a) and not(b);  check(0,1)
# 12  with c:  #c;  check(0,1,2,3,4,5,6,7,8,9,10,11)
