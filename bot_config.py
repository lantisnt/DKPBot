import os
from configparser import ConfigParser

from enum import Enum

DEFAULT_CONFIG = "default.ini"

def public_to_dict(o):
    d = {}
    a = filter(lambda x: not str(x).startswith("_"), dir(o))
    for i in a:
        d[i] = getattr(o, i)
    return d

class BotConfigType(Enum):
    SPECIFIC  = 0 # Server specific ini
    DEFAULT   = 1 # Default ini
    HARDCODED = 2 # Hardcoded

class GuildInfo():
    BotType = ''
    FileUploadChannel = 0
    FileName = ''
    Premium = False
    
    def __init__(self, BotType, FileUploadChannel, FileName, Premium):
        self.BotType = BotType
        self.FileUploadChannel = FileUploadChannel
        self.FileName = FileName
        self.Premium = bool(Premium)

class DisplayConfig():
    MaxFields = 0
    MaxEntriesPerField = 0
    MaxSeparateMessages = 0
    UseMultipleColumns = False
    
    def __init__(self, MaxFields, MaxEntriesPerField, MaxSeparateMessages, UseMultipleColumns):
        self.MaxFields = MaxFields
        self.MaxEntriesPerField = MaxEntriesPerField
        self.MaxSeparateMessages = MaxSeparateMessages
        self.UseMultipleColumns = UseMultipleColumns

class BotConfig():
    __type = BotConfigType.HARDCODED
    __filepath = ""
    __config = None

    GuildInfo = GuildInfo('EssentialDKP', 0, 'EssentialDKP.lua', False)
    DKP = DisplayConfig(6, 16, 5, True)
    DKPHistory = DisplayConfig(1, 10, 1, True)
    LootHistory = DisplayConfig(1, 10, 1, True)
    LatestLoot = DisplayConfig(6, 5, 1, False)
    ItemSearch = DisplayConfig(6, 5, 3, False)

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

    ## Load from config to dictionary
    def __load(self):
        self.GuildInfo = GuildInfo(
            self.__config.get('Guild Info', 'BotType', fallback = 'EssentialDKP'),
            self.__config.getint('Guild Info', 'FileUploadChannel', fallback = 0),
            self.__config.get('Guild Info', 'FileName', fallback = 'EssentialDKP.lua'),
            self.__config.getint('Guild Info', 'Premium', fallback = False),
        )
        self.DKP = DisplayConfig(
            self.__config.getint('DKP Display', 'MaxFields', fallback = 1),
            self.__config.getint('DKP Display', 'MaxEntriesPerField', fallback = 1),
            self.__config.getint('DKP Display', 'MaxSeparateMessages', fallback = 1),
            self.__config.getboolean('DKP Display', 'UseMultipleColumns', fallback = False)
        )
        self.DKPHistory = DisplayConfig(
            self.__config.getint('DKP History Display', 'MaxFields', fallback = 1),
            self.__config.getint('DKP History Display', 'MaxEntriesPerField', fallback = 1),
            self.__config.getint('DKP History Display', 'MaxSeparateMessages', fallback = 1),
            self.__config.getboolean('DKP History Display', 'UseMultipleColumns', fallback = False)
        )
        self.LootHistory = DisplayConfig(
            self.__config.getint('Loot History Display', 'MaxFields', fallback = 1),
            self.__config.getint('Loot History Display', 'MaxEntriesPerField', fallback = 1),
            self.__config.getint('Loot History Display', 'MaxSeparateMessages', fallback = 1),
            self.__config.getboolean('Loot History Display', 'UseMultipleColumns', fallback = False)
        )
        self.LatestLoot = DisplayConfig(
            self.__config.getint('Latest Loot Display', 'MaxFields', fallback = 1),
            self.__config.getint('Latest Loot Display', 'MaxEntriesPerField', fallback = 1),
            self.__config.getint('Latest Loot Display', 'MaxSeparateMessages', fallback = 1),
            self.__config.getboolean('Latest Loot Display', 'UseMultipleColumns', fallback = False)
        )
        self.ItemSearch = DisplayConfig(
            self.__config.getint('Item Search Display', 'MaxFields', fallback = 1),
            self.__config.getint('Item Search Display', 'MaxEntriesPerField', fallback = 1),
            self.__config.getint('Item Search Display', 'MaxSeparateMessages', fallback = 1),
            self.__config.getboolean('Item Search Display', 'UseMultipleColumns', fallback = False)
        )

    ## Store from config to dictionary
    def __store(self):

        section_variable_mapping = {
            'Guild Info' : self.GuildInfo,
            'DKP Display' : self.DKP,
            'DKP History Display' : self.DKPHistory,
            'Loot History Display' : self.LootHistory,
            'Latest Loot Display' : self.LatestLoot,
            'Item Search Display' : self.ItemSearch
        }

        for section, variable in section_variable_mapping.items():
            for option, value in public_to_dict(variable).items():
                if not self.__config.has_section(section):
                    self.__config.add_section(section)
                self.__config.set(section, str(option), str(value))

    def Store(self):
        with open(self.__filepath, "w") as file:
            self.__store()
            self.__config.write(file, space_around_delimiters=False)

    def __str__(self):
        s = ""
        s += str(self.__type) + "\n"
        s += str(self.__filepath) + "\n"

        s += str(public_to_dict(self.GuildInfo)) + "\n"
        s += str(public_to_dict(self.DKP)) + "\n"
        s += str(public_to_dict(self.DKPHistory)) + "\n"
        s += str(public_to_dict(self.LootHistory)) + "\n"
        s += str(public_to_dict(self.LatestLoot)) + "\n"
        s += str(public_to_dict(self.ItemSearch)) + "\n"
        return s