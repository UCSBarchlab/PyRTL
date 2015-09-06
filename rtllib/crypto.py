""" Alpha-stage implementations of montgomery multiplier, modular exponentiation, and
RSA encrypt/decrypt.  These have not been tested extensively and so please do not
assume they are correct.  In addition, the current implemtnations are completely
combintational and will blow up to be gigantic circuits very quickly.  Work is needed
to make these iterative rather than strictly combinational.
"""

import io
from pyrtl import *


# ------------------------------------------------------------------------------------------------
#        __       ___  __   __         ___  __                         ___    __          ___  __
#  |\/| /  \ |\ |  |  / _` /  \  |\/| |__  |__) \ /     |\/| |  | |     |  | |__) |    | |__  |__)
#  |  | \__/ | \|  |  \__> \__/  |  | |___ |  \  |      |  | \__/ |___  |  | |    |___ | |___ |  \


""" Here is our current understanding of the full montgomery multiplier process.

We would like c = a * b mod n to happen, but to do so we need to
go into the montgomery domain, where modulus is really easy.

Modulus is an expensive operation normally (1251258 % 17) by modulus the way you
normally think about modulus would require trial division, and using the remainder you get.
That's too slow. We want it to be faster.

First we define some variables
k = # of bits in a, b, and n
R = 2^k
R_inverse = modinv(R, n)

So basically there are 5 steps.

1) Get the value of precomputed_value -
We need this value to figure out the a and b residues.

precomputed_value = R^2 mod n (this requires a modulus unit)

2) Get the a residue:

a_residue = a * precomputed_value mod n

3) Get the b residue:

b_residue = b * precomputed_value mod n

4) Get the c residue:

c_residue = a_residue * b_residue mod n

5) Get the c real value, converted back from the residue value (transform back from
montgomery domain)

c = c_residue * 1 mod n

There's a lot of dense mathematics that's going on here.

Step 1 is basically precomputing the value of R^2 mod n so that we can
figure out the a_residue and b_residue values, which are the values in Montgomerys domain.
These values allow for us to do multiplication and modulus very quickly because
they only require 4 operations: addition, bitwise and, modulus by 2, and shift.

Step 2 and 3 give us the a and b residues.

Step 4 gives us the c residue, which is just the montgomery product of the a and b residues.

Step 5 is the transformation step that converts the c_residue back into the normal domain.
This works by multiplying c_residue * 1 and results in C.

The interesting thing is that in every montgomery product operation, there is an implicit
multiplication by R_inverse. This implicit multiplication happens because in the montgomery
product we shift k times.

A shift by k = dividing by k = dividing by R = multiplying by R_inverse

So that explains why in the beginning we multiply by the precomputed_value because
R^2 mod n * R_inverse is just R

TODO: We should really change this to a Register based model. We didn't have time
to actualize it, but that could be a fun project for a new PyRTL'er!

Your quest: You will have to change the mod_product function into a register based model.
The montgomery_mult function likely will need to be changed into a state machine that will
reflect this new register based model.

Likely what it will look like is that the montgomery_mult function will have a series of
conditional statements that wait for the mod_product circuits to finish computing their
results (in parallel for a_residue and b_residue which is cool!).

Then you will have another conditional statement that waits for the c_residue to finish, and
it will get passed through one more circuit and then passed back to whatever function called
montgomery_mult
"""


def montgomery_mult(a, b, n, nval):
    """ Computue a * b mod n via Montgomery's Algorithm. """
    input_length = len(a)
    precomputed_value = Const(2**(input_length * 2) % nval, bitwidth=input_length)

    its_a_one = Const(1, bitwidth=input_length)

    a_residue = WireVector(bitwidth=input_length)
    b_residue = WireVector(bitwidth=input_length)
    c_residue = WireVector(bitwidth=input_length)

    a_residue <<= mod_product(a, precomputed_value, n, input_length)
    b_residue <<= mod_product(b, precomputed_value, n, input_length)
    c_residue <<= mod_product(a_residue, b_residue, n, input_length)
    return mod_product(c_residue, its_a_one, n, input_length)


""" The mod_product function is where the actual "montgomery multiplication" happens.

What we want to happen:

return A * B mod N

It takes the following arguments
A: The multiplicand
B: The multiplier
N: The modulus value
k: The number of bits in A, B, and N (input_length from previous function)

The way that mod_product works is a lot of dense math.

Sources:
http://alicebob.cryptoland.net/understanding-the-montgomery-reduction-algorithm/
http://www.powershow.com/view/11a7e5-YTBmM/AreaTimeEfficient_Montgomery_Modular_Multiplication_powerpoint_ppt_presentation

TODO: Change this to the register based model!!

This function should store P as an intermediate value in a register, instead of chaining
hardware units together, which is what we currently do. What we do is INCREDIBLY stupid
and I'm truly ashamed that I have to commit it, but I just didn't have time to
implement the register model. So you get to :)


Here is our attempt at switching it to the register based model, that didn't work.
You'll probably need to have a "done" boolean register value as well, which you will
check from the montgomery_mult function. This done register will notify the montgomery_mult
function and say that the mod_product function has completed.


CHANGE P INTO A REGISTER - store P at each stage of the for loop,
    instead of adding it to the circuit

    p_reg = Register(k, 'i')
    i = Register(k, 'i')
    local_k = Register(k, 'local_k')

    n_reg = Register(len(N), 'n')
    a_reg = Register(len(A), 'a')
    b_reg = Register(len(B), 'b')

    temp_reg1 = Register(k, 'temp_reg1')
    temp_reg2 = Register(k, 'temp_reg2')
    temp_reg3 = Register(k, 'temp_reg3')

    with pyrtl.ConditionalUpdate() as condition:

        with condition(i == 0):
            i.next |= 1
            temp_reg1 |= 0
            temp_reg2 |= 0
            temp_reg3 |= 0
            p_reg |= 0
            local_k |= k - 1

        with condition.fallthrough:
            i.next |= i + 1
            temp_reg1.next |= p_reg + (A & B[i]].sign_extended(k))
            temp_reg2.next |= mux(P[0] == 1, falsecase = temp_reg1, truecase = temp_reg1 + N)
            temp_reg3.next |= temp_reg2[1:]
            p_reg.next |= temp_reg3

"""


def mod_product(A, B, N, k):

    P = WireVector(bitwidth=k)
    P <<= 0

    for i in range(0, k):
        P = P + (A & B[i].sign_extended(k))
        P = mux(P[0] == 1, falsecase=P, truecase=P + N)
        P = P[1:]

    P = P[:k]

    P = mux(P >= N, falsecase=P, truecase=P - N)

    return P


# ----------------------------------------------------------------------------------
#         __   __                  __      ___      __
#   |\/| /  \ |  \ |  | |     /\  |__)    |__  \_/ |__)
#   |  | \__/ |__/ \__/ |___ /~~\ |  \    |___ / \ |

""" Modular Exponentiation is the key to RSA encryption and decrpyption. Modular Exponentiation
directly relies on Montgomery Multiplication, so if you haven't read that SCROLL UP RIGHT NOW.

The way that mod_exp works is that it takes in 4 arguments.
m: The number we are exponentiating.
e: The exponent value.
n: The WireVector that we are modding by.
nval: The value we are modding by, that goes into n.

TODO: The for loop here must be replaced with a Register based model!!!
Replace c2 with a register, and

Source (from Professor Koc himself!) : http://cryptocode.net/docs/r02.pdf
"""


def mod_exp(m, e, n, nval):
    input_length = len(m)

    its_a_one = Const(1, bitwidth=input_length)

    exp = Const(e, bitwidth=e.bit_length())

    h = len(exp)
    c = WireVector(bitwidth=12)

    c <<= mux(exp[h-1] == 1, falsecase=its_a_one, truecase=m)

    c2 = WireVector(bitwidth=12)
    c2 <<= c

    for i in range(h-2, -1, -1):
        c2 = c
        c = montgomery_mult(c, c2, n, nval)
        c = mux(exp[i] == 1, falsecase=c, truecase=montgomery_mult(c, m, n, nval))
    return c


# ----------------------------------------------------------------------------------
#  __   __           ___       __   __       __  ___    __
# |__) /__`  /\     |__  |\ | /  ` |__) \ / |__)  |  | /  \ |\ |
# |  \ .__/ /~~\    |___ | \| \__, |  \  |  |     |  | \__/ | \|

""" These are the RSA encrpytion and decryption functions.

So RSA encryption is a public-key cryptosystem that uses the parameters:
p: distinct large prime
q: distinct large prime
n: p * q
e: public exponent in the range of 1 < e < Phi(n)

Phi(n) = (p - 1) * (q - 1)    # This is also known as Euler's Totient

d: private exponent obtained by doing the inverse modulus of n. use our modinv() function for this

Given these parameters, the encryption and decryption is actually very simple.

C = M ** e (mod n)
M = C ** d (mod n)

where C is the encrypted text, and M is the original message.

For the sake of our "machine" you can extend the rsa function so that it can take in custom p and q
and of course custome messages as well. But for now, they are just hard coded (They should be
put in registers at the very least).

TODO: Make this work for 128 bit and 256 bit encrpytion. Currently we didn't handle this, because
we got errors involving Long types for pyrtl. Hopefully that will be fixed!

You might notice that rsa_encrypt and rsa_decrypt are the EXACT same code.
We decided to implement the coding strategy called DRY (do repeat yourself)

Just kidding. You can clean this up if you want. I just kept it as two separate
functions so that it's clear what is happening.
"""


def rsa_encrypt(e, m):
    p = 5
    q = 7
    n = Const(35, bitwidth=12)

    nval = p * q

    c = mod_exp(m, e, n, nval)

    return c


def rsa_decrypt(d, m):
    p = 5
    q = 7
    n = Const(35, bitwidth=12)

    nval = p * q

    c = mod_exp(m, d, n, nval)

    return c


# ----------------------------------------------------------------
#  ___  ___  __  ___         __
#   |  |__  /__`  |  | |\ | / _`
#   |  |___ .__/  |  | | \| \__>

def test_montgomery_mult():
    input_length = 6
    a, b, n = Input(input_length, "a"), Input(input_length, "b"), Input(input_length, "n")

    c = Output(input_length * 2, "Montgomery result")

    aval, bval, nval = 5, 9, 7

    c <<= montgomery_mult(a, b, n, nval)

    trueval = Output(16, "True Answer")
    trueval <<= (aval * bval) % nval

    sim_trace = SimulationTrace()
    sim = Simulation(tracer=sim_trace)
    sim.step({a: aval, b: bval, n: nval})

    sim_trace.render_trace()
    output = sim_trace.trace
    print("Result in Decimal: " + str(output[c]))


def test_mod_exp():
    input_length = 6
    a, n = Input(input_length, "a"), Input(input_length, "n")
    aval, expval, nval = 3, 5, 7

    c = Output(input_length * expval, "Montgomery result")

    c <<= mod_exp(a, expval, n, nval)

    trueval = Output(16, "True Answer")
    trueval <<= (aval ** expval) % nval

    sim_trace = SimulationTrace()
    sim = Simulation(tracer=sim_trace)
    sim.step({a: aval, n: nval})

    sim_trace.render_trace()
    output = sim_trace.trace
    print("Result in Decimal: " + str(output[c]))


def test_rsa():
    input_length = 6
    m = Input(input_length, "message")
    mval = 10

    c = WireVector(input_length * 2, "Rsa encrypted")

    message_after = Output(input_length * 2, "Rsa decrypted")

    c <<= rsa_encrypt(7, m)

    message_after <<= rsa_decrypt(7, c)

    trueval = Output(16, "True Answer")
    trueval <<= mval

    sim_trace = SimulationTrace()
    sim = Simulation(tracer=sim_trace)
    sim.step({m: mval})

    sim_trace.render_trace()
    output = sim_trace.trace
    print("Result in Decimal: " + str(output[c]))


# These functions were used to help debug the Montgomery Multiplier, and are likely
# useful to keep around, as they relate to the mathematics behind RSA encryption.

def _rsa(p, q, M):
    n = p * q
    totient = (p - 1) * (q - 1)
    print("n,totient: ", n, " ,", totient)
    e = 5
    print("e: ", e)
    d = _modinv(e, totient)
    print("d :", d)
    C = pow(M, e, n)
    print("c: ", C)
    return pow(C, d, n)


def _extended_gcd(aa, bb):
    lastremainder, remainder = abs(aa), abs(bb)
    x, lastx, y, lasty = 0, 1, 1, 0
    while remainder:
        lastremainder, (quotient, remainder) = remainder, divmod(lastremainder, remainder)
        x, lastx = lastx - quotient*x, x
        y, lasty = lasty - quotient*y, y
    return lastremainder, lastx * (-1 if aa < 0 else 1), lasty * (-1 if bb < 0 else 1)


def _modinv(a, m):
    g, x, y = _extended_gcd(a, m)
    if g != 1:
        raise ValueError
    return x % m


def main():
    test_rsa()


if __name__ == "__main__":
    main()
