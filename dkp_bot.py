import argparse
import re
import json

from datetime import datetime, timezone
from enum import Enum

from savedvariables_parser import SavedVariablesParser
from bot_config import BotConfig
import bot_memory_manager
from display_templates import RawEmbed

class ResponseStatus(Enum):
    SUCCESS = 0
    ERROR = 1
    REQUEST = 2
    IGNORE = 3


class Request(Enum):
    NONE = 0
    RELOAD = 1
    RESPAWN = 2


class Response:
    status = ResponseStatus.IGNORE
    # Response on SUCCESS
    # Error information on ERROR
    # Request type on REQUEST
    # None on IGNORE
    data = None
    direct_message = False

    def __init__(self, status=ResponseStatus.IGNORE, data=None, direct_message=False):
        self.status = status
        self.data = data
        self.direct_message = bool(direct_message)


class DKPBot:
    DEFAULT_TEAM = "0"

    __config = None
    __guild_id = 0
    __input_file_name = ""
    __channel = 0
    __prefix = '!'
    __premium = False
    __enabled = False
    __parser = None
    __param_parser = None
    _all_groups = []
    __db = {}

    __server_side = ''
    __guild_name = ''

    def __init__(self, guild_id: int, config: BotConfig):
        self.__config = config
        self.__guild_id = int(guild_id)
        self.__param_parser = re.compile("\s*([\d\w\-!?+.:<>|*^]*)[\s[\/\,]*") # pylint: disable=anomalous-backslash-in-string
        self._all_groups = ['warrior', 'druid', 'priest', 'paladin', 'shaman', 'rogue', 'hunter', 'mage', 'warlock']
        self.__channel_team_map = {}
        self.__db_loaded = False
        self.__db = {
            # Database for all global data indexed by player name. Unsorted.
            'global': {},
            'group': {},   # Database for all grouped data. Indexed by group name. Sorted by DKP value descending
            'time': 0,
            'info': {
                'comment' : '',
                'date' : '',
                'author' : ''
            }
        }

    def _configure(self):
        self.__input_file_name = self.__config.guild_info.filename
        self.__channel = int(self.__config.guild_info.file_upload_channel)
        self.__prefix = str(self.__config.guild_info.prefix)
        self.__premium = bool(self.__config.guild_info.premium)
        self.__server_side = self.__config.guild_info.server_side
        self.__guild_name = self.__config.guild_info.guild_name
        self.__channel_team_map = json.loads(self.__config.guild_info.channel_team_map)

    def _reconfigure(self):
        self.__config.store()
        self._configure()

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
        return self.__db_loaded

    def get_prefix(self):
        return self.__prefix

    def get_server_side(self):
        return self.__config.guild_info.server_side

    def get_guild_name(self):
        return self.__config.guild_info.guild_name

    def is_premium(self):
        return self.__premium

    # Config
    def _get_config(self):
        return self.__config

    def __register_file_upload_channel(self, channel):
        self.__channel = channel
        self.__config.guild_info.file_upload_channel = channel
        self._reconfigure()

    # Direct access for pickling
    def database_get(self):
        return self.__db

    def database_set(self, database):
        self.__db = database
        self.__db_loaded = True

    # Try requesting garbage collecting
    def database_free(self):
        del self.__db
        self.__db = {}
        self.__db_loaded = False

    ## Class related
    def __decode_aliases(self, groups):
        # Always allow querying all
        if 'all' in groups:
            return self._all_groups

        # If not premium we don't allow doing any group mixin calls
        if not self.is_premium():
            # Remove groups
            new_groups = [x for x in groups if x not in self._all_groups]
            # Remove mixins
            if len(new_groups) > 1:
                new_groups = [new_groups[0]]

            return new_groups

        # Else we consider everything for premium users
        new_groups = groups.copy()
        for group in groups:
            if group == 'all':
                return self._all_groups

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

    ### Team related
    def _get_channel_team_mapping(self, channel_id):
        team = self.__channel_team_map.get(str(channel_id))
        if team is None:
            return DKPBot.DEFAULT_TEAM

        return team

    def _set_channel_team_mapping(self, channel_id, team):
        # String due to how it is used in some lua files
        # Limit to 10
        if (len(self.__channel_team_map) == 10) and (str(channel_id) not in self.__channel_team_map):
            return False

        self.__channel_team_map[str(channel_id)] = str(team)
        self.__config.guild_info.channel_team_map = json.dumps(self.__channel_team_map)
        self._reconfigure()

        return True

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
                args.param = " ".join(args.param)
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
        return

    def _build_loot_database(self, saved_variable):  # pylint: disable=unused-argument
        return

    def _build_history_database(self, saved_variable):  # pylint: disable=unused-argument
        return

    def _finalize_database(self):
        return

    def _get_dkp(self, player, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            return None
        return team_data['dkp'].get(player.lower())

    def _get_player_loot(self, player, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            return None
        return team_data['player_loot'].get(player.lower())

    def _get_loot(self, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            return None
        return team_data['loot']

    def _get_history(self, player, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            return None
        return team_data['history'].get(player.lower())

    def __init_team_structure(self, team):
        self.__db['global'][team]  = {}
        self.__db['global'][team]['dkp']  = {}
        self.__db['global'][team]['loot']  = []
        self.__db['global'][team]['player_loot']  = {}
        self.__db['global'][team]['history']  = {}
        self.__db['group'][team] = {}

    def _set_dkp(self, player, entry, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            self.__init_team_structure(team)
        self.__db['global'][team]['dkp'][player.lower()] = entry

    def _add_loot(self, entry, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            self.__init_team_structure(team)
        self.__db['global'][team]['loot'].append(entry)

    def _sort_loot(self, newest=True, team=None):
        if team is None:
            for team_data in self.__db['global'].values():
                team_data['loot'].sort(key=lambda info: info.timestamp(), reverse=bool(newest))
        else:
            team_data = self.__db['global'].get(team)
            if team_data is not None:
                team_data['loot'].sort(key=lambda info: info.timestamp(), reverse=bool(newest))

    def _find_loot(self, keyword, team):
        if not keyword or not isinstance(keyword, str) or len(keyword) == 0:
            return list()

        team_data = self.__db['global'].get(team)
        if team_data is None:
            return list()

        loot_pattern = re.compile(keyword.strip(), flags=re.IGNORECASE)

        def get_loot_if_matching(entry):
            if loot_pattern.search(entry.item_name()) is not None:
                return entry

            return None

        matching_loot = list(map(get_loot_if_matching, team_data['loot']))
        return list(filter(None, matching_loot))

    def _validate_player(self, player, team):
        if player is None:
            return False

        if isinstance(player, str):
            player = self._get_dkp(player, team)
            if player is None:
                return False

        return True

    def _add_player_loot(self, player, entry, team):
        if not self._validate_player(player, team):
            return

        team_data = self.__db['global'].get(team)
        if team_data is None:
            return None

        player = player.lower()
        player_loot = team_data['player_loot'].get(player)
        if not player_loot:
            self.__db['global'][team]['player_loot'][player] = []
        self.__db['global'][team]['player_loot'][player].append(entry)

    def _sort_player_loot(self, newest=True, player=None, team=None):
        if team is None:
            for team_data in self.__db['global'].values():
                if team_data['player_loot'].get(player):
                    team_data['player_loot'][player].sort(
                        key=lambda info: info.timestamp(), reverse=bool(newest))
                else:
                    for loot in team_data['player_loot'].values():
                        loot.sort(key=lambda info: info.timestamp(), reverse=bool(newest))
        else:
            team_data = self.__db['global'].get(team)
            if team_data is None:
                return None

            if team_data['player_loot'].get(player):
                team_data['player_loot'][player].sort(key=lambda info: info.timestamp(), reverse=bool(newest))
            else:
                for loot in team_data['player_loot'].values():
                    loot.sort(key=lambda info: info.timestamp(), reverse=bool(newest))

    def _add_history(self, player, entry, team):
        if not self._validate_player(player, team):
            return

        team_data = self.__db['global'].get(team)
        if team_data is None:
            self.__init_team_structure(team)
            team_data = self.__db['global'].get(team)

        player = player.lower()
        player_history = team_data['history'].get(player)
        if not player_history:
            self.__db['global'][team]['history'][player] = []
        self.__db['global'][team]['history'][player].append(entry)

    def _sort_history(self, newest=True, player=None, team=None):
        if team is None:
            for team_data in self.__db['global'].values():
                if team_data['history'].get(player):
                    team_data['history'][player].sort(
                        key=lambda info: info.timestamp(), reverse=bool(newest))
                else:
                    for loot in team_data['history'].values():
                        loot.sort(key=lambda info: info.timestamp(), reverse=bool(newest))
        else:
            team_data = self.__db['global'].get(team)
            if team_data is None:
                return None

            if team_data['history'].get(player):
                team_data['history'][player].sort(key=lambda info: info.timestamp(), reverse=bool(newest))
            else:
                for loot in team_data['history'].values():
                    loot.sort(key=lambda info: info.timestamp(), reverse=bool(newest))

    def _sort_group_dkp(self, group=None, team=None):
        if team is None:
            for team_data in self.__db['group'].values():
                if team_data.get(group):
                    team_data[group].sort(
                        key=lambda info: info.dkp(), reverse=True)
                else:
                    for values in team_data.values():
                        values.sort(key=lambda info: info.dkp(), reverse=True)
        else:
            team_data = self.__db['group'].get(team)
            if team_data is None:
                return None

            if team_data.get(group):
                team_data[group].sort(
                    key=lambda info: info.dkp(), reverse=True)
            else:
                for values in team_data.values():
                    values.sort(key=lambda info: info.dkp(), reverse=True)

    def _set_group_dkp(self, group, entry, team, sort=False):
        if group:
            group = group.lower()
            team_data = self.__db['group'].get(team)
            if team_data is None:
                self.__init_team_structure(team)

            if not group in team_data:
                team_data[group] = []
            team_data[group].append(entry)
            if sort:
                self._sort_group_dkp(group)

    def _get_group_dkp(self, group, team):
        team_data = self.__db['group'].get(team)
        if team_data is None:
            return None

        if group:
            return team_data.get(group.lower())

        return None

    def _set_player_latest_loot(self):
        for team, team_data in self.__db['global'].items():
            for dkp in team_data['dkp'].values():
                loot = self._get_player_loot(dkp.name(), team)
                if loot and isinstance(loot, list):
                    dkp.set_latest_loot_entry(loot[0])

    def _set_player_latest_history(self):
        for team, team_data in self.__db['global'].items():
            for dkp in team_data['dkp'].values():
                history = self._get_history(dkp.name(), team)
                if history and isinstance(history, list):
                    dkp.set_latest_history_entry(history[0])

    def _set_player_latest_positive_history_and_activity(self, inactive_time=200000000000):
        now = int(datetime.now(tz=timezone.utc).timestamp())
        for team, team_data in self.__db['global'].items():
            for dkp in team_data['dkp'].values():
                history = self._get_history(dkp.name(), team)
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

        for team in self.__db['global']:
            for table in team:
                if len(table) <= 0:
                    return Response(ResponseStatus.SUCCESS, "Database building failed.")

        for team in self.__db['group']:
            if len(team) <= 0:
                return Response(ResponseStatus.SUCCESS, "Database building failed.")

        self.__db_loaded = True

        return Response(ResponseStatus.SUCCESS, "Database building complete.")

    ### Setting Handlers
    def __list_configs(self):
        string = str(self.__config)
        string += "\n"
        string += "To set new value type:\n"
        string += "{0}config `category` `config` `value` e.g. `{0}config dkp max-fields 6`".format(self.__prefix)
        return Response(ResponseStatus.SUCCESS, string)

    def __set_config(self, group, config, value):
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

    def __set_config_specific(self, config, value): # pylint: disable=unused-argument
        return "Invalid value"

    ### Command related ###
    @staticmethod
    def get_supported_prefixes():
        return ['!', '?', '+', '.', ':', '<', '>', '|', '*', '^']

    @staticmethod
    def get_supported_prefixes_string(prefix_list):
        string = ""
        for prefix in prefix_list:
            string += "`{0}`, ".format(prefix)

        return string.rstrip(", ")


    ### Command callbacks ###

    def call_help(self, param, request_info): # pylint: disable=unused-argument
        return Response(ResponseStatus.IGNORE)

    def call_config(self, param, request_info):
        if not request_info.get('is_privileged'):
            return Response(ResponseStatus.IGNORE)

        params = self._parse_param(param, False)
        num_params = len(params)
        if num_params == 0:
            return Response(ResponseStatus.IGNORE)

        command = params[0]

        method = "config_call_" + command.replace("-", "_").lower()
        callback = getattr(self, method, None)
        if callback and callable(callback):
            return callback(params, num_params, request_info)
        else:
            # string += "`filename` - change filename of lua file expected by bot including the .lua extension - **case sensitive** - up to 20 characters\n"
            # string += "current: `{0}`\n\n".format(self.__config.guild_info.filename)
            embed = RawEmbed()
            embed.build(None, "Supported commands", None, None, 16553987, "[WoW DKP Bot Discord](https://discord.gg/t42qW4j)")
            # bot-type
            string = "Set bot type to handle specified addon\n"
            string += "```"
            string += "Current:   {0}\n".format(self.__config.guild_info.bot_type)
            string += "Supported: essential monolith community\n"
            string += "Usage:     {0}config bot-type essential".format(self.__prefix)
            string += "```"
            embed.add_field("bot-type", string, False)
            # server-side
            string = "Set ingame server and side data required by some addons\n"
            string += "```"
            data = self.__config.guild_info.server_side.split("-")
            if len(data) == 2:
                string += "Current:   {0}".format(' '.join(word.capitalize() for word in data))
            else:
                string += "Current:   not set"
            string += "Usage:     {0}config server-side MirageRaceway Alliance".format(self.__prefix)
            string += "```"
            embed.add_field("server-side", string, False)
            # guild-name
            string = "Set ingame guild name required by some addons\n"
            string += "```"
            data = self.__config.guild_info.guild_name
            if len(data) == 2:
                string += "Current:   {0}".format(' '.join(word.capitalize() for word in data))
            else:
                string += "Current:   not set"
            string += "Usage:     {0}config guild-name Some Guild".format(self.__prefix)
            string += "```"
            embed.add_field("guild-name", string, False)
            # team
            string = "`Register current channel to handle specified team number\n"
            string += "```"
            num_teams = len(self.__channel_team_map)
            string += "Current:\n"
            if num_teams > 0:
                for channel, team in self.__channel_team_map.items():
                    string += "{1}: <#{0}>\n".format(channel, team)
            else:
                string += "none\n"
            string += "Usage:     {0}config team 0".format(self.__prefix)
            string += "```"
            embed.add_field("team", string, False)
            # register
            string = "Register current channel as the only one on which lua saved variable upload will be accepted\n"
            string += "```"
            if self.__config.guild_info.bot_type == 0:
                string += "Current:   any\n"
            else:
                string += "Current:   <#{0}>\n".format(self.__config.guild_info.bot_type)
            string += "Usage:     {0}config register".format(self.__prefix)
            string += "```"
            embed.add_field("register", string, False)
            # prefix
            string = "Change bot prefix\n"
            string += "```"
            string += "Current:   {0}\n".format(self.__prefix)
            string += "Supported: {0}\n".format(' '.join(self.get_supported_prefixes()))
            string += "Usage:     {0}config register".format(self.__prefix)
            string += "```"
            embed.add_field("prefix", string, False)
            # default
            string = "Instantly reset bot configuration to default - this also resets `prefix` and `bot type`\n"
            string += "```"
            string += "Usage:     {0}config default".format(self.__prefix)
            string += "```"
            embed.add_field("default", string, False)

            return Response(ResponseStatus.SUCCESS, embed.get())
        return Response(ResponseStatus.IGNORE)

    def call_display(self, param, request_info):
        if not request_info.get('is_privileged'):
            return Response(ResponseStatus.IGNORE)

        param = self._parse_param(param, False)
        params = list(map(lambda p: p.lower().replace("-", "_"), param))

        num_params = len(params)
        if num_params<= 1:
            return self.__list_configs() # list current config

        if num_params >= 3:
            category = params[0]
            config = params[1]
            value = params[2]
            if category in self.__config.get_directly_accessible_configs():
                if self.__set_config(category, config, value):
                    self.__config.store()
                    self._configure()
                    return Response(ResponseStatus.SUCCESS, "Successfuly set **{0} {1}** to **{2}**".format(param[0], param[1], param[2]))
                else:
                    return Response(ResponseStatus.SUCCESS, "Unsupported value **{2}** provided for **{0} {1}**".format(param[0], param[1], param[2]))
            else:
                return Response(ResponseStatus.SUCCESS, "Invalid category **{0}**".format(param[0]))

        return Response(ResponseStatus.SUCCESS, "Invalid number of parameters")

    ### Config handlers ###

    def config_call_bot_type(self, params, num_params, request_info):
        if num_params == 2:
            value = params[1]
            if value in ['community', 'monolith', 'essential']:
                current = self.__config.guild_info.bot_type
                if value == current:
                    return Response(ResponseStatus.SUCCESS, 'Retaining current bot type')

                self.__config.guild_info.bot_type = value
                new = self.__config.guild_info.bot_type

                if new == value:
                    self.__config.guild_info.filename = value.capitalize() + 'DKP.lua'
                    self._reconfigure()
                    return Response(ResponseStatus.REQUEST, Request.RESPAWN)
                else:
                    return Response(ResponseStatus.ERROR, 'Unexpected error during bot type setup')
            else:
                return Response(ResponseStatus.SUCCESS, 'Unsupported bot type')
        else:
            return Response(ResponseStatus.SUCCESS, "Invalid number of parameters")

    def config_call_prefix(self, params, num_params, request_info):
        if num_params == 2:
            value = params[1]
            if value in self.get_supported_prefixes():
                self.__config.guild_info.prefix = value
                new = self.__config.guild_info.prefix
                if new == value:
                    self._reconfigure()
                    return Response(ResponseStatus.SUCCESS, 'Set prefix to `{0}`'.format(value))
                else:
                    return Response(ResponseStatus.ERROR, 'Unexpected error during prefix change')
            else:
                return Response(ResponseStatus.SUCCESS, 'Unsupported prefix')
        else:
            return Response(ResponseStatus.SUCCESS, "Invalid number of parameters")

    def config_call_default(self, params, num_params, request_info):
        self.__config.default()
        return Response(ResponseStatus.REQUEST, Request.RESPAWN)

    def config_call_reload(self, params, num_params, request_info):
        return Response(ResponseStatus.REQUEST, Request.RESPAWN)

    def config_call_register(self, params, num_params, request_info):
        self.__register_file_upload_channel(request_info['channel'])
        return Response(ResponseStatus.SUCCESS,
            'Registered to expect Saved Variable lua file on channel <#{0}>'.format(request_info['channel']))

    def config_call_server_side(self, params, num_params, request_info):
        if num_params == 3:
            server = params[1]
            side = params[2]
            value = "{0}-{1}".format(server, side).lower()
            if len(value) > 50:
                return Response(ResponseStatus.ERROR, 'Data is too long.')

            self.__config.guild_info.server_side = value
            new = self.__config.guild_info.server_side
            if new == value:
                self._reconfigure()
                return Response(ResponseStatus.SUCCESS, 'Serve-side data set to `{0} {1}`'.format(server, side))
            else:
                return Response(ResponseStatus.ERROR, 'Unexpected error during server-side change.')
        else:
            return Response(ResponseStatus.SUCCESS, "Invalid number of parameters")

    def config_call_guild_name(self, params, num_params, request_info):
        if num_params >= 2:
            value = ' '.join(params[1:])
            if len(value) > 50:
                return Response(ResponseStatus.ERROR, 'Data is too long.')

            self.__config.guild_info.guild_name = value
            new = self.__config.guild_info.guild_name
            if new == value:
                self._reconfigure()
                return Response(ResponseStatus.SUCCESS, 'Guild Name set to `{0}`'.format(value))
            else:
                return Response(ResponseStatus.ERROR, 'Unexpected error during guild name change.')
        else:
            return Response(ResponseStatus.SUCCESS, "Invalid number of parameters")

    def config_call_team(self, params, num_params, request_info):
        if num_params == 2:
            success = self._set_channel_team_mapping(request_info['channel'], params[1])
            if success:
                return Response(ResponseStatus.SUCCESS, 'Registered channel <#{0}> to handle team {1}'.format(request_info['channel'], params[1]))
            else:
                return Response(ResponseStatus.SUCCESS, 'Exceeded maximum number of channels. Please reuse existing one.')
        else:
            return Response(ResponseStatus.SUCCESS, "Invalid number of parameters")
