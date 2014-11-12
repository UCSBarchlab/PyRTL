""" Example 4:  A State Machine built with ConditionalUpdate

    In this example we describe how ConditionalUpdate works in the context of
    a vending machine that will dispense an item when it has recieved 4 tokens.
    If a refund is requested, it returns the tokens.
"""

import sys
sys.path.append("..")

import pyrtl


def build_everything():
    """ A Function to build all the hardware in the system. """

    token_in = Input(1, 'token_in')
    req_refund = Input(1, 'req_refund')
    dispense = Output(1, 'dispense')
    refund = Output(1, 'refund')
    current_state = Register(3, 'current_state')

    # First new step, let's enumerate a set of constant to serve as our states
    WAIT, TOK1, TOK2, TOK3, DISPENSE, REFUND = [pyrtl.Const(x, bitwidth=3) for x in range(6)]

    # Now we could build a state machine using just the registers and logic discussed
    # in the earlier examples, but doing operations *conditional* on some input is a pretty
    # fundemental operation in hardware design.  PyRTL provides a class "ConditionalUpdate"
    # to provide a predicated update to a registers.  Any *register* update that happens under
    # a condition only happens when that condition is true.  In hardware this is implemented
    # with a simply mux -- for people coming from software it is important to remember that this
    # is describing a big logic function NOT an "if-then-else" clause.  All of these things will
    # execute straight through when "build_everything" is called.  More comments after the code.

    condition = ConditionalUpdate()
    with condition(req_refund):  # signal of highest precedence
        state.next <<= REFUND
    with condition(token_in):  # if token recieved, advance state in counter sequence
        with condition(state == WAIT):
            state.next <<= TOK1
        with condition(state == TOK1):
            state.next <<= TOK2
        with condition(state == TOK2):
            state.next <<= TOK3
        with condition(state == TOK3):
            state.next <<= DISPENSE  # 4th token recieved, go to dispense
        with condition():  # token recieved but in state where we can't handle it
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
    # blank (as seend on the line above "state.next <<= REFUND").  This condition will be true if
    # none of the other conditions at the same level were also true (for this example specifically
    # state.next will get REFUND when req_refund==0, token_in==1, and state is not in TOK1, TOK2,
    # TOK3, or DISPENSE.   Finally 5) not shown here, you can update multiple different registers
    # all under the same set of conditionals.

# Now let's build and test our state machine.

build_everything()
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)


def getGen(inputs):
    def f(vals):
        return {inp: val for inp, val in zip(inputs, vals)}
    return f


def parseTable(s):
    s = s.split('\n')
    names = []
    while names == []:
        names = s[0].strip().split()
        s = s[1:]

    wnames = pyrtl.working_block().wirevector_by_name
    ins = [wnames[n] for n in names]
    f = getGen(ins)

    def next():
        for line in s:
            vals = line.strip().split()
            if vals != []:
                yield f(map(int, vals))

    return next

testvals = '''
token_in req_refund
0 1
0 1
1 0
0 0
1 0
0 1
0 0
1 0
1 0
1 0
0 0
1 0
0 0
0 0
0 0
0 0
'''

f = parseTable(testvals)
for x in f():
    sim.step(x)

"""
vals = {  # dictionary of values to assign in each cycle
    0: {token_in: 0, req_refund: 1},
    1: {token_in: 0, req_refund: 1},
    2: {token_in: 1, req_refund: 0},
    3: {token_in: 0, req_refund: 0},
    4: {token_in: 1, req_refund: 0},
    5: {token_in: 0, req_refund: 1},
    6: {token_in: 0, req_refund: 0},
    7: {token_in: 1, req_refund: 0},
    8: {token_in: 1, req_refund: 0},
    9: {token_in: 1, req_refund: 0},
    10: {token_in: 0, req_refund: 0},
    11: {token_in: 1, req_refund: 0},
    12: {token_in: 0, req_refund: 0},
    13: {token_in: 0, req_refund: 0},
    14: {token_in: 0, req_refund: 0},
    15: {token_in: 0, req_refund: 0}
}

for i in range(len(vals)):
    sim.step(vals[i])
"""

sim_trace.render_trace()

# output the state machine in verilog
f = open('statemachine.v', 'w')
output_to_verilog(f)
f.close()

# output the testbench to verilog
f = open('statemachinetb.v', 'w')
output_verilog_testbench(f, pyrtl.working_block(), sim_trace)
f.close()
