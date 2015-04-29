import sys
sys.path.append("..")
import io
from pyrtl import *


def main():
    # test_simple_mult()
    # test_wallace_tree()
    # test_wallace_timing()
     test_modulus()
    # test_conditional()


def simple_mult(A, B, start, done):
    """Build a slow, small multiplier using the simple shift-and-add algorithm.
    Requires very small area (it uses only a single adder), but has long delay
    (worst case is len(a) cycles). a and b are arbitrary-length inputs; start
    is a one-bit input to indicate inputs are ready.done is a one-bit signal
    output raised when the multiplication is finished, at which point the
    product will be on the result line (returned by the function)."""
    alen = len(A)
    blen = len(B)
    areg = Register(alen)
    breg = Register(blen+alen)
    accum = Register(blen+alen)
    aiszero = areg == 0

    # Multiplication is finished when a becomes 0
    done <<= aiszero

    # During multiplication, shift a right every cycle, b left every cycle
    with ConditionalUpdate() as condition:
        with condition(start):  # initialization
            areg.next |= A
            breg.next |= B
            accum.next |= 0
        with condition(~aiszero):  # don't run when there's no work to do
            areg.next |= areg[1:]  # right shift
            breg.next |= concat(breg, "1'b0")  # left shift

            # "Multply" shifted breg by LSB of areg by conditionally adding
            with condition(areg[0]):
                accum.next |= accum + breg  # adds to accum only when LSB of areg is 1

    return accum



def conditional_broken(A, B, C):

    #not_zero_vector = Const(2**2, bitwidth=3)
    all_ones = Const(1, bitwidth=3)
    #zero_vector = WireVector(bitwidth=3)
    #output = WireVector(bitwidth=3)

    zero_vector = WireVector(bitwidth=3)
    zero_vector <<= 5

    zero_vector.name = "it_is_four"

    #with ConditionalUpdate(zero_vector[0] == 1):
    zero_vector <<= mux(zero_vector[0] == 1, zero_vector, zero_vector + all_ones)  

    zero_vector.name = "what is it"

    return zero_vector


def test_conditional():
    input_length = 4
    a, b, n = Input(input_length, "ignore"), Input(input_length, "ignore2"), Input(input_length, "ignore3")

    modded = Output(input_length*2, "ignore4")


    modded <<= conditional_broken(a, b, n)

    aval, bval, nval = 1, 2, 3


    sim_trace = SimulationTrace()
    sim = Simulation(tracer=sim_trace)
    sim.step({a: aval, b: bval, n: nval})

    sim_trace.render_trace()

def test_simple_mult():

    a, b, start = Input(8, "a"), Input(8, "b"), Input(1, "start")
    done, product = Output(1, "done"), Output(16, "product")

    product <<= simple_mult(a, b, start, done)

    aval, bval = 12, 19
    trueval = Output(16, "Answer")
    trueval <<= aval * bval

    sim_trace = SimulationTrace()
    sim = Simulation(tracer=sim_trace)
    sim.step({a: aval, b: bval, start: 1})
    for cycle in range(14):
        sim.step({a: 0, b: 0, start: 0})

    sim_trace.render_trace()


def wallace_tree(A, B):
    """Build an unclocked multiplier for inputs A and B using a Wallace Tree.
    Delay is order logN, while area is order N^2. It's very important to note that
    the delay is computed only for gates, and not for wires too, and the wire
    delay could be substantial.

    The Wallace Tree multiplier basically works by splitting the multiplication
    into a series of many additions, and it works by applying 'reductions'.
    These reductions take place in the form of full-adders (3 inputs),
    half-adders (2 inputs), or just passing a wire along (1 input).

    These reductions take place as long as there are more than 2 wire
    vectors left. When there are 2 wire vectors left, you simply run the
    2 wire vectors through a Kogge-Stone adder.
    """
    import adders

    bits_length = (len(A) + len(B))

    # create a list of lists, with slots for all the weights (bit-positions)
    bits = [[] for weight in range(bits_length)]

    # AND every bit of A with every bit of B (N^2 results) and store by "weight" (bit-position)
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            bits[i+j].append(a & b)

    # create a list of "deferred" values, which hold the reduced bits until
    # the end of the reduction
    deferred = [[] for weight in range(bits_length)]

    result = bits[0][0]  # Start with bit 0, we'll concatenate bits to the left

    while not all([len(i) <= 2 for i in bits]):  # While there's more than 2 wire vectors left

        for i in range(1, bits_length):  # Start with low weights and start reducing
            while len(bits[i]) >= 3:  # Reduce with Full Adders until < 3 wires
                a, b, cin = bits[i].pop(0), bits[i].pop(0), bits[i].pop(0)
                deferred[i].append(a ^ b ^ cin)  # deferred bit keeps this sum
                if(i + 1 < bits_length):  # watch out for index bounds
                    deferred[i+1].append((a & b) | (b & cin) | (a & cin))  # cout goes up by one

            if len(bits[i]) == 2:  # Reduce with a Half Adder if exactly 2 wires
                a, b = bits[i].pop(0), bits[i].pop(0)
                deferred[i].append(a ^ b)  # deferred bit keeps this sum
                if(i + 1 < bits_length):
                    deferred[i+1].append(a & b)  # cout goes up one weight

            if len(bits[i]) == 1:  # Remaining wire is passed along the reductions
                deferred[i].append(bits[i][0])  # deferred bit keeps this value

            if i >= bits_length - 1:  # If we're done reducing for this set
                bits = deferred  # Set bits equal to the deferred values
                deferred = [[] for weight in range(bits_length)]  # Reset deferred to empty

    # At this stage in the multiplication we have only 2 wire vectors left.

    num1 = []
    num2 = []
    # This humorous variable tells us when we have seen the start of the overlap
    # of the two wire vectors
    weve_seen_a_two = False

    for i in range(1, bits_length):

        if len(bits[i]) == 2:  # Check if the two wire vectors overlap yet
            weve_seen_a_two = True

        if not weve_seen_a_two:  # If they have not overlapped, add the 1's to result
            result = concat(bits[i][0], result)

        # For overlapping bits, create num1 and num2
        if weve_seen_a_two and len(bits[i]) == 2:
            num1.insert(0, bits[i][0])
            num2.insert(0, bits[i][1])

        # If there's 1 left it's part of num2
        if weve_seen_a_two and len(bits[i]) == 1 and i < bits_length - 1:
            num2.insert(0, bits[i][0])

    # Pass the wire vectors through a kogge_stone adder
    kogge_result = adders.kogge_stone(concat(*num1), concat(*num2))

    # Concatenate the results, and then return them.
    result = concat(kogge_result, result)

    # Perhaps here we should slice off the overflow bit, if it exceeds bit_length?
    # result = result[:-1]

    return result


def test_wallace_timing():
    x = 4
    a, b = Input(x, "a"), Input(x, "b")
    product = Output(2*x, "product")

    product <<= wallace_tree(a, b)

    timing_map = timing_analysis()

    print_max_length(timing_map)


def test_wallace_tree():

    input_length = 16
    a, b = Input(input_length, "a"), Input(input_length, "b")
    product = Output(2 * input_length, "Wallace Answer")

    product <<= wallace_tree(a, b)

    aval, bval = 20, 4
    trueval = Output(16, "True Answer")
    trueval <<= aval * bval

    sim_trace = SimulationTrace()
    sim = Simulation(tracer=sim_trace)
    sim.step({a: aval, b: bval})
    for cycle in range(14):
        sim.step({a: 0, b: 0})

    sim_trace.render_trace()


def another_montgomery_multiplier(A,B,N):
    
    assert len(A) == len(B) == len(N)
    k = len(A)

    P = WireVector(bitwidth = k)
    P <<= 0 


    for i in range(0, k):
        #temp <<= 0
        P = P + (A & B[i].sign_extended(k))
        #P.name = "p_after_addition" + str(i)

        #with ConditionalUpdate(P[0] == 1):
        #    P |= P + N 
        P = mux(P[0] == 1, falsecase = P, truecase = P + N)  
        #P.name = "p_after_modulus" + str(i)

        P = P[1:]
        #P.name = "p_after_division" + str(i)

    #with ConditionalUpdate(P > N):
    #    P = P - N
    P = mux(P >= N, falsecase = P, truecase = P - N)  
    
    P.name = "p_halfway"
    
    # round 2
    newP = WireVector(bitwidth = k)
    newP <<= 0

    r = Const(9, bitwidth = k)
    #r <<= 2**k #this is 16 -> do temp*16%13  = 12

    for i in range(0, k):
        newP = newP + (r & P[i].sign_extended(len(r)))

        newP.name = "p_afteraddition" + str(i)
        #with ConditionalUpdate(newP[0] == 1):
        #    newP |= newP + N
        newP = mux(newP[0] == 1, falsecase = newP, truecase = newP + N)  
        newP.name = "p_after_modulus" + str(i)

        newP = newP[1:]
        newP.name = "p_after_division" + str(i)

    #with ConditionalUpdate(newP > N):
    #    newP |= newP - N
    newP = mux(newP >= N, falsecase = newP, truecase = newP - N)  
    newP.name = "p_final"
    
    return newP
    
    #return P


def test_modulus():
    input_length = 4
    a, b, n = Input(input_length, "a"), Input(input_length, "b"), Input(input_length, "n")

    modded = Output(input_length*2, "Modulus")


    modded <<= another_montgomery_multiplier(a, b, n)
    # A B N  Magic 
    # 3 7 5  1
    # A Magic N => x
    # B Magic N => y
    # x * y N => z 
    # z Magic N => result
    aval, bval, nval = 4, 1, 5
    trueval = Output(16, "True Answer")
    trueval <<= (aval * bval) % nval

    sim_trace = SimulationTrace()
    sim = Simulation(tracer=sim_trace)
    sim.step({a: aval, b: bval, n: nval})

    sim_trace.render_trace()
if __name__ == "__main__":
    main()
