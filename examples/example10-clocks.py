""" Example 10: Multiple Clock Domains

    In simple designs, all the registers can update together, triggered by a single clock.
    More complicated designs, however, may have pieces that need to run at different speeds,
    whether to interface to the outside world or to satisfy internal timing constraints.
    PyRTL allows specifying any number of clocks, each of which can tick independently of the
    others. Every register is associated with one of these clocks, and the register will only
    update its contents when that clock ticks.

    Every signal is considered to belong to a single clock domain, based on the clock used by any
    registers driving that signal. Operations are not allowed to cross clock domains, because
    the setup and hold timings needed by registers could no longer be guaranteed without knowing
    the exact phase and frequency relationships between the different clocks.

    When information does need to cross clock domains, special crossing functions are available
    that will generate appropriate logic to synchronize the signals to the new domain.
"""

import sys
sys.path.append('/home/abe/school/PyRTL')
import pyrtl

# Newly created wires are associated with the default clock domain
i1 = pyrtl.Input(name='i1', bitwidth=3)
print(i1.clock)  # Clock('clk')
# New clocks can be created
fast = pyrtl.Clock('fast')
# The clock for a wire can be specified
i2 = pyrtl.Input(name='i2', bitwidth=3, clock=fast)
# If several wires will use the same clock, it can be set as the new default
fast.set_default()
o1 = pyrtl.Output(name='o1', bitwidth=3)
print(o1.clock)  # Clock('fast')
# The original default clock is accessible through the block
clk = pyrtl.working_block().clocks['clk']
clk.set_default()
o2 = pyrtl.Output(name='o2', bitwidth=3)
# To automatically change the default clock back, a context manager can be used:
with fast.set_default():
    # Anything created in this block uses Clock('fast')
    i3 = pyrtl.Input(name='i3', bitwidth=3)
    r1 = pyrtl.Register(name='r1', bitwidth=3)
# And now it returns to Clock('clk')
r2 = pyrtl.Register(name='r2', bitwidth=3)
# The default clock doesn't matter when building logic
r1.next <<= i2 + i3
o1 <<= r1
r2.next <<= i1
o2 <<= r2

# Simulation of multiple clock domains follows the same pattern as other simulations
sim = pyrtl.Simulation()
# Each step must specify, in addition to the inputs, which clock to trigger that step
# Only one clock can be triggered on a given step
# Only the inputs in that clock domain need to be given
sim.step({i1: 1}, clock=clk)
sim.step({i2: 2, i3: 3}, clock=fast)
# The same clock can be stepped several times in a row
# In general, no order is enforced between the different clocks
sim.step({i2: 4, i3: 5}, clock=fast)
sim.step({i1: 6}, clock=clk)
sim.step({i1: 7}, clock=clk)
# The simulation trace can be printed as normal
sim.tracer.render_trace()
# In addition, a list of the clock triggered at each step is available
print(sim.tracer.clocks)

# Trying to cross clock domains without any synchronization is not allowed
try:
    x = i1 + i2
except pyrtl.PyrtlError as e:
    print(e)

pyrtl.reset_working_block()

# Instead, use the appropriate clock domain crossing function xing_*
# Most of these function work on single-bit signals, as it cannot be guaranteed that all bits
# of a multi-bit signal would cross on the same cycle.
# When moving from a slow to a fast clock domain, use xing_simple
slow = pyrtl.Clock('slow')
fast = pyrtl.Clock('fast')
a = pyrtl.Input(name='a', bitwidth=1, clock=slow)
b = pyrtl.Output(name='b', bitwidth=1, clock=fast)
pyrtl.xing_simple(a, b)  # like b.next <<= a
# Note that all the xing_* functions introduce a small delay from the synchronization logic

# Crossing from a fast to a slow domain is more difficult, as the signal might change before
# the receiving domain notices it.
# For signals that only go high for a single clock cycle at a time, with a delay between pulses
# much longer than the period of the slower clock, use xing_event
c = pyrtl.Register(name='c', bitwidth=4, clock=fast)
c.next <<= c + 1
d = (c == 15)  # generate a pulse every 16 clock cycles
e = pyrtl.WireVector(name='e', bitwidth=1, clock=slow)
pyrtl.xing_event(d, e)  # like e.next <<= d

# For signals wider than a signal bit, use xing_bus
# Besides the data, it uses an additional `send` signal to initiate transferring the data
# between domains. In this example, we generate that signal by comparing the current and previous
# values of the input data.
f = pyrtl.Input(name='f', bitwidth=64, clock=slow)
g = pyrtl.Output(name='g', bitwidth=64, clock=fast)
h = pyrtl.Register(name='h', bitwidth=64, clock=slow)
h.next <<= f
pyrtl.xing_bus(f, (h != f), g)  # like g.next <<= select((h != f), f, g)

pyrtl.reset_working_block()

# When dealing with the outside world, inputs and outputs are not always nicely aligned to clocks.
# To represent this, they can be put in the clock domain Unclocked(), meaning that they may change
# value independently of any clock edge.
a = pyrtl.Input(name='a', bitwidth=3, clock=pyrtl.Unclocked())
# To use unclocked inputs in a clocked design, they must be synchronized to some clock
# The sync_signal function returns a new WireVector in the given clock domain
clk = pyrtl.working_block().clocks['clk']
a_sync = pyrtl.sync_signal(a, clk)  # like a_sync.next <<= a
print(a_sync.clock)
# Just like the xing_* functions, sync_signal introduces a small delay
# If you have a clocked signal and want to connect it to an unclocked output, this is perfectly
# safe, but PyRTL will still warn about a clock domain crossing. To indicate that it is
# intentional, use desync_signal, which returns a new unclocked WireVector
b = pyrtl.Output(name='b', bitwidth=3, clock=pyrtl.Unclocked())
c = pyrtl.WireVector(name='c', bitwidth=3, clock=clk)
c_desync = pyrtl.desync_signal(c)  # like c_desync << = c
print(c_desync.clock)
b <<= c_desync
# No delay is introduced by desync_signal
