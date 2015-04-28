""" Introduction to Hardware Design

    This code works through the hardware design process with the the
    audience of software developers more in mind.  We start with the simple
    problem of designing a fibonacci sequence calculator (http://oeis.org/A000045).  
"""
import sys
sys.path.append("..")
import pyrtl


def software_fibonacci(n):
    """ a normal old python function to return the Nth fibonacci number. """
    a, b = 0, 1
    for i in range(n):
        a, b = b, a + b
    return a

def attempt1_hardware_fibonacci(n, bitwidth):
    a = pyrtl.Const(0)
    b = pyrtl.Const(1)
    for i in range(n):
        a, b = b, a + b
    return a

def attempt2_hardware_fibonacci(n, bitwidth):
    a = pyrtl.Register(bitwidth, 'a')
    b = pyrtl.Register(bitwidth, 'b')

    a.next <<= b
    b.next <<= a + b

    return a

def attempt3_hardware_fibonacci(n, bitwidth):
    a = pyrtl.Register(bitwidth, 'a')
    b = pyrtl.Register(bitwidth, 'b')
    i = pyrtl.Register(bitwidth, 'i')

    i.next <<= i + 1
    a.next <<= b
    b.next <<= a + b

    return a, i==n

def attempt3_hardware_fibonacci(n, req, bitwidth):
    a = pyrtl.Register(bitwidth, 'a')
    b = pyrtl.Register(bitwidth, 'b')
    i = pyrtl.Register(bitwidth, 'i')
    local_n = pyrtl.Register(bitwidth, 'local_n')
    done = pyrtl.WireVector(bitwidth=1, 'done')

    with ConditionalUpdate() as condition:
        with condition(req):
            local_n.next |= n
            i.next |= 0
            a.next |= 0
            b.next |= 1
        with condition.default:
            i.next |= i + 1
            a.next |= b
            b.next |= a + b            
    done <<= i == local_n
    return a, done

