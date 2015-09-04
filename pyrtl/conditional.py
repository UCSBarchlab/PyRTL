""" Conditional assignement of registers and wirevectors based on a predicate.

The management of selected assignments is expected to happen through
the "with" blocks which will ensure that the region of execution for
which the condition should apply is well defined.  It is easiest
to see with an example:

>   r1 = Register()
>   r2 = Register()
>   w3 = WireVector()
>   with conditional_assignment:
>       with a:
>           r.next |= i  # set when a is true
>           with b:
>               r2.next |= j  # set when a and b are true
>       with c:
>           r.next |= k  # set when a is false and c is true
>           r2.next |= k
>       with otherwise:
>           r2.next |= l  # a is false and c is false
>
>       with d:
>           w3.next |= m  # d is true (assignments must be independent)

Access should be done through instances "conditional_update" and "otherwise",
as described above, not through the classes themselves.
"""

import core
import wire
from contextlib import contextmanager

# -----------------------------------------------------------------------
#    __   __        __    ___    __                  __
#   /  ` /  \ |\ | |  \ |  |  | /  \ |\ |  /\  |    /__`
#   \__, \__/ | \| |__/ |  |  | \__/ | \| /~~\ |___ .__/
#


def currently_under_condition():
    """Returns True if execution is currently in the context of a _ConditionalAssignment."""
    return _depth > 0


def _reset_conditional_state():
    """Set or reset all the module state required for conditionals."""
    global _conditions_list_stack, _register_predicate_map
    global _wirevector_predicate_map, _memblock_write_predicate_map
    global _depth
    _depth = 0
    _conditions_list_stack = [[]]
    _register_predicate_map = {}  # map reg -> [(pred, rhs), ...]
    _wirevector_predicate_map = {}  # map wirevector -> [(pred, rhs), ...]
    _memblock_write_predicate_map = {}  # map mem -> [(pred, addr, data, enable), ...]


def _check_no_nesting():
    if _depth != 0:
        raise core.PyrtlError('no nesting of conditional assignments allowed')

def _check_under_condition():
    if not currently_under_condition():
        raise core.PyrtlError('conditional assignment "|=" only valid under a condition')


class _ConditionalAssignment():
    """ helper type of global "conditional_assignment". """
    def __enter__(self):
        global _depth
        _check_no_nesting()
        _depth = 1

    def __exit__(self, *exc_info):
        # default value for underspecified wirevectors is zero
        _finalize(_wirevector_predicate_map, lambda x: wire.Const(0))
        # default value for underspecified registers is the prior value
        _finalize(_register_predicate_map, lambda x: x)
        _finalize_memblocks()
        _reset_conditional_state()  # sets _depth back to 0


class _Otherwise():
    """ helper type of global "otherwise". """
    def __enter__(self):
        _push_condition(True)

    def __exit__(self, *exc_info):
        _pop_condition()


def _push_condition(predicate):
    """As we enter new conditions, this pushes them on the predicate stack."""
    global _depth
    _check_under_condition()
    _depth += 1
    _conditions_list_stack[-1].append(predicate)
    _conditions_list_stack.append([])


def _pop_condition():
    """As we exit conditions, this pops them off the stack."""
    global _depth
    _check_under_condition()
    _conditions_list_stack.pop()
    _depth -= 1

def _build(wirevector, rhs):
    """Stores the wire assignment details until finalize is called."""
    _check_under_condition()
    p = _current_select()
    if isinstance(wirevector, wire.Register):
        plist = _register_predicate_map.setdefault(wirevector, [])
    elif isinstance(wirevector, wire.WireVector):
        plist = _wirevector_predicate_map.setdefault(wirevector, [])
    else:
        raise core.PyrtlInternalError('unknown type passed to _build')
    plist.append((p, rhs))


def _finalize(predicate_map, default):
    """Build the required muxes and call back to WireVector to finalize the wirevector build."""
    from helperfuncs import mux
    for wirevector in predicate_map:
        result = default(wirevector)
        # TODO: right now this is totally not optimzied, should use muxes
        # in conjuction with predicates to encode efficiently.
        predlist = predicate_map[wirevector]
        for p, rhs in predlist:
            result = mux(p, truecase=rhs, falsecase=result)
        wirevector._build(result)


def _build_read_port(mem, addr):
    # TODO: reduce number of ports through collapsing reads
    return mem._build_read_port(addr)


def _build_write_port(mem, addr, data, enable):
    """Stores the write-port details until finalize is called."""
    _check_under_condition()
    p = _current_select()
    plist = _memblock_write_predicate_map.setdefault(mem, [])
    plist.append((p, addr, data, enable))


def _finalize_memblocks():
    """Build the required muxes and call back to MemBlock to finalize the write port build."""
    from helperfuncs import mux
    for mem in _memblock_write_predicate_map:
        is_first = True
        for p, addr, data, enable in _memblock_write_predicate_map[mem]:
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

def _current_select():
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
    for predlist in _conditions_list_stack[:-1]:
        # negate all of the predicates before the current one
        for predicate in predlist[:-1]:
            assert(predicate is not None)
            select = and_with_possible_none(select, ~predicate)
        # include the predicate for the current one (not negated)
        select = and_with_possible_none(select, predlist[-1])

    if select is None:
        raise core.PyrtlError('update inside conditional assignment not covered by condition')
    return select


_reset_conditional_state()
conditional_assignment = _ConditionalAssignment()
otherwise = _Otherwise()
