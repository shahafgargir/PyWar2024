import random

import common_types

OUR_TILE = 0
UNCLAIMED_TILE = 1
ENEMY_TILE = 2

builder_built_builder = {}

def mass_center_of_our_territory(strategic):
    our_tiles = []
    x_sum = 0
    y_sum = 0

    for x in range(strategic.get_game_width()):
        for y in range(strategic.get_game_height()):
            coordinate = common_types.Coordinates(x, y)
            danger = strategic.estimate_tile_danger(coordinate)
            if danger == OUR_TILE:
                x_sum += 1
                y_sum += 1
                our_tiles.append(coordinate)

    x_center = x_sum // len(our_tiles)
    y_center = y_sum // len(our_tiles)
    mass_center = common_types.Coordinates(x_center, y_center)

    return mass_center

    

def get_ring_of_radius(strategic, tile, r):
    ret = []
    x, y = tile.x, tile.y
    for i in range(-r, r+1):
        for j in range(-r, r+1):
            t = common_types.Coordinates((x+i) % strategic.get_game_width(), (y+j) % strategic.get_game_height())
            if common_types.distance(t, tile) == r:
                ret.append(t)
    return ret


def get_tile_to_attack(strategic, center, tank_coord):
    radius = 1
    possible_tiles = []
    while True:
        if radius >= 100:
            return None # everything is ours, long live Shahaf the king
        for tile in get_ring_of_radius(strategic, tank_coord, radius):
            if strategic.estimate_tile_danger(tile) != OUR_TILE:
                possible_tiles.append(tile)

            if len(possible_tiles) != 0:
                possible_tiles.sort(key = lambda c : common_types.distance(c, center))
                return possible_tiles[0]
            else:
                radius += 1
                possible_tiles = []


def do_turn(strategic):

    attacking_pieces = strategic.report_attacking_pieces()

    for piece, command_id in attacking_pieces.items():
        if command_id is not None:
            continue
        strategic.attack(piece, get_tile_to_attack(strategic, mass_center_of_our_territory(), piece.tile), 1)

    builders : dict = strategic.report_builders()

    for builder in builders.keys():
        if builders[builder][0] is not None:
            continue
        if builder_built_builder.get(builder, False):
            strategic.build_piece(builder, "tank")
        else:
            builder_built_builder[builder] = True
            strategic.build_piece(builder, "builder")


