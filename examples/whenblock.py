from pyrtl import *

a,b,c = [Input(1, signame) for signame in ['a', 'b', 'c']]
x,y = [Output(1, signame) for signame in ['x', 'y']]
r = Register(1, 'r')

#u = ConditionalUpdate()
#with u.when(a):
#    r.next = b
#with u.otherwise():
#    r.next = c
r.next = a
x <<= r
y <<= r
