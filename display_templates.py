from player_db_models import PlayerInfo, PlayerDKPHistory, PlayerLoot
from datetime import datetime
import pytz


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


def get_icon_string(c=None):
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

def get_thumbnail(c):
    if not c or not isinstance(c, str):
        return None

    c = c.lower()

    if c == 'rogue':
        return "https://media.discordapp.net/attachments/747858424540430457/750760643593765037/rogue.png"

    if c == 'warrior':
        return "https://media.discordapp.net/attachments/747858424540430457/750760648031600720/warrior.png"

    if c == 'hunter':
        return "https://media.discordapp.net/attachments/747858424540430457/750760636753117325/hunter.png"

    if c == 'druid':
        return "https://media.discordapp.net/attachments/747858424540430457/750760633729024030/druid.png"

    if c == 'priest':
        return "https://media.discordapp.net/attachments/747858424540430457/750760641740013741/priest.png"

    if c == 'paladin':
        return "https://media.discordapp.net/attachments/747858424540430457/750760640167280640/paladin.png"

    if c == 'warlock':
        return "https://media.discordapp.net/attachments/747858424540430457/750760645770739893/warlock.png"

    if c == 'mage':
        return "https://media.discordapp.net/attachments/747858424540430457/750760638699143288/mage.png"

    return None

def generate_dkp_history_entry(history_entry, format_string=None):
    if history_entry and isinstance(history_entry, PlayerDKPHistory):
        if not format_string:
            format_string = "`{{0:{0}.1f}} DKP`".format(
                len(str(int(history_entry.Dkp()))))
        row = ""
        row += "`{0:16}` - ".format(datetime.fromtimestamp(history_entry.Timestamp(
        ), tz=pytz.timezone("Europe/Paris")).strftime("%b %d %a %H:%M"))
        row += format_string.format(history_entry.Dkp())
        row += " - {0} _by {1}_".format(history_entry.Reason(),
                                      history_entry.Officer())
        row += "\n"
        return row
    return "- No data available -"

def generate_loot_entry(loot_entry, format_string=None, player=False):
    if loot_entry and isinstance(loot_entry, PlayerLoot):
        if not format_string:
            format_string = "`{{0:{0}.1f}} DKP`".format(
                len(str(int(loot_entry.Dkp()))))
        row = ""
        row += "`{0:16}` - ".format(datetime.fromtimestamp(loot_entry.Timestamp(
        ), tz=pytz.timezone("Europe/Paris")).strftime("%b %d %a %H:%M"))
        row += format_string.format(loot_entry.Dkp())
        row += " - [{0}](https://classic.wowhead.com/item={1})".format(loot_entry.ItemName(),
                                      loot_entry.ItemId())
        if player:
            row += " - "
            row += "{0}".format(get_icon_string(loot_entry.Player().Class()))
            row += "{0}".format(loot_entry.Player().Player())
        row += "\n"
        return row
    return "- No data available -"


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

    def SetAuthor(self, value):
        self._d['author'] = {'name': str(value)}

    def SetTitle(self, value):
        self._d['title'] = str(value)

    def SetDescription(self, value):
        self._d['description'] = str(value)

    def AddField(self, name, value, inline=True):
        if name and value and (len(name) > 0) and (len(value) > 0) and (len(self._d['fields']) < 25):
            field = {
                'name': str(name),
                'value': str(value),
                'inline': bool(inline)
            }
            self._d['fields'].append(field)

    def EditField(self, id, name=None, value=None, inline=None):
        if id < len(self._d['fields']):
            if name and len(name) > 0:
                self._d['fields'][id]['name'] = str(name)
            if value and len(value) > 0:
                self._d['fields'][id]['value'] = str(value)
            if inline:
                self._d['fields'][id]['inline'] = bool(inline)

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

        if thumbnail:
            thumbnail = get_thumbnail(thumbnail)

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
                             generate_dkp_history_entry(info.GetLatestHistoryEntry()), False)
        self._embed.AddField("Last received loot:",
                             generate_loot_entry(info.GetLatestLootEntry()), False)

        return self

    def Get(self):
        return self._embed.Get()


class MultipleResponse(BaseResponse):
    __response_list = []
    __field_limit = 6
    __entry_limit = 16
    __allow_multiple_responses = True
    __multiple_columns = True

    _value_format_string = "{0:8.1f}"

    def __init__(self, title, field_limit, entry_limit, allow_multiple_responses, multiple_columns):
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

        self.__allow_multiple_responses = bool(allow_multiple_responses)
        self.__multiple_columns = bool(multiple_columns)

    def _prepare(self, data_list):
        True

    def _overrideResponseLoop(self, response_id):
        True

    def _overrideFieldLoop(self, response_id, field_id):
        True

    def _buildRow(self, data, requester):
        return str(data) + "\n"

    def Build(self, data_list, requester="", thumbnail=None):
        self._embed.Clear()

        if not requester or not isinstance(requester, str):
            requester = ""

        if not isinstance(data_list, list):
            return None

        data_list = data_list.copy()

        requester = requester.strip().capitalize()

        num_entries = len(data_list)

        response_count = int(
            num_entries / (self.__field_limit * self.__entry_limit)) + 1

        if response_count > 1 and not self.__allow_multiple_responses:
            response_count = 1

        self.__response_list = []

        # Hook to prepare format strings if needed
        self._prepare(data_list)

        start_value = 1
        for response_id in range(response_count):
            if len(data_list) == 0:
                break
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

            # Hook to allow template overrides
            self._overrideResponseLoop(response_id)

            for field_id in range(self.__field_limit):
                if len(data_list) == 0:
                    break

                name = "{0} - {1}".format(start_value,
                                          min(start_value + self.__entry_limit - 1, num_entries))
                value = ""

                for _ in range(self.__entry_limit):
                    if len(data_list) == 0:
                        break
                    value += self._buildRow(data_list.pop(0), requester)

                self._embed.AddField(name, value, self.__multiple_columns)
                self._overrideFieldLoop(response_id, field_id)
                start_value += self.__entry_limit

            self.__response_list.append(self._embed.Get())

        return self

    def Get(self):
        return self.__response_list


class DKPMultipleResponse(MultipleResponse):

    def __init__(self, title, field_limit, entry_limit, allow_multiple_responses, multiple_columns):
        super().__init__(title, field_limit, entry_limit, allow_multiple_responses, multiple_columns)

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.Dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)
        # +2 for decimal
        value_width = max(len(str(int(data_list_min.Dkp()))),
                          len(str(int(data_list_max.Dkp())))) + 2
        self._value_format_string = "`{{0:{0}.1f}} DKP`".format(value_width)

    def _buildRow(self, data, requester):
        if data and isinstance(data, PlayerInfo):
            row = "{0}".format(get_icon_string(data.Class()))
            row += self._value_format_string.format(data.Dkp())
            row += " "
            if requester == data.Player():
                row += "**{0}**".format(data.Player())
            else:
                row += "{0}".format(data.Player())
            row += "\n"
            return row

        return ""


class HistoryMultipleResponse(MultipleResponse):

    __user = None

    def __init__(self, title, field_limit, entry_limit, allow_multiple_responses, multiple_columns):
        super().__init__(title, field_limit, entry_limit, allow_multiple_responses, multiple_columns)

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.Dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)
        # +2 for decimal
        value_width = max(len(str(int(data_list_min.Dkp()))),
                          len(str(int(data_list_max.Dkp())))) + 2
        self._value_format_string = "`{{0:{0}.1f}} DKP`".format(value_width)

        for data in data_list:
            if data and isinstance(data, PlayerDKPHistory):
                self.__user = data.Player()
                break

    #def _overrideResponseLoop(self, response_id):
    #    self._embed.SetTitle(self.__user)

    def _overrideFieldLoop(self, response_id, field_id):
        if field_id == 0:
            self._embed.EditField(field_id, self.__user)
        else:
            self._embed.EditField(field_id, name="\u200b")

    def _buildRow(self, data, requester):
        if data and isinstance(data, PlayerDKPHistory):
            return generate_dkp_history_entry(data, self._value_format_string)

        return ""

class PlayerLootMultipleResponse(MultipleResponse):

    __user = None

    def __init__(self, title, field_limit, entry_limit, allow_multiple_responses, multiple_columns):
        super().__init__(title, field_limit, entry_limit, allow_multiple_responses, multiple_columns)

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.Dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)
        # +2 for decimal
        value_width = max(len(str(int(data_list_min.Dkp()))),
                          len(str(int(data_list_max.Dkp())))) + 2
        self._value_format_string = "`{{0:{0}.1f}} DKP`".format(value_width)

        for data in data_list:
            if data and isinstance(data, PlayerLoot):
                self.__user = data.Player().Player()
                break

    #def _overrideResponseLoop(self, response_id):
    #    self._embed.SetTitle(self.__user)

    def _overrideFieldLoop(self, response_id, field_id):
        if field_id == 0:
            self._embed.EditField(field_id, self.__user)
        else:
            self._embed.EditField(field_id, name="\u200b")

    def _buildRow(self, data, requester):
        if data and isinstance(data, PlayerLoot):
            return generate_loot_entry(data, self._value_format_string)

        return ""

class LootMultipleResponse(MultipleResponse):

    __user = None

    def __init__(self, title, field_limit, entry_limit, allow_multiple_responses, multiple_columns):
        super().__init__(title, field_limit, entry_limit, allow_multiple_responses, multiple_columns)

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.Dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)
        # +2 for decimal
        value_width = max(len(str(int(data_list_min.Dkp()))),
                          len(str(int(data_list_max.Dkp())))) + 2
        self._value_format_string = "`{{0:{0}.1f}} DKP`".format(value_width)

        for data in data_list:
            if data and isinstance(data, PlayerLoot):
                self.__user = data.Player().Player()
                break

    #def _overrideResponseLoop(self, response_id):
    #    self._embed.SetTitle(self.__user)

    def _overrideFieldLoop(self, response_id, field_id):
        if field_id == 0:
            self._embed.EditField(field_id, self.__user)
        else:
            self._embed.EditField(field_id, name="\u200b")

    def _buildRow(self, data, requester):
        if data and isinstance(data, PlayerLoot):
            return generate_loot_entry(data, self._value_format_string, True)

        return ""