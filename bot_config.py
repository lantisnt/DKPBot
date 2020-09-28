import os
from configparser import ConfigParser

from enum import Enum

from bot_utility import public_to_dict

DEFAULT_CONFIG = "/var/wowdkpbot-runner/default.ini"

class BotConfigType(Enum):
    SPECIFIC = 0  # Server specific ini
    DEFAULT = 1  # Default ini
    HARDCODED = 2  # Hardcoded

class GuildInfo():
    __bot_type = ''
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

class DisplayConfig(object):
    __max_fields = 0
    __max_entries_per_field = 0
    __max_separate_messages = 0
    __use_multiple_columns = False

    def __init__(self, max_fields, max_entries_per_field, max_separate_messages, use_multiple_columns):
        self.__max_fields = max_fields
        self.__max_entries_per_field = max_entries_per_field
        self.__max_separate_messages = max_separate_messages
        self.__use_multiple_columns = use_multiple_columns

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
        except ValueError:
            pass

    @staticmethod
    def __supported_max_fields():
        return (0, 6)

    def __get_max_fields(self):
        return self.__max_fields

    def __set_max_fields(self, max_fields):
        max_fields = int(max_fields)
        val = self.__supported_max_fields()
        if val[0] <= max_fields <= val[1]:
            self.__max_fields = max_fields

    max_fields = property(__get_max_fields, __set_max_fields)

    @staticmethod
    def __supported_max_entries_per_field():
        return (1, 16)

    def __get_max_entries_per_field(self):
        return self.__max_entries_per_field

    def __set_max_entries_per_field(self, max_entries_per_field):
        max_entries_per_field = int(max_entries_per_field)
        val = self.__supported_max_entries_per_field()
        if val[0] <= max_entries_per_field <= val[1]:
            self.__max_entries_per_field = max_entries_per_field

    max_entries_per_field = property(__get_max_entries_per_field, __set_max_entries_per_field)

    @staticmethod
    def __supported_max_separate_messages():
        return (1, 16)

    def __get_max_separate_messages(self):
        return self.__max_separate_messages

    def __set_max_separate_messages(self, max_separate_messages):
        max_separate_messages = int(max_separate_messages)
        val = self.__supported_max_separate_messages()
        if val[0] <= max_separate_messages <= val[1]:
            self.__max_separate_messages = max_separate_messages

    max_separate_messages = property(__get_max_separate_messages, __set_max_separate_messages)

    @staticmethod
    def __supported_use_multiple_columns():
        return [True, False]

    def __get_use_multiple_columns(self):
        return self.__use_multiple_columns

    def __set_use_multiple_columns(self, use_multiple_columns):
        use_multiple_columns = str(use_multiple_columns)
        if use_multiple_columns.lower() == 'true':
            self.__use_multiple_columns = True
        elif use_multiple_columns.lower() == 'false':
            self.__use_multiple_columns = False

    use_multiple_columns = property(__get_use_multiple_columns, __set_use_multiple_columns)

    def __str__(self):
        string = ""
        
        attributes = public_to_dict(self)
        for attr in attributes:
            # Config name
            string += "**{0}**".format(attr.capitalize().replace("_", " "))
            # Config value
            string += "\n`{0}`".format(attr.replace("_", "-"))
            # Current value
            string += "\ncurrent: `{0}`".format(attributes[attr])
            # Supported values - if we have
            supported_values = getattr(self, "_" + self.__class__.__name__ + "__supported_" + attr, None)
            if supported_values is None or not callable(supported_values):
                string += "\n"
                continue
            # Supported values
            supported_values = supported_values()
            if supported_values is not None:
                string += "\nsupported values:"
            if isinstance(supported_values, tuple):
                # Tuple = from [0] to [1]
                string += " `from {0} to {1}`".format(supported_values[0], supported_values[1])
            elif isinstance(supported_values, list):
                string += ' `'
                for element in supported_values:
                    string += "{0} ".format(element)
                string = string.rstrip()
                string += '`'
            #elif isinstance(supported_values, (str, int, float)):
            else:
                string += " `{0}`".format(supported_values)
            string += "\n"
        return string

class BotConfig():
    __type = BotConfigType.HARDCODED
    __filepath = ""
    __config = None

    guild_info = GuildInfo('essential', 0, 'EssentialDKP.lua', '!', False)
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
            print("Error loading DEFAULT_CONFIG file. Falling back to hardcoded settings.")


    # Load from config to dictionary
    def __load(self):
        self.guild_info = GuildInfo(
            self.__config.get('Guild Info', 'bot_type', fallback='essential'),
            self.__config.getint('Guild Info', 'file_upload_channel', fallback=0),
            self.__config.get('Guild Info', 'filename', fallback='EssentialDKP.lua'),
            self.__config.get('Guild Info', 'prefix', fallback='!'),
            self.__config.getboolean('Guild Info', 'premium', fallback=False),
        )

        display_configs = {
            'DKP Display': self.dkp,
            'DKP History Display': self.dkp_history,
            'Loot History Display': self.loot_history,
            'Latest Loot Display': self.latest_loot,
            'Item Search Display': self.item_search
        }

        for group in display_configs:
            display_configs[group] = DisplayConfig(
                self.__config.getint(group, 'max_fields', fallback=1),
                self.__config.getint(group, 'max_entries_per_field', fallback=1),
                self.__config.getint(group, 'max_separate_messages', fallback=1),
                self.__config.getboolean(group, 'use_multiple_columns', fallback=False)
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

    def default(self):
        result = self.__config.read(DEFAULT_CONFIG)
        if DEFAULT_CONFIG in result:
            self.__load()
            self.__type = BotConfigType.DEFAULT

        self.store()


    @staticmethod
    def get_directly_accessible_configs():
        return ['dkp', 'dkp_history', 'loot_history', 'latest_loot', 'item_search']

    def __str__(self):
        string = ""
        string += str((self.guild_info)) + "\n"
        string += str((self.dkp)) + "\n"
        string += str((self.dkp_history)) + "\n"
        string += str((self.loot_history)) + "\n"
        string += str((self.latest_loot)) + "\n"
        string += str((self.item_search)) + "\n"

        return string
