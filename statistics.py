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

from bot_utility import public_to_dict


class Statistics:

    INDENT_OFFSET = 2

    class Data(dict):
        class Instrumentation:
            min = None
            max = None
            avg = None
            num = None

            def __init__(self, value=None):
                if not isinstance(value, (int, float)):
                    self.min = float("inf")
                    self.max = 0
                    self.avg = 0
                    self.num = 0
                else:
                    self.min = value
                    self.max = value
                    self.avg = value
                    self.num = 1

            def update(self, value):
                if not isinstance(value, (int, float)):
                    raise TypeError

                if value < self.min:
                    self.min = value

                if value > self.max:
                    self.max = value

                tmp_sum = (self.avg * self.num) + value

                self.num = self.num + 1

                self.avg = tmp_sum / self.num

            def override(self, other):
                if isinstance(other, type(self)):
                    self.min = other.min
                    self.max = other.max
                    self.avg = other.avg
                    self.num = other.num
                else:
                    raise TypeError

            def __add__(self, other):
                if isinstance(other, type(self)):
                    tmp = Statistics.Data.Instrumentation()

                    tmp.min = self.min if self.min < other.min else other.min
                    tmp.max = self.max if self.max > other.max else other.max

                    tmp.num = self.num + other.num

                    total = (self.avg * self.num) + (other.avg * other.num)
                    tmp.avg = total / tmp.num

                    return tmp
                else:
                    raise TypeError

            def __str__(self):
                return "Min: {0} Max: {1} Avg: {2} Num: {3}".format(
                    self.min, self.max, self.avg, self.num
                )

            __repr__ = __str__

        ### End Internal class Instrumentation

        def __setitem__(self, key, item):
            if key not in self:
                super().__setitem__(key, self.Instrumentation(item))
            else:
                self[key].update(item)

        def __add__(self, other):
            if isinstance(self, type(other)):
                data_list = list(dict.fromkeys(list(self.keys()) + list(other.keys())))
                data = Statistics.Data()
                for _data in data_list:
                    data[_data] = 0
                    if _data in self:
                        data[_data].override(self[_data])
                        if _data in other:
                            data[_data].override(data[_data] + other[_data])
                    elif _data in other:
                        data[_data].override(other[_data])
                return data
            else:
                raise TypeError

        def get(self):
            data = {}
            for key in self:
                data[key] = public_to_dict(self[key], filter_callable=True)
            return data

    database = None
    data = None

    def __init__(self):
        self.database = {}
        self.data = Statistics.Data()

    @staticmethod
    def format_list(data, indent=0):
        string = ""
        for entry in data:
            string += Statistics.format(entry, indent + Statistics.INDENT_OFFSET) + ", "
        string.strip(",")
        return string

    @staticmethod
    def format_dict(data, indent=0):
        string = ""
        max_key_len = max(list(map(len, data.keys())))
        for key, value in data.items():
            string += "\n" + (indent * " ") + "{0}: ".format(key)
            if isinstance(value, (dict, tuple)):
                value_indent = indent + Statistics.INDENT_OFFSET
            else:
                value_indent = max_key_len - len(key) + 2
            string += (value_indent * " ") + Statistics.format(
                value, value_indent + Statistics.INDENT_OFFSET
            )
        return string

    @staticmethod
    def format_tuple(data, indent=0):
        string = ""
        string += indent * " "
        string += "( " + Statistics.format(data[0], indent + Statistics.INDENT_OFFSET)
        string += Statistics.format(data[1], indent + Statistics.INDENT_OFFSET) + " )"
        return string

    @staticmethod
    def format(data, indent=0):
        if isinstance(data, list):
            return Statistics.format_list(data, indent)
        elif isinstance(data, dict):
            return Statistics.format_dict(data, indent)
        elif isinstance(data, tuple):
            return Statistics.format_tuple(data, indent)
        else:
            return str(data)

    def print_database(self):
        string = ""
        string += "```asciidoc\n=== Database ===```"
        string += "```c\n"
        string += Statistics.format(self.database, -2)
        string += "```"
        return string

    def print_data(self):
        string = ""
        string += "```asciidoc\n=== Data ===```"
        if len(self.data) > 0:
            string += "```c\n"
            string += Statistics.format(self.data.get(), -2)
            string += "```"
        else:
            string += "```asciidoc\n"
            string += "[ none ]"
            string += "```"
        return string

    def __str__(self):
        string = ""
        string += self.print_database()
        string += self.print_data()
        return string
