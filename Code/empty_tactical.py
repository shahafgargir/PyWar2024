import common_types
from common_types import Coordinates
from tactical_api import Tank, Antitank, Builder, TurnContext, distance, Tile
from strategic_api import CommandStatus, StrategicPiece
from strategic_api import StrategicApi
import math
import random

tank_to_coordinate_to_attack = {}
tank_to_attacking_command = {}

antitank_to_coordinate_to_attack = {}
antitank_to_attacking_command = {}

builder_to_building_command = {}
builder_to_piece_type = {}

commands = []
price_per_piece = {'tank': 8, 'builder': 20, 'artillery': 8, 'antitank': 10}

builder_chosen_tiles = set()

builder_money_taken: dict[Coordinates, list[int]] = {}

def mass_center_of_our_territory(context: TurnContext) -> Coordinates:
    our_area = 0
    x_sum = 0
    y_sum = 0
    our_tiles = context.get_tiles_of_country(context.my_country)
    our_area = len(our_tiles)
    for tile in our_tiles:
        x_sum += tile.x
        y_sum += tile.y

    x_center = x_sum // our_area
    y_center = y_sum // our_area
    mass_center = Coordinates(x_center, y_center)

    return mass_center

def get_step_to_destination(start: Coordinates, destination: Coordinates):
    if destination.x < start.x:
        return common_types.Coordinates(start.x - 1, start.y)
    elif destination.x > start.x:
        return common_types.Coordinates(start.x + 1, start.y)
    elif destination.y < start.y:
        return common_types.Coordinates(start.x, start.y - 1)
    elif destination.y > start.y:
        return common_types.Coordinates(start.x, start.y + 1)

    return start


def get_ring_of_radius(context: TurnContext, coords: Coordinates, r: int) -> list[Tile]:
    ret = []
    x, y = coords.x, coords.y
    for i in range(-r, r+1):
        for j in range(-r, r+1):
            t = common_types.Coordinates((x+i) % context.game_width, (y+j) % context.game_height)
            if common_types.distance(t, coords) == r:
                ret.append(context.tiles[t])
    
    return ret

def get_tile_map(context: TurnContext, coords: Coordinates) -> dict[int, list[Tile]]:
    ret = {r:[] for r in range(60)}
    for tile_coords, tile in context.tiles.items():
        ret[distance(Coordinates(*tile_coords), coords)].append(tile)
    
    del ret[0]
    
    return ret




def builder_get_tile_with_money(context: TurnContext, builder: Builder) -> Tile:
    coords = builder.tile.coordinates
    tile_map = get_tile_map(context, coords)
    max_tile_amount = 0
    goodtiles = []
    for radius, tiles_at_radius in tile_map.items():
        context.log(f"radius: {radius}")
        context.log(f"tile: {tile}")
        context.log(f"tile.money: {tile.money}")
        for tile in tiles_at_radius:
            tile_money = tile.money - 5*(radius - 1)
            if tile.country != context.my_country:
                continue
            if tile_money <= 0:
                continue
            if tile in builder_chosen_tiles:
                continue

            if tile_money > max_tile_amount:
                max_tile_amount = tile_money
                goodtiles.clear()
                goodtiles.append(tile)
                continue

            if tile_money == max_tile_amount:
                goodtiles.append(tile)
            
    if len(goodtiles) != 0:
        chosen =  random.choice(goodtiles)
        builder_chosen_tiles.add(chosen)
        return chosen
    
    for radius in sorted(tile_map.keys()):
        tiles_at_radius = tile_map[radius]
        max_tile_amount = 0
        goodtiles = []
        for tile in tiles_at_radius:
            tile_money = tile.money
            if tile.country != context.my_country:
                continue
            if tile_money <= 0:
                continue
            if tile in builder_chosen_tiles:
                continue

            if tile_money > max_tile_amount:
                max_tile_amount = tile_money
                goodtiles.clear()
                goodtiles.append(tile)
                continue

            if tile_money == max_tile_amount:
                goodtiles.append(tile)
        if len(goodtiles) != 0:
            chosen =  random.choice(goodtiles)
            builder_chosen_tiles.add(chosen)
            return chosen
        
    return context.tiles[mass_center_of_our_territory(context)]


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


def move_antitank_to_destination(antitank: Antitank, dest, context):
    """Returns True if the antitank's mission is complete."""
    command_id = antitank_to_attacking_command[antitank.id]
    if dest is None:
        commands[int(command_id)] = CommandStatus.failed(command_id)
        return
    antitank_coordinate = antitank.tile.coordinates
    tile = context.tiles[(antitank_coordinate.x, antitank_coordinate.y)]
    if dest.x < antitank_coordinate.x:
        new_coordinate = common_types.Coordinates(antitank_coordinate.x - 1, antitank_coordinate.y)
    elif dest.x > antitank_coordinate.x:
        new_coordinate = common_types.Coordinates(antitank_coordinate.x + 1, antitank_coordinate.y)
    elif dest.y < antitank_coordinate.y:
        new_coordinate = common_types.Coordinates(antitank_coordinate.x, antitank_coordinate.y - 1)
    elif dest.y > antitank_coordinate.y:
        new_coordinate = common_types.Coordinates(antitank_coordinate.x, antitank_coordinate.y + 1)
    else:
        commands[int(command_id)] = CommandStatus.success(command_id)
        del antitank_to_attacking_command[antitank.id]
        return True
    antitank.move(new_coordinate)
    prev_command = commands[int(command_id)]
    commands[int(command_id)] = CommandStatus.in_progress(command_id,
                                                          prev_command.elapsed_turns + 1,
                                                          prev_command.estimated_turns - 1)
    return False

def builder_collect_money(context: TurnContext, builder: Builder):
    if not builder or builder.type != 'builder':
        return None

    tile_coords = builder.tile.coordinates
    if tile_coords not in builder_money_taken:
        builder_money_taken[tile_coords] = []
    tile_money = builder.tile.money - sum(builder_money_taken[tile_coords])

    if tile_money > 0 and builder.tile.country == context.my_country:
        collected_amnt = min(builder.tile.money, 5)
        builder.collect_money(collected_amnt)
        builder_money_taken[tile_coords].append(collected_amnt)
    else:
        destination = builder_get_tile_with_money(context, builder)
        step = get_step_to_destination(builder.tile.coordinates, destination.coordinates)
        builder.move(step)

def builder_do_work(context: TurnContext, builder: Builder, piece_type: str):
    command_id = builder_to_building_command[builder.id]
    if price_per_piece[piece_type] <= builder.money:
            if piece_type == 'tank':
                builder.build_tank()
            elif piece_type == 'builder':
                builder.build_builder()
            elif piece_type == 'artillery':
                builder.build_artillery()
            elif piece_type == 'antitank':
                builder.build_antitank()
            context.log(f"builder built {piece_type}")
            commands[int(command_id)] = CommandStatus.success(command_id)
            del builder_to_building_command[builder.id]
            return True
    # we dont have enough money, go collect it!
    return builder_collect_money(context, builder)


class MyStrategicApi(StrategicApi):
    def __init__(self, *args, **kwargs):
        super(MyStrategicApi, self).__init__(*args, **kwargs)

        tanks_to_remove = set()
        antitanks_to_remove = set()
        builders_to_remove = set()

        builder_chosen_tiles.clear()
        builder_money_taken.clear()

        for tank_id, destination in tank_to_coordinate_to_attack.items():
            tank: Tank = self.context.my_pieces.get(tank_id)
            if tank is None:
                tanks_to_remove.add(tank_id)
                continue
            if move_tank_to_destination(tank, destination, self.context):
                tanks_to_remove.add(tank_id)

        for antitank_id, destination in antitank_to_coordinate_to_attack.items():
            antitank: Antitank = self.context.my_pieces.get(antitank_id)
            if antitank is None:
                antitanks_to_remove.add(antitank_id)
                continue
            if move_antitank_to_destination(antitank, destination, self.context):
                antitanks_to_remove.add(antitank_id)

        for builder_id, piece_type in builder_to_piece_type.items():
            builder: Builder = self.context.my_pieces.get(builder_id)
            if builder is None:
                builders_to_remove.add(builder_id)
                continue
            if builder_do_work(self.context, builder, piece_type):
                builders_to_remove.add(builder_id)

        for tank_id in tanks_to_remove:
            del tank_to_coordinate_to_attack[tank_id]

        for antitank_id in antitanks_to_remove:
            del antitank_to_coordinate_to_attack[antitank_id]

        for builder_id in builders_to_remove:
            del builder_to_piece_type[builder_id]

    def attack(self, pieces: set[StrategicPiece], destination: Coordinates, radius: int):
        if len(pieces) == 0:
            return None
        for piece in pieces:
            if piece.type == 'tank':
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
            if piece.type == 'antitank':
                antitank = self.context.my_pieces[piece.id]
                if not antitank or antitank.type != 'antitank':
                    return None

                if piece.id in antitank_to_attacking_command:
                    old_command_id = int(antitank_to_attacking_command[piece.id])
                    commands[old_command_id] = CommandStatus.failed(old_command_id)

                command_id = str(len(commands))
                attacking_command = CommandStatus.in_progress(command_id, 0, common_types.distance(antitank.tile.coordinates, destination))
                antitank_to_coordinate_to_attack[piece.id] = destination
                antitank_to_attacking_command[piece.id] = command_id
                commands.append(attacking_command)


    def estimate_tile_danger(self, destination):
        tile = self.context.tiles[Coordinates(destination.x, destination.y)]
        if any([piece.country != self.context.my_country for piece in tile.pieces]):
            return 3
        elif tile.country == self.context.my_country:
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
        attacking_pieces = {}
        for piece_id, piece in self.context.my_pieces.items():
            if piece.type == 'tank':
                attacking_pieces[piece] = tank_to_attacking_command.get(piece_id)
            if piece.type == 'antitank':
                attacking_pieces[piece] = antitank_to_attacking_command.get(piece_id)
        return attacking_pieces

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
        builder_to_piece_type[piece.id] = piece_type
        commands.append(building_command)

        return command_id



    def log(self, log_entry):
        return self.context.log(log_entry)

    def report_builders(self):
        return {piece : builder_to_building_command.get(piece_id)
                for piece_id, piece in self.context.my_pieces.items()
                if piece.type == 'builder'}
    
def get_strategic_implementation(context):
    return MyStrategicApi(context)
