import random
import sys
sys.path.append("../..")
import pyrtl

def place_and_route(block=None):
    import numpy as np
    block = pyrtl.working_block(block)

    # extract connection graph
    connection_graph = {
        1: [9, 7, 8],
        3: [4, 18],
        6: [2, 10],
        12: [13, 16],
        15: [17, 5],
        }

    def between(a, b):
        return range(min(a,b), max(a,b)+1)
    def cordinate_of_terminal(number):
        assert number < starting_x_size * starting_y_size
        macro_x = number % starting_x_size 
        macro_y = number / starting_x_size
        x = macro_x * starting_y_size + macro_y
        y = macro_y * starting_x_size + macro_x
        return (y, x)
    def identical_rows(arr, row1, row2):
        return (arr[row1,:] == arr[row2,:]).all()
    def non_overlapping_rows(arr, row1, row2):
        return (arr[row1,:] == arr[row2,:]).all()

    def col_safe_to_eliminate(c):
        return False
    def eliminate_col(c):
        pass
    def row_safe_to_eliminate(r):
        # do the checks to see if it is safe to eliminate this row
        # e.g. if (~vert[r,:] & vert[r-1,:] & vert[r+1,:]).any():
        return False
    def eliminate_row(r):
        # need to actually do the compression here
        # h, v, t, i = [np.delete(a, r, 0) for a in [horiz, vert, terminal, via]]
        # return h, v, t, i
        return horiz, vert, terminal, via

    starting_y_size, starting_x_size = 5, 5
    initial_die_size = (starting_x_size * starting_y_size, starting_y_size * starting_x_size)
    horiz, vert, terminal, via = [np.zeros(initial_die_size, dtype=bool) for _ in range(4)]

    for (_from, tolist) in connection_graph.iteritems():
        for _to in tolist:
            (from_y, from_x) = cordinate_of_terminal(_from)
            (to_y, to_x) = cordinate_of_terminal(_to)
            terminal[from_y, from_x] = 1
            terminal[to_y, to_x] = 1
            for x in between(from_x, to_x):
                horiz[from_y, x] = 1
            for y in between(from_y, to_y):
                vert[y, to_x] = 1
            via[from_y, to_x] = 1

    # compress
    for i in range(0):
        current_y_size, current_x_size = terminal.shape
        c = random.randrange(1, current_x_size-1)
        if col_safe_to_eliminate(c):
            horiz, vert, terminal, via = eliminate_col(c)
        r = random.randrange(1, current_y_size-1)
        if row_safe_to_eliminate(r):
            horiz, vert, terminal, via = eliminate_row(r)

    print connection_graph
    final_y_size, final_x_size = terminal.shape
    print terminal.shape
    for y in range(final_y_size):
        for x in range(final_x_size):
            if terminal[y,x]:
                sys.stdout.write( '* ' )
            elif via[y,x]:
                #sys.stdout.write('x')
                if horiz[y, x+1]:
                    sys.stdout.write( unichr(0x2588) + unichr(0x2500) )
                else:
                    sys.stdout.write( unichr(0x2588) + ' ' )
            elif horiz[y, x] and vert[y, x]:
                #sys.stdout.write('+-')
                sys.stdout.write( unichr(0x253C) + unichr(0x2500) )
            elif horiz[y, x]:
                #sys.stdout.write('--')
                sys.stdout.write( unichr(0x2500) * 2 )
            elif vert[y, x]:
                #sys.stdout.write('| ')
                sys.stdout.write( unichr(0x2502) + ' ')
            else:
                sys.stdout.write('. ')
        print
            

place_and_route()
