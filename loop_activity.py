import collections
from discord import Game

class LoopActivity(Game):

    __activities = None
    __num_activities = 0
    __current_activity = None

    def __init__(self, name, **extra):
        super().__init__(name, **extra)
        self.__activities = collections.OrderedDict()

    def update(self, activities):
        if isinstance(activities, dict):
            for key, value in activities.items():
                self.__activities[key] = value

    def next(self):
        if self.__num_activities > 0:
            activity = self.__activities.popitem(False)
            self.__current_activity = activity[1]
#            print(self.__current_activity)
            self.__activities[activity[0]] = activity[1]
            self.name = self.__current_activity
        return self
