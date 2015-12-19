
import pyrtl
from pyrtl import transform


def insert_random_inversions(rate=0.5):
    import random

    def randomly_replace(wire):
        if random.random() < rate:
            new_src, new_dst = transform.clone_wire(wire), transform.clone_wire(wire)
            new_dst <<= ~new_src
            return new_src, new_dst
        return wire, wire

    transform.wire_transform(randomly_replace)


def probe_wire_if(condition_func):
    """

    :param condition_func: (logic net) -> bool
    :return:
    """

    def add_probe_if(wire):
        if condition_func(wire):
            pyrtl.probe(wire)
        return wire, wire

    transform.wire_transform(add_probe_if)
