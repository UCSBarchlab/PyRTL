from __future__ import print_function, unicode_literals

from .pyrtlexceptions import PyrtlError
from .core import LogicNet, working_block
from .wire import WireVector, Register
from .corecircuits import select
from .clock import Unclocked


def unsafe_domain_crossing(win, wout):
    net = LogicNet(op='d', op_param=None, args=(win,), dests=(wout,))
    working_block().add_net(net)


def sync_signal(w, clk, stages=2):
    """Synchronize an unclocked signal `w` to the clock `clk`.

    Returns the synchronized signal.
    Most designs require stages=2 to avoid metastability,
    but some high-speed designs may require stages=3.
    """
    if w.clock.name is not None:
        raise PyrtlError('Signal to be synchronized must be unclocked')
    x = WireVector(bitwidth=len(w), clock=clk)
    unsafe_domain_crossing(w, x)
    for n in range(stages):
        y = x
        x = Register(bitwidth=len(w), clock=clk)
        x.next <<= y
    return x


def desync_signal(w):
    """Desynchronize a clocked signal `w`.

    Returns a signal that copies `w` but is unclocked.
    """
    if w.clock.name is None:
        raise PyrtlError('Signal is already unclocked')
    x = WireVector(bitwidth=len(w), clock=Unclocked())
    unsafe_domain_crossing(w, x)
    return x


def xing_simple(win, wout, stages=2, align=True):
    """Simple clock domain crossing from `win` to `wout`.

    Use when passing a 1-bit signal from a slow to a fast clock domain.
    Most designs require stages=2 to avoid metastability,
    but some high-speed designs may require stages=3.
    If win comes directly from a register, align may be set to False to save a clock cycle.
    """
    if len(win) != 1 or len(wout) != 1:
        raise PyrtlError('Simple crossing only works on bitwidth 1')
    if align:
        x = Register(bitwidth=1, clock=win.clock)
        x.next <<= win
    else:
        x = win
    y = WireVector(bitwidth=1, clock=wout.clock)
    unsafe_domain_crossing(x, y)
    for n in range(stages):
        z = y
        y = Register(bitwidth=1, clock=wout.clock)
        y.next <<= z
    wout <<= y


def xing_event(win, wout, stages=2):
    """Clock domain crossing for an event from `win` to `wout`.

    Use when passing a 1-bit event between clock domains.
    An event is a signal that occassionally goes high for a single cycle,
    and otherwise remains low.
    Most designs require stages=2 to avoid metastability,
    but some high-speed designs may require stages=3.
    """
    if len(win) != 1 or len(wout) != 1:
        raise PyrtlError('Event crossing only works on bitwidth 1')
    rin = Register(bitwidth=1, clock=win.clock)
    rin.next <<= win ^ rin
    x = WireVector(bitwidth=1, clock=wout.clock)
    xing_simple(rin, x, stages=stages, align=False)
    rout = Register(bitwidth=1, clock=wout.clock)
    rout.next <<= x
    wout <<= x ^ rout


def xing_task(start, busy, req, done, stages=2):
    """Clock domain crossing for a task.

    The `start` and `busy` signals are in domain A, where the task is requested,
    and `req` and `done` are in domain B, where the task is performed.
    Must pulse `start` high for one cycle to request the beginning of a task.
    The `busy` signal will remain high until the task is completed.
    The `req` signal will pulse high for one cycle when the task is requested.
    Must pulse `done` high for one cycle when the task has been completed.
    Most designs require stages=2 to avoid metastability,
    but some high-speed designs may require stages=3.
    """
    if any(len(x) != 1 for x in (start, busy, req, done)):
        raise PyrtlError('All control signals are bitwidth 1 for task crossing')
    if start.clock != busy.clock:
        raise PyrtlError('Signals start and busy must be in same clock domain')
    if req.clock != done.clock:
        raise PyrtlError('Signals req and done must be in same clock domain')
    r = Register(bitwidth=1, clock=start.clock)
    busy <<= r
    xing_event(start & ~r, req, stages=stages)
    fin = WireVector(bitwidth=1, clock=start.clock)
    xing_event(done, fin, stages=stages)
    r.next <<= start | (r & ~fin)


def xing_bus(din, send, dout, stages=2):
    """Clock domain crossing for a bus.

    Use when passing a multi-bit signal that only changes occasionally.
    The `din` and `send` signals are in domain A, while `dout` is in domain B.
    To send the data, pulse `send` high for one cycle.
    The data in `din` will be sampled and sent to `dout`.
    """
    if len(send) != 1:
        raise PyrtlError('All control signals are bitwidth 1 for bus crossing')
    if din.clock != send.clock:
        raise PyrtlError('Signals din and send must be in same clock domain')
    mid = Register(bitwidth=len(din), clock=din.clock)
    mid.next <<= select(send, din, mid)
    x = WireVector(bitwidth=1, clock=dout.clock)
    xing_event(send, x, stages=stages)
    y = WireVector(bitwidth=len(dout), clock=dout.clock)
    unsafe_domain_crossing(mid, y)
    r = Register(bitwidth=len(dout), clock=dout.clock)
    r.next <<= select(x, y, r)
    dout <<= r
