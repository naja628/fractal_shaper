import numpy as np

### singleton closure thingy
# the point is to compute all the matrices once and for all
#
# note :
# not sure it's worth it but we need to keep track of the tuples anyway to get
# the names of the transforms right
def init_sgroup():
    # basic matrices
    id_ = np.array([[1, 0], [0, 1]])
    s = np.array([[-1 , 0], [0, 1]]) # vertical symetry
    r = np.array([[0, 1], [-1, 0]]) # trigo quarter-rotation. note : y goes down
    #
    sgroup_dict = {None : None}
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
            sgroup_dict[(i, j)] = (mat.copy(), str_of_sxry((i,j)))
    def get_it():
        return sgroup_dict
    return get_it

get_sgroup = init_sgroup()

# "interface" functions
def sgroup_valxy(x_y):
    if x_y == None:
        return None
    else :
        return get_sgroup()[x_y]

def sxry(x_y):
    val = sgroup_valxy(x_y)
    if val == None:
        return None
    else:
        return val[0]

def str_sxry(x_y):
    val = sgroup_valxy(x_y)
    if val == None:
        return None
    else:
        return val[1]

### math part

# util to iterate on "square" 2d lists
def iterij_sq(side, sq, f):
    for i in range(side):
        for j in range(side):
            f(i, j, sq[i][j])

# apply 'mat' to 'point' on a [0, grid_side[ * [0, grid_side[ coord system
# as if the transform was centered around the center of the grid (not [0, 0]).
#
# implementation note :
# do weird coordinate change to center properly 
# without needing floats, then apply transform.
# (twice as many points to handle odd and even)
def transform (mat, point, grid_side):
    # change origin
    u = point.copy()
    u *= 2
    left_corner = np.array([1 - grid_side, 1 - grid_side])
    u += left_corner
    # apply transform
    v = np.dot(mat, u)
    # change back
    v -= left_corner
    v //= 2
    return v.reshape((2))

# assume lattice is a "square" 2d list containing 2d transforms (as np.matrices)
# TODO too lazy to explain now
def make_fractalizer(shaper):
    shaper_side = len(shaper)
    def fractalize(grid_side, points):
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
    return fractalize

def n_steps(one_step, n):
    grid_side = 1
    points = [np.array([0,0])]
    for i in range(n):
        grid_side, points = one_step(grid_side, points)
    return grid_side, points

### graphics part

import pygame as pg

def draw_grid(win, grid_side, points, color = (0x00, 0xff, 0x80)):
    cell_s = win.get_width() // grid_side # assumes win is square
    # reset win
    win.fill((0x00, 0x00, 0x00))
    # draw cells
    for point in points:
        cell = pg.Rect(point[0] * cell_s, point[1] * cell_s, cell_s, cell_s)
        # maybe we don't need to create all the rectangles
        pg.draw.rect(win, color, cell)
    return

### control_panel

from pygame.locals import *

def panel_closures(keys, shaper, win, winpos):
    N = len(shaper) # should be same as len(keys)
    font = pg.font.SysFont(None, 24)
    cell_side = win.get_width() // N
    def draw_it():
        win.fill((0x00, 0x00, 0x00))
        def draw_cell(i, j, x_y):
            text = (x_y == None) and "___" or str_sxry(x_y)
            text = font.render(text, True, (0x00, 0xff, 0x00))
            win.blit(text, (cell_side * i, cell_side * j))
        iterij_sq(N, keys, draw_cell) 
    def update_it():
        # i, j <- which "button" (on the screen) was pressed
        for e in pg.event.get(MOUSEMOTION):
            pass
        wx, wy = winpos
        x, y = pg.mouse.get_pos()
        i, j = (x - wx) // cell_side, (y - wy) // cell_side
        changed = False
        if not ( 0 <= i < N and 0 <= j < N ):
            return False
        # update depending on mouse button
        for e in pg.event.get(MOUSEBUTTONDOWN):
            changed = True
            if (e.button == 1) and keys[i][j] != None :
                x, y = keys[i][j]
                keys[i][j] = (x + 1) % 2, y
            if (e.button == 2):
                keys[i][j] = (keys[i][j] is None) and (0,0) or None
            if (e.button == 3) and keys[i][j] != None:
                x, y = keys[i][j]
                keys[i][j] = x, (y + 1) % 4
            if changed:
                shaper[i][j] = sxry(keys[i][j])
        return changed
    return draw_it, update_it
         
### main

from math import log
def main(shaper_size):
    pg.init()
    # set layout
    fract_s = 700
    ctrl_s = 230
    win = pg.display.set_mode((fract_s + ctrl_s, fract_s))
    win.fill((0x00, 0x00, 0x00))
    fract_win = pg.Surface((fract_s, fract_s))
    ctrl_win = pg.Surface((ctrl_s, ctrl_s))
    def show_scr():
        win.blit(fract_win, (0, 0))
        win.blit(ctrl_win, (fract_s, 0))
        pg.display.update()
    #
    # keep track of the shaper used to draw the fractals
    # TODO fix same object
    keys = [[None for _ in range(shaper_size)] for _ in range(shaper_size)]
    shaper = [[None for _ in range(shaper_size)] for _ in range(shaper_size)]
    #
    # init a control_panel to interact with the shaper
    # show_panel displays the panel/shaper
    # update_shaper uses user mouse input to change the shaper
    show_panel, update_shaper = panel_closures(keys, shaper, ctrl_win, (fract_s, 0)) 
    #
    # main loop
    clock = pg.time.Clock()
    def draw_all():
        fractalize = make_fractalizer(shaper)
        num_steps = int(log(fract_s, len(shaper)))
        grid_s, points = n_steps(fractalize, num_steps)
        draw_grid(fract_win, grid_s, points, (0xff, 0x00, 0x40))
        show_panel()
        show_scr()
    draw_all()
    while True:
        clock.tick(60)
        if update_shaper(): # maybe pb with get_pressed
            draw_all()
        for e in pg.event.get(QUIT):
            print("quit")
            pg.quit()
            return
    return

import sys 
## TODO try catch block instead and check valid arg
shaper_size = 2
if len(sys.argv) != 2:
    print("Warning: shaper size not provided, defaulting to 2")
else:
    shaper_size = int(sys.argv[1])

main(shaper_size)
