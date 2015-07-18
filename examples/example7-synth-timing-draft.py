import pyrtl

# Timing and area usage are key considerations of any hardware block that one
# makes. PyRTL provides functions to do this

#
pyrtl.reset_working_block()
constwire = pyrtl.Const(6, bitwidth=4)
inwire2 = pyrtl.Input(bitwidth=4, name="input2")
outwire = pyrtl.Output(bitwidth=5, name="output")

outwire <<= constwire + inwire2

timing_map = pyrtl.timing_analysis()
print "Pre Synthisis:"
pyrtl.print_max_length(timing_map)
print ""

block_max_time = pyrtl.timing_max_length(timing_map)
# tempxx = pyrtl.passes.timing_critical_path(timing_map)


#
# Synthesis
#

pyrtl.synthesize()
timing_map = pyrtl.timing_analysis()
print "Pre Optimization:"
pyrtl.print_max_length(timing_map)
print ""
for net in pyrtl.working_block().logic:
    print str(net)


#
# Optimization
#

# tempxx = pyrtl.passes.timing_critical_path(timing_map)

pyrtl.optimize()

timing_map = pyrtl.timing_analysis()
print "Post Optimization:"
pyrtl.print_max_length(timing_map)
print ""
for net in pyrtl.working_block().logic:
    print str(net)

block_max_time = pyrtl.passes.timing_max_length(timing_map)
tempxx = pyrtl.passes.timing_critical_path(timing_map)
