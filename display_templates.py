from datetime import datetime
import pytz
from player_db_models import PlayerInfo, PlayerDKPHistory, PlayerLoot
from bot_utility import get_date_from_timestamp

def get_class_color(class_name=None):
    if not class_name:
        return 10204605

    class_name = class_name.lower()

    if class_name == 'rogue':
        return 16774505

    if class_name == 'warrior':
        return 13081710

    if class_name == 'hunter':
        return 11261043

    if class_name == 'druid':
        return 16743690

    if class_name == 'priest':
        return 16777215

    if class_name == 'paladin':
        return 16092346

    if class_name == 'warlock':
        return 8882157

    if class_name == 'mage':
        return 4245483

    return 10204605

def get_icon_string(class_name=None):
    if not class_name:
        return ""

    class_name = class_name.lower()

    if class_name == 'rogue':
        return "<:rogue:760863674071777280>"

    if class_name == 'warrior':
        return "<:warrior:760863673978978314>"

    if class_name == 'hunter':
        return "<:hunter:760863674196951060>"

    if class_name == 'druid':
        return "<:druid:760863673458622488>

    if class_name == 'priest':
        return "<:priest:760863673974784071>"

    if class_name == 'paladin':
        return "<:paladin:760863674306527243>"

    if class_name == 'warlock':
        return "<:warlock:760863673982910484>"

    if class_name == 'mage':
        return "<:mage:760863673719455835>"

    if class_name == 'shaman':
        return "<:shaman:760863673887227955>"

    return ""

def get_thumbnail(class_name):
    if not class_name or not isinstance(class_name, str):
        return None

    class_name = class_name.lower()
        # host the images
    if class_name == 'rogue':
        return "https://media.discordapp.net/attachments/747858424540430457/750760643593765037/rogue.png"

    if class_name == 'warrior':
        return "https://media.discordapp.net/attachments/747858424540430457/750760648031600720/warrior.png"

    if class_name == 'hunter':
        return "https://media.discordapp.net/attachments/747858424540430457/750760636753117325/hunter.png"

    if class_name == 'druid':
        return "https://media.discordapp.net/attachments/747858424540430457/750760633729024030/druid.png"

    if class_name == 'priest':
        return "https://media.discordapp.net/attachments/747858424540430457/750760641740013741/priest.png"

    if class_name == 'paladin':
        return "https://media.discordapp.net/attachments/747858424540430457/750760640167280640/paladin.png"

    if class_name == 'warlock':
        return "https://media.discordapp.net/attachments/747858424540430457/750760645770739893/warlock.png"

    if class_name == 'mage':
        return "https://media.discordapp.net/attachments/747858424540430457/750760638699143288/mage.png"

    return None

def generate_dkp_history_entry(history_entry, format_string=None):
    if history_entry and isinstance(history_entry, PlayerDKPHistory):
        if not format_string:
            format_string = "`{{0:{0}.1f}} DKP`".format(
                len(str(int(history_entry.dkp()))))
        row = ""
        row += "`{0:16}` - ".format(get_date_from_timestamp(history_entry.timestamp()))
        row += format_string.format(history_entry.dkp())
        row += " - {0} _by {1}_".format(history_entry.reason(),
                                      history_entry.officer())
        row += "\n"
        return row
    return "- No data available -"

def generate_loot_entry(loot_entry, format_string=None, player=False):
    if loot_entry and isinstance(loot_entry, PlayerLoot):
        if not format_string:
            format_string = "`{{0:{0}.1f}} DKP`".format(
                len(str(int(loot_entry.dkp()))))
        row = ""
        row += "`{0:16}` - ".format(get_date_from_timestamp(loot_entry.timestamp()))
        row += format_string.format(loot_entry.dkp())
        row += " - [{0}](https://classic.wowhead.com/item={1})".format(loot_entry.item_name(),
                                      loot_entry.item_id())
        if player:
            row += " - "
            row += "{0}".format(get_icon_string(loot_entry.player().ingame_class()))
            row += "{0}".format(loot_entry.player().name())
        row += "\n"
        return row
    return "- No data available -"


class RawEmbed:
    _d = {}
    __is_built = False

    def build(self, author_name, title, description, thumbnail_url, color, footer_text):
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

        self.__is_built = True

    def set_author(self, value):
        self._d['author'] = {'name': str(value)}

    def set_title(self, value):
        self._d['title'] = str(value)

    def set_description(self, value):
        self._d['description'] = str(value)

    def add_field(self, name, value, inline=True):
        if name and value and (len(name) > 0) and (len(value) > 0) and (len(self._d['fields']) < 25):
            field = {
                'name': str(name),
                'value': str(value),
                'inline': bool(inline)
            }
            self._d['fields'].append(field)

    def edit_field(self, idx, name=None, value=None, inline=None):
        if idx < len(self._d['fields']):
            if name and len(name) > 0:
                self._d['fields'][idx]['name'] = str(name)
            if value and len(value) > 0:
                self._d['fields'][idx]['value'] = str(value)
            if inline:
                self._d['fields'][idx]['inline'] = bool(inline)

    def clear(self):
        self._d = {}
        self.__is_built = False

    def get(self):
        return self._d.copy()


class BaseResponse:
    _embed = None
    _title = ""
    _date = ""
    _author = ""
    _comment = ""
    _isBuilt = False

    def __init__(self, title):
        self._embed = RawEmbed()

        if title:
            self._title = str(title)

    def _get_footer(self):
        return "Database updated by {0._author} | {0._comment} | {0._date}".format(self)

    def is_built(self):
        return self._isBuilt

    def set_database_info(self, info):
        self._date = info.get('date')
        self._author = info.get('author')
        self._comment = info.get('comment')

        return self


class SinglePlayerProfile(BaseResponse):

    def build(self, info, thumbnail=None):
        self._embed.clear()

        if thumbnail:
            thumbnail = get_thumbnail(thumbnail)

        self._embed.build(
            author_name=self._title,
            title=info.player().name(),
            description=info.ingame_class(),
            thumbnail_url=thumbnail,
            color=get_class_color(info.ingame_class()),
            footer_text=self._get_footer()
        )

        self._embed.add_field("Current:", "`{0} DKP`".format(
            info.dkp()), False)
        self._embed.add_field("Lifetime gained:", "`{0} DKP`".format(
            info.lifetime_gained()), True)
        self._embed.add_field("Lifetime spent:", "`{0} DKP`".format(
            info.lifetime_spent()), True)
        self._embed.add_field("Last DKP award:",
                             generate_dkp_history_entry(info.get_latest_history_entry()), False)
        self._embed.add_field("Last received loot:",
                             generate_loot_entry(info.get_latest_loot_entry()), False)

        return self

    def get(self):
        return self._embed.get()


class MultipleResponse(BaseResponse):
    __response_list = []
    __field_limit = 6
    __entry_limit = 16
    __response_limit = 0
    __multiple_columns = True

    _value_format_string = "{0:8.1f}"

    def __init__(self, title, field_limit, entry_limit, response_limit, multiple_columns):
        super().__init__(title)

        if field_limit and isinstance(field_limit, int):
            if field_limit > 9:
                self.__field_limit = 9
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

        if response_limit and isinstance(response_limit, int):
            if response_limit < 1:
                self.__response_limit = 0
            else:
                self.__response_limit = response_limit

        self.__multiple_columns = bool(multiple_columns)
        #print("MR: {0} | {1} | {2} | {3}".format(self.__field_limit, self.__entry_limit, self.__response_limit, self.__multiple_columns))
    def _prepare(self, data_list): # pylint: disable=unused-argument
        pass

    def _override_response_loop(self, response_id): # pylint: disable=unused-argument
        pass

    def _override_field_loop(self, response_id, field_id): # pylint: disable=unused-argument
        pass

    def _build_row(self, data, requester): # pylint: disable=unused-argument
        return str(data) + "\n"

    def _display_filter(self, data): # pylint: disable=unused-argument
        return True

    def build(self, data_list_unfiltered, requester="", thumbnail=None):
        self._embed.clear()

        if not requester or not isinstance(requester, str):
            requester = ""

        if not isinstance(data_list_unfiltered, list):
            return None

        #data_list = data_list.copy()
        data_list = []
        for data in data_list_unfiltered:
            if self._display_filter(data):
                data_list.append(data)

        requester = requester.strip().capitalize()

        num_entries = len(data_list)

        response_count = int(
            num_entries / (self.__field_limit * self.__entry_limit)) + 1

        if self.__response_limit > 0:
            response_count = min(response_count, self.__response_limit)

        self.__response_list = []

        # Hook to prepare format strings if needed
        self._prepare(data_list)

        start_value = 1
        for response_id in range(response_count):
            if len(data_list) == 0:
                break
            self._embed.clear()

            append_id = ""
            if response_count > 1:
                append_id = " {0}/{1}".format(response_id + 1,
                                              response_count)

            self._embed.build(
                author_name=self._title + append_id,
                title=None,
                description=None,
                thumbnail_url=thumbnail,
                color=get_class_color(),
                footer_text=self._get_footer()
            )

            # Hook to allow template overrides
            self._override_response_loop(response_id)

            for field_id in range(self.__field_limit):
                if len(data_list) == 0:
                    break

                name = "{0} - {1}".format(start_value,
                                          min(start_value + self.__entry_limit - 1, num_entries))
                value = ""

                for _ in range(self.__entry_limit):
                    if len(data_list) == 0:
                        break
                    value += self._build_row(data_list.pop(0), requester)

                self._embed.add_field(name, value, self.__multiple_columns)
                self._override_field_loop(response_id, field_id)
                start_value += self.__entry_limit

            self.__response_list.append(self._embed.get())

        return self

    def get(self):
        return self.__response_list

    def __str__(self):
        string = ""
        string += str(self.__field_limit) + " | "
        string += str(self.__entry_limit) + " | "
        string += str(self.__response_limit) + " | "
        string += str(self.__multiple_columns)
        return string

class DKPMultipleResponse(MultipleResponse):

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)
        # +2 for decimal
        value_width = max(len(str(int(data_list_min.dkp()))),
                          len(str(int(data_list_max.dkp())))) + 2
        self._value_format_string = "`{{0:{0}.1f}} DKP`".format(value_width)

    def _display_filter(self, data):
        if data and isinstance(data, PlayerInfo):
            return data.is_active()

        return False

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerInfo):
            row = "{0}".format(get_icon_string(data.ingame_class()))
            row += self._value_format_string.format(data.dkp())
            row += " "
            if requester == data.player().name():
                row += "**{0}**".format(data.player().name())
            else:
                row += "{0}".format(data.player().name())
            row += "\n"
            return row

        return ""


class HistoryMultipleResponse(MultipleResponse):

    __user = None

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)
        # +2 for decimal
        value_width = max(len(str(int(data_list_min.dkp()))),
                          len(str(int(data_list_max.dkp())))) + 2
        self._value_format_string = "`{{0:{0}.1f}} DKP`".format(value_width)

        for data in data_list:
            if data and isinstance(data, PlayerDKPHistory):
                self.__user = data.player().name()
                break

    #def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        if field_id == 0:
            self._embed.edit_field(field_id, self.__user)
        else:
            self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerDKPHistory):
            return generate_dkp_history_entry(data, self._value_format_string)

        return ""

class PlayerLootMultipleResponse(MultipleResponse):

    __user = None


    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)
        # +2 for decimal
        value_width = max(len(str(int(data_list_min.dkp()))),
                          len(str(int(data_list_max.dkp())))) + 2
        self._value_format_string = "`{{0:{0}.1f}} DKP`".format(value_width)

        for data in data_list:
            if data and isinstance(data, PlayerLoot):
                self.__user = data.player().name()
                break

    #def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        if field_id == 0:
            self._embed.edit_field(field_id, self.__user)
        else:
            self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerLoot):
            return generate_loot_entry(data, self._value_format_string)

        return ""

class LootMultipleResponse(MultipleResponse):

    __user = None


    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)
        # +2 for decimal
        value_width = max(len(str(int(data_list_min.dkp()))),
                          len(str(int(data_list_max.dkp())))) + 2
        self._value_format_string = "`{{0:{0}.1f}} DKP`".format(value_width)

        for data in data_list:
            if data and isinstance(data, PlayerLoot):
                self.__user = data.player().name()
                break

    #def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerLoot):
            return generate_loot_entry(data, self._value_format_string, True)

        return ""
