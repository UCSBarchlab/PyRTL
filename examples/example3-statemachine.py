# # Example 3: A State Machine built with `conditional_assignment`
#
# In this example we describe how `conditional_assignment` works in the context of a
# vending machine that will dispense an item when it has received 4 tokens. If a refund
# is requested, it returns the tokens.
import enum

import pyrtl

# Define `Inputs`, `Outputs`, and a `Register` to keep track of the vending machine's
# current state.
token_in = pyrtl.Input(1, "token_in")
req_refund = pyrtl.Input(1, "req_refund")

dispense = pyrtl.Output(1, "dispense")
refund = pyrtl.Output(1, "refund")

state = pyrtl.Register(3, "state")


# First new step, let's enumerate a set of constants to serve as our states
class State(enum.IntEnum):
    WAIT = 0  # Waiting for first token.
    TOK1 = 1  # Received first token, waiting for second token.
    TOK2 = 2  # Received second token, waiting for third token.
    TOK3 = 3  # Received third token, waiting for fourth token.
    DISP = 4  # Received fourth token, dispense item.
    RFND = 5  # Issue refund.


# Now we could build a state machine using just the `Registers` and logic discussed in
# prior examples, but doing operations **conditionally** on some input is a pretty
# fundamental operation in hardware design. PyRTL provides `conditional_assignment` to
# provide a predicated update to `Registers`, `WireVectors`, and `MemBlocks`.
#
# `conditional_assignments` are specified with the `|=` operator instead of the usual
# `<<=` operator. The `conditional_assignment` is only valid in the context of a
# condition, and updates to those values only happens when that condition is `True`. In
# hardware this is implemented with a simple `mux()` -- for people coming from software
# it is important to remember that this is describing a big logic function, **NOT** an
# "if-then-else" clause. The `conditional_assignment` below just builds hardware
# multiplexers. Nothing conditional actually happens until the `Simulation` is run.
#
# One more thing: `conditional_assignment` might not always be the best solution. For
# simple updates, a regular
#
#     select(sel_wire, truecase=t_wire, falsecase=f_wire)
#
# can be easier to read.
with pyrtl.conditional_assignment:
    with req_refund:  # signal of highest precedence
        state.next |= State.RFND
    with token_in:  # if token received, advance state in counter sequence
        with state == State.WAIT:
            state.next |= State.TOK1
        with state == State.TOK1:
            state.next |= State.TOK2
        with state == State.TOK2:
            state.next |= State.TOK3
        with state == State.TOK3:
            state.next |= State.DISP  # 4th token received, go to dispense
        with pyrtl.otherwise:  # token received in unsupported state
            state.next |= State.RFND
    # unconditional transition from these two states back to wait state

    # NOTE: the parens are needed because in Python the "|" operator is lower
    # precedence than the "==" operator!
    with (state == State.DISP) | (state == State.RFND):
        state.next |= State.WAIT

dispense <<= state == State.DISP
refund <<= state == State.RFND

# A few more notes:
#
# 1. A condition can be nested within another condition and the implied hardware is that
#    the left-hand-side should only get that value if ALL of the encompassing conditions
#    are satisfied.
# 2. Only one conditional at each level can be `True`, so all conditions imply that NONE
#    of the prior conditions at the same level are `True`. The highest priority
#    condition is listed first, and in a sense you can think about each other condition
#    as an `elif`.
# 3. If a `WireVector`'s value is not specified for some combination of conditions,
#    `conditional_assignment` will supply a default value. By default,`Registers` will
#    retain their value from the prior cycle ("state.next |= state" in this example).
#    `WireVectors` default to `0`.
# 4. There is a way to specify something like an `else` instead of `elif` and that is
#    with an `otherwise` (as seen on the line above "state.next <<= State.RFND"). This
#    condition will be `True` if none of the other conditions at the same level were
#    also `True`. For this example specifically, `state.next` will get `RFND` when
#    `req_refund==0`, and `token_in==1`, and state is not any of {`WAIT`, `TOK1`,
#    `TOK2`, or `TOK3`}.
# 5. Not shown here, but you can update multiple `Registers`, `WireVectors`, and
#    `MemBlocks` within one `conditional_assignment`.
#
# A more artificial example might make it even more clear how these rules interact:
#
#     with a:
#         r.next |= 1        # ← When `a` is `True`.
#         with d:
#             r2.next |= 2   # ← When `a` is `True` and `d` is `True`.
#         with pyrtl.otherwise:
#             r2.next |= 3   # ← When `a` is `True` and `d` is `False`.
#     with b == c:
#         r.next |= 0        # ← When `a` is `False` and `b == c`.
#
# Now let's build and test our state machine.
sim = pyrtl.Simulation()

# Rather than just give some random inputs, let's specify some specific 1-bit values. To
# make it easier to `Simulate` over several steps, we'll use `step_multiple()`, which
# takes in a `dict` mapping each `Input` to its value in each cycle.
sim_inputs = {"token_in": "0010100111010000", "req_refund": "1100010000000000"}
sim.step_multiple(sim_inputs)

# Also, to make our input/output easy to reason about let's specify an order to the
# traces with `trace_list`. We also use `enum_name` to display the state names (`WAIT`,
# `TOK1`, ...) rather than their numbers (0, 1, ...).
sim.tracer.render_trace(
    trace_list=["token_in", "req_refund", "state", "dispense", "refund"],
    repr_per_name={"state": pyrtl.enum_name(State)},
)

# Finally, suppose you want to simulate your design and verify its output matches your
# expectations. `step_multiple()` also accepts as a second argument a `dict` mapping
# output wires to their expected value in each cycle. If during the `Simulation` the
# actual and expected values differ, it will be reported to you! This might be useful if
# you have a working design which, after some tweaks, you'd like to test for functional
# equivalence, or as a basic sanity check.
expected_sim_outputs = {"dispense": "0000000000001000", "refund": "0111001000000000"}
sim = pyrtl.Simulation()
sim.step_multiple(sim_inputs, expected_sim_outputs)
