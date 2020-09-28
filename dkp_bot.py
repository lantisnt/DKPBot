import argparse
import re

from datetime import datetime, timezone
from enum import Enum

from savedvariables_parser import SavedVariablesParser
from bot_config import BotConfig
from bot_utility import public_to_dict
import bot_memory_manager


class ResponseStatus(Enum):
    SUCCESS = 0
    ERROR = 1
    REQUEST = 2
    IGNORE = 3


class Request(Enum):
    NONE = 0
    RELOAD = 1


class Response:
    status = ResponseStatus.IGNORE
    # Response on SUCCESS
    # Error information on ERROR
    # Request type on REQUEST
    # None on IGNORE
    message = None
    direct_message = False

    def __init__(self, status=ResponseStatus.IGNORE, data=None, direct_message=False):
        self.status = status
        self.data = data
        self.direct_message = bool(direct_message)


class DKPBot:
    __config = None
    __guild_id = 0
    __input_file_name = ""
    __channel = 0
    __prefix = '!'
    __enabled = False
    __parser = None
    __param_parser = None
    __db = {}

    def __init__(self, guild_id: int, config: BotConfig):
        self.__config = config
        self.__guild_id = int(guild_id)
        self.__param_parser = re.compile("\s*([\d\w-]*)[\s[\/\,]*") # pylint: disable=anomalous-backslash-in-string
        self.__db = {
            # Database for all global data indexed by player name. Unsorted.
            'global': {},
            'group': {},   # Database for all grouped data. Indexed by group name. Sorted by DKP value descending
            'time': 0,
            'info': {}
        }

    def _configure(self):
        self.__input_file_name = self.__config.guild_info.filename
        self.__channel = int(self.__config.guild_info.file_upload_channel)
        self.__prefix = str(self.__config.guild_info.prefix)

    def enable(self):
        self.__enabled = True

    def disable(self):
        self.__enabled = False

    def is_enabled(self):
        return self.__enabled

    def is_channel_registered(self):
        return self.__channel != 0

    def check_channel(self, channel):
        return self.__channel == channel

    def check_attachment_name(self, filename):
        return self.__input_file_name == filename

    def is_database_loaded(self):
        return len(self.__db) > 0

    def get_prefix(self):
        return self.__prefix

    # Config
    def _get_config(self):
        return self.__config

    def __register_file_upload_channel(self, channel):
        self.__channel = channel
        self.__config.guild_info.file_upload_channel = channel
        self.__config.store()

    # Direct access for pickling
    def database_get(self):
        return self.__db

    def database_set(self, database):
        self.__db = database

    # Try requesting garbage collecting
    def database_free(self):
        del self.__db
        self.__db = {}

    ## Class related
    def __decode_aliases(self, groups):
        if not self._get_config().guild_info.premium:
            return groups

        new_groups = groups.copy()
        for group in groups:
            if group == 'all':
                return ['warrior', 'druid', 'priest', 'paladin', 'shaman', 'rogue', 'hunter', 'mage', 'warlock']

            if group == 'tank' or group == 'tanks':
                new_groups.extend(['warrior', 'druid'])

            elif group == 'healer' or group == 'healers':
                new_groups.extend(['priest', 'paladin', 'druid', 'shaman'])

            elif group == 'dps':
                new_groups.extend(
                    ['warrior', 'rogue', 'hunter', 'mage', 'warlock', 'shaman'])

            elif group == 'caster' or group == 'casters':
                new_groups.extend(['mage', 'warlock'])

            elif group == 'physical':
                new_groups.extend(['warrior', 'rogue', 'hunter', 'shaman'])

            elif group == 'range' or group == 'ranged':
                new_groups.extend(['mage', 'warlock'])

            elif group == 'melee':
                new_groups.extend(['warrior', 'rogue', 'shaman'])

        return new_groups

    ### Command handling and parsing ###

    def _parse_param(self, param, decode_aliases=True):
        # Remove empty strings
        targets = list(filter(None, self.__param_parser.findall(param)))
        # Decode aliases
        if decode_aliases:
            targets = self.__decode_aliases(targets)
        # Remove duplicates either from input or introduced by aliases
        targets = list(dict.fromkeys(targets))
        # Lowercase all
        return list(map(lambda x: x.strip().lower(), targets))

    def __get_command_parser(self):
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

    def __parse_command(self, string):
        if string:
            return self.__get_command_parser().parse_args(string.split())
        else:
            return None

    def __handle_command(self, command, param, request_info):
        method = ''
        direct_message = False
        if command[0] == self.__prefix:
            method = 'call_'
            if command[1] == self.__prefix:
                direct_message = True  # direct message
                method += command[2:]  # remove second ! also
            else:
                method += command[1:]
        else:
            return Response(ResponseStatus.IGNORE)

        callback = getattr(self, method, None)
        if callback and callable(callback):
            bot_memory_manager.Manager().Handle(self.__guild_id)  # pylint: disable=no-value-for-parameter
            response = callback(param, request_info)  # pylint: disable=not-callable

            response.direct_message = direct_message

            return response
        else:
            return Response(ResponseStatus.IGNORE)

    def handle(self, message, request_info):
        args = self.__parse_command(message)
        if args:
            if args.command:
                if not args.param:
                    if not request_info or not request_info.get('name'):
                        return Response(ResponseStatus.ERROR, "No param and no author. How?")
                    args.param = [request_info.get('name')]
                print(args.param)
                args.param = " ".join(args.param)
                print(args.param)
                return self.__handle_command(args.command.lower(), args.param.lower(), request_info)
            else:
                # Empty message, attachement only probably
                return Response(ResponseStatus.IGNORE)
        else:
            # Empty message, attachement only probably
            return Response(ResponseStatus.IGNORE)

    ### File handling and parsing ###

    def __get_saved_variables(self, input_string):
        return SavedVariablesParser().parse_string(input_string)

    def _db_get_info(self):
        return self.__db['info']

    def _build_dkp_database(self, saved_variable):  # pylint: disable=unused-argument
        self.__db['global']['dkp'] = {}
        self.__db['group'] = {}

    def _build_loot_database(self, saved_variable):  # pylint: disable=unused-argument
        self.__db['global']['loot'] = []
        self.__db['global']['player_loot'] = {}

    def _build_history_database(self, saved_variable):  # pylint: disable=unused-argument
        self.__db['global']['history'] = {}

    def _finalize_database(self):
        return

    def _get_dkp(self, player):
        return self.__db['global']['dkp'].get(player.lower())

    def _get_player_loot(self, player):
        return self.__db['global']['player_loot'].get(player.lower())

    def _get_loot(self,):
        return self.__db['global']['loot']

    def _get_history(self, player):
        return self.__db['global']['history'].get(player.lower())

    def _set_dkp(self, player, entry):
        self.__db['global']['dkp'][player.lower()] = entry

    def _add_loot(self, entry):
        self.__db['global']['loot'].append(entry)

    def _sort_loot(self, newest=True):
        self.__db['global']['loot'].sort(
            key=lambda info: info.timestamp(), reverse=bool(newest))

    def _find_oot(self, keyword):
        if not keyword or not isinstance(keyword, str) or len(keyword) == 0:
            return list()

        loot_pattern = re.compile(keyword.strip(), flags=re.IGNORECASE)

        def get_loot_if_matching(entry):
            if loot_pattern.search(entry.item_name()) is not None:
                return entry

            return None

        matching_loot = list(map(get_loot_if_matching, self.__db['global']['loot']))
        return list(filter(None, matching_loot))

    def _validate_player(self, player):
        if not player:
            return False

        if isinstance(player, str):
            player = self._get_dkp(player)
            if not player:
                return False

        return True

    def _add_player_loot(self, player, entry):
        if not self._validate_player(player):
            return

        player = player.lower()
        player_loot = self.__db['global']['player_loot'].get(player)
        if not player_loot:
            self.__db['global']['player_loot'][player] = []
        self.__db['global']['player_loot'][player].append(entry)

    def _sort_player_loot(self, newest=True, player=None):
        if self.__db['global']['player_loot'].get(player):
            self.__db['global']['player_loot'][player].sort(
                key=lambda info: info.timestamp(), reverse=bool(newest))
        else:
            for loot in self.__db['global']['player_loot'].values():
                loot.sort(key=lambda info: info.timestamp(), reverse=bool(newest))

    def _add_history(self, player, entry):
        if not self._validate_player(player):
            return

        player = player.lower()
        player_history = self.__db['global']['history'].get(player)
        if not player_history:
            self.__db['global']['history'][player] = []
        self.__db['global']['history'][player].append(entry)

    def _sort_history(self, newest=True, player=None):
        if self.__db['global']['history'].get(player):
            self.__db['global']['history'][player].sort(
                key=lambda info: info.timestamp(), reverse=bool(newest))
        else:
            for history in self.__db['global']['history'].values():
                history.sort(key=lambda info: info.timestamp(), reverse=bool(newest))

    def _sort_group_dkp(self, group=None):
        if self.__db['group'].get(group):
            self.__db['group'][group].sort(
                key=lambda info: info.dkp(), reverse=True)
        else:
            for values in self.__db['group'].values():
                values.sort(key=lambda info: info.dkp(), reverse=True)

    def _set_group_dkp(self, group, entry, sort=False):
        if group:
            group = group.lower()
            if not group in self.__db['group']:
                self.__db['group'][group] = []
            self.__db['group'][group].append(entry)
            if sort:
                self._sort_group_dkp(group)

    def _get_group_dkp(self, group):
        if group:
            return self.__db['group'].get(group.lower())

        return None

    def _set_player_latest_loot(self):
        for dkp in self.__db['global']['dkp'].values():
            loot = self._get_player_loot(dkp.name())
            if loot and isinstance(loot, list):
                dkp.set_latest_loot_entry(loot[0])

    def _set_player_latest_history(self):
        for dkp in self.__db['global']['dkp'].values():
            history = self._get_history(dkp.name())
            if history and isinstance(history, list):
                dkp.set_latest_history_entry(history[0])

    def _set_player_latest_positive_history_and_activity(self, inactive_time=200000000000):
        now = int(datetime.now(tz=timezone.utc).timestamp())
        for dkp in self.__db['global']['dkp'].values():
            history = self._get_history(dkp.name())
            if history and isinstance(history, list):
                for history_entry in history:
                    if history_entry.dkp() > 0:
                        dkp.set_latest_history_entry(history_entry)
                        if abs(now - history_entry.timestamp()) > inactive_time:
                            dkp.set_inactive()
                        break

    def build_database(self, input_string, info):
        print('Building database')

        start = datetime.now(tz=timezone.utc).timestamp()

        saved_variable = self.__get_saved_variables(input_string)
        if saved_variable is None:
            return Response(ResponseStatus.ERROR, "Error Parsing .lua file.")

        if not isinstance(saved_variable, dict):
            return Response(ResponseStatus.ERROR, "No SavedVariables found in .lua file.")

        self.__db['info']['comment'] = info.get('comment')
        self.__db['info']['date'] = info.get('date')
        self.__db['info']['author'] = info.get('author')

        self._build_dkp_database(saved_variable)
        self._build_loot_database(saved_variable)
        self._build_history_database(saved_variable)

        self._finalize_database()

        print('Building complete in {:04.2f} seconds'.format(
            datetime.now(tz=timezone.utc).timestamp() - start))

        for table in self.__db['global']:
            if len(table) <= 0:
                return Response(ResponseStatus.SUCCESS, "(DKP) Database building failed.")

        if len(self.__db['global']['history']) <= 0:
            return Response(ResponseStatus.SUCCESS, "(DKP History) Database building failed.")

        return Response(ResponseStatus.SUCCESS, "Database building complete.")

    ### Setting Handlers
    def __list_configs(self):
        return Response(ResponseStatus.IGNORE, str(self.__config))

    def __set_config(self, group, config, value):
        print("set config {0} {1} {2}".format(group, config, value))
        internal_group = getattr(self.__config, group, None)
        if internal_group:
            if hasattr(internal_group, config):
                setattr(internal_group, config, value)
                new_value = getattr(internal_group, config)
                if isinstance(new_value, bool):
                    return (new_value and value == 'true') or (not new_value and value == 'false')
                elif isinstance(new_value, int):
                    try:
                        return new_value == int(value)
                    except ValueError:
                        return False
                else:
                    return new_value == value
        return False

    def __set_config_specific(self, config, value):
        return "Invalid value"

    ### Command callbacks ###

    def call_dkphelp(self, param, request_info): # pylint: disable:unused-argument
        pass

    def call_dkpbotconfig(self, param, request_info):
        if not request_info.get('is_privileged'):
            return Response(ResponseStatus.IGNORE)
        param = self._parse_param(param, False)
        params = list(map(lambda p: p.lower().replace("-", "_"), param))
        num_params = len(params)
        if num_params == 0:
            return Response(ResponseStatus.IGNORE)

        command = params[0]
        if command == 'list': # list current config
            return self.__list_configs()
        elif command == 'set': # set config
            if num_params == 1:
                return Response(ResponseStatus.IGNORE)

            if num_params == 3:
                config = params[1]
                value = params[2]

                return Response(ResponseStatus.SUCCESS, self.__set_config_specific(config, value))

            print(params)
            if num_params == 4:
                group = params[1]
                config = params[2]
                value = params[3]
                if group in self.__config.get_directly_accessible_configs():
                    if self.__set_config(group, config, value):
                        self.__config.store()
                        self._configure()
                        return Response(ResponseStatus.SUCCESS, "Successfuly set **{0} {1}** to **{2}**".format(param[1], param[2], param[3]))
                    else:
                        return Response(ResponseStatus.SUCCESS, "Invalid setting **{0}** or unsupported value **{1}**".format(param[1], param[2]))

        elif command == 'register':
            if request_info['channel'] > 0:
                self.__register_file_upload_channel(request_info['channel']['id'])
                return Response(ResponseStatus.SUCCESS,
                    'Registered to expect Saved Variable lua file on channel {0.name}'.format(request_info['channel']['name']))

        return Response(ResponseStatus.IGNORE)
