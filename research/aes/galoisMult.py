def galoisMult(a, b):
	p = pyrtl.WireVector(8, 'p')
	hiBitSet = pyrtl.WireVector(8, 'hiBitSet')
	temp_1 = pyrtl.WireVector(8, 'temp_1')
	temp_2 = pyrtl.WireVector(8, 'temp_2')
	temp_1 <<= a
	temp_2 <<= b
	p <<= 0
	hiBitSet <<= 0
	for i in range(8):
		with pyrtl.ConditionalUpdate() as condition:
			with condition((temp_2 & 1) == 1):
				p <<= p ^ temp_1
		hiBitSet <<= temp_1 & 0x80
		temp_1 <<= temp_1 << 1
		with pyrtl.ConditionalUpdate() as condition:
			with condition(hiBitSet == 0x80):
				temp_1 <<= temp_1 ^ 0x1b
		temp_2 <<= temp_2 >> 1
	return p % 256
		
