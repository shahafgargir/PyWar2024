import random
import math
import common_types
from common_types import Coordinates, distance
from strategic_api import StrategicApi, StrategicPiece
from tactical_api import Tile, BasePiece

ENEMY_TANK = 128
BORDER_TILE = 64
UNCLAIMED_TILE = 32
OUR_TILE = 16
ENEMY_UNIT = 8
ENEMY_BUILDER = 4
ENEMY_ARTILLERY = 2
ANTITANK = 1

builder_built_builder = set()
builder_to_pieces_built = {}
attack_list = set()
artillery_attack = {}
num_of_pieces_built = 0

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
                if strategic.estimate_tile_danger(tile) & (OUR_TILE | ANTITANK) == 0:
                    possible_tiles.append(tile)
            elif piece.type == "antitank":
                if strategic.estimate_tile_danger(tile) & ENEMY_TANK == ENEMY_TANK:
                    possible_tiles.append(tile)
            elif piece.type == "artillery":
                if strategic.estimate_tile_danger(tile) & ENEMY_ARTILLERY == ENEMY_ARTILLERY:
                    possible_tiles.clear()
                    possible_tiles.append(tile)
                    artillery_attack[piece.id] = True
                    break
                elif strategic.estimate_tile_danger(tile) & BORDER_TILE == BORDER_TILE:
                    possible_tiles.append(tile)
        else:
            if piece.type == "artillery":
                artillery_attack[piece.id] = False
        strategic.log(f"{radius=} possible_tiles amnt: {len(possible_tiles)}")
        if len(possible_tiles) == 0:
            radius += 1
            possible_tiles = []
            continue
        
        return random.choice(possible_tiles)
                
        if len(possible_tiles) != 0 and piece.type != "artillery":
            return random.choice(possible_tiles)

        else:
            radius += 1
            possible_tiles = []


def do_turn(strategic: StrategicApi):
    global num_of_pieces_built

    attack_list.clear()

    attacking_pieces: dict[BasePiece, str] = strategic.report_attacking_pieces()

    for piece, command_id in attacking_pieces.items():
        if command_id is not None:
            continue
        if piece.type == "artillery":
            tile_to_attack = get_tile_to_attack(strategic, mass_center_of_our_territory(strategic), piece.tile, piece)
            strategic.attack({StrategicPiece(piece.id, piece.type)},tile_to_attack, 3 if artillery_attack[piece.id] else 1)
        elif piece.type == "antitank" or piece.type == "tank":
            strategic.attack({StrategicPiece(piece.id, piece.type)}, get_tile_to_attack(strategic, mass_center_of_our_territory(strategic), piece.tile, piece), 1)
        elif piece.type == "iron_dome":
            strategic.attack({StrategicPiece(piece.id, piece.type)}, piece.tile.coordinates, 0)

    builders : dict[BasePiece, str] = strategic.report_builders()

    total_money_in_teritorry = strategic.get_total_country_tiles_money()
    strategic.log(f"{total_money_in_teritorry=}")
    MAX_BUILDERS =  total_money_in_teritorry/ 100

    for builder in builders.keys():
        if builders[builder] is not None:
            continue
        if builder.id not in builder_to_pieces_built:
            builder_to_pieces_built[builder.id] = 1
        if len(builders) < MAX_BUILDERS:
            strategic.build_piece(builder, "builder")
            builder_built_builder.add(builder.id)
        elif num_of_pieces_built % 5 == 0:
            strategic.build_piece(builder, "antitank")
        elif num_of_pieces_built % 5 == 4:
            strategic.build_piece(builder, "artillery")
        elif num_of_pieces_built % 20 == 1:
            strategic.build_piece(builder, "iron_dome")
        else:
            strategic.build_piece(builder, "tank")
        
        num_of_pieces_built += 1
        builder_to_pieces_built[builder.id] += 1