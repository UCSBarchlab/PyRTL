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
#          __   __               __      __        __   __       
#    |  | /  \ |__) |__/ | |\ | / _`    |__) |    /  \ /  ` |__/ 
#    |/\| \__/ |  \ |  \ | | \| \__>    |__) |___ \__/ \__, |  \ 
#


# Right now we use singlton_block to store the one global
# block, but in the future we should support multiple Blocks.
# The argument "singlton_block" should never be passed.
_singleton_block = Block()
def working_block():
    return _singleton_block
def reset_working_block():
    global _singleton_block
    _singleton_block = Block()

#------------------------------------------------------------------------
#  ___     ___  ___       __   ___  __           ___  __  ___  __   __   __  
# |__  \_/  |  |__  |\ | |  \ |__  |  \    \  / |__  /  `  |  /  \ |__) /__` 
# |___ / \  |  |___ | \| |__/ |___ |__/     \/  |___ \__,  |  \__/ |  \ .__/ 
#                                                                        

class Input(WireVector):
    """ A WireVector type denoting inputs to a block (no writers) """

    def __init__(self, bitwidth=None, name=None):
        super(Input,self).__init__(bitwidth, name)

    def __ilshift__(self, _):
        raise PyrtlError(
            'Input, such as "%s", cannot have values generated internally'
            % str(self.name))


class Output(WireVector):
    """ A WireVector type denoting outputs of a block (no readers) """

    def __init__(self, bitwidth=None, name=None):
        super(Output,self).__init__(bitwidth, name)
    # todo: check that we can't read from this vector


class Const(WireVector):
    """ A WireVector representation of an integer constant """

    def __init__(self, val, bitwidth=None):
        """ Construct a constant implementation at initialization """
        name = Block.next_constvar_name(val)        
        # infer bitwidth if it is not specified explicitly
        if bitwidth is None:
            bitwidth = len(bin(val))-2
        if not isinstance(bitwidth,int):
            raise PyrtlError(
                'error, bitwidth must be from type int, instead Const was passed "%s" of type %s'
                % (str(bitwidth),type(bitwidth)) )
        # check sanity of bitwidth
        if (val >> bitwidth) != 0:
            raise PyrtlError(
                'error constant "%s" cannot fit in the specified %d bits'
                % (str(val),bitwidth) )

        # initialize the WireVector
        super(Const, self).__init__(bitwidth=bitwidth, name=name)
        # add the member "val" to track the value of the constant
        self.val = val            

    def __ilshift__(self, other):
        raise PyrtlError(
            'ConstWires, such as "%s", should never be assigned to with <<='
            % str(self.name))


class Register(WireVector):
    """ A WireVector with a latch in the middle (read current value, set .next value) """

    def __init__(self, bitwidth, name=None):
        super(Register,self).__init__(bitwidth=bitwidth, name=name)
        self.reg_in = None

    def _makereg(self):
        if self.reg_in is None:
            n = WireVector(bitwidth=self.bitwidth, name=self.name+"'")
            net = LogicNet(
                op='r',
                op_param=None,
                args=(n,),
                dests=(self,))
            self.block.add_net(net)
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
    """ An object for specifying block memories """

    # data = memory[addr]  (infer read port)
    # memory[addr] = data  (infer write port)
    # Not currently implemented:  memory[addr] <<= data (infer write port)
    def __init__(self,  bitwidth, addrwidth, name=None):
        if bitwidth <= 0:
            raise PyrtlError
        if addrwidth <= 0:
            raise PyrtlError
        if name is None:
            name = Block.next_tempvar_name()

        self.bitwidth = bitwidth
        self.name = name
        self.addrwidth = addrwidth
        self.stored_net = None
        self.id = Block.next_memid()
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
            self.block.logic.remove(self.stored_net)
        assert len(self.write_addr) == len(self.write_data) # not sure about this one

        net = LogicNet(
            op='m',
            op_param=(self.id, len(self.read_addr), len(self.write_addr)),
            args=tuple(self.read_addr + self.write_addr + self.write_data),
            dests=tuple(self.read_data))
        self.block.add_net(net)
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
        outwire.block.add_net(net)
        return outwire
