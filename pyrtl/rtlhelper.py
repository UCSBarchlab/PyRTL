"""
rtlhelper has all of the basic extended types useful for creating logic.

Types defined in this file include:
Input: a wire vector that recieves an input for a block
Output: a wire vector that defines an output for a block
Const: a wire vector fed by a constant set of values defined as an integer
Register: a wire vector that is latched each cycle
MemBlock: a block of memory that can be read (async) and written (sync)

In addition, two helper functions are defined, as_wires (which does nothing
but return original wire vector if passed one, but converts integers into
Const wire vectors), and concat (which takes an arbitrary set of wire vector
parameters and concats them into one new wire vector which it returns.
"""

from rtlcore import *

#------------------------------------------------------------------------
#  ___     ___  ___       __   ___  __           ___  __  ___  __   __   __  
# |__  \_/  |  |__  |\ | |  \ |__  |  \    \  / |__  /  `  |  /  \ |__) /__` 
# |___ / \  |  |___ | \| |__/ |___ |__/     \/  |___ \__,  |  \__/ |  \ .__/ 
#                                                                        

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


#------------------------------------------------------------------------
#
#         ___        __   __          __        __   __       
#   |\/| |__   |\/| /  \ |__) \ /    |__) |    /  \ /  ` |__/ 
#   |  | |___  |  | \__/ |  \  |     |__) |___ \__/ \__, |  \ 
#

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
    """ Return wires from val which may be wires or int. """
    if isinstance(val, int):
        return Const(val)
    if not isinstance(val, WireVector):
        raise PyrtlError
    return val


def concat(*args):
    """ Take any number of wire vector params and return a wire vector concatinating them."""
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


