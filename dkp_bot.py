import argparse, re, pytz
from datetime import datetime, timezone
from enum import Enum

from savedvariables_parser import SavedVariablesParser
from bot_config import BotConfig

class ResponseStatus(Enum):
    SUCCESS = 0
    ERROR = 1
    REQUEST = 2
    IGNORE = 3


class Request(Enum):
    NONE = 0
    CHANNEL_ID = 1
    ATTACHEMENT = 2


class Response:
    status = ResponseStatus.IGNORE
    # Response on SUCCESS
    # Error information on ERROR
    # Request type on REQUEST
    # None on IGNORE
    message = None
    dm = False

    def __init__(self, status=ResponseStatus.IGNORE, data=None, dm=False):
        self.status = status
        self.data = data
        self.dm = bool(dm)


class DKPBot:
    __inputFileName = ""
    __channel = 0
    __enabled = False
    __parser = None
    __db = {}

    def __init__(self, config: BotConfig):
        self.__inputFileName = config.GuildInfo.FileName
        self.__channel = int(config.GuildInfo.FileUploadChannel)
        self.__db = {
            # Database for all global data indexed by player name. Unsorted.
            'global': {},
            'group': {},   # Database for all grouped data. Indexed by group name. Sorted by DKP value descending
            'time': 0,
            'info': {}
        }

    def Enable(self):
        self.__enabled = True

    def Disable(self):
        self.__enabled = False

    def IsEnabled(self):
        return (self.__enabled == True)

    def RegisterChannel(self, channel):
        self.__channel = channel

    def IsChannelRegistered(self):
        return (self.__channel != 0)

    def CheckChannel(self, channel):
        #return (self.__channel == channel)
        return True

    def CheckAttachmentName(self, filename):
        return (self.__inputFileName == filename)

    def IsDatabaseLoaded(self):
        return (len(self.__db) > 0)

    ### Command handling and parsing ###

    def __getCommandParser(self):
        if not(self.__parser and isinstance(self.__parser, argparse.ArgumentParser)):
            self.__parser = argparse.ArgumentParser(
                description='Process commands.')
            self.__parser.add_argument(
                'command', metavar='command', type=str, help='Actual command', nargs='?', default=None)
            self.__parser.add_argument(
                'param', metavar='param', type=str, help='Command parameter', nargs='*', default=None)
#            self.__parser.add_argument('varargs', metavar='varargs', type=str,
#                                       help='All other string values will be put here', nargs='*', default=None)
        return self.__parser

    def __parseCommand(self, string):
        if string:
            return self.__getCommandParser().parse_args(string.split())
        else:
            return None

    def __handleCommand(self, command, param, requester_info):
        method = ''
        dm = False
        if command[0] == '?':
            method = 'help_'
        elif command[0] == '!':
            method = 'call_'
            if command[1] == '!':
                dm = True # direct message
                method += command[2:] #remove second ! also
            else:
                method += command[1:]
        else:
            return Response(ResponseStatus.IGNORE)

        callback = getattr(self, method, None)
        if callback and callable(callback):
            response = callback(param, requester_info) # pylint: disable=not-callable

            response.dm = dm

            return response
        else:
            return Response(ResponseStatus.IGNORE)

    def Handle(self, message, requester_info):
        args = self.__parseCommand(message)
        if args:
            if args.command:
                if not args.param:
                    if not requester_info or not requester_info.get('name'):
                        return Response(ResponseStatus.ERROR, "No param and no author. How?")
                    args.param = [requester_info.get('name')]
                args.param = " ".join(args.param)
                return self.__handleCommand(args.command.lower(), args.param.lower(), requester_info)
            else:
                # Empty message, attachement only probably
                return Response(ResponseStatus.IGNORE)
        else:
            # Empty message, attachement only probably
            return Response(ResponseStatus.IGNORE)

    ### File handling and parsing ###

    def __getSavedVariables(self, inputString):
        return SavedVariablesParser().ParseString(inputString)

    def _dbGetInfo(self):
        return self.__db['info']

    def _buildDkpDatabase(self, sv):
        self.__db['global']['dkp'] = {}
        self.__db['group'] = {}

    def _buildLootDatabase(self, sv):
        self.__db['global']['loot'] = []
        self.__db['global']['player_loot'] = {}

    def _buildHistoryDatabase(self, sv):
        self.__db['global']['history'] = {}

    def _finalizeDatabase(self):
        return

    def _getDkp(self, player):
        return self.__db['global']['dkp'].get(player.lower())

    def _getPlayerLoot(self, player):
        return self.__db['global']['player_loot'].get(player.lower())

    def _getLoot(self,):
        return self.__db['global']['loot']

    def _getHistory(self, player):
        return self.__db['global']['history'].get(player.lower())

    def _setDkp(self, player, entry):
        self.__db['global']['dkp'][player.lower()] = entry

    def _addLoot(self, entry):
        self.__db['global']['loot'].append(entry)

    def _sortLoot(self, newest=True):
            self.__db['global']['loot'].sort(
                key=lambda info: info.Timestamp(), reverse=bool(newest))

    def _findLoot(self, keyword):
        if not keyword or not isinstance(keyword, str) or len(keyword) == 0:
            return list()

        loot_pattern = re.compile(keyword.strip(), flags=re.IGNORECASE)

        def get_loot_if_matching(entry):
            if loot_pattern.search(entry.ItemName()) != None:
                return entry
            
            return None

        l = list(map(get_loot_if_matching, self.__db['global']['loot']))
        return list(filter(None, l))


    def _addPlayerLoot(self, player, entry):
        if player and player != "":
            player = player.lower()
            player_loot = self.__db['global']['player_loot'].get(player)
            if not player_loot:
                self.__db['global']['player_loot'][player] = []
            self.__db['global']['player_loot'][player].append(entry)

    def _sortPlayerLoot(self, newest=True, player=None):
        if self.__db['global']['player_loot'].get(player):
            self.__db['global']['player_loot'][player].sort(
                key=lambda info: info.Timestamp(), reverse=bool(newest))
        else:
            for p in self.__db['global']['player_loot'].values():
                p.sort(key=lambda info: info.Timestamp(), reverse=bool(newest))

    def _addHistory(self, player, entry):
        if player and player != "":
            player = player.lower()
            player_history = self.__db['global']['history'].get(player)
            if not player_history:
                self.__db['global']['history'][player] = []
            self.__db['global']['history'][player].append(entry)

    def _sortHistory(self, newest=True, player=None):
        if self.__db['global']['history'].get(player):
            self.__db['global']['history'][player].sort(
                key=lambda info: info.Timestamp(), reverse=bool(newest))
        else:
            for p in self.__db['global']['history'].values():
                p.sort(key=lambda info: info.Timestamp(), reverse=bool(newest))

    def _sortGroupDkp(self, group=None):
        if self.__db['group'].get(group):
            self.__db['group'][group].sort(
                key=lambda info: info.Dkp(), reverse=True)
        else:
            for g in self.__db['group'].values():
                g.sort(key=lambda info: info.Dkp(), reverse=True)

    def _setGroupDkp(self, group, entry, sort=False):
        if group:
            group = group.lower()
            if not group in self.__db['group']:
                self.__db['group'][group] = []
            self.__db['group'][group].append(entry)
            if sort and sort == True:
                self._sortGroupDkp(group)

    def _getGroupDkp(self, group):
        if group:
            return self.__db['group'].get(group.lower())

        return None

    def _setPlayerLatestLoot(self):
        for p in self.__db['global']['dkp'].values():
            loot = self._getPlayerLoot(p.Player())
            if loot and isinstance(loot, list):
                p.SetLatestLootEntry(loot[0])

    def _setPlayerLatestHistory(self):
        for p in self.__db['global']['dkp'].values():
            history = self._getHistory(p.Player())
            if history and isinstance(history, list):
                p.SetLatestHistoryEntry(history[0])

    def _setPlayerLatestPositiveHistoryAndActivity(self, inactive_time = 200000000000):
        now = int(datetime.now(tz=timezone.utc).timestamp())
        for p in self.__db['global']['dkp'].values():
            history = self._getHistory(p.Player())
            if history and isinstance(history, list):
                for history_entry in history:
                    if history_entry.Dkp() > 0:
                        p.SetLatestHistoryEntry(history_entry)
                        if abs(now - history_entry.Timestamp()) > inactive_time:
                            p.SetInactive()
                        break

    def BuildDatabase(self, inputString, info):
        print('Building database')

        start = int(datetime.now(tz=timezone.utc).timestamp())

        sv = self.__getSavedVariables(inputString)
        if sv == None:
            return Response(ResponseStatus.ERROR, "Error Parsing .lua file.")

        if not isinstance(sv, dict):
            return Response(ResponseStatus.ERROR, "No SavedVariables found in .lua file.")

        self.__db['info']['comment'] = info.get('comment')
        self.__db['info']['date'] = info.get('date')
        self.__db['info']['author'] = info.get('author')

        self._buildDkpDatabase(sv)
        self._buildLootDatabase(sv)
        self._buildHistoryDatabase(sv)

        self._finalizeDatabase()

        print('Building complete in {0} seconds'.format(
            int(datetime.now(tz=timezone.utc).timestamp()) - start))

        if len(self.__db['global']['dkp']) <= 0:
            # for table in self.__db['global']:
            #    if len(table) <= 0:
            return Response(ResponseStatus.SUCCESS, "(DKP) Database building failed.")

        if len(self.__db['global']['history']) <= 0:
            return Response(ResponseStatus.SUCCESS, "(DKP History) Database building failed.")

        return Response(ResponseStatus.SUCCESS, "Database building complete.")

    def ReloadData(self):
        return Response(ResponseStatus.REQUEST, Request.ATTACHEMENT)

    ### Command callbacks ###

    def call_dkpmanage(self, param, requester_info):
        if requester_info.get('is_privileged') != True:
            return Response(ResponseStatus.IGNORE)

        if param == 'register':
            return Response(ResponseStatus.REQUEST, Request.CHANNEL_ID)

        if param == 'reload':
            return self.ReloadData()

        return Response(ResponseStatus.SUCCESS, "Sorry :frowning: !dkpmanage {0} is not yet implemented.".format(str(requester_info.get('name'))))
