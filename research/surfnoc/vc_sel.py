import pyrtl

go_x_n = pyrtl.Input(9,'go_x_n')
go_y_n = pyrtl.Input(9,'go_y_n')
go_x_s = pyrtl.Input(9,'go_x_s')
go_y_s = pyrtl.Input(9,'go_y_s')
go_x_e = pyrtl.Input(9,'go_x_e')
go_y_e = pyrtl.Input(9,'go_y_e')
go_x_w = pyrtl.Input(9,'go_x_w')
go_y_w = pyrtl.Input(9,'go_y_w')
go_x_l = pyrtl.Input(9,'go_x_l')
go_y_l = pyrtl.Input(9,'go_y_l')

north_out = pyrtl.Output(9,'north_out')
south_out = pyrtl.Output(9,'south_out')
east_out  = pyrtl.Output(9,'east_out')
west_out  = pyrtl.Output(9,'west_out')
local_out = pyrtl.Output(9,'local_out')

north_out = pyrtl.mux(go_x_n[8],truecase=go_x_n,falsecase=go_y_n)
south_out = pyrtl.mux(go_x_s[8],truecase=go_x_s,falsecase=go_y_s)
east_out  = pyrtl.mux(go_x_e[8],truecase=go_x_e,falsecase=go_y_e)
west_out  = pyrtl.mux(go_x_w[8],truecase=go_x_w,falsecase=go_y_w)
local_out = pyrtl.mux(go_x_l[8],truecase=go_x_l,falsecase=go_y_l)


