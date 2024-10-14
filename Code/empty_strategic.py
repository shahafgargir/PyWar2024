from strategic_api import StrategicApi, StrategicPiece
import corn_strategic
import banana_strategic

MAP_BOUND = 15


def do_turn(strategic: StrategicApi):
    if strategic.get_game_height() > MAP_BOUND:
        return corn_strategic.do_turn(strategic)
    else:
        return banana_strategic.do_turn(strategic)
    