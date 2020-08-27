import argparse
import time

from enum import Enum

from savedvariables_parser import SavedVariablesParser

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
    
    def __init__(self, status = ResponseStatus.IGNORE, data = None):
        self.status = status
        self.data = data

class DKPBot:
    __inputFileName = ""
    __channel = 0
    __enabled = False
    __parser = None
    __db = { }

    def __init__(self, inputFileName = "SavedVariable.lua", channel = 0, enabled = False, parser = None):
        self.__inputFileName = inputFileName
        self.__channel = channel
        self.__enabled = enabled
        self.__parser = parser
        self.__db = {
            'global': {}, # Database for all global data indexed by player name. Unsorted.
            'group': {},   # Database for all grouped data. Indexed by groupn name. Sorted by DKP value descending
            'timestamp' : 0,
            'comment' : ""
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
        return (self.__channel == channel)

    def CheckAttachmentName(self, filename):
        return (self.__inputFileName == filename)

    def IsDatabaseLoaded(self):
        return (len(self.__db) > 0)

    ### Command handling and parsing ###

    def __getCommandParser(self):
        if not(self.__parser and isinstance(self.__parser, argparse.ArgumentParser)):
            self.__parser = argparse.ArgumentParser(description='Process commands.')
            self.__parser.add_argument('command', metavar='command', type=str, help='Actual command', nargs='?', default=None)
            self.__parser.add_argument('param', metavar='param', type=str, help='Command parameter', nargs='?', default=None)
            self.__parser.add_argument('varargs', metavar='varargs', type=str, help='All other string values will be put here', nargs='*', default=None)
        return self.__parser

    def __parseCommand(self, string):
        if string:
            return self.__getCommandParser().parse_args(string.split())
        else:
            return None

    def __handleCommand(self, command, param, isPrivileged):
        method = ''
        if command[0] == '?':
            method = 'help_'
        elif command[0] == '!':
            method = 'call_'
        else:
            return Response(ResponseStatus.IGNORE)

        method += command[1:]        
        callback = getattr(self, method, None)
        if callback:
            return callback(param, isPrivileged)
        else:
            return Response(ResponseStatus.IGNORE)

    def Handle(self, message, author, isPrivileged):
        args = self.__parseCommand(message)
        if args:
            if args.command:
                if not args.param:
                    if not author:
                        return Response(ResponseStatus.ERROR, "No param and no author. How?")
                    args.param = author
                return self.__handleCommand(args.command.lower(), args.param.lower(), isPrivileged)
            else:
                # Empty message, attachement only probably
                return Response(ResponseStatus.IGNORE)
        else:
            # Empty message, attachement only probably
            return Response(ResponseStatus.IGNORE)

    ### File handling and parsing ###

    def __getSavedVariables(self, inputString):
        return SavedVariablesParser().ParseString(inputString)

    def _dbSetTimestamp(self):
        self.__db['timestamp'] = int(time.time())

    def _dbGetTimestamp(self):
        return self.__db['timestamp']

    def _dbGetComment(self):
        return self.__db['comment']

    def _buildDkpDatabase(self, sv):
        self.__db['global']['dkp'] = {}
        self.__db['group'] = {}
    
    def _buildLootDatabase(self, sv):
        self.__db['global']['loot'] = {}

    def _buildHistoryDatabase(self, sv):
        self.__db['global']['history'] = {}

    def _getDkp(self, player):
        return self.__db['global']['dkp'].get(player.lower())

    def _getLoot(self, player):
        return self.__db['global']['loot'].get(player.lower())

    def _getHistory(self, player):
        return self.__db['global']['history'].get(player.lower())

    def _setDkp(self, player, entry):
        self.__db['global']['dkp'][player.lower()] = entry

    def _setLoot(self, player, entry):
        self.__db['global']['loot'][player.lower()] = entry

    def _addHistory(self, player, entry):
        player_history = self.__db['global']['history'].get(player.lower())
        if not player_history:
            self.__db['global']['history'][player.lower()] = []
        self.__db['global']['history'][player.lower()].push(entry)

    def _sortGroupDkp(self, group = None):
        if self.__db['group'].get(group):
            self.__db['group'][group].sort(key=lambda info: info.Dkp(), reverse=True)
        else:
            for g in self.__db['group'].values():
                g.sort(key=lambda info: info.Dkp(), reverse=True)

    def _setGroupDkp(self, group, entry, sort = False):
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

    def BuildDatabase(self, inputString, comment):
        print('Building database')

        start = int(time.time())

        sv = self.__getSavedVariables(inputString)
        if sv == None:
            return Response(ResponseStatus.ERROR, "Error Parsing .lua file.")
        
        if not isinstance(sv, dict):
            return Response(ResponseStatus.ERROR, "No SavedVariables found in .lua file.")

        self.__db['comment'] = comment

        self._buildDkpDatabase(sv)
        self._buildLootDatabase(sv)
        self._buildHistoryDatabase(sv)

        print('Building complete in {0} seconds'.format(int(time.time()) - start))

        if len(self.__db['global']['dkp']) <= 0:
        #for table in self.__db['global']:
        #    if len(table) <= 0:
                return Response(ResponseStatus.SUCCESS, "Database building failed.")

        return Response(ResponseStatus.SUCCESS, "Database building complete.")

    def ReloadData(self):
        return Response(ResponseStatus.REQUEST, Request.ATTACHEMENT)

    ### Command callbacks ###

    def call_dkpmanage(self, param, isPrivileged):
        if not isPrivileged == True:
            return Response(ResponseStatus.IGNORE)

        if param == 'register':
            return Response(ResponseStatus.REQUEST, Request.CHANNEL_ID)

        if param == 'reload':
            return self.ReloadData()

        return Response(ResponseStatus.SUCCESS, "Sorry :frowning: !dkpmanage {0} is not yet implemented.".format(param))
