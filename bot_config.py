import os
from configparser import ConfigParser

from enum import Enum

DEFAULT_CONFIG = "default.ini"


def public_to_dict(obj):
    dictionary = {}
    public = filter(lambda x: not str(x).startswith("_"), dir(obj))
    for attr in public:
        dictionary[attr] = getattr(obj, attr)
    return dictionary


class BotConfigType(Enum):
    SPECIFIC = 0  # Server specific ini
    DEFAULT = 1  # Default ini
    HARDCODED = 2  # Hardcoded


class GuildInfo():
    bot_type = ''
    file_upload_channel = 0
    filename = ''
    prefix = "!"
    premium = False

    def __init__(self, bot_type, file_upload_channel, filename, prefix, premium):
        self.bot_type = bot_type
        self.file_upload_channel = file_upload_channel
        self.filename = filename
        self.prefix = prefix
        self.premium = bool(premium)

class DisplayConfig():
    max_fields = 0
    max_entries_per_field = 0
    max_separate_messages = 0
    use_multiple_columns = False

    def __init__(self, max_fields, max_entries_per_field, max_separate_messages, use_multiple_columns):
        self.max_fields = max_fields
        self.max_entries_per_field = max_entries_per_field
        self.max_separate_messages = max_separate_messages
        self.use_multiple_columns = use_multiple_columns


class BotConfig():
    __type = BotConfigType.HARDCODED
    __filepath = ""
    __config = None

    guild_info = GuildInfo('EssentialDKP', 0, 'EssentialDKP.lua', '!', False)
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

        result = self.__config.read(DEFAULT_CONFIG)
        if DEFAULT_CONFIG in result:
            self.__load()
            self.__type = BotConfigType.DEFAULT
            return
        else:
            print("Error loading DEFAULT_CONFIG file")

    # Load from config to dictionary
    def __load(self):
        self.guild_info = GuildInfo(
            self.__config.get('Guild Info', 'BotType', fallback='EssentialDKP'),
            self.__config.getint('Guild Info', 'FileUploadChannel', fallback=0),
            self.__config.get('Guild Info', 'FileName', fallback='EssentialDKP.lua'),
            self.__config.getint('Guild Info', 'Prefix', fallback='!'),
            self.__config.getint('Guild Info', 'Premium', fallback=False),
        )
        self.dkp = DisplayConfig(
            self.__config.getint('DKP Display', 'MaxFields', fallback=1),
            self.__config.getint('DKP Display', 'MaxEntriesPerField', fallback=1),
            self.__config.getint('DKP Display', 'MaxSeparateMessages', fallback=1),
            self.__config.getboolean('DKP Display', 'UseMultipleColumns', fallback=False)
        )
        self.dkp_history = DisplayConfig(
            self.__config.getint('DKP History Display', 'MaxFields', fallback=1),
            self.__config.getint('DKP History Display', 'MaxEntriesPerField', fallback=1),
            self.__config.getint('DKP History Display', 'MaxSeparateMessages', fallback=1),
            self.__config.getboolean('DKP History Display', 'UseMultipleColumns', fallback=False)
        )
        self.loot_history = DisplayConfig(
            self.__config.getint('Loot History Display', 'MaxFields', fallback=1),
            self.__config.getint('Loot History Display', 'MaxEntriesPerField', fallback=1),
            self.__config.getint('Loot History Display', 'MaxSeparateMessages', fallback=1),
            self.__config.getboolean('Loot History Display', 'UseMultipleColumns', fallback=False)
        )
        self.latest_loot = DisplayConfig(
            self.__config.getint('Latest Loot Display', 'MaxFields', fallback=1),
            self.__config.getint('Latest Loot Display', 'MaxEntriesPerField', fallback=1),
            self.__config.getint('Latest Loot Display', 'MaxSeparateMessages', fallback=1),
            self.__config.getboolean('Latest Loot Display', 'UseMultipleColumns', fallback=False)
        )
        self.item_search = DisplayConfig(
            self.__config.getint('Item Search Display', 'MaxFields', fallback=1),
            self.__config.getint('Item Search Display', 'MaxEntriesPerField', fallback=1),
            self.__config.getint('Item Search Display', 'MaxSeparateMessages', fallback=1),
            self.__config.getboolean('Item Search Display', 'UseMultipleColumns', fallback=False)
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

    def __str__(self):
        string = ""
        string += str(self.__type) + "\n"
        string += str(self.__filepath) + "\n"

        string += str(public_to_dict(self.guild_info)) + "\n"
        string += str(public_to_dict(self.dkp)) + "\n"
        string += str(public_to_dict(self.dkp_history)) + "\n"
        string += str(public_to_dict(self.loot_history)) + "\n"
        string += str(public_to_dict(self.latest_loot)) + "\n"
        string += str(public_to_dict(self.item_search)) + "\n"
        return string
