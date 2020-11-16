""" Example 3:  A State Machine built with conditional_assignment

    In this example we describe how conditional_assignment works in the context of
    a vending machine that will dispense an item when it has received 4 tokens.
    If a refund is requested, it returns the tokens.
"""

import pyrtl

token_in = pyrtl.Input(1, 'token_in')
req_refund = pyrtl.Input(1, 'req_refund')
dispense = pyrtl.Output(1, 'dispense')
refund = pyrtl.Output(1, 'refund')
state = pyrtl.Register(3, 'state')

# First new step, let's enumerate a set of constants to serve as our states
WAIT, TOK1, TOK2, TOK3, DISPENSE, REFUND = [pyrtl.Const(x, bitwidth=3) for x in range(6)]

# Now we could build a state machine using just the registers and logic discussed
# in the earlier examples, but doing operations *conditionally* on some input is a pretty
# fundamental operation in hardware design.  PyRTL provides an instance called
# "conditional_assignment" to provide a predicated update to a registers, wires, and memories.
#
# Conditional assignments are specified with a "|=" instead of a "<<=" operator.  The
# conditional assignment is only valid in the context of a condition, and updates to those
# values only happens when that condition is true.  In hardware this is implemented
# with a simple mux -- for people coming from software it is important to remember that this
# is describing a big logic function, **NOT** an "if-then-else" clause.  All of these things will
# execute straight through when "build_everything" is called.  More comments after the code.
#
# One more thing: conditional_assignment might not always be the best item to use.
# If the update is simple, a regular 'mux(sel_wire, falsecase=f_wire, truecase=t_wire)'
# can be sufficient.

with pyrtl.conditional_assignment:
    with req_refund:  # signal of highest precedence
        state.next |= REFUND
    with token_in:  # if token received, advance state in counter sequence
        with state == WAIT:
            state.next |= TOK1
        with state == TOK1:
            state.next |= TOK2
        with state == TOK2:
            state.next |= TOK3
        with state == TOK3:
            state.next |= DISPENSE  # 4th token received, go to dispense
        with pyrtl.otherwise:  # token received but in state where we can't handle it
            state.next |= REFUND
    # unconditional transition from these two states back to wait state
    # NOTE: the parens are needed because in Python the "|" operator is lower precedence
    # than the "==" operator!
    with (state == DISPENSE) | (state == REFUND):
        state.next |= WAIT

dispense <<= state == DISPENSE
refund <<= state == REFUND

# A couple of other things to note: 1) A condition can be nested within another condition
# and the implied hardware is that the left-hand-side should only get that value if ALL of the
# encompassing conditions are satisfied.  2) Only one conditional at each level can be
# true meaning that all conditions are implicitly also saying that none of the prior conditions
# at the same level also have been true.  The highest priority condition is listed first,
# and in a sense you can think about each other condition as an "elif".  3) If not every
# condition is enumerated, the default value for the register under those cases will be the
# same as it was the prior cycle ("state.next |= state" in this example).  The default for a
# wirevector is 0.  4) There is a way to specify something like an "else" instead of "elif" and
# that is with an "otherwise" (as seen on the line above "state.next <<= REFUND").  This condition
# will be true if none of the other conditions at the same level were also true (for this example
# specifically, state.next will get REFUND when req_refund==0, token_in==1, and state is not in
# TOK1, TOK2, TOK3, or DISPENSE.  Finally 5) not shown here, you can update multiple different
# registers, wires, and memories all under the same set of conditionals.

# A more artificial example might make it even more clear how these rules interact:
# with a:
#     r.next |= 1        <-- when a is true
#     with d:
#         r2.next |= 2   <-- when a and d are true
#     with otherwise:
#         r2.next |= 3   <-- when a is true and d is false
# with b == c:
#     r.next |= 0        <-- when a is not true and b==c is true

# Now let's build and test our state machine.

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

# Rather than just give some random inputs, let's specify some specific 1-bit values.
# To make it easier to simulate it over several steps, we'll use sim.step_multiple,
# which takes in a dictionary mapping each input to its value on each step.

sim_inputs = {
    'token_in': '0010100111010000',
    'req_refund': '1100010000000000'
}

sim.step_multiple(sim_inputs)

# Also, to make our input/output easy to reason about let's specify an order to the traces
sim_trace.render_trace(trace_list=['token_in', 'req_refund', 'state', 'dispense', 'refund'])

# Finally, suppose you want to simulate your design and verify its output matches your
# expectations. sim.step_multiple also accepts as a second argument a dictionary mapping
# output wires to their expected value on each step. If during the simulation the
# actual and expected values differ, it will be reported to you! This might be useful
# if you have a working design which, after some tweaks, you'd like to test for functional
# equivalence, or as a basic sanity check.

sim_outputs = {
    'dispense': '0000000000001000',
    'refund': '0111001000000000'
}

# Note that you don't need to explicitly supply a tracer to Simulation(); it
# will create one internally for you if needed.
sim = pyrtl.Simulation()

sim.step_multiple(sim_inputs, sim_outputs)
