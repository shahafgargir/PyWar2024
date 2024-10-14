import random

import common_types
from common_types import Coordinates, distance
from strategic_api import StrategicApi, StrategicPiece
from tactical_api import Tile, BasePiece

OUR_TILE = 0
UNCLAIMED_TILE = 1
ENEMY_TILE = 2
ENEMY_TANK = 3

builder_built_builder = {}
attack_list = set()
def mass_center_of_our_territory(strategic: StrategicApi) -> Coordinates:
    our_area = 0
    x_sum = 0
    y_sum = 0

    for x in range(strategic.get_game_width()):
        for y in range(strategic.get_game_height()):
            coordinate = common_types.Coordinates(x, y)
            danger = strategic.estimate_tile_danger(coordinate)
            if danger == OUR_TILE:
                x_sum += x
                y_sum += y
                our_area += 1

    x_center = x_sum // our_area
    y_center = y_sum // our_area
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


def get_tile_to_attack(strategic: StrategicApi, center: Coordinates, tank_tile: Tile, piece : BasePiece) -> Coordinates:
    radius = 3
    possible_tiles: list[Coordinates] = []
    while True:
        if radius >= 50:
            possible_tiles = get_ring_of_radius(strategic, tank_tile, 5)
            possible_tiles.sort(key = lambda c : distance(c, center), reverse=True)
            return possible_tiles[0]
        
        for tile in get_ring_of_radius(strategic, tank_tile, radius):
            if piece.type == "tank":
                if strategic.estimate_tile_danger(tile) != OUR_TILE:
                    possible_tiles.append(tile)
            elif piece.type == "antitank":
                if strategic.estimate_tile_danger(tile) == ENEMY_TANK:
                    possible_tiles.append(tile)
                
        if len(possible_tiles) != 0:
            return random.choice(possible_tiles)
        else:
            radius += 1
            possible_tiles = []


def do_turn(strategic: StrategicApi):
    attack_list.clear()

    attacking_pieces: dict[BasePiece, str] = strategic.report_attacking_pieces()

    for piece, command_id in attacking_pieces.items():
        if command_id is not None:
            continue
        strategic.attack({StrategicPiece(piece.id, piece.type)}, get_tile_to_attack(strategic, mass_center_of_our_territory(strategic), piece.tile, piece), 1)

    builders : dict[BasePiece, str] = strategic.report_builders()

    MAX_BUILDERS = 10
    if strategic.get_game_height() < 15:
        MAX_BUILDERS = 3

    for builder in builders.keys():
        if builders[builder] is not None:
            continue
        if builder.id not in builder_built_builder and len(builders) >= MAX_BUILDERS:
            builder_built_builder[builder.id] = 1
        if  builder.id not in builder_built_builder:
            strategic.build_piece(builder, "builder")
            builder_built_builder[builder.id] = 0
        elif builder_built_builder[builder.id] % 3 == 0:
            strategic.build_piece(builder, "antitank")
        else:
            strategic.build_piece(builder, "tank")

        builder_built_builder[builder.id] += 1


