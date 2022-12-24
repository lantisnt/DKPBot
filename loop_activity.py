# Copyright 2020-2023 Lantis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
from disnake import Game
from bot_logger import trace, trace_func_only, for_all_methods


@for_all_methods(trace, trace_func_only)
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
