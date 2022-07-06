import numpy as np

### singleton closure thingy
# the point is to compute all the matrices once and for all
#
# note :
# not sure it's worth it but we need to keep track of the tuples anyway to get
# the names of the transforms right
def init_dgroup():
    '''
    builds the dihedral group D8 (symetries of the square) as a dictionary
    (int, int) -> (np.array, str) such that:
        dict[(x, y)][0] is the matrix of s ^ x * r ^ y
        dict[(x, y)][1] is a 3-length string representing its name (padded with '_')
        dict[None] is None
    convention : 
        the y axis points down
        s is the symetry through the y-axis
        r is an anticlockwise quarter-turn
    returns a closure 'f' such that f() is the dictionary
    '''
    # basic matrices
    id_ = np.array([[1, 0], [0, 1]])
    s = np.array([[-1 , 0], [0, 1]]) # vertical symetry
    r = np.array([[0, 1], [-1, 0]]) # trigo quarter-rotation. note : y goes down
    #
    dgroup_dict = {None : None}
    def str_of_sxry(x_y):
        x, y = x_y
        name = ""
        name += (x and 's' or '_')
        name += (y != 0 and 'r' or '_')
        name += (y > 1 and str(y) or '_')
        if (name == "___"):
            name = "_id"
        return name
    #
    for i in [0, 1]:
        [mat] = (i and [s] or [id_])
        for j in range(4):
            if j :
                mat = np.dot(mat, r)
            dgroup_dict[(i, j)] = (mat.copy(), str_of_sxry((i,j)))
    def get_it():
        return dgroup_dict
    return get_it

get_dgroup = init_dgroup()

# is this useless? 
def dgroup_valxy(x_y):
    if x_y is not None:
        x, y = x_y
        x_y = x % 2, y % 4
    return get_dgroup()[x_y]

# "interface" functions
def sxry(x_y):
    ''' 
    get matrix of s ^ x * r ^ y if x_y is (x, y)
    or None if x_y is None 
    '''
    val = dgroup_valxy(x_y)
    if val == None:
        return None
    else:
        return val[0]

def str_sxry(x_y):
    ''' 
    get 3-length name of s ^ x * r ^ y if x_y is (x, y)
    or None if x_y is None
    eg:
        str_sxry((0, 2)) = "_r2"
        str_sxry((1, 1)) = "sr_"
    '''
    val = dgroup_valxy(x_y)
    if val == None:
        return None
    else:
        return val[1]

### math part

def iterij_sq(side, sq, f):
    '''iterate f(i, j, x) on a 'side' x 'side' 2d list'''
    for i in range(side):
        for j in range(side):
            f(i, j, sq[i][j])

# implementation note :
# do weird coordinate change to center properly 
# without needing floats, then apply transform.
# (twice as many points to handle odd and even)
def transform (mat, point, grid_side):
    '''
    apply 'mat' to 'point' on a [0, grid_side[ * [0, grid_side[ coord system
    as if the transform was centered around the center of the grid (not [0, 0]).
    note: the original point is unchanged
    '''
    # change origin
    u = point.copy()
    u *= 2
    left_corner = np.array([1 - grid_side, 1 - grid_side])
    u += left_corner
    # apply transform
    u = np.dot(mat, u)
    # change back
    u -= left_corner
    u //= 2
    return u

def fractalize(shaper, n = 1, grid_side = 1, points = [np.array([0, 0])]):
    ''' 
    'shaper' is square list of transforms.
    'points' is a list of points in [0, grid_side[ * [0, grid_side[.
    Using shaper as a guide, make copies of set of points
    and place them "at the right place".
    Repeat this process n times.
    returns: (<new_grid_side>, <new_points>)
    '''
    shaper_side = len(shaper)
    def one_step (grid_side, points):
        new_points = []
        def add_transformed_points(i, j, mat):
            if mat is not None:
                for point in points:
                    new_point = transform(mat, point, grid_side)
                    new_point += np.array([i * grid_side, j * grid_side])
                    new_points.append(new_point)
        # do above fun for all transforms in shaper
        iterij_sq(shaper_side, shaper, add_transformed_points)
        return grid_side * shaper_side, new_points
    #
    for _ in range(n):
        grid_side, points = one_step(grid_side, points)
    return grid_side, points

### graphics part

import pygame as pg

def draw_grid(win, grid_side, points, color = (0x00, 0xff, 0x80)):
    ''' 
    'points' is a list of points in [0, grid_side[ * [0, grid_side[.
    Draw the points on 'win' (pygame surface) as squares.
    The size of the squares is the biggest possible integer (in pixels)
    such that everything will fit on 'win'.
    note :
        assumes 'win' is square
    '''
    cell_s = win.get_width() // grid_side # assumes win is square
    # draw cells
    cell = pg.Surface((cell_s, cell_s))
    cell.fill(color)
    for point in points:
        win.blit(cell, (point[0] * cell_s, point[1] * cell_s))
    return

### control_panel

from pygame.locals import *

# use closure returning function as lightweight "class"
def panel_closures(keys, shaper, win, winpos):
    ''' 
    create a control panel for interacting with/changing a shaper.
    returns 2 "interface" functions/closures.
        first one draws the panel (doesn't update display).
        second one polls mouse events and updates accordingly.
    '''
    N = len(shaper) # should be same as len(keys)
    font = pg.font.SysFont(None, 24)
    cell_side = win.get_width() // N
    #
    def draw_it():
        def draw_cell(i, j, x_y):
            text = (x_y == None) and "___" or str_sxry(x_y)
            text = font.render(text, True, (0x00, 0xff, 0x00))
            win.blit(text, (cell_side * i, cell_side * j))
        iterij_sq(N, keys, draw_cell) 
    #
    def get_clicks():
        # allow mouse position to be updated
        for e in pg.event.get(MOUSEMOTION):
            pass
        # i, j <- which "button" (on the screen) was pressed
        (wx, wy), (x, y) = winpos, pg.mouse.get_pos()
        i, j = (x - wx) // cell_side, (y - wy) // cell_side
        #
        changed = False # do we need to update the shaper?
        if not ( 0 <= i < N and 0 <= j < N ):
            return False
        # update depending on mouse button
        for e in pg.event.get(MOUSEBUTTONDOWN):
            changed = True
            if (e.button == 2):
                keys[i][j] = (keys[i][j] is None) and (0,0) or None
            if (e.button == 1) and keys[i][j] != None :
                x, y = keys[i][j]
                keys[i][j] = (x + 1) % 2, y
            if (e.button == 3) and keys[i][j] != None:
                x, y = keys[i][j]
                keys[i][j] = x, (y + 1) % 4
            #
            if changed:
                shaper[i][j] = sxry(keys[i][j])
        return changed
    return draw_it, get_clicks
         
### main

# maybe should be only if module is __main__

## "Config". all 3 values need to be defined for 'main' to work
win_height = 700 # program may feel sluggish if this too big
fractal_color = (0x00, 0xff, 0x80) # bluish green
background = (0x00, 0x00, 0x00) # black

from math import log
def main(shaper_size):
    pg.init()
    # set layout
    fract_s = win_height # size of fractal window
    ctrl_s = win_height // 3
    win = pg.display.set_mode((fract_s + ctrl_s, fract_s))
    win.fill(background)
    fract_win = pg.Surface((fract_s, fract_s))
    ctrl_win = pg.Surface((ctrl_s, ctrl_s))
    def reset_scr(background = (0x00, 0x00, 0x00)):
        fract_win.fill(background)
        ctrl_win.fill(background)
    #
    def show_scr():
        win.blit(fract_win, (0, 0))
        win.blit(ctrl_win, (fract_s, 0))
        pg.display.update()
    #
    # keep track of the shaper used to draw the fractals
    keys = [[None for _ in range(shaper_size)] for _ in range(shaper_size)]
    shaper = [[None for _ in range(shaper_size)] for _ in range(shaper_size)]
    #
    # init a control_panel to interact with the shaper
    # draw_panel displays the panel/shaper (needs display update)
    # get_clicks uses user mouse input to change the shaper
    draw_panel, get_clicks = panel_closures(keys, shaper, ctrl_win, (fract_s, 0)) 
    #
    # main loop
    clock = pg.time.Clock()
    def draw_all():
        reset_scr(background)
        num_steps = int(log(fract_s, len(shaper)))
        grid_s, points = fractalize(shaper, num_steps)
        draw_grid(fract_win, grid_s, points, fractal_color)
        draw_panel()
        show_scr()
    #
    draw_all()
    while True:
        clock.tick(60)
        if get_clicks(): # maybe pb with get_pressed
            draw_all()
        for e in pg.event.get(QUIT):
            print("quit")
            pg.quit()
            return
        #pg.event.get() # maybe we should flush the event queue?
    return

import sys 
## TODO try-catch block instead and check valid arg
shaper_size = 2
if len(sys.argv) != 2:
    print("Warning: shaper size not provided, defaulting to 2")
else:
    shaper_size = int(sys.argv[1])
main(shaper_size)
