import re
import six
from slpp import SLPP
from bot_logger import BotLogger


class WowLuaParser(SLPP):
    def decode(self, text):
        if not text or not isinstance(text, six.string_types):
            return
        # Remove only wow saved variable comments
        reg = re.compile(
            "-{2,}\s+\[\d*\].*$", re.M
        )  # pylint: disable=anomalous-backslash-in-string
        text = reg.sub("", text)
        self.text = text
        self.at, self.ch, self.depth = 0, "", 0
        self.len = len(text)
        self.next_chr()
        result = self.value()
        return result


wlp = WowLuaParser()


class SavedVariablesParser:
    def parse_string(self, input_string):
        strings = input_string.split("}\r\n")  # split variables
        if not isinstance(strings, list):
            BotLogger().get().error("Something not ok with split")
            return None
        pattern = re.compile(
            "^\s*([a-zA-Z0-9-_]*)\s*=\s*"
        )  # pylint: disable=anomalous-backslash-in-string
        saved_variables = {}
        for string in strings:
            if len(string) == 0:
                continue
            string += "}"
            out = pattern.match(string)
            saved_variables[out.group().replace(" = ", "").strip()] = wlp.decode(
                pattern.sub("", string, 1)
            )
        return saved_variables

    def parse_file(self, filepath):
        with open(filepath) as file:
            return self.parse_string(file.read())
        return None
