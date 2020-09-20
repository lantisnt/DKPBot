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
    GuildId = 0
    BotType = ''
    FileUploadChannel = 0
    FileName = ''
    
    def __init__(self, GuildId, BotType, FileUploadChannel, FileName):
        self.GuildId = GuildId
        self.BotType = BotType
        self.FileUploadChannel = FileUploadChannel
        self.FileName = FileName

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

    GuildInfo = GuildInfo(0, 'EssentialDKP', 0, 'EssentialDKP.lua')
    DKP = DisplayConfig(6, 16, 5, True)
    DKPHistory = DisplayConfig(1, 10, 1, True)
    LootHistory = DisplayConfig(1, 10, 1, True)
    LatestLoot = DisplayConfig(6, 5, 1, False)
    ItemSearch = DisplayConfig(6, 5, 3, False)

    def __init__(self, filepath):
        self.__filepath = filepath

        if not os.path.isfile(filepath):
            return

        self.__config = ConfigParser()
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
            self.__config.getint('Guild Info', 'GuildId', fallback = 0),
            self.__config.get('Guild Info', 'BotType', fallback = 'EssentialDKP'),
            self.__config.getint('Guild Info', 'FileUploadChannel', fallback = 0),
            self.__config.get('Guild Info', 'FileName', fallback = 'EssentialDKP.lua')
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
        self.__config['Guild Info'] = public_to_dict(self.GuildInfo)
        self.__config['DKP Display'] = public_to_dict(self.DKP)
        self.__config['DKP History Display'] = public_to_dict(self.DKPHistory)
        self.__config['Loot History Display'] = public_to_dict(self.LootHistory)
        self.__config['Latest Loot Display'] = public_to_dict(self.LatestLoot)
        self.__config['Item Search Display'] = public_to_dict(self.ItemSearch)

    def Store(self):
        if not os.path.isfile(self.__filepath):
            return
        
        with open(self.__filepath, "w") as file:
            self.__store()
            self.__config.write(file, space_around_delimiters=False)