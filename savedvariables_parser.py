import re
from slpp import slpp as lua
from bot_logger import BotLogger

class SavedVariablesParser:
    def parse_string(self, input_string):
        strings = input_string.split("}\r\n")  # split variables
        if not isinstance(strings, list):
            BotLogger().get().error("Something not ok with split")
            return None
        pattern = re.compile("^\s*([a-zA-Z0-9-_]*)\s*=\s*") # pylint: disable=anomalous-backslash-in-string
        saved_variables = {}
        for string in strings:
            if len(string) == 0:
                continue
            string += "}"
            out = pattern.match(string)
            saved_variables[out.group().replace(" = ", "").strip()
                           ] = lua.decode(pattern.sub("", string, 1))
        return saved_variables

    def parse_file(self, filepath):
        with open(filepath) as file:
            return self.parse_string(file.read())
        return None
