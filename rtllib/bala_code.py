'''
Balakrishnan Vasudevan
'''
def xgcd(a,b):
	prevx, x = 1, 0
	prevy, y = 0, 1
	while b:
		q = a/b
		x, prevx = prevx - q*x, x
		y, prevy = prevy - q*y, y
		a, b = b, a % b				
	return prevx

def monpro(a,b,r,n):
	result = False
	x = xgcd(r,n)
	n1 = (1+(r*x))/n
	t = a*b
	m = (t*n1)%r
	u = (t+(m*n))/r
	if u>n:
		u = u-n
		result = True
		return u 
	else:
		return u
	

def monexp(g,a,r,p):
	l = len(bin(a))
	b = bin(a)
	c = 3
	m1 = (g*r)%p
	c1 = r%p
	e1 = monpro(c1,c1,r,p)
	e2 = monpro(e1,m1,r,p)

	for c in range (c,l):
		if '0' in b[c]:
			e1 = monpro(e2,e2,r,p)
		else:
			e1 = monpro(e1,e1,r,p)
			e1 = monpro(e1,m1,r,p)
			
	return e1	


		
	
print('100 randomly generated messages and their RSA keys in the format (message, RSA Key)')
import random
a = 127
r = 1024
p = 553
for num in range(1):
	g = random.randint(1000,10000)
	m1 = (g*r)%p
	exp1 = monexp(g,a,r,p)
	ans = monpro(exp1,m1,r,p)
	print (g, ans)


	


