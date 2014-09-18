import pyrtl
from pyrtl import Input, Output, WireVector, Const, Register, concat

import numpy as np
import matplotlib.pyplot as plt


def main():
	
	#testBasicGates()
	#testmux()
	#plotop('^')
	#analyzeAdder(width=2)
	
	a, b, c = Input(1, 'a'), Input(1, 'b'), Input(1, 'c')
	a.tainted = True
	
	z1, z2 = Output(1, 'z1'), Output(1, 'z2')
	z1 <<= (a ^ b) ^ c
	z2 <<= a ^ (b ^ c)
	
	#s = a & b
	#a.tainted = [True, False]
	#s = concat(a,b)
	#x = concat(b,a)
	print pyrtl.working_block()
	mibound(pyrtl.working_block())
	#print s.MI
	for w in pyrtl.working_block().wirevector_subset():
		if type(w) != Const:
			print w, w.DIST0, w.DIST1, w.tainted, w.MI
    
def analyzeAdder(width=8):
	import sys
	sys.path.append("..")  # needed only if not installed
	import pyrtl
	from pyrtl import Const, Register, concat
	
	a, b, cin = Input(width, 'a'), Input(width, 'b'), Input(1, 'cin')
	#s, cout = Output(width, 's'), Output(1, 'cout')
	s, cout = add(a, b, cin=cin)
	
	cin.tainted = True
	#a[1].tainted = True
	mibound(pyrtl.working_block())
	#print [s in x.dests for x in pyrtl.working_block().logic]
	
	print 
	for gate in pyrtl.working_block().logic.copy():
		print gate, "d0={:.2f}, d1={:.2f}, MI={:.2f}".format(gate.dests[0].DIST0, gate.dests[0].DIST0, gate.dests[0].MI)
	#print pyrtl.working_block()
	#print s, s[0], s[1], s[2], s[3]
	#print len(s)
	#print "s[0] MI = {:f}".format(s[0].MI)
	print s, s.MI
	print cout, cout.MI
	
	
def plotop(op):
	
	stride = 5
	
	from mpl_toolkits.mplot3d import Axes3D
	
	a, b = Input(1, 'a'), Input(1, 'b')
	z = Output(1, 'z')
	if op == '&':
		z <<= a & b
	elif op == '|':
		z <<= a | b
	elif op == '^':
		z <<= a ^ b
	else:
		print "unsupported op"
		return
		
	a.tainted = True
	
	X = []
	Y = []
	Z = []
	
	for i in np.arange(0.,1.,.01):

		tz = []
		tx = []
		for j in np.arange(0.,1.,.01):

			a.DIST1 = i
			a.DIST0 = 1. - i
			b.DIST1 = j
			b.DIST0 = 1. - j
		
			mibound(pyrtl.working_block())
			tz.append(z.MI)
			tx.append(j)
		
		X.append(tx)
		Y.append([i]*len(tx))
		Z.append(tz)
		
	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')
	
	ax.plot_surface(X, Y, Z, rstride=stride, cstride=stride, alpha=0.6)
	from matplotlib import cm
	cset = ax.contour(X, Y, Z, zdir='z', offset=0, cmap=cm.coolwarm)
	cset = ax.contour(X, Y, Z, zdir='x', offset=0, cmap=cm.coolwarm)
	cset = ax.contour(X, Y, Z, zdir='y', offset=0, cmap=cm.coolwarm)

	ax.set_xlabel('a prob 1')
	#ax.set_xlim(-40, 40)
	ax.set_ylabel('b prob 1')
	#ax.set_ylim(-40, 40)
	ax.set_zlabel('MI(output, a)')
	#ax.set_zlim(-100, 100)
	fig.canvas.set_window_title("op:   {:s}".format(op))
	plt.show()
	
def testmux():

	a, b, s = Input(1, 'a'), Input(1, 'b'), Input(1, 's')
	out = Output(1, 'out')
	
	out <<= (a&(~s)) | (b&s)
	
	a.tainted = True
	
	dists = [(.5,0.), (.5,.5), (.5,1.)]
	
	for dist in dists:
		a.DIST0 = dist[0]
		a.DIST1 = 1.0 - dist[0]
		s.DIST0 = dist[1]
		s.DIST1 = 1.0 - dist[1]
		
		mibound(pyrtl.working_block())

		print "Input probabilites"
		print "\t0\t1"
		print "a\t{:.0f}%\t{:.0f}%".format(a.DIST0*100., a.DIST1*100.)
		print "b\t{:.0f}%\t{:.0f}%".format(b.DIST0*100., b.DIST1*100.)
		print "s\t{:.0f}%\t{:.0f}%".format(s.DIST0*100., s.DIST1*100.)

		D = {}
		for gate in pyrtl.working_block().logic.copy():
			if gate.op == None:
				D[gate.args[0]] = gate.dests[0] 


		for gate in pyrtl.working_block().logic.copy():
			print gate, gate.dests[0].DIST0, gate.dests[0].DIST1
			if gate.op:
				if gate.op == '~':
					print "op {:s} = ~{:s}: MI = {:.1f}".format(wiren(D.get(gate.dests[0],gate.dests[0])), wiren(gate.args[0]), gate.dests[0].MI)
				else:
					print "op {:s} = {:s}{:s}{:s}: MI = {:.1f}".format(wiren(D.get(gate.dests[0],gate.dests[0])), wiren(gate.args[0]), gate.op, wiren(gate.args[1]), gate.dests[0].MI)
					

def testBasicGates():

	a, b = Input(1, 'a'), Input(1, 'b')
	z1, z2, z3 = Output(1, 'z1'), Output(1, 'z2'), Output(1, 'z3')
	
	z1 <<= a & b
	z2 <<= a | b
	z3 <<= a ^ b
	
	a.tainted = True
	
	dists = [(.5,.0), (.5,.25), (.5,.5), (.5,.75), (.5,1.)]
	#dists = []
	#X, Y = [],[]
	#for i in np.arange(0.,1.,.01):
	#	dists.append((i,.5))
	#	X.append(i)
	
	
	for dist in dists:
		a.DIST0 = dist[0]
		a.DIST1 = 1.0 - dist[0]
		b.DIST0 = dist[1]
		b.DIST1 = 1.0 - dist[1]
		
		mibound(pyrtl.working_block())

		print "Input probabilites"
		print "\t0\t1"
		print "a\t{:.0f}%\t{:.0f}%".format(a.DIST0*100., a.DIST1*100.)
		print "b\t{:.0f}%\t{:.0f}%".format(b.DIST0*100., b.DIST1*100.)

		#print "Inputs probabilities: a - p0={:.0f}%, p1={:.0f}%, b - p0={:.0f}%, p1={:.0f}%".format(a.DIST0*100., a.DIST1*100., b.DIST0*100., b.DIST1*100.)

		D = {}
		for gate in pyrtl.working_block().logic.copy():
			if gate.op == None:
				D[gate.args[0]] = gate.dests[0] 


		for gate in pyrtl.working_block().logic.copy():
			if gate.op:
				print "op {:s} = {:s}{:s}{:s}: MI(out, a) = {:f}".format(wiren(D.get(gate.dests[0],gate.dests[0])), wiren(gate.args[0]), gate.op, wiren(gate.args[1]), gate.dests[0].MI)
				print gate.args[0], gate.args[0].DIST0, '/', gate.args[0].DIST1, gate.op, gate.args[1], gate.args[1].DIST0, '/', gate.args[1].DIST1, '---', gate.dests[0].DIST0, '/', gate.dests[0].DIST1
				#Y.append(gate.dests[0].MI)
	
	#plt.plot(X,Y)
	#plt.show()


def wiren(s):
	s = str(s)
	return s[s.find(':')+1:s.find('/')]

def testadder():

	a,b,c = Input(1,'a'), Input(1,'b'), Input(1,'c')
	sum, cout = Output(1,'sum'), Output(1,'cout')
	sum <<= a ^ b ^ c
	cout <<= a & b | a & c | b & c

	a.DIST0, a.DIST1 = .15, .15
	b.DIST0, b.DIST1 = .15, .15
	c.DIST0, c.DIST1 = .15, .15

	print mibound(pyrtl.working_block())

	for i in range(10):
		for x in (a,b,c):
			x.DIST0 = np.random.rand()
			x.DIST1 = np.random.rand()
		print mibound(pyrtl.working_block())

def mibound(block):
	
	# copy set of all gates to working set
	#toProcess = block.wirevector_subset().copy()
	#processed = set()
	
	# Check to make sure all inputs have distribution assigned
	I = block.wirevector_subset(Input)
	for w in I:
		if not hasattr(w,'DIST1'):
			if len(w) == 1:
				w.DIST1 = .5
			else:
				w.DIST1 = [.5] * len(w)
		if not hasattr(w,'DIST0'):
			if len(w) == 1:
				w.DIST0 = .5
			else:
				w.DIST0 = [.5] * len(w)
		if not hasattr(w,'tainted'):
			if len(w) == 1:
				w.tainted = False
			else:
				w.tainted = [False] * len(w)
		if len(w) == 1:
			w.MI = 1.
		else:
			w.MI = [1.] * len(w)
		#processed.add(w)

	# Assign distribution for all const wires
	C = block.wirevector_subset(Const)
	for w in C:
		w.DIST1 = float(w.val)
		w.DIST0 = 1. - w.DIST1
		
	#toProcess.difference_update(processed) # remove inputs from set
	gates = block.logic.copy() # work on copy of circuit

	while len(gates) != 0:
		
		#print toProcess
		#print [type(x) for x in toProcess]
		#print [x.args for x in toProcess]
		#print gates
		
		# iterate through all gates, processing ones that are ready
		doneG = set()
		for G in gates:
			ready = True
			for i in G.args:
				ready &= hasattr(i, 'DIST1') # ready if all inputs processed

			if ready:
				#print processGateVector(block, G)
				d0, d1, tainted = processGateVector(block, G) # pass through probs
				for D in G.dests: # assign probs on outputs
					D.DIST0 = d0
					D.DIST1 = d1
					D.tainted = tainted
					#processed.add(D) # gate is now processed
					#toProcess.remove(D) # remove from set of gates to do
				
				doneG.add(G) # this gate is done
				
				# compute MI across this gate
				gateMI(G)
				
		gates.difference_update(doneG) # remove from working block
		
	
	
	#return entropy(block.wirevector_subset(Output))

def gateMI(G):

	# First, handle wire-connection, select, concat, and NOT operations
	# (these do not affect MI, just how it is propogated through circuit)

	if G.op == None: 
		# Wires of same width are connected; pass through MI
		G.dests[0].MI = G.args[0].MI
		return
		
	if G.op == 's': 
		# selecting one wire; source should have list of MI vals
		inds = G.op_param
		
		if len(inds) == 1: # selecting a single wire, use scalar MI in dest
			G.dests[0].MI = G.args[0].MI[inds[0]]
			
		else: # selecting multiple wires, use list of MI vals in dest
			dMI = [0.] * len(inds)
			for di, si in enumerate(inds): # dest and source indices
				dMI[di] = (G.args[0].MI[si])
			G.dests[0].MI = dMI
			
		return

	if G.op == 'c': 
		# concatenating wires
		arg1, arg2 = G.args
		
		# first, turn single-wire MI vals into lists
		if len(arg1) == 1:
			arg1MI = [arg1.MI]
		else:
			arg1MI = arg1.MI
		if len(arg2) == 1:
			arg2MI = [arg2.MI]
		else:
			arg2MI = arg2.MI
		
		# create concatenated lists
		G.dests[0].MI = arg1MI + arg2MI
		
		return
		
	if G.op == '~':
		# inversion: pass through MI val
		G.dests[0].MI = G.args[0].MI
		return

	
	# Now, handle AND, OR, and XOR gates
	# Operands can be single wires or bundles

	A,B = G.args # get args
	Z = G.dests[0] # get dest
	op = G.op

	# each bit-line may have different probs/taintedness;
	#  handle each bit of the operation separately

	MI = [0.0] * len(Z)
	lists = []
	
	# for each attribute needed, if scalar, make it a length-1 list
	# lists = A.DIST0, A.DIST1, A.tainted, A.MI, B.DIST0, B.DIST1, B.tainted, B.MI
	for attr in (A.DIST0, A.DIST1, A.tainted, A.MI, B.DIST0, B.DIST1, B.tainted, B.MI):
		if type(attr) == list:
			lists.append(attr)
		else:
			lists.append([attr])
	
	for i, (A0,A1,At,Ami,B0,B1,Bt,Bmi) in enumerate(zip(*lists)):
		# iterate through arrays of the args and compute MI for each wire in bundle Z
		# a-prob0, a-prob1, a-tainted, a-MI, b-prob0, ..., b-MI

		if At and Bt:
			# if both inputs tainted, MI = H(z)
			# entropy() will return array of values; take just the val for bit i
			if len(Z) == 1:
				MI[i] = min(entropy(Z), Ami+Bmi)
			else:
				MI[i] = min(entropy(Z)[i], Ami+Bmi)
			continue

		if not(At) and not(Bt):
			# if neither matters, MI = 0
			MI[i] = 0.0
			continue

		if not(At) and Bt:
			# make sure a is the tainted wire
			# if not, swap to make a tainted and b untainted
			tmp = A0,A1,At,Ami
			A0,A1,At,Ami = B0,B1,Bt,Bmi
			B0,B1,Bt,Bmi = tmp
		
		# now, compute MI for each possible op

		mi = 0.0

		# get distribution for wire 'a' (tainted) that maximizes entropy
		if A0 >= .5 and A1 >= .5:
			a0, a1 = .5, .5
		elif A0 < .5: # 0's are limiting reagent
			a0, a1 = A0, 1. - A0
		else: # 1's are limiting reagent
			a0, a1 = 1. - A1, A1

		if op == '&':
			# Contributing states:
			# a z (b)
			# ---------
			# 0 0 (0,1)
			# 1 0 (0)
			# 1 1 (1)	
		
			# choose b distribution that maximizes MI of output with a
			b0, b1 = 1. - B1, B1
			# re-formulate output distribution based on new inputs
			z0 = min(a0 + b0, 1.0)
			z1 = min(a1, b1)
			z0,z1 = worstCaseCorr(a0,a1,z0,z1)
			
			#print a0,a1
			#print b0,b1
			#print z0,z1
			
			#mi += miterm(a.DIST0, z.DIST0, min(a.DIST0, b.DIST0) + min(a.DIST0, b.DIST1))
			mi += miterm(a0, z0, a0)
			mi += miterm(a1, z0, a1 * b0)
			mi += miterm(a1, z1, a1 * b1)
		
		elif op == '|':
			# Contributing states:
			# a z (b)
			# ---------
			# 0 0 (0)
			# 0 1 (1)
			# 1 1 (0,1)		
		
			# choose b distribution that maximizes MI of output with a
			b0, b1 = B0, 1. - B0
			# re-formulate output distribution based on new inputs
			z0 = min(a0, b0)
			z1 = min(a1 + b1, 1.0)
			z0,z1 = worstCaseCorr(a0,a1,z0,z1)
		
			mi += miterm(a0, z0, a0 * b0)
			mi += miterm(a0, z1, a0 * b1)
			#mi += miterm(a.DIST1, z.DIST1, min(a.DIST1, b.DIST0) + min(a.DIST1, b.DIST1))
			mi += miterm(a1, z1, a1)
	
		elif op == '^':
			# Contributing states:
			# a z (b)
			# ---------
			# 0 0 (0)
			# 0 1 (1)
			# 1 1 (0)
			# 1 0 (1)
		
			# choose b distribution that maximizes MI of output with a
			if B0 >= B1: 
				b0, b1 = B0, 1. - B0
			else:
				b0, b1 = 1. - B1, B1
			# re-formulate output distribution based on new inputs
			z0 = min( min(a0, b0) + min(a1, b1), 1.0)
			z1 = min( min(a0, b1) + min(a1, b0), 1.0)
			z0,z1 = worstCaseCorr(a0,a1,z0,z1)
		
			#print a0,a1
			#print b0,b1
			#print z0,z1
				
			mi += miterm(a0, z0, a0 * b0)
			mi += miterm(a0, z1, a0 * b1)
			mi += miterm(a1, z1, a1 * b0)
			mi += miterm(a1, z0, a1 * b1)
	
		MI[i] = min(mi, Ami) # limit flow of information
		
		#print G, "Ami={:.2f}, MaxMI={:.2f}, outMI={:.2f}".format(Ami, mi, MI[i])
		
	# if operation was actually length-1, store scalar instead of arrays
	if len(MI) == 1:
		Z.MI = MI[0]
	else:
		Z.MI = MI
		
	#print Z, G.op, G.args, Z.MI

def worstCaseCorr(a0, a1, z0, z1):
	if z0 >= a0 and z1 >= a1:
		return a0, a1
	if z0 < a0:
		return z0, 1.-z0
	else:
		return 1.-z1, z1

def miterm(px, py, pxy):
	#print px, py, pxy
	if pxy == 0:
		return 0.0
	#if pxy < (px*py):
		
	#if pxy * np.log2(pxy / (px * py)) < 0.0:
	#	print "negative term DINGDINGDING***********"
	#	print '\t',px, py, pxy
	return pxy * np.log2(pxy / (px * py))

def entropy(w):
	# calculate the entropy given a wire of arbitrary width
	
	if len(w) == 1: # length-1 wire, return a scalar entropy val
		H = 0.0
		p0, p1 = worstCaseProbs(w)
		for x in (p0, p1):
			H += -1.0 * x * np.log2(x)
	
	else: # else, return a list of entropy vals (per-wire)
		pvals = worstCaseProbs(w) # pvals is list of 2-tupls of (prob-0, prob-1)
		H = [ -1.0 * (p[0] * np.log2(p[0]) + p[1] * np.log2(p[1])) for p in pvals]
	
	return H

def worstCaseProbs(wire):
	# return the probabilities that maximize entropy on wire
	# wire can be arbitrary length; if ==1, return pair of vals;
	#  if > 1, return list of 2-tuples of vals
	
	if len(wire) == 1:
		d0 = [wire.DIST0]
		d1 = [wire.DIST1]
	else:
		d0 = wire.DIST0
		d1 = wire.DIST1
	vals = []
	
	for i in range(len(d0)): # for each wire in bundle
		if (d0[i] >= .5) and (d1[i] >= .5):
			vals.append((.5, .5))
		elif d0[i] < .5: # 0's are limiting factor
			vals.append((d0[i], 1.-d0[i]))
		else: # 1's are limiting factor
			vals.append((1.-d1[i], d1[i]))
			
	if len(vals) == 1: # if single wire, return scalars
		return vals[0]
	return vals
	
def processGateVector(block, G):
	# G can be a length-1 wire or a wire bundle
	# Return the worst-case prob-0 and prob-1 (or lists if len>1)
	#  and if the wire is tainted (boolean list if len>1)
	
	# Concat and select ops are handled separately, at the bundle level
	
	if G.op == None: # passing wire through
		return G.args[0].DIST0, G.args[0].DIST1, G.args[0].tainted
	
	if G.op == 's': # selecting one wire from a set; source should have list of vals
		inds = G.op_param
		if len(inds) == 1: # selecting a single wire, use scalar probs in dest
			d0 = G.args[0].DIST0[inds[0]]
			d1 = G.args[0].DIST1[inds[0]]
			tainted = G.args[0].tainted[inds[0]]
		else: # selecting multiple wires, use list of probs in dest
			d0 = [0.] * len(inds)
			d1 = [0.] * len(inds)
			tainted = [False] * len(inds)
			for di, si in enumerate(inds): # dest and source indices
				d0[di] = (G.args[0].DIST0[si])
				d1[di] = (G.args[0].DIST1[si])
				tainted[di] = G.args[0].tainted[si]
		return d0, d1, tainted
	
	elif G.op == 'c': # concatenating wires
		arg1, arg2 = G.args
		
		# first, turn single-wire vals into lists
		if len(arg1) == 1:
			arg1d0 = [arg1.DIST0]
			arg1d1 = [arg1.DIST1]
			arg1t = [arg1.tainted]
		else:
			arg1d0 = arg1.DIST0
			arg1d1 = arg1.DIST1
			arg1t = arg1.tainted
		if len(arg2) == 1:
			arg2d0 = [arg2.DIST0]
			arg2d1 = [arg2.DIST1]
			arg2t = [arg2.tainted]
		else:
			arg2d0 = arg2.DIST0
			arg2d1 = arg2.DIST1
			arg2t = arg2.tainted
		
		# create concatenated lists
		d0 = arg1d0 + arg2d0
		d1 = arg2d1 + arg2d1
		tainted = arg1t + arg2t
		
		return d0, d1, tainted

	# For all other ops, iterate through each bit of wire and perform op
	else: 
	
		L = len(G.dests[0])
		if L == 1: # if single-wires, return scalars
			#print G
			return processGate(G.args[0].DIST0, G.args[0].DIST1, \
							   G.args[1].DIST0, G.args[1].DIST1, G.op) + \
					(G.args[0].tainted | G.args[1].tainted,)

		# otherwise, build and return lists
		d0, d1, tainted = [0.]*L, [0.]*L, [False]*L
		for i in range(L):
			tainted[i] = G.args[0].tainted[i] | G.args[1].tainted[i]
			d0[i], d1[i] = processGate(G.args[0].DIST0[i], G.args[0].DIST1[i], G.args[1].DIST0[i], G.args[1].DIST1[i], G.op)

		return d0, d1, tainted

def processGate(a0, a1, b0, b1, op):
	# given input distributions for single-wires 'a' and 'b', and the op performed,
	#  return the worst-case distributions for the op output

	if op == '&':
		d0 = min(a0 + b0, 1.0)
		d1 = min(a1, b1)
		
	elif op == '|':
		d1 = min(a1 + b1, 1.0)
		d0 = min(a0, b0)
	
	elif op == '^':
		#d0 = min(max(a0 + b1, a1 + b0), 1.0)
		#d1 = min(max(a0 + b0, a1 + b1), 1.0)
		d0 = min(min(a0, b0) + min(a1, b1), 1.0)
		d1 = min(min(a0, b1) + min(a1, b0), 1.0)
	
	elif op == '~':
		d0 = a1
		d1 = a0
	
	elif op == None:
		d0 = a0
		d1 = a1
		
	else:
		raise pyrtl.PyrtlError('Cannot handle logic operation of type {:s}'.format(op))
		
	return d0, d1
	
# -------------------------------------------------------------------------------------
# This is code to recursively generate a RCA
# -------------------------------------------------------------------------------------

def one_bit_add(a, b, cin):
    """ Generates hardware for a 1-bit full adder. """
    assert len(a) == len(b) == len(cin) == 1
    sum = a ^ b ^ cin
    cout = a & b | a & cin | b & cin
    return sum, cout


def add(a, b, cin=Const(0)):
    """ Recursively generates hardware for ripple carry adder. """
    assert len(a) == len(b)
    if len(a) == 1:
        sumbits, cout = one_bit_add(a, b, cin)
    else:
        lsbit, ripplecarry = one_bit_add(a[0], b[0], cin)
        msbits, cout = add(a[1:], b[1:], ripplecarry)
        sumbits = concat(msbits, lsbit)
    return sumbits, cout
	
	

if __name__ == "__main__":
	main()

