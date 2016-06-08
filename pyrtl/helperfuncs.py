""" Defines a set of helper functions that make constructing hardware easier.

The set of functions includes
as_wires: converts consts to wires if needed (and does nothing to wires)
and_all_bits, or_all_bits, xor_all_bits: apply function across all bits
parity: same as xor_all_bits
mux: generate a multiplexer
concat: concatenate multiple wirevectors into one long vector
get_block: get the block of the arguments, throw error if they are different
"""

from __future__ import print_function, unicode_literals

import keyword
import re
import six

from .core import working_block
from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .wire import WireVector, Input, Output, Const, Register

_rtl_assert_number = 1
_probe_number = 1

# -----------------------------------------------------------------
#        ___       __   ___  __   __
#  |__| |__  |    |__) |__  |__) /__`
#  |  | |___ |___ |    |___ |  \ .__/
#


def input_list(names, bitwidth=1):
    """ Allocate and return a list of Inputs. """
    return wirevector_list(names, bitwidth, wvtype=Input)


def output_list(names, bitwidth=1):
    """ Allocate and return a list of Outputs. """
    return wirevector_list(names, bitwidth, wvtype=Output)


def register_list(names, bitwidth=1):
    """ Allocate and return a list of Registers. """
    return wirevector_list(names, bitwidth, wvtype=Register)


def wirevector_list(names, bitwidth=1, wvtype=WireVector):
    """ Allocate and return a list of WireVectors. """
    if '/' in names and bitwidth != 1:
        raise PyrtlError('only one of optional "/" or bitwidth parameter allowed')
    names = names.replace(',', ' ')

    wirelist = []
    for fullname in names.split():
        try:
            name, bw = fullname.split('/')
        except:
            name, bw = fullname, bitwidth
        wirelist.append(wvtype(bitwidth=bw, name=name))
    return wirelist


def as_wires(val, bitwidth=None, truncating=True, block=None):
    """ Return wires from val which may be wires, integers, strings, or bools.

    :param val: a wirevector-like object or something that can be converted into
      a Const
    :param bitwidth: The bitwidth the resulting wire should be
    :param bool truncating: determines whether bits will be dropped to acheive
     the desired bitwidth if it is too long (if true, the most-significant-bits
     will be dropped)
    :param Block block: block to use for wire

    This function is mainly used to coerce values into WireVectors (for
    example, operations such as "x+1" where "1" needs to be converted to
    a Const WireVector.)
    """
    from .memory import _MemIndexed
    block = working_block(block)

    if isinstance(val, (int, six.string_types)):
        # note that this case captures bool as well (as bools are instances of ints)
        return Const(val, bitwidth=bitwidth, block=block)
    elif isinstance(val, _MemIndexed):
        # covert to a memory read when the value is actually used
        return as_wires(val.mem._readaccess(val.index), bitwidth, truncating, block)
    elif not isinstance(val, WireVector):
        raise PyrtlError('error, expecting a wirevector, int, or verilog-style '
                         'const string got %s instead' % repr(val))
    elif bitwidth == '0':
        raise PyrtlError('error, bitwidth must be >= 1')
    elif val.bitwidth is None:
        raise PyrtlError('error, attempting to use wirevector with no defined bitwidth')
    elif bitwidth and bitwidth > val.bitwidth:
        return val.zero_extended(bitwidth)
    elif bitwidth and truncating and bitwidth < val.bitwidth:
        return val[:bitwidth]  # truncate the upper bits
    else:
        return val


def match_bitwidth(*args):
    # TODO: allow for custom bit extension functions
    """ Matches the bitwidth of all of the input arguments

    :type args: WireVector
    :return tuple of args in order with extended bits
    """
    max_len = max(len(wv) for wv in args)
    return (wv.zero_extended(max_len) for wv in args)


def probe(w, name=None):
    """ Print useful information about a WireVector when in debug mode.

    :type w: WireVector
    :type name: None or string
    :return: original WireVector w

    Probe can be inserted into a existing design easily as it returns the original wire unmodified.
    For example "y <<= x[0:3] + 4" could be turned into "y <<= probe(x)[0:3] + 4" to give visibility
    into both the origin of x (including the line that WireVector was originally created) and the
    run-time values of x (which will be named and thus show up by default in a trace.  Likewise
    "y <<= probe(x[0:3]) + 4", "y <<= probe(x[0:3] + 4)", and "probe(y) <<= x[0:3] + 4" are all
    valid uses of probe.  Note: probe does actually add wire to the working block of w (which can
    confuse various post-processing transforms such as output to verilog)
    """
    global _probe_number
    if not isinstance(w, WireVector):
        raise PyrtlError('Only WireVectors can be probed')

    print('(Probe-%d)' % _probe_number, end=' ')
    print(get_stack(w))

    if name:
        pname = 'Probe%d_%s__%s)' % (_probe_number, name, w.name)
    else:
        pname = '(Probe%d__%s)' % (_probe_number, w.name)

    p = Output(name=pname)
    p <<= w  # late assigns len from w automatically
    _probe_number += 1
    return w


def get_stacks(*wires):
    call_stack = getattr(wires[0], 'init_call_stack', None)
    if not call_stack:
        return '    No call info found for wires: use set_debug_mode() ' \
               'to provide more information\n'
    else:
        return '\n'.join(str(wire) + ":\n" + get_stack(wire) for wire in wires)


def get_stack(wire):
    if not isinstance(wire, WireVector):
        raise PyrtlError('Only WireVectors can be traced')

    call_stack = getattr(wire, 'init_call_stack', None)
    if call_stack:
        frames = ' '.join(frame for frame in call_stack[:-1])
        return "Wire Traceback, most recent call last \n" + frames + "\n"
    else:
        return '    No call info found for wire: use set_debug_mode()'\
               ' to provide more information'


def rtl_assert(w, exp, block=None):
    """ Add hardware assertions to be checked on the RTL design.

    :param w: should be a WireVector
    :param Exception exp: Exception to throw when assertion fails
    :param Block block: block to which the assertion should be added (default to working block)
    :return: the Output wire for the assertion (can be ignored in most cases)

    If at any time during execution the wire w is not `true` (i.e. asserted low)
    then simulation will raise exp.
    """

    global _rtl_assert_number

    block = working_block(block)

    if not isinstance(w, WireVector):
        raise PyrtlError('Only WireVectors can be asserted with rtl_assert')
    if len(w) != 1:
        raise PyrtlError('rtl_assert checks only a WireVector of bitwidth 1')
    if not isinstance(exp, Exception):
        raise PyrtlError('the second argument to rtl_assert must be an instance of Exception')
    if isinstance(exp, KeyError):
        raise PyrtlError('the second argument to rtl_assert cannot be a KeyError')
    if w not in block.wirevector_set:
        raise PyrtlError('assertion wire not part of the block to which it is being added')
    if w not in block.wirevector_set:
        raise PyrtlError('assertion not a known wirevector in the target block')

    if w in block.rtl_assert_dict:
        raise PyrtlInternalError('assertion conflicts with existing registered assertion')

    assertion_name = 'assertion%d' % _rtl_assert_number
    assert_wire = Output(bitwidth=1, name=assertion_name, block=block)
    assert_wire <<= w
    _rtl_assert_number += 1
    block.rtl_assert_dict[assert_wire] = exp
    return assert_wire


def check_rtl_assertions(sim):
    """ Checks the values in sim to see if any registers assertions fail.

    :param sim: Simulation in which to check the assertions
    :return: None
    """

    for (w, exp) in sim.block.rtl_assert_dict.items():
        try:
            value = sim.inspect(w)
            if not value:
                raise exp
        except KeyError:
            pass


def _check_for_loop(block=None):
    block = working_block(block)
    logic_left = block.logic.copy()
    wires_left = block.wirevector_subset(exclude=(Input, Const, Output, Register))
    prev_logic_left = len(logic_left) + 1
    while prev_logic_left > len(logic_left):
        prev_logic_left = len(logic_left)
        nets_to_remove = set()  # bc it's not safe to mutate a set inside its own iterator
        for net in logic_left:
            if not any(n_wire in wires_left for n_wire in net.args):
                nets_to_remove.add(net)
                wires_left.difference_update(net.dests)
        logic_left -= nets_to_remove

    if 0 == len(logic_left):
        return None
    return wires_left, logic_left


def find_loop(block=None):
    block = working_block(block)
    block.sanity_check()  # make sure that the block is sane first

    result = _check_for_loop(block)
    if not result:
        return
    wires_left, logic_left = result
    import random

    class _FilteringState(object):
        def __init__(self, dst_w):
            self.dst_w = dst_w
            self.arg_num = -1

    def dead_end():
        # clean up after a wire is found to not be part of the loop
        wires_left.discard(cur_item.dst_w)
        current_wires.discard(cur_item.dst_w)
        del checking_stack[-1]

    # now making a map to quickly look up nets
    dest_nets = {dest_w: net_ for net_ in logic_left for dest_w in net_.dests}
    initial_w = random.sample(wires_left, 1)[0]

    current_wires = set()
    checking_stack = [_FilteringState(initial_w)]

    # we don't use a recursive method as Python has a limited stack (default: 999 frames)
    while len(checking_stack):
        cur_item = checking_stack[-1]
        if cur_item.arg_num == -1:
            #  first time testing this item
            if cur_item.dst_w not in wires_left:
                dead_end()
                continue
            current_wires.add(cur_item.dst_w)
            cur_item.net = dest_nets[cur_item.dst_w]
            if cur_item.net.op == 'r':
                dead_end()
                continue
        cur_item.arg_num += 1  # go to the next item
        if cur_item.arg_num == len(cur_item.net.args):
            dead_end()
            continue
        next_wire = cur_item.net.args[cur_item.arg_num]
        if next_wire not in current_wires:
            current_wires.add(next_wire)
            checking_stack.append(_FilteringState(next_wire))
        else:  # We have found the loop!!!!!
            loop_info = []
            for f_state in reversed(checking_stack):
                loop_info.append(f_state)
                if f_state.dst_w is next_wire:
                    break
            else:
                raise PyrtlError("Shouldn't get here! Couldn't figure out the loop")
            return loop_info
    raise PyrtlError("Error in detecting loop")


def find_and_print_loop(block=None):
    loop_data = find_loop(block)
    print_loop(loop_data)
    return loop_data


def print_loop(loop_data):
    if not loop_data:
        print("No Loop Found")
    else:
        print("Loop found:")
        print('\n'.join("{}".format(fs.net) for fs in loop_data))
        # print '\n'.join("{} (dest wire: {})".format(fs.net, fs.dst_w) for fs in loop_info)
        print("")


def _currently_in_ipython():
    """ Return true if running under ipython, otherwise return False. """
    try:
        __IPYTHON__  # pylint: disable=undefined-variable
        return True
    except NameError:
        return False

py_regex = '^[^\d\W]\w*\Z'


class NameIndexer(object):
    """ Provides internal names that are based on a prefix and an index"""
    def __init__(self, internal_prefix='_sani_temp'):
        self.internal_prefix = internal_prefix
        self.internal_index = 0

    def make_valid_string(self):
        """ Inputting a value for the first time """
        internal_name = self.internal_prefix + str(self.internal_index)
        self.internal_index += 1
        return internal_name


class NameSanitizer(NameIndexer):
    """
    Sanitizes the names so that names can be used in places that don't allow
    for arbitrary names while not mangling valid names

    Put the values you want to validate into make_valid_string the first time
    you want to sanitize a particular string (or before the first time), and
    retrieve from the NameSanitizer through indexing directly thereafter
    eg: sani["__&sfhs"] for retrieval after the first time

    """
    def __init__(self, identifier_regex_str, internal_prefix='_sani_temp', map_valid_vals=True):
        self.identifier = re.compile(identifier_regex_str)
        self.val_map = {}
        self.map_valid = map_valid_vals
        super(NameSanitizer, self).__init__(internal_prefix)

    def __getitem__(self, item):
        """ Get a value from the sanitizer"""
        if not self.map_valid and self.is_valid_str(item):
            return item
        return self.val_map[item]

    def is_valid_str(self, string):
        return re.match(self.identifier, string) and self._extra_checks(string)

    def _extra_checks(self, string):
        return True

    def make_valid_string(self, string=''):
        """ Inputting a value for the first time """
        if not self.is_valid_str(string):
            if string in self.val_map:
                raise IndexError("Value {} has already been given to the sanitizer".format(string))
            internal_name = super(NameSanitizer, self).make_valid_string()
            self.val_map[string] = internal_name
            return internal_name
        else:
            if self.map_valid:
                self.val_map[string] = string
            return string


class PythonSanitizer(NameSanitizer):
    def __init__(self, internal_prefix='_sani_temp', map_valid_vals=True):
        super(PythonSanitizer, self).__init__(py_regex, internal_prefix, map_valid_vals)

    def _extra_checks(self, str):
        return not keyword.iskeyword(str)
