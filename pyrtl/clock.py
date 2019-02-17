"""Support for multiple clock domains in PyRTL.
"""

from __future__ import print_function, unicode_literals

from .pyrtlexceptions import PyrtlError


class _ClockDefaultManager(object):
    def __init__(self, clk):
        self._clk = clk
        self._old = clk._block.default_clock
        clk._block.default_clock = clk

    def __enter__(self):
        return self._clk

    def __exit__(self, *e):
        self._clk._block.default_clock = self._old


class Clock(object):
    def __init__(self, name, block=None):
        from .core import working_block
        self._block = working_block(block)
        if name in self._block.clocks:
            raise PyrtlError('Clock with name {} already exists'.format(name))
        if name in self._block.wirevector_by_name:
            raise PyrtlError('Cannot create clock with same name as wire')
        self._name = name
        self._block.clocks[name] = self

    @property
    def name(self):
        return self._name

    def set_default(self):
        return _ClockDefaultManager(self)

    def __repr__(self):
        return 'Clock({!r})'.format(self._name)

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and self._block == other._block
            and self.name == other.name)

    def __hash__(self):
        return hash((self._name, self._block))


class Unclocked(Clock):
    def __init__(self, block=None):
        from .core import working_block
        self._block = working_block(block)
        self._name = None

    def __repr__(self):
        return 'Unclocked()'
