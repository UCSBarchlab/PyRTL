import sys
sys.path.append("..")
import pyrtl
from pyrtl import *

"""
Test a simple state machine.
This vending machine will dispense an item when it has recieved 4 tokens.
If a refund is requested, it returns the tokens.
"""

''' ***Inputs/Outputs*** '''
token_in = Input(1, 'token_in')
req_refund = Input(1, 'req_refund')
dispense = Output(1, 'dispense')
refund = Output(1, 'refund')


''' ***Internal states*** '''
# state register
state = Register(3, 'state')

# enumerate states
WAIT, TOK1, TOK2, TOK3, DISPENSE, REFUND = [Const(x, bitwidth=3) for x in range(6)]


''' ***Handle state transitions*** '''
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


''' ***Assign outputs*** '''
dispense <<= state == DISPENSE
refund <<= state == REFUND


''' ***Simulation*** '''
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
