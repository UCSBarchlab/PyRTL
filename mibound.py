import pyrtl
from pyrtl import Input, Output, WireVector, Const, Register, concat

import numpy as np
import matplotlib.pyplot as plt


def main():
	
	#testBasicGates()
	
	a, b, s = Input(1, 'a'), Input(1, 'b'), Input(1, 's')
	out = Output(1, 'out')
	
	out <<= (a&(~s)) | (b&s)
	
	a.tainted = True
	
	dists = [(.25,0.), (.25,.5), (.25,1.)]
	
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
	
	dists = [(.5,0.), (.5,.5), (.5,1.)]
	
	for dist in dists:
		a.DIST0 = dist[0]
		a.DIST1 = 1.0 - dist[0]
		b.DIST0 = dist[1]
		b.DIST1 = 1.0 - dist[1]
		
		mibound(pyrtl.working_block())

		print "Inputs probabilities: a - p0={:.0f}%, p1={:.0f}%, b - p0={:.0f}%, p1={:.0f}%".format(a.DIST0*100., a.DIST1*100., b.DIST0*100., b.DIST1*100.)

		D = {}
		for gate in pyrtl.working_block().logic.copy():
			if gate.op == None:
				D[gate.args[0]] = gate.dests[0] 


		for gate in pyrtl.working_block().logic.copy():
			if gate.op:
				print "op {:s} = {:s}{:s}{:s}: MI(out, a) = {:.1f}".format(wiren(D.get(gate.dests[0],gate.dests[0])), wiren(gate.args[0]), gate.op, wiren(gate.args[1]), gate.dests[0].MI)
				#print gate.args[0], gate.args[0].DIST0, '/', gate.args[0].DIST1, gate.op, gate.args[1], gate.args[1].DIST0, '/', gate.args[1].DIST1, '---', gate.dests[0].MI

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
	toProcess = block.wirevector_subset().copy()
	processed = set()
	
	# Check to make sure all inputs have distribution assigned
	I = block.wirevector_subset(Input)
	for w in I:
		if not hasattr(w,'DIST1'):
			w.DIST1 = .5
		if not hasattr(w,'DIST0'):
			w.DIST0 = .5
		if not hasattr(w,'tainted'):
			w.tainted = False
		processed.add(w)

	toProcess.difference_update(processed) # remove inputs from set
	gates = block.logic.copy() # work on copy of circuit

	while len(toProcess) != 0:
		
		# iterate through all gates, processing ones that are ready
		doneG = set()
		for G in gates:
			ready = True
			for i in G.args:
				ready &= i in processed # ready if all inputs processed

			if ready:
			
				tainted = False
				for i in G.args:
					tainted |= i.tainted # if any input matters
					
				d0, d1 = processGate(block, G) # pass through probs
				for D in G.dests: # assign probs on outputs
					D.DIST0 = d0
					D.DIST1 = d1
					D.tainted = tainted
					processed.add(D) # gate is now processed
					toProcess.remove(D) # remove from set of gates to do
				
				doneG.add(G) # this gate is done
				
				# compute MI across this gate
				gateMI(G)
				
		gates.difference_update(doneG) # remove from working block
		
	
	
	#return entropy(block.wirevector_subset(Output))

def gateMI(G):

	if G.op == None:
		G.dests[0].MI = G.args[0].MI
		return

	if G.op == '~':
		if G.args[0].tainted:
			G.dests[0].MI = 1.0
		else:
			G.dests[0].MI = 0.0
		return

	a,b = G.args
	z = G.dests[0]

	if a.tainted and b.tainted:
		# if both inputs matter, MI = H(z)
		z.MI = entropy(z)
		return

	if not(a.tainted) and not(b.tainted):
		# if neither matters, MI = 0
		z.MI = 0.0
		return

	if not(a.tainted) and b.tainted:
		# make sure a is the tainted wire
		tmp = a
		a = b
		b = tmp
		
	# now, compute MI for each possible op

	mi = 0.0

	if G.op == '&':
		# Contributing states:
		# a z (b)
		# ---------
		# 0 0 (0,1)
		# 1 0 (0)
		# 1 1 (1)		
		#mi += miterm(a.DIST0, z.DIST0, min(a.DIST0, b.DIST0) + min(a.DIST0, b.DIST1))
		mi += miterm(a.DIST0, z.DIST0, min(a.DIST0, b.DIST0 + b.DIST1))
		mi += miterm(a.DIST1, z.DIST0, min(a.DIST1, b.DIST0))
		mi += miterm(a.DIST1, z.DIST1, min(a.DIST1, b.DIST1))
		
	elif G.op == '|':
		# Contributing states:
		# a z (b)
		# ---------
		# 0 0 (0)
		# 0 1 (1)
		# 1 1 (0,1)		
		mi += miterm(a.DIST0, z.DIST0, min(a.DIST0, b.DIST0))
		mi += miterm(a.DIST0, z.DIST1, min(a.DIST0, b.DIST1))
		#mi += miterm(a.DIST1, z.DIST1, min(a.DIST1, b.DIST0) + min(a.DIST1, b.DIST1))
		mi += miterm(a.DIST1, z.DIST1, min(a.DIST1, b.DIST0 + b.DIST1))
	
	elif G.op == '^':
		# Contributing states:
		# a z (b)
		# ---------
		# 0 0 (0)
		# 0 1 (1)
		# 1 1 (0)
		# 1 0 (1)		
		mi += miterm(a.DIST0, z.DIST0, min(a.DIST0, b.DIST0))
		mi += miterm(a.DIST0, z.DIST1, min(a.DIST0, b.DIST1))
		mi += miterm(a.DIST1, z.DIST1, min(a.DIST1, b.DIST0))
		mi += miterm(a.DIST1, z.DIST0, min(a.DIST1, b.DIST1))
	
	z.MI = mi

def miterm(px, py, pxy):
	if pxy == 0:
		return 0.0
	#if pxy < (px*py):
		
	#if pxy * np.log2(pxy / (px * py)) < 0.0:
	#	print "negative term DINGDINGDING***********"
	#	print '\t',px, py, pxy
	return pxy * np.log2(pxy / (px * py))

def entropy(*gates):
	# calculate the entropy given an arbitrary number of wires
	H = 0.0
	for g in gates:
		p0, p1 = worstCaseProbs(g)
		for x in (p0, p1):
			H += -1.0 * x * np.log2(x)
	
	for g in gates:
		print g, g.DIST0, g.DIST1
	
	return H

def worstCaseProbs(wire):
	if (wire.DIST0 > .5) and (wire.DIST1 > .5):
		return .5, .5
	p = min(wire.DIST0, wire.DIST1)
	return p, 1.0-p
	
def processGate(block, G):
	
	d0, d1 = 0.0, 0.0
	
	if G.op == '&':
		d0 = min(G.args[0].DIST0 + G.args[1].DIST0, 1.0)
		d1 = min(G.args[0].DIST1, G.args[1].DIST1)
		
	elif G.op == '|':
		d1 = min(G.args[0].DIST1 + G.args[1].DIST1, 1.0)
		d0 = min(G.args[0].DIST0, G.args[1].DIST0)
	
	elif G.op == '^':
		#d0 = min(max(G.args[0].DIST0 + G.args[1].DIST1, G.args[0].DIST1 + G.args[1].DIST0), 1.0)
		#d1 = min(max(G.args[0].DIST0 + G.args[1].DIST0, G.args[0].DIST1 + G.args[1].DIST1), 1.0)
		d0 = min(min(G.args[0].DIST0, G.args[1].DIST0) + min(G.args[0].DIST1, G.args[1].DIST1), 1.0)
		d1 = min(min(G.args[0].DIST0, G.args[1].DIST1) + min(G.args[0].DIST1, G.args[1].DIST0), 1.0)
	
	elif G.op == '~':
		d0 = G.args[0].DIST1
		d1 = G.args[0].DIST0
	
	elif G.op == None:
		d0 = G.args[0].DIST0
		d1 = G.args[0].DIST1
	
	else:
		raise pyrtl.PyrtlError('Cannot handle logic operation of type {:s}'.format(G.op))
		
	return d0, d1
	
if __name__ == "__main__":
	main()

