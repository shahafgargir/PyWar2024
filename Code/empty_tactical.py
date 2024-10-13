import common_types
from common_types import Coordinates
from tactical_api import Tank, Builder, TurnContext, distance, Tile
from strategic_api import CommandStatus, StrategicPiece
from strategic_api import StrategicApi
import math
import random

tank_to_coordinate_to_attack = {}
tank_to_attacking_command = {}

builder_to_building_command = {}
builder_to_piece_type = {}

commands = []
price_per_piece = {'tank': 8, 'builder': 20}

def get_mass_center(context: TurnContext):
    tiles = context.get_tiles_of_country(context.my_country)
    sum_x = 0
    sum_y = 0
    for tile in tiles:
        sum_x += tile.coordinates.x
        sum_y += tile.coordinates.y
    
    center_coords = (math.floor(sum_x / len(tiles)), math.floor(sum_y / len(tiles)))
    if context.tiles[Coordinates(*center_coords)].country != context.my_country:
        return None
    return center_coords

def get_step_to_destination(start, destination):
    if start.x < destination.x:
        return common_types.Coordinates(start.x - 1, start.y)
    elif start.x > destination.x:
        return common_types.Coordinates(start.x + 1, start.y)
    elif start.y < destination.y:
        return common_types.Coordinates(start.x, start.y - 1)
    elif start.y > destination.y:
        return common_types.Coordinates(start.x, start.y + 1)

    return start


def get_tile_ring(context: TurnContext, coords: Coordinates, radius: int) -> list[Tile]:
    retval = []
    for tile_coord, tile in context.tiles.items():
        if distance(tile_coord, coords) <= radius:
            retval.append(tile)
    return retval


def builder_get_tile_with_money(context: TurnContext, builder: Builder) -> Tile:
    coords = builder.tile.coordinates
    for radius in range(1, 4):
        maxtile : Tile = None
        tiles = get_tile_ring(context, coords, radius)
        for tile in tiles:
            if tile.country != context.my_country:
                continue
            if tile.money == 0:
                continue
            if maxtile is None:
                maxtile = tile
            elif maxtile.money < tile.money:
                maxtile = tile
    
    return random.choice(tiles)


def move_tank_to_destination(tank: Tank, dest, context):
    """Returns True if the tank's mission is complete."""
    command_id = tank_to_attacking_command[tank.id]
    if dest is None:
        commands[int(command_id)] = CommandStatus.failed(command_id)
        return
    tank_coordinate = tank.tile.coordinates
    tile = context.tiles[(tank_coordinate.x, tank_coordinate.y)]
    if dest.x < tank_coordinate.x:
        new_coordinate = common_types.Coordinates(tank_coordinate.x - 1, tank_coordinate.y)
    elif dest.x > tank_coordinate.x:
        new_coordinate = common_types.Coordinates(tank_coordinate.x + 1, tank_coordinate.y)
    elif dest.y < tank_coordinate.y:
        new_coordinate = common_types.Coordinates(tank_coordinate.x, tank_coordinate.y - 1)
    elif dest.y > tank_coordinate.y:
        new_coordinate = common_types.Coordinates(tank_coordinate.x, tank_coordinate.y + 1)
    else:
        tank.attack()
        commands[int(command_id)] = CommandStatus.success(command_id)
        del tank_to_attacking_command[tank.id]
        return True
    if tile.country != context.my_country:
        tank.attack()
        prev_command = commands[int(command_id)]
        commands[int(command_id)] = CommandStatus.in_progress(command_id,
                                                          prev_command.elapsed_turns + 1,
                                                          prev_command.estimated_turns - 1)
        return False
    tank.move(new_coordinate)
    prev_command = commands[int(command_id)]
    commands[int(command_id)] = CommandStatus.in_progress(command_id,
                                                          prev_command.elapsed_turns + 1,
                                                          prev_command.estimated_turns - 1)
    return False

def builder_do_work(strat_api, context: TurnContext, builder: Builder, piece_type: str):
    return strat_api.build_piece(StrategicPiece(builder.id, builder.type), piece_type)




class MyStrategicApi(StrategicApi):
    def __init__(self, *args, **kwargs):
        super(MyStrategicApi, self).__init__(*args, **kwargs)
        tanks_to_remove = set()
        builders_to_remove = set()
        for tank_id, destination in tank_to_coordinate_to_attack.items():
            tank: Tank = self.context.my_pieces.get(tank_id)
            if tank is None:
                tanks_to_remove.add(tank_id)
                continue
            if move_tank_to_destination(tank, destination, self.context):
                tanks_to_remove.add(tank_id)
        
        for builder_id, piece_type in builder_to_piece_type.items():
            builder: Builder = self.context.my_pieces.get(builder_id)
            if builder is None:
                builders_to_remove.add(builder_id)
                continue
            if builder_do_work(self, self.context, builder, piece_type):
                builders_to_remove.add(builder_id)
        
        for tank_id in tanks_to_remove:
            del tank_to_coordinate_to_attack[tank_id]
        
        for builder_id in builders_to_remove:
            del builder_to_piece_type[builder_id]

    def attack(self, piece, destination, radius):
        tank = self.context.my_pieces[piece.id]
        if not tank or tank.type != 'tank':
            return None

        if piece.id in tank_to_attacking_command:
            old_command_id = int(tank_to_attacking_command[piece.id])
            commands[old_command_id] = CommandStatus.failed(old_command_id)

        command_id = str(len(commands))
        attacking_command = CommandStatus.in_progress(command_id, 0, common_types.distance(tank.tile.coordinates, destination))
        tank_to_coordinate_to_attack[piece.id] = destination
        tank_to_attacking_command[piece.id] = command_id
        commands.append(attacking_command)

        return command_id

    def estimate_tile_danger(self, destination):
        tile = self.context.tiles[Coordinates(destination.x, destination.y)]
        if tile.country == self.context.my_country:
            return 0
        elif tile.country is None:
            return 1
        else:   # Enemy country
            return 2

    def get_game_height(self):
        return self.context.game_height

    def get_game_width(self):
        return self.context.game_width

    def report_attacking_pieces(self):
        return {piece : tank_to_attacking_command.get(piece_id)
                for piece_id, piece in self.context.my_pieces.items()
                if piece.type == 'tank'}
    
    def build_piece(self, piece, piece_type):
        builder: Builder = self.context.my_pieces[piece.id]
        if not builder or builder.type != 'builder':
            return None

        if piece.id in builder_to_building_command:
            old_command_id = int(builder_to_building_command[piece.id])
            commands[old_command_id] = CommandStatus.failed(old_command_id)
        
        command_id = str(len(commands))
        building_command = CommandStatus.in_progress(command_id, 0, 0)
        builder_to_building_command[piece.id] = command_id
        commands.append(building_command)

        if price_per_piece[piece_type] <= builder.money:
            if piece_type == 'tank':
                builder.build_tank()
            elif piece_type == 'builder':
                builder.build_builder()
            else:
                return False
            builder_to_building_command[piece.id]
        else:
            self.collect_money(piece, price_per_piece[piece_type] - builder.money)

    def log(self, log_entry):
        return self.context.log(log_entry)

    def report_builders(self):
        return {piece : builder_to_building_command.get(piece_id)
                for piece_id, piece in self.context.my_pieces.items()
                if piece.type == 'builder'}
    
    def collect_money(self, piece, amount):
        # add function if not added
        builder: Builder = self.context.my_pieces[piece.id]
        if not builder or builder.type != 'builder':
            return None

        if builder.tile.money > 0:
            builder.collect_money(builder.tile.money)
        else:
            destination = builder_get_tile_with_money(self.context, builder)
            step = get_step_to_destination(builder.tile, destination)
            builder.move(step)


def get_strategic_implementation(context):
    return MyStrategicApi(context)
