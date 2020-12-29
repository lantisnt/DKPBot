from player_db_models import PlayerInfo, PlayerDKPHistory, PlayerLoot
from bot_utility import get_date_from_timestamp
from bot_config import DisplayConfig
from bot_logger import trace, for_all_methods
import build_info

INVITE = "[Invite Bot](http://wowdkpbot.com/invite)"
SUPPORT_SERVER = "[Support Server](http://{0})".format(
    build_info.SUPPORT_SERVER)
DONATE = "[Donate](http://wowdkpbot.com/donate)"

@trace
def get_bot_links():
    return INVITE + " | " + SUPPORT_SERVER + " | " + DONATE

@trace
def get_bot_color():
    return 10204605

@trace
def get_config_color():
    return 16553987

@trace
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
        return 16711422

    if class_name == 'paladin':
        return 16092346

    if class_name == 'warlock':
        return 8882157

    if class_name == 'mage':
        return 4245483

    if class_name == 'shaman':
        return 159965

    return 10204605

@trace
def get_plus_minus_icon_string(plus=True):
    if plus:
        return "<:plus:782168773875728384>"
    else:
        return "<:minus:782168774035374080>"

@trace
def get_class_icon_string(class_name=None, spec_id=0):
    if not class_name:
        return ""

    class_name = class_name.lower()

    if class_name == 'rogue':
        return "<:rogue:760863674071777280>"

    if class_name == 'warrior':
        if spec_id == 2:
            return "<:warrtank:760863674222510120>"
        else:
            return "<:warrior:760863673978978314>"

    if class_name == 'hunter':
        return "<:hunter:760863674196951060>"

    if class_name == 'druid':
        if spec_id == 0:
            return "<:druidmoon:760863673564135434>"
        elif spec_id == 1:
            return "<:druidtank:760863673643302934>"
        elif spec_id == 2:
            return "<:restodruid:760863673740165151>"
        else:
            return "<:druid:760863673458622488>"

    if class_name == 'priest':
        if spec_id == 2:
            return "<:spriest:760863673752223797>"
        else:
            return "<:priest:760863673974784071>"

    if class_name == 'paladin':
        if spec_id == 0:
            return "<:holypala:760863674067583006>"
        elif spec_id == 1:
            return "<:palatank:760863674147274822>"
        elif spec_id == 2:
            return "<:retripala:760863673908199436>"
        else:
            return "<:paladin:760863674306527243>"

    if class_name == 'warlock':
        return "<:warlock:760863673982910484>"

    if class_name == 'mage':
        return "<:mage:760863673719455835>"

    if class_name == 'shaman':
        if spec_id == 2:
            return "<:restosham:774936622620868609>"
        else:
            return "<:shaman:760863673887227955>"

    return ""

@trace
def get_thumbnail(class_name):
    if not class_name or not isinstance(class_name, str):
        return None

    class_name = class_name.lower()

    if class_name == 'rogue':
        return "https://cdn.discordapp.com/attachments/765089790295015425/765091109558550608/rogue.png"

    if class_name == 'warrior':
        return "https://cdn.discordapp.com/attachments/765089790295015425/765091114561568798/warrior.png"

    if class_name == 'hunter':
        return "https://cdn.discordapp.com/attachments/765089790295015425/765091099626307614/hunter.png"

    if class_name == 'druid':
        return "https://cdn.discordapp.com/attachments/765089790295015425/765091097680019496/druid.png"

    if class_name == 'priest':
        return "https://cdn.discordapp.com/attachments/765089790295015425/765091107477782548/priest.png"

    if class_name == 'paladin':
        return "https://cdn.discordapp.com/attachments/765089790295015425/765091105670430750/paladin.png"

    if class_name == 'warlock':
        return "https://cdn.discordapp.com/attachments/765089790295015425/765091111822950430/warlock.png"

    if class_name == 'mage':
        return "https://cdn.discordapp.com/attachments/765089790295015425/765091102545412096/mage.png"

    if class_name == 'shaman':
        return "https://cdn.discordapp.com/attachments/765089790295015425/765241408449019914/shaman.png"

    return None

@trace
def get_points_format_string(width, rounding, value_suffix):
    return "`{{0:{0}.{1}f}}{2}`".format(width, rounding, " DKP" if value_suffix else "")

@trace
def get_history_format_string(width, rounding, value_suffix):
    return get_points_format_string(width, rounding, value_suffix)

@trace
def get_loot_format_string(width, rounding, value_suffix):
    return get_points_format_string(width, rounding, value_suffix)

@trace
def preformatted_block(string: str, language='swift'):
    return "```" + language + "\n" + string + "```"

@trace
def generate_dkp_history_entry(history_entry, format_string, enable_icons, alternative_display_mode):
    if history_entry and isinstance(history_entry, PlayerDKPHistory):
        row = ""
        if enable_icons:
            row += get_plus_minus_icon_string(history_entry.dkp() > 0) + " "
        row += "`{0:16}` - ".format(
            get_date_from_timestamp(history_entry.timestamp()))
        row += format_string.format(history_entry.dkp())
        row += " - {0} _by {1}_".format(history_entry.reason(),
                                        history_entry.officer())
        row += "\n"
        return row
    return "- No data available -"

@trace
def generate_loot_entry(loot_entry, format_string, enable_icons, alternative_display_mode, player):
    if loot_entry and isinstance(loot_entry, PlayerLoot):
        row = ""
        row += "`{0:16}` - ".format(
            get_date_from_timestamp(loot_entry.timestamp()))
        row += format_string.format(loot_entry.dkp())
        row += " - [{0}](https://classic.wowhead.com/item={1})".format(loot_entry.item_name(),
                                                                       loot_entry.item_id())
        if player:
            row += " - "
            if enable_icons:
                row += "{0}".format(get_class_icon_string(
                    loot_entry.player().ingame_class(), loot_entry.player().role().spec_id()))
            row += "{0}".format(loot_entry.player().name())
        row += "\n"
        return row
    return "- No data available -"

@for_all_methods(trace)
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

    def __call__(self):
        return self.get()

@for_all_methods(trace)
class BasicCritical(RawEmbed):

    def __init__(self, message):
        self.build(
            None,
            "Critical Error",
            message,
            "https://cdn.discordapp.com/attachments/765089790295015425/766300558289666048/dkpbot-alert-error.png",
            14368774,
            None)
        self.add_field("\u200b", get_bot_links(), False)


class BasicError(RawEmbed):

    def __init__(self, message):
        self.build(
            None,
            "Error",
            message,
            "https://cdn.discordapp.com/attachments/765089790295015425/766300547589865472/dkpbot-alert-warning.png",
            15116570,
            None)
        self.add_field("\u200b", get_bot_links(), False)


class BasicSuccess(RawEmbed):

    def __init__(self, message):
        self.build(
            None,
            "Success",
            message,
            "https://cdn.discordapp.com/attachments/765089790295015425/766300574685593631/dkpbot-alert-success.png",
            2601546,
            None)
        self.add_field("\u200b", get_bot_links(), False)

@for_all_methods(trace)
class BasicInfo(RawEmbed):

    def __init__(self, message):
        self.build(
            None,
            "Info",
            message,
            "https://cdn.discordapp.com/attachments/765089790295015425/766304397508345856/dkpbot-alert-info.png",
            1735398,
            None)
        self.add_field("\u200b", get_bot_links(), False)

@for_all_methods(trace)
class BasicAnnouncement(RawEmbed):

    def __init__(self, message):
        self.build(
            None,
            "Announcement",
            message,
            "https://cdn.discordapp.com/attachments/765089790295015425/766304397508345856/dkpbot-alert-info.png",
            1735398,
            None)
        self.add_field("\u200b", get_bot_links(), False)

@for_all_methods(trace)
class SupporterResponse(RawEmbed):
    def __init__(self, title):
        self.build(
            None,
            title,
            "Thank you for using the **WoW DKP Bot**. Visit support server and donate to unlock powerful features and help keeping the bot actively developed.",
            "https://cdn.discordapp.com/avatars/746132320297156608/1d6c8788497eb6418c821e4d9450e06c.png",
            get_config_color(),
            None)
        self.add_field("\u200b", get_bot_links(), False)

@for_all_methods(trace)
class SupporterOnlyResponse(SupporterResponse):

    def __init__(self):
        super().__init__("Supporter only command")

@for_all_methods(trace)
class SupportReminder(SupporterResponse):

    def __init__(self):
        super().__init__("Unlock access to supporter commands for your server")

@for_all_methods(trace)
class BaseResponse:
    _embed = None
    _title = ""
    _date = ""
    _author = ""
    _comment = ""
    _isBuilt = False
    _rounding = 1

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

    def set_info(self, rounding):
        if isinstance(rounding, int) and rounding >= 0 and rounding <= 7:
            self._rounding = rounding

@for_all_methods(trace)
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

        dkp_format = "`{{0:.{0}f}} DKP`".format(self._rounding)
        self._embed.add_field("Current:", dkp_format.format(
            info.dkp()), False)
        self._embed.add_field("Lifetime gained:", dkp_format.format(
            info.lifetime_gained()), True)
        self._embed.add_field("Lifetime spent:", dkp_format.format(
            info.lifetime_spent()), True)
        history = info.get_latest_history_entry()
        self._embed.add_field("Last DKP award:",
                              generate_dkp_history_entry(history, get_history_format_string(
                                0 if history is None else history.width(), self._rounding, True), False, False), False)
        loot = info.get_latest_loot_entry()
        self._embed.add_field("Last received loot:",
                              generate_loot_entry(loot, get_loot_format_string(
                                0 if loot is None else loot.width(), self._rounding, True), False, False, False), False)

        return self

    def get(self):
        return self._embed.get()

@for_all_methods(trace)
class MultipleResponse(BaseResponse):
    __response_list = []
    __field_limit = 6
    __entry_limit = 32
    __response_limit = 0
    __multiple_columns = True
    _enable_icons = True
    _value_suffix = True
    _alternative_display_mode = False

    _value_format_string = "{0:8.1f}"

    def __init__(self, title, field_limit, entry_limit, response_limit, multiple_columns, enable_icons, value_suffix, alternative_display_mode):
        super().__init__(title)

        if field_limit and isinstance(field_limit, int):
            if field_limit > 16:
                self.__field_limit = 16
            elif field_limit < 1:
                self.__field_limit = 1
            else:
                self.__field_limit = field_limit

        if entry_limit and isinstance(entry_limit, int):
            if entry_limit > 32:
                self.__entry_limit = 32
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

        self._enable_icons = bool(enable_icons)

        self._value_suffix = bool(value_suffix)

        self._alternative_display_mode = bool(alternative_display_mode)

    def _prepare(self, data_list):  # pylint: disable=unused-argument
        pass

    def _override_response_loop(self, response_id):  # pylint: disable=unused-argument
        pass

    def _override_field_loop(self, response_id, field_id):  # pylint: disable=unused-argument
        pass

    def _build_row(self, data, requester):  # pylint: disable=unused-argument
        return str(data) + "\n"

    def _display_filter(self, data):  # pylint: disable=unused-argument
        return True

    def build(self, data_list_unfiltered, requester="", thumbnail=None):
        self._embed.clear()

        if not requester or not isinstance(requester, str):
            requester = ""

        if not isinstance(data_list_unfiltered, list):
            return None

        data_list = []
        for data in data_list_unfiltered:
            if self._display_filter(data):
                data_list.append(data)

        requester = requester.strip().capitalize()

        num_entries = len(data_list)

        # Cover very outdated database
        if num_entries == 0:
            data_list = data_list_unfiltered
            num_entries = len(data_list_unfiltered)

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

@for_all_methods(trace)
class DKPMultipleResponse(MultipleResponse):

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)

        float_extend = 0 if self._rounding == 0 else self._rounding + 1
        value_width = max(len(str(int(data_list_min.dkp()))),
                          len(str(int(data_list_max.dkp())))) + float_extend
        self._value_format_string = get_points_format_string(value_width, self._rounding, self._value_suffix)

    def _display_filter(self, data):
        if data and isinstance(data, PlayerInfo):
            return data.is_active()

        return False

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerInfo):
            if self._enable_icons:
                row = "{0}".format(get_class_icon_string(
                        data.ingame_class(), data.role().spec_id()))
            else:
                row = ""
        
            if self._alternative_display_mode:
                if requester == data.player().name():
                    row += "**{0}**".format(data.player().name())
                else:
                    row += "{0}".format(data.player().name())
                row += "\n"
                row += self._value_format_string.format(data.dkp())
            else:
                row += self._value_format_string.format(data.dkp())
                row += " "
                if requester == data.player().name():
                    row += "**{0}**".format(data.player().name())
                else:
                    row += "{0}".format(data.player().name())
            row += "\n"
            return row

        return ""

@for_all_methods(trace)
class HistoryMultipleResponse(MultipleResponse):

    __user = None

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)

        float_extend = 0 if self._rounding == 0 else self._rounding + 1
        value_width = max(len(str(int(data_list_min.dkp()))),
                          len(str(int(data_list_max.dkp())))) + float_extend
        #self._value_format_string = "`{{0:{0}.{1}f}}{2}`".format(value_width, self._rounding, " DKP" if self._value_suffix else "")
        self._value_format_string = get_history_format_string(
            value_width, self._rounding, self._value_suffix)

        for data in data_list:
            if data and isinstance(data, PlayerDKPHistory):
                self.__user = data.player().name()
                break

    # def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        if field_id == 0:
            self._embed.edit_field(field_id, self.__user)
        else:
            self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerDKPHistory):
            return generate_dkp_history_entry(data, self._value_format_string, self._enable_icons, self._alternative_display_mode)

        return ""

@for_all_methods(trace)
class PlayerLootMultipleResponse(MultipleResponse):

    __user = None

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)

        float_extend = 0 if self._rounding == 0 else self._rounding + 1
        value_width = max(len(str(int(data_list_min.dkp()))),
                          len(str(int(data_list_max.dkp())))) + float_extend
        self._value_format_string = get_loot_format_string(value_width, self._rounding, self._value_suffix)

        for data in data_list:
            if data and isinstance(data, PlayerLoot):
                self.__user = data.player().name()
                break

    # def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        if field_id == 0:
            self._embed.edit_field(field_id, self.__user)
        else:
            self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerLoot):
            return generate_loot_entry(data, self._value_format_string, self._enable_icons, self._alternative_display_mode, False)

        return ""

@for_all_methods(trace)
class LootMultipleResponse(MultipleResponse):

    __user = None

    def _prepare(self, data_list):
        # Prepare format string
        def get_dkp(i):
            return i.dkp()

        data_list_min = min(data_list, key=get_dkp)
        data_list_max = max(data_list, key=get_dkp)

        float_extend = 0 if self._rounding == 0 else self._rounding + 1
        value_width = max(len(str(int(data_list_min.dkp()))),
                          len(str(int(data_list_max.dkp())))) + float_extend
        self._value_format_string = get_loot_format_string(value_width, self._rounding, self._value_suffix)

        for data in data_list:
            if data and isinstance(data, PlayerLoot):
                self.__user = data.player().name()
                break

    # def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerLoot):
            return generate_loot_entry(data, self._value_format_string, self._enable_icons, self._alternative_display_mode, True)

        return ""
