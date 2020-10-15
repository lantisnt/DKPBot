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
            self.__num_activities = len(self.__activities)

    def remove(self, activity_key):
        if activity_key in self.__activities.keys():
            del self.__activities[activity_key]

    def next(self):
        if self.__num_activities > 0:
            activity = self.__activities.popitem(False)
            self.__current_activity = activity[1]
            self.__activities[activity[0]] = activity[1]
            self.name = self.__current_activity
        return self
