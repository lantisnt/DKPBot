from player_db_models import PlayerInfo

def get_class_color(c):
    if not c:
        return 10204605
        
    c = c.lower()

    if c == 'rogue':
        return 16774505
        
    if c == 'warrior':
        return 13081710

    if c == 'hunter':
        return 11261043

    if c == 'druid':
        return 16743690

    if c == 'priest':
        return 16777215

    if c == 'paladin':
        return 16092346

    if c == 'warlock':
        return 8882157

    if c == 'mage':
        return 4245483

    return 10204605

class RawEmbed:
    _d = {}

    def Build(self, author_name, title, description, thumbnail_url, color, footer_text):
        self._d = {}
        self._d['type'] = "rich"

        if author_name:
            self._d['author'] = { 'name' : str(author_name) }

        if title:
            self._d['title'] = str(title)

        if description:
            self._d['description'] = str(description)

        if thumbnail_url:
            self._d['thumbnail'] = { 'url' : str(thumbnail_url) }

        if color:
            self._d['color'] = int(color)

        if footer_text:
            self._d['footer'] = { 'text' : str(footer_text) }

        self._d['fields'] : []

        self.__isBuilt = True

    def AddField(self, name, value, inline=True):
        if name and value and (len(name) > 0) and (len(value) > 0) and (len(self._d['fields']) < 25):
            field = {
                'name'      : str(name),
                'value'     : str(value),
                'inline'    : bool(inline)
            }
            self._d['fields'].append(field)

    def Clear(self):
        self._d = {}
        self.__isBuilt = False

    def Get(self):
        return self._d.copy()

class SingleDKPEntry():
    __embed = None
    __title = ""
    __time = ""
    __comment = ""
    __isBuilt = False

    def __init__(self, title):
        self.__embed = RawEmbed()
        
        if title:
            self.__title = str(title)

    def IsBuilt(self):
        return self.__isBuilt

    def SetDbInfo(self, time, comment):
        if time:
            self.__time = str(time)

        if comment:
            self.__comment = str(comment)

        return self

    def Get(self, info, thumbnail = None):
        self.__embed.Clear()
        self.__embed.Build(
            self.__title,
            info.Player(),
            info.Class(),
            thumbnail,
            get_class_color(info.Class()),
            "Last updated {0} with comment: {1}".format(self.__time, self.__comment))

        self.__embed.AddField("Current",           "`{0} DKP`".format(info.Dkp()),             False)
        self.__embed.AddField("Lifetime Gained",   "`{0} DKP`".format(info.LifetimeGained()),  True)
        self.__embed.AddField("Lifetime Spent",    "`{0} DKP`".format(info.LifetimeSpent()),   True)

        return self.__embed.Get()