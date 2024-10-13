import random

import common_types
from common_types import Coordinates, distance
from strategic_api import StrategicApi, StrategicPiece
from tactical_api import Tile, BasePiece

OUR_TILE = 0
UNCLAIMED_TILE = 1
ENEMY_TILE = 2

builder_built_builder = {}

def mass_center_of_our_territory(strategic: StrategicApi) -> Coordinates:
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

    

def get_ring_of_radius(strategic: StrategicApi, tile: Tile, r: int) -> list[Coordinates]:
    ret = []
    x, y = tile.coordinates.x, tile.coordinates.y
    for i in range(-r, r+1):
        for j in range(-r, r+1):
            t = common_types.Coordinates((x+i) % strategic.get_game_width(), (y+j) % strategic.get_game_height())
            if common_types.distance(t, tile.coordinates) == r:
                ret.append(t)
    return ret


def get_tile_to_attack(strategic: StrategicApi, center: Coordinates, tank_tile: Tile) -> Coordinates:
    radius = 1
    possible_tiles: list[Coordinates] = []
    while True:
        if radius >= 100:
            return None # everything is ours, long live Shahaf the king
        for tile in get_ring_of_radius(strategic, tank_tile, radius):
            if strategic.estimate_tile_danger(tile) != OUR_TILE:
                possible_tiles.append(tile)

            if len(possible_tiles) != 0:
                possible_tiles.sort(key = lambda c : distance(c, center))
                return possible_tiles[0]
            else:
                radius += 1
                possible_tiles = []


def do_turn(strategic: StrategicApi):

    attacking_pieces: dict[BasePiece, str] = strategic.report_attacking_pieces()

    for piece, command_id in attacking_pieces.items():
        if command_id is not None:
            continue
        strategic.attack({StrategicPiece(piece.id, piece.type)}, get_tile_to_attack(strategic, mass_center_of_our_territory(strategic), piece.tile), 1)

    builders : dict[BasePiece, str] = strategic.report_builders()

    for builder in builders.keys():
        if builders[builder] is not None:
            continue
        if builder_built_builder.get(builder, False):
            strategic.build_piece(builder, "tank")
        else:
            builder_built_builder[builder] = True
            strategic.build_piece(builder, "builder")


