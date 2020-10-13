import os
from configparser import ConfigParser
from bot_logger import BotLogger

from enum import Enum

from bot_utility import public_to_dict

DEFAULT_CONFIG = "/var/wowdkpbot-runner/default.ini"

def get_row_format():
    return  "{0:17} | {1:5} | {2:17}"

class BotConfigType(Enum):
    SPECIFIC = 0  # Server specific ini
    DEFAULT = 1  # Default ini
    HARDCODED = 2  # Hardcoded

class GuildInfo():
    bot_type = ''
    file_upload_channel = 0
    announcement_channel = 0
    filename = ''
    prefix = "!"
    premium = False
    server_side = ''
    guild_name = ''
    channel_team_map = '{}'

    def __init__(self, bot_type, file_upload_channel, announcement_channel, filename, prefix, premium, server_side, guild_name, channel_team_map):
        self.bot_type = bot_type
        self.file_upload_channel = file_upload_channel
        self.announcement_channel = announcement_channel
        self.filename = filename
        self.prefix = prefix
        self.premium = bool(premium)
        self.server_side = server_side
        self.guild_name = guild_name
        self.channel_team_map = channel_team_map

class DisplayConfig(object):
    __fields = 0
    __entries_per_field = 0
    __separate_messages = 0
    __multiple_columns = False

    def __init__(self, fields, entries_per_field, separate_messages, multiple_columns):
        self.__fields = fields
        self.__entries_per_field = entries_per_field
        self.__separate_messages = separate_messages
        self.__multiple_columns = bool(multiple_columns)

    def __getattr__(self, name):
        if not name.startswith('__get_') and hasattr(self,'__get_' + name):
            return getattr(self,'__get_' + name)()

        raise AttributeError("no such attribute: {0}".format(name))

    def __setattr__(self, name, value):
        try:
            try:
                return getattr(self,'__set_' + name)(value)
            except AttributeError:
                return super(DisplayConfig,self).__setattr__(name, value)
        except ValueError as exception:
            BotLogger().get().error(exception, exc_info=True)

    @staticmethod
    def __supported_fields():
        return (1, 9)

    def __get_fields(self):
        return self.__fields

    def __set_fields(self, fields):
        fields = int(fields)
        val = self.__supported_fields()
        if val[0] <= fields <= val[1]:
            self.__fields = fields

    fields = property(__get_fields, __set_fields)

    @staticmethod
    def __supported_entries_per_field():
        return (1, 16)

    def __get_entries_per_field(self):
        return self.__entries_per_field

    def __set_entries_per_field(self, entries_per_field):
        entries_per_field = int(entries_per_field)
        val = self.__supported_entries_per_field()
        if val[0] <= entries_per_field <= val[1]:
            self.__entries_per_field = entries_per_field

    entries_per_field = property(__get_entries_per_field, __set_entries_per_field)

    @staticmethod
    def __supported_separate_messages():
        return (0, 16)

    def __get_separate_messages(self):
        return self.__separate_messages

    def __set_separate_messages(self, separate_messages):
        separate_messages = int(separate_messages)
        val = self.__supported_separate_messages()
        if val[0] <= separate_messages <= val[1]:
            self.__separate_messages = separate_messages

    separate_messages = property(__get_separate_messages, __set_separate_messages)

    @staticmethod
    def __supported_multiple_columns():
        return [True, False]

    def __get_multiple_columns(self):
        return self.__multiple_columns

    def __set_multiple_columns(self, multiple_columns):
        multiple_columns = str(multiple_columns)
        if multiple_columns.lower() == 'true':
            self.__multiple_columns = True
        elif multiple_columns.lower() == 'false':
            self.__multiple_columns = False

    multiple_columns = property(__get_multiple_columns, __set_multiple_columns)

    def __str__(self):
        row_format = get_row_format()
        string = ""
        attributes = public_to_dict(self)
        for attr in attributes:
            supported_values_string = ""
            supported_values = getattr(self, "_" + self.__class__.__name__ + "__supported_" + attr, None)
            if supported_values is not None and callable(supported_values):
                supported_values = supported_values()

            if isinstance(supported_values, tuple):
                supported_values_string = "from {0} to {1}".format(supported_values[0], supported_values[1])
            elif isinstance(supported_values, list):
                for element in supported_values:
                    supported_values_string += "{0} ".format(element)
                supported_values_string = supported_values_string.rstrip()
            else:
                supported_values_string = " {0}".format(supported_values)

            current = attributes[attr]
            if isinstance(current, bool):
                current = "True" if current else "False"

            string += row_format.format(attr.replace("_", "-"), current, supported_values_string) + "\n"
        return string

class BotConfig():
    __type = BotConfigType.HARDCODED
    __filepath = ""
    __config = None

    guild_info = GuildInfo('essential', 0, 0, 'EssentialDKP.lua', '!', False, '', '','{}')
    dkp = DisplayConfig(6, 16, 5, True)
    dkp_history = DisplayConfig(1, 10, 1, True)
    loot_history = DisplayConfig(1, 10, 1, True)
    latest_loot = DisplayConfig(6, 5, 1, False)
    item_search = DisplayConfig(6, 5, 3, False)

    def __init__(self, filepath):
        self.__filepath = filepath
        self.__config = ConfigParser()

        if os.path.isfile(filepath):
            result = self.__config.read(filepath)
            if filepath in result:
                self.__load()
                self.__type = BotConfigType.SPECIFIC
                return
            else:
                BotLogger().get().warning("Server specific config {0} not loaded.".format(filepath))
        else:
            BotLogger().get().warning("Server specific config {0} not found.".format(filepath))

        result = self.__config.read(DEFAULT_CONFIG)
        if DEFAULT_CONFIG in result:
            self.__load()
            self.__type = BotConfigType.DEFAULT
            return
        else:
            BotLogger().get().error("Error loading DEFAULT_CONFIG file.")


    # Load from config to dictionary
    def __load(self):
        group = 'Guild Info'
        self.guild_info = GuildInfo(
            self.__config.get(group, 'bot_type', fallback='essential'),
            self.__config.getint(group, 'file_upload_channel', fallback=0),
            self.__config.getint(group, 'announcement_channel', fallback=0),
            self.__config.get(group, 'filename', fallback='EssentialDKP.lua'),
            self.__config.get(group, 'prefix', fallback='!'),
            self.__config.getboolean(group, 'premium', fallback=False),
            self.__config.get(group, 'server_side', fallback=''),
            self.__config.get(group, 'guild_name', fallback=''),
            self.__config.get(group, 'channel_team_map', fallback='{}')
        )

        group = 'DKP Display'
        self.dkp = DisplayConfig(
            self.__config.getint(group, 'fields', fallback=1),
            self.__config.getint(group, 'entries_per_field', fallback=1),
            self.__config.getint(group, 'separate_messages', fallback=1),
            self.__config.getboolean(group, 'multiple_columns', fallback=False)
        )

        group = 'DKP History Display'
        self.dkp_history = DisplayConfig(
            self.__config.getint(group, 'fields', fallback=1),
            self.__config.getint(group, 'entries_per_field', fallback=1),
            self.__config.getint(group, 'separate_messages', fallback=1),
            self.__config.getboolean(group, 'multiple_columns', fallback=False)
        )

        group = 'Loot History Display'
        self.loot_history = DisplayConfig(
            self.__config.getint(group, 'fields', fallback=1),
            self.__config.getint(group, 'entries_per_field', fallback=1),
            self.__config.getint(group, 'separate_messages', fallback=1),
            self.__config.getboolean(group, 'multiple_columns', fallback=False)
        )

        group = 'Latest Loot Display'
        self.latest_loot = DisplayConfig(
            self.__config.getint(group, 'fields', fallback=1),
            self.__config.getint(group, 'entries_per_field', fallback=1),
            self.__config.getint(group, 'separate_messages', fallback=1),
            self.__config.getboolean(group, 'multiple_columns', fallback=False)
        )

        group = 'Item Search Display'
        self.item_search = DisplayConfig(
            self.__config.getint(group, 'fields', fallback=1),
            self.__config.getint(group, 'entries_per_field', fallback=1),
            self.__config.getint(group, 'separate_messages', fallback=1),
            self.__config.getboolean(group, 'multiple_columns', fallback=False)
        )

    # Store from config to dictionary
    def __store(self):
        section_variable_mapping = {
            'Guild Info': self.guild_info,
            'DKP Display': self.dkp,
            'DKP History Display': self.dkp_history,
            'Loot History Display': self.loot_history,
            'Latest Loot Display': self.latest_loot,
            'Item Search Display': self.item_search
        }

        for section, variable in section_variable_mapping.items():
            for option, value in public_to_dict(variable).items():
                if not self.__config.has_section(section):
                    self.__config.add_section(section)
                self.__config.set(section, str(option), str(value))

    def store(self):
        with open(self.__filepath, "w") as file:
            self.__store()
            self.__config.write(file, space_around_delimiters=False)

    def default(self, retain_premium=True):
        is_premium = self.guild_info.premium
        result = self.__config.read(DEFAULT_CONFIG)
        if DEFAULT_CONFIG in result:
            self.__load()
            self.__type = BotConfigType.DEFAULT

        self.guild_info.premium = (is_premium and retain_premium)

        self.store()

    @staticmethod
    def get_directly_accessible_configs():
        return ['dkp', 'dkp_history', 'loot_history', 'latest_loot', 'item_search']

    def get_configs_data(self):
        return {
            'dkp' : {
                'title' : "Multiple players DKP Display",
                'value' : str(self.dkp)
            },
            'dkp-history' : {
                'title' : "Player DKP history",
                'value' : str(self.dkp_history)
            },
            'loot-history' : {
                'title' : "Player loot history",
                'value' : str(self.loot_history)
            },
            'latest-loot' : {
                'title' : "Latest raid loot",
                'value' : str(self.latest_loot)
            },
            'item-search'  : {
                'title' : "Item search results",
                'value' : str(self.item_search)
            },
        }
