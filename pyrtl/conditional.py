"""
conditional contains the class for ConditionUpdate
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

    >   with ConditionalUpdate() as condition:
    >       r1 = Register()
    >       r2 = Register()
    >       with condition(a):
    >           r.next <<= x  # set when a is true
    >           with condition(b):
    >               r2.next <<= y  # set when a and b are true
    >       with condition(c):
    >           r.next <<= z  # set when a is false and c is true
    >           r2.next <<= z
    >       with condition.default:
    >           r.next <<= w  # a is false and c is false
    """

    stack = None

    def __init__(self, block=None):
        self.predicate_on_deck = None

    def __enter__(self):
        # if this is the root condition update
        if self.predicate_on_deck is None:
            ConditionalUpdate.stack = []
        else:
            ConditionalUpdate.stack.append(predicate_on_deck)
        return None

    def __exit__(self, etype, evalue, etraceback):
        ConditionalUpdate.stack.pop()

    def __call__(self, predicate):
        self.predicate_on_deck = predicate
        return self

    @property
    def default(self):
        self.predicate_on_deck = True
        return self
