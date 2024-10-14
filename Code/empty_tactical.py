from tactical_api import TurnContext
from strategic_api import StrategicApi
import corn_tactical
import banana_tactical

MAP_BOUND = 15
    

class MyStrategicApi(StrategicApi):
    def __init__(self, *args, **kwargs):
        super(MyStrategicApi, self).__init__(*args, **kwargs)
        if self.context.game_height > MAP_BOUND:
            return corn_tactical.MyStrategicApi().__init__(*args, **kwargs)
        else:
            return banana_tactical.MyStrategicApi().__init__(*args, **kwargs)