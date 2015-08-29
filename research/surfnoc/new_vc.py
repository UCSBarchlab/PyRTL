import pyrtl
#self
north_in = pyrtl.Input(9,'north_in')
south_in = pyrtl.Input(9,'south_in')
east_in = pyrtl.Input(9,'east_in')
west_in = pyrtl.Input(9,'west_in')
self_in = pyrtl.Input(9,'self_in')

#surf_sch - pyrtl.Input(1,'surf_sch')

grant_reg = pyrtl.Register(9,'grant_reg')
grant_next = pyrtl.Output(9,'grant_reg_net')
grant_reg_next = pyrtl.WireVector(9,'grant_reg_next')
with pyrtl.ConditionalUpdate() as condition:
    with condition(grant_reg[4:]==31):
        grant_reg_next |= north_in
    with condition(grant_reg[4:]==24):
        grant_reg_next |= south_in
    with condition(grant_reg[4:]==20):
        grant_reg_next |= east_in
    with condition(grant_reg[4:]==18):
        grant_reg_next |= west_in
    with condition(grant_reg[4:]==17):
        grant_reg_next |= self_in

grant_reg.next <<= grant_reg_next
grant_next <<= grant_reg_next
