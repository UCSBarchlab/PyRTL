""" Example 4:  A State Machine built with ConditionalUpdate

    In this example we describe how ConditionalUpdate works in the context of
    a vending machine that will dispense an item when it has received 4 tokens.
    If a refund is requested, it returns the tokens.
"""

import sys
sys.path.append("..")

import pyrtl


token_in = pyrtl.Input(1, 'token_in')
req_refund = pyrtl.Input(1, 'req_refund')
dispense = pyrtl.Output(1, 'dispense')
refund = pyrtl.Output(1, 'refund')
state = pyrtl.Register(3, 'state')

# First new step, let's enumerate a set of constant to serve as our states
WAIT, TOK1, TOK2, TOK3, DISPENSE, REFUND = [pyrtl.Const(x, bitwidth=3) for x in range(6)]

# Now we could build a state machine using just the registers and logic discussed
# in the earlier examples, but doing operations *conditional* on some input is a pretty
# fundamental operation in hardware design.  PyRTL provides a class "ConditionalUpdate"
# to provide a predicated update to a registers.  Any *register* update that happens under
# a condition only happens when that condition is true.  In hardware this is implemented
# with a simply mux -- for people coming from software it is important to remember that this
# is describing a big logic function NOT an "if-then-else" clause.  All of these things will
# execute straight through when "build_everything" is called.  More comments after the code.

condition = pyrtl.ConditionalUpdate()
with condition(req_refund):  # signal of highest precedence
    state.next <<= REFUND
with condition(token_in):  # if token received, advance state in counter sequence
    with condition(state == WAIT):
        state.next <<= TOK1
    with condition(state == TOK1):
        state.next <<= TOK2
    with condition(state == TOK2):
        state.next <<= TOK3
    with condition(state == TOK3):
        state.next <<= DISPENSE  # 4th token received, go to dispense
    with condition():  # token received but in state where we can't handle it
        state.next <<= REFUND
# unconditional transition from these two states back to wait state
with condition((state == DISPENSE) | (state == REFUND)):
    state.next <<= WAIT

dispense <<= state == DISPENSE
refund <<= state == REFUND

# A couple of other things to note: 1) A condition can be nested within another condition
# and the implied hardware is that the register should only get that value if ALL of the
# encompassing conditions are satisfied.  2) Only one conditional at each level can be
# true meaning that all conditions are implicitly also saying that none of the prior conditions
# at the same level also have been true.  The highest priority condition is listed first,
# and in a sense you can think about each other condition as an "elif".  3) If not every
# condition is enumerated, the default value for the register under those cases will be the
# same as it was the prior cycle ("state.next <<= state" in this example).  4) There is a
# way to specify something like an "else" instead of "elif" and that is to leave the condition
# blank (as seen on the line above "state.next <<= REFUND").  This condition will be true if
# none of the other conditions at the same level were also true (for this example specifically
# state.next will get REFUND when req_refund==0, token_in==1, and state is not in TOK1, TOK2,
# TOK3, or DISPENSE.   Finally 5) not shown here, you can update multiple different registers
# all under the same set of conditionals.

# A more artificial example might make it even more clear how these rules interact:
# with condition(a):
#     r.next <<= 1        <-- when a is true
#     with condition(d):
#         r2.next <<= 2   <-- when a and d are true
#     with condition():
#         r2.next <<= 3   <-- when a is true and d is false
# with condition(b == c):
#     r.next <<= 0        <-- when a is not true and b & c is true

# Now let's build and test our state machine.

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

# Rather than just give some random inputs, let's specify some specific 1 bit values.  Recall
# that the sim.step method takes a dictionary mapping inputs to their values.  We could just
# specify the input set directly as a dictionary but it gets pretty ugly -- let's use some python
# to parse them up.

sim_inputs = {
    token_in:   '0010100111010000',
    req_refund: '1100010000000000'
    }

for cycle in range(len(sim_inputs[token_in])):
    sim.step({w: int(v[cycle]) for w, v in sim_inputs.items()})

# also, to make our input/output easy to reason about let's specify an order to the traces
sim_trace.render_trace(trace_list=[token_in, req_refund, state, dispense, refund])
