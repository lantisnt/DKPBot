from slpp import slpp as lua
import re

class SavedVariablesParser:
    def ParseString(self, string):
        # todo select valid split option
#        strings = string.split("}\r\n\r\n") #split variables
#        print(len(strings))
        strings = string.split("}\r\n") #split variables
#        print(len(strings))
#        strings = string.split("}\n")
#        print(len(strings))
        if not isinstance(strings, list):
            print("Something not ok with split")
            return None
        pattern = re.compile("^\s*([a-zA-Z0-9-_]*)\s*=\s*")
        SavedVariables = {}
        for s in strings:
            if(len(s) == 0):
                continue
            s += "}"
            out = pattern.match(s)
            SavedVariables[out.group().replace(" = ", "").strip()] = lua.decode(pattern.sub("", s, 1))
        return SavedVariables

    def ParseFile(self, filepath):
        with open("filepath") as file:
            return self.ParseString(file.read())
        return None
