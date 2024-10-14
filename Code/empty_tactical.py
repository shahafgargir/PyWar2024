from tactical_api import TurnContext
from strategic_api import StrategicApi
import corn_tactical
import banana_tactical

MAP_BOUND = 15
    

def get_strategic_implementation(context):
    if context.game_height > MAP_BOUND:
        return corn_tactical.MyStrategicApi(context)
    else:
        return banana_tactical.MyStrategicApi(context)
    return MyStrategicApi(context)