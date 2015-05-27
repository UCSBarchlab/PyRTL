def rsa(p,q,M):
    n = p*q
    totient = (p-1)*(q-1)
    print "n,totient: ",n," ,",totient
    e = 175
    print "e: ",e
    d = modinv(e,totient)
    print "d :", d
    C = pow(M,e,n)
    print "c: ", C
    return pow(C,d,n)

def extended_gcd(aa, bb):
    lastremainder, remainder = abs(aa), abs(bb)
    x, lastx, y, lasty = 0, 1, 1, 0
    while remainder:
        lastremainder, (quotient, remainder) = remainder, divmod(lastremainder, remainder)
        x, lastx = lastx - quotient*x, x
        y, lasty = lasty - quotient*y, y
    return lastremainder, lastx * (-1 if aa < 0 else 1), lasty * (-1 if bb < 0 else 1)
 
def modinv(a, m):
    g, x, y = extended_gcd(a, m)
    if g != 1:
        raise ValueError
    return x % m

print "RSA: ", rsa(13,17,22)