from player_db_models import PlayerInfo


def get_class_color(c=None):
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


def get_icon_string(c = None):
    if not c:
        return ""

    c = c.lower()

    if c == 'rogue':
        return "<:rogue:641645675045453824>"

    if c == 'warrior':
        return "<:warrior:641604892364111872>"

    if c == 'hunter':
        return "<:hunter:641604891969716225>"

    if c == 'druid':
        return "<:druid:641604891671920642>"

    if c == 'priest':
        return "<:priest:641604894154948638>"

    if c == 'paladin':
        return "<:paladin:641645675112693799>"

    if c == 'warlock':
        return "<:warlock:641604892171173928>"

    if c == 'mage':
        return "<:mage:641604891877310486>"

    return "<:essential:743883972206919790>"


class RawEmbed:
    _d = {}

    def Build(self, author_name, title, description, thumbnail_url, color, footer_text):
        self._d = {}
        self._d['type'] = "rich"

        if author_name:
            self._d['author'] = {'name': str(author_name)}

        if title:
            self._d['title'] = str(title)

        if description:
            self._d['description'] = str(description)

        if thumbnail_url:
            self._d['thumbnail'] = {'url': str(thumbnail_url)}

        if color:
            self._d['color'] = int(color)

        if footer_text:
            self._d['footer'] = {'text': str(footer_text)}

        self._d['fields'] = []

        self.__isBuilt = True

    def AddField(self, name, value, inline=True):
        if name and value and (len(name) > 0) and (len(value) > 0) and (len(self._d['fields']) < 25):
            field = {
                'name': str(name),
                'value': str(value),
                'inline': bool(inline)
            }
            self._d['fields'].append(field)

    def Clear(self):
        self._d = {}
        self.__isBuilt = False

    def Get(self):
        return self._d.copy()


class BaseResponse:
    _embed = None
    _title = ""
    _time = ""
    _comment = ""
    _isBuilt = False

    def __init__(self, title):
        self._embed = RawEmbed()

        if title:
            self._title = str(title)

    def _GetFooter(self):
        return "{0._comment} updated {0._time}".format(self)

    def IsBuilt(self):
        return self._isBuilt

    def SetDbInfo(self, time, comment):
        if time:
            self._time = str(time)

        if comment:
            self._comment = str(comment)

        return self


class SinglePlayerProfile(BaseResponse):

    def __init__(self, title):
        super().__init__(title)

    def Build(self, info, thumbnail=None):
        self._embed.Clear()

        self._embed.Build(
            author_name=self._title,
            title=info.Player(),
            description=info.Class(),
            thumbnail_url=thumbnail,
            color=get_class_color(info.Class()),
            footer_text=self._GetFooter()
        )

        self._embed.AddField("Current:", "`{0} DKP`".format(
            info.Dkp()), False)
        self._embed.AddField("Lifetime gained:", "`{0} DKP`".format(
            info.LifetimeGained()), True)
        self._embed.AddField("Lifetime spent:", "`{0} DKP`".format(
            info.LifetimeSpent()), True)
        self._embed.AddField("Last DKP award:",
                             "- No data yet -", False)
        self._embed.AddField("Last received loot:",
                             "- No data yet -", False)

        return self

    def Get(self):
        return self._embed.Get()


class MultipleResponse(BaseResponse):
    __response_list = []
    __field_limit = 6
    __entry_limit = 16
    __allow_multiple_responses = True
    _decimals = 2

    _value_format_string = "{0:8.1f}"
    _min = 0
    _max = 0

    def __init__(self, title, field_limit, entry_limit, allow_multiple_responses, decimals = 0):
        super().__init__(title)

        if field_limit and isinstance(field_limit, int):
            if field_limit > 6:
                self.__field_limit = 6
            elif field_limit < 1:
                self.__field_limit = 1
            else:
                self.__field_limit = field_limit

        if entry_limit and isinstance(entry_limit, int):
            if entry_limit > 16:
                self.__entry_limit = 16
            elif entry_limit < 1:
                self.__entry_limit = 1
            else:
                self.__entry_limit = entry_limit

        if decimals and isinstance(decimals, int):
            if decimals > 2:
                self._decimals = 2
            elif decimals < 0:
                self._decimals = 1
            else:
                self._decimals = decimals

        self.__allow_multiple_responses = bool(allow_multiple_responses)

    def _prepare(self):
        True

    def _setLimits(self, data_list):
        self._min = 0
        self._max = 0

    def _buildRow(self, data):
        return str(data) + "\n"

    def Build(self, data_list, requester="", thumbnail=None):
        self._embed.Clear()

        if not requester or not isinstance(requester, str):
            requester = ""

        requester = requester.strip().capitalize()

        num_entries = len(data_list)

        response_count = int(
            num_entries / (self.__field_limit * self.__entry_limit)) + 1

        if response_count > 1 and not self.__allow_multiple_responses:
            response_count = 1

        self.__response_list = []

        self._setLimits(data_list)
        
        # Hook to prepare format strings if needed
        self._prepare()

        start_value = 1
        for response_id in range(response_count):
            if len(data_list) == 0: break
            self._embed.Clear()

            append_id = ""
            if response_count > 1:
                append_id = " {0}/{1}".format(response_id + 1,
                                              response_count)

            self._embed.Build(
                author_name=self._title + append_id,
                title=None,
                description=None,
                thumbnail_url=None,
                color=get_class_color(),
                footer_text=self._GetFooter()
            )

            for _ in range(self.__field_limit):
                if len(data_list) == 0: break

                name = "{0} - {1}".format(start_value,
                                          min(start_value + self.__entry_limit - 1, num_entries))
                value = ""

                for _ in range(self.__entry_limit):
                    if len(data_list) == 0: break
                    value += self._buildRow(data_list.pop(), requester)

                self._embed.AddField(name, value, True)
                start_value += self.__entry_limit

            self.__response_list.append(self._embed.Get())

        return self

    def Get(self):
        return self.__response_list


class DKPMultipleResponse(MultipleResponse):

    def __init__(self, title, field_limit, entry_limit, allow_multiple_responses, decimals):
        super().__init__(title, field_limit, entry_limit, allow_multiple_responses, decimals)

    def _setLimits(self, data_list):
        self._min = min(data_list)
        self._max = max(data_list)
        
    def _prepare(self):
        value_width = 0
        decimals_format = ""
        if self._decimals > 0:
            value_width += (self._decimals + 1)
            decimals_format = ".{0}".format(self._decimals)

        if self._min < 0:
            value_width += 1

        if   self._min > 999999 or self._max > 999999:
            value_width += 7
        elif self._min > 99999  or self._max > 99999:
            value_width += 6
        elif self._min > 9999   or self._max > 9999:
            value_width += 5
        elif self._min > 999    or self._max > 999:
            value_width += 4
        elif self._min > 99     or self._max > 99:
            value_width += 3
        elif self._min > 9      or self._max > 9:
            value_width += 2
        else:
            value_width += 1

        self._value_format_string = "{{0:{0}{1}f}}".format(value_width, decimals_format)


#self._format_string = "{0:8.1f}"
    def _buildRow(self, data, requester):
        if data and isinstance(data, PlayerInfo):
            row =  "{0}`".format(get_icon_string(data.Class()))
            row += self._value_format_string.format(data.Dkp())
            row += "` "
            if requester != data.Player():
                row += "{0}".format(data.Player())
            else:
                row += "**{0}**".format(data.Player())
            row += "\n"
            return row

        return ""
