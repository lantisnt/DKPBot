import argparse
import re
import json
import collections
from enum import Enum

from savedvariables_parser import SavedVariablesParser
from bot_config import BotConfig
from bot_logger import BotLogger
from bot_utility import timestamp_now, public_to_dict
import bot_memory_manager
from display_templates import SUPPORT_SERVER
from display_templates import get_bot_color, get_bot_links, preformatted_block
from display_templates import RawEmbed, BasicCritical, BasicError, BasicSuccess, BasicAnnouncement, BasicInfo

class ResponseStatus(Enum):
    SUCCESS = 0
    ERROR = 1
    DELEGATE = 2
    RELOAD = 3
    IGNORE = 99


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

class Statistics():

    INDENT_OFFSET = 2

    class Commands(dict):
        class Instrumentation:
            min = None
            max = None
            avg = None
            num = None

            def __init__(self, value=None):
                if not isinstance(value, (int, float)):
                    self.min = float("inf")
                    self.max = 0
                    self.avg = 0
                    self.num = 0
                else:
                    self.min = value
                    self.max = value
                    self.avg = value
                    self.num = 1

            def update(self, value):
                if not isinstance(value, (int, float)):
                    raise TypeError

                if value < self.min:
                    self.min = value

                if value > self.max:
                    self.max = value

                tmp_sum = (self.avg * self.num) + value

                self.num =  self.num + 1

                self.avg = tmp_sum / self.num

            def override(self, other):
                if isinstance(other, type(self)):
                    self.min = other.min
                    self.max = other.max
                    self.avg = other.avg
                    self.num = other.num
                else:
                    raise TypeError

            def __add__(self, other):
                if isinstance(other, type(self)):
                    tmp = Statistics.Commands.Instrumentation()

                    tmp.min = self.min if self.min < other.min else other.min
                    tmp.max = self.max if self.max > other.max else other.max

                    tmp.num = self.num + other.num

                    total = (self.avg * self.num) + (other.avg * other.num)
                    tmp.avg = total/tmp.num

                    return tmp
                else:
                    raise TypeError

        ### End Internal class Instrumentation

        def __setitem__(self, key, item):
            if key not in self:
                super().__setitem__(key, self.Instrumentation(item))
            else:
                self[key].update(item)

        def __add__(self, other):
            if isinstance(self, type(other)):
                command_list = list(dict.fromkeys(list(self.keys()) + list(other.keys())))
                commands = Statistics.Commands()
                for command in command_list:
                    commands[command] = 0
                    if command in self:
                        commands[command].override(self[command])
                        if command in other:
                            commands[command].override(commands[command] + other[command])
                    elif command in other:
                        commands[command].override(other[command])
                return commands
            else:
                raise TypeError

        def get(self):
            data = {}
            for key in self:
                data[key] = public_to_dict(self[key], filter_callable=True)
            return data

    database = None
    commands = None

    def __init__(self):
        self.database = {}
        self.commands = Statistics.Commands()

    @staticmethod
    def format_list(data, indent=0):
        string  = ""
        for entry in data:
            string += Statistics.format(entry, indent + Statistics.INDENT_OFFSET) + ", "
        string.strip(",")
        return string

    @staticmethod
    def format_dict(data, indent=0):
        string = ""
        max_key_len = max(list(map(len, data.keys())))
        for key, value in data.items():
            string += "\n" + (indent * " ") + "{0}: ".format(key)
            if isinstance(value, (dict, tuple)):
                value_indent = (indent + Statistics.INDENT_OFFSET)
            else:
                value_indent = max_key_len - len(key) + 2
            string += (value_indent * " ") + Statistics.format(value, value_indent + Statistics.INDENT_OFFSET)
        return string

    @staticmethod
    def format_tuple(data, indent=0):
        string = ""
        string += (indent * " ")
        string += "( " + Statistics.format(data[0], indent + Statistics.INDENT_OFFSET)
        string += Statistics.format(data[1], indent + Statistics.INDENT_OFFSET) + " )"
        return string

    @staticmethod
    def format(data, indent=0):
        if isinstance(data, list):
            return Statistics.format_list(data, indent)
        elif isinstance(data, dict):
            return Statistics.format_dict(data, indent)
        elif isinstance(data, tuple):
            return Statistics.format_tuple(data, indent)
        else:
            return str(data)

    def print_database(self):
        string  = ""
        string += "```asciidoc\n=== Database ===```"
        string += "```c\n"
        string += Statistics.format(self.database, -2)
        string += "```"
        return string

    def print_commands(self):
        string  = ""
        string += "```asciidoc\n=== Commands ===```"
        if len(self.commands) > 0:
            string += "```c\n"
            string += Statistics.format(self.commands.get(), -2)
            string += "```"
        else:
            string += "```asciidoc\n"
            string += "[ none ]"
            string += "```"
        return string

    def __str__(self):
        string  = ""
        string += self.print_database()
        string += self.print_commands()
        return string

class DKPBot:
    DEFAULT_TEAM = "0"
    statistics = None
    __config = None
    __guild_id = 0
    __input_file_name = ""
    __channel = 0
    __prefix = '!'
    __premium = False
    __enabled = False
    __parser = None
    __param_parser = None
    _classes = [
        'warrior',
        'druid',
        'priest',
        'paladin',
        'shaman',
        'rogue',
        'hunter',
        'mage',
        'warlock'
    ]
    _aliases = [
        'tank', 'tanks', 'healer', 'healers', 'dps', 'caster', 'casters', 'physical', 'range', 'ranged', 'melee'
    ]
    __db = {}

    __server_side = ''
    __guild_name = ''
    __direct_message_response = False
    __block_response_modifier = False
    __smart_roles = True

    def __init__(self, guild_id: int, config: BotConfig):
        self.__config = config
        self.__guild_id = int(guild_id)
        self.__channel = 0
        self.__announcement_channel = 0
        self.__announcement_mention_role = 0
        self.__param_parser = re.compile("\s*([\d\w\-!?+.:<>|*^'\"]*)[\s[\/\,]*")  # pylint: disable=anomalous-backslash-in-string
        self._channel_team_map = collections.OrderedDict()
        self.__db_loaded = False
        self.__init_db_structure()
        self.statistics = Statistics()

    def _configure(self):
        self.__input_file_name = self.__config.guild_info.filename
        self.__channel = int(self.__config.guild_info.file_upload_channel)
        self.__announcement_channel = int(self.__config.guild_info.announcement_channel)
        self.__announcement_mention_role = int(self.__config.guild_info.announcement_mention_role)
        self.__prefix = str(self.__config.guild_info.prefix)
        self.__premium = bool(self.__config.guild_info.premium)
        self.__server_side = self.__config.guild_info.server_side
        self.__guild_name = self.__config.guild_info.guild_name
        channel_mapping = json.loads(self.__config.guild_info.channel_team_map)
        for channel, team in channel_mapping.items():
            self._channel_team_map[channel] = team
        self.__direct_message_response = bool(self.__config.guild_info.direct_message_response)
        self.__block_response_modifier = bool(self.__config.guild_info.block_response_modifier)
        self.__smart_roles = bool(self.__config.guild_info.smart_roles)

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

    def is_announcement_channel_registered(self):
        return self.__announcement_channel != 0

    def get_announcement_channel(self):
        return self.__announcement_channel

    def is_announcement_mention_role_set(self):
        return self.__announcement_mention_role != 0

    def get_announcement_mention_role(self):
        return self.__announcement_mention_role

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

    def smart_roles(self):
        return self.__smart_roles

    def get_announcement(self):
        announcement = "DKP standings have just been updated by {0}!\n".format(self.__db['info']['author'])
        if len(self.__db['info']['comment']) > 0:
            announcement += "```{0}```".format(self.__db['info']['comment'])

        if self.is_announcement_mention_role_set():
            return ("<@&{0}>".format(self.__announcement_mention_role), BasicAnnouncement(announcement).get())
        else:
            return BasicAnnouncement(announcement).get()

    # Config
    def _get_config(self):
        return self.__config

    def __register_file_upload_channel(self, channel):
        self.__channel = channel
        self.__config.guild_info.file_upload_channel = channel
        self._reconfigure()

    def __register_announcement(self, channel, role):
        self.__announcement_channel = channel
        self.__config.guild_info.announcement_channel = channel
        self.__announcement_mention_role = role
        self.__config.guild_info.announcement_mention_role = role
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

    # Class related
    def _decode_alias_internal(self, group):
        if group == 'tank' or group == 'tanks':
            return ['warrior', 'druid']

        elif group == 'healer' or group == 'healers':
            return ['priest', 'paladin', 'druid', 'shaman']

        elif group == 'dps':
            return ['warrior', 'rogue', 'hunter', 'mage', 'warlock', 'shaman', 'druid']

        elif group == 'caster' or group == 'casters':
            return ['mage', 'warlock', 'shaman']

        elif group == 'physical':
            return ['warrior', 'rogue', 'hunter', 'druid']

        elif group == 'range' or group == 'ranged':
            return ['mage', 'warlock', 'shaman']

        elif group == 'melee':
            return ['warrior', 'rogue', 'druid']

        return []

    def __decode_aliases(self, groups):
        # Always allow querying all
        if 'all' in groups:
            return (self._classes, self._aliases)

        # If not premium we don't allow doing any group mixin calls
        if not self.is_premium():
            # Remove classes
            new_groups = [x for x in groups if x not in self._classes]
            # Remove aliases
            new_groups = [x for x in new_groups if x not in self._aliases]
            # Remove mixins
            if len(new_groups) > 1:
                new_groups = [new_groups[0]]

            return (new_groups, [])

        # Else we consider everything for premium users
        new_groups = []
        for group in groups:
            if group in self._classes: # singulars
                new_groups.append(group)
            elif not group in self._aliases:
                if group.endswith('s'): # class prulals
                    subgroup = group[:-1]
                    if subgroup in self._classes:
                        new_groups.append(subgroup)
                    else:
                        new_groups.append(group)
                else:
                    new_groups.append(group)
            else:
                new_groups.extend(self._decode_alias_internal(group))

        # Get aliases
        aliases = []
        for alias in self._aliases:
            if alias in groups:
                aliases.append(alias)

        return (new_groups, aliases)

    # Team related
    def _get_channel_team_mapping(self, channel_id): #pylint: disable=unused-argument
        return DKPBot.DEFAULT_TEAM

    def _set_channel_team_mapping(self, channel_id, team):
        # String due to how it is used in some lua files
        # Limit to 8
        in_limit = True
        if (len(self._channel_team_map) == 8) and (str(channel_id) not in self._channel_team_map):
            self._channel_team_map.popitem(False)
            in_limit = False

        self._channel_team_map[str(channel_id)] = str(team)
        self.__config.guild_info.channel_team_map = json.dumps(self._channel_team_map)
        self._reconfigure()

        return in_limit

    ### Command handling and parsing ###

    def _parse_param(self, param):
        # Remove empty strings
        targets = list(filter(None, self.__param_parser.findall(param)))
        # Lowercase all
        return list(map(lambda x: x.strip().lower(), targets))

    def _parse_player_param(self, param):
        # Remove empty strings
        original = list(filter(None, self.__param_parser.findall(param)))
        # Remove duplicates from input
        original = list(dict.fromkeys(original))
        # Decode aliases
        (targets, aliases) = self.__decode_aliases(original)
        # Remove introduced by aliases
        targets = list(dict.fromkeys(targets))
        aliases = list(dict.fromkeys(aliases))
        # Lowercase all
        original = list(map(lambda x: x.strip().lower(), original))
        targets = list(map(lambda x: x.strip().lower(), targets))
        aliases = list(map(lambda x: x.strip().lower(), aliases))

        return (targets, aliases, original)


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
        sanitized_command = ''
        direct_message = self.__direct_message_response
        if command[0] == self.__prefix:
            if len(command) > 1 and command[1] == self.__prefix:
                sanitized_command = command[2:]  # remove second ! also
                if (not self.__block_response_modifier or (self.__block_response_modifier and request_info['is_privileged'])):
                    direct_message = not self.__direct_message_response  # direct message
            else:
                sanitized_command = command[1:]
            method = 'call_' + sanitized_command
        else:
            return Response(ResponseStatus.IGNORE)

        callback = getattr(self, method, None)
        if callback and callable(callback):
            bot_memory_manager.Manager().Handle(self.__guild_id)  # pylint: disable=no-value-for-parameter
            start = timestamp_now()
            response = callback(param, request_info)  # pylint: disable=not-callable
            self.statistics.commands[sanitized_command] = (1000 * (timestamp_now() - start)) # miliseconds
            response.direct_message = direct_message

            return response
        elif sanitized_command.startswith('su_'):
            return Response(ResponseStatus.DELEGATE, (sanitized_command, param))
        else:
            return Response(ResponseStatus.IGNORE)

    def handle(self, message, request_info):
        if len(message) > 0 and message[0] == self.__prefix:
            args = self.__parse_command(message)
            if args:
                if args.command:
                    if not args.param:
                        args.param = [request_info['author']['name']]
                    args.param = " ".join(args.param)
                    return self.__handle_command(args.command.lower(), args.param.lower(), request_info)
        # Empty message, attachement only probably
        return Response(ResponseStatus.IGNORE)

    ### File handling and parsing ###

    def __get_saved_variables(self, input_string):
        return SavedVariablesParser().parse_string(input_string)

    def _db_get_info(self):
        return self.__db['info']

    def _build_config_database(self, saved_variable):  # pylint: disable=unused-argument
        return False

    def _build_dkp_database(self, saved_variable):  # pylint: disable=unused-argument
        return False

    def _build_loot_database(self, saved_variable):  # pylint: disable=unused-argument
        return False

    def _build_history_database(self, saved_variable):  # pylint: disable=unused-argument
        return False

    def _finalize_database(self):
        return

    def _get_dkp(self, player, team):
            team_data = self.__db['global'].get(team)
            if team_data is None:
                return None
            return team_data['dkp'].get(player.lower())

    def _get_team_dkp(self, team):
            team_data = self.__db['global'].get(team)
            if team_data is None:
                return None
            team_dkp_data = []
            for entry in team_data['dkp'].values():
                team_dkp_data.append(entry)
            return team_dkp_data

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

    def __init_db_structure(self):
        self.__db.clear()
        self.__db = {
            'config' : {},
            # Database for all global data indexed by player name. Unsorted.
            'global': {},
            'group': {},   # Database for all grouped data. Indexed by group name. Sorted by DKP value descending
            'time': 0,
            'info': {
                'comment': '',
                'date': '',
                'author': ''
            }
        }

    def __init_team_structure(self, team):
        self.__db['global'][team] = {}
        self.__db['global'][team]['dkp'] = {}
        self.__db['global'][team]['loot'] = []
        self.__db['global'][team]['player_loot'] = {}
        self.__db['global'][team]['history'] = {}
        self.__db['group'][team] = {}

    def __log_database_statistics(self):
        self.statistics.database['teams'] = {
            'global' : len(self.__db['global']),
            'group'  : len(self.__db['group']),
            'ids'   : []
        }

        self.statistics.database['entries'] = {}
        self.statistics.database['teams']['ids'] = []
        for team, data in self.__db['global'].items():
            self.statistics.database['teams']['ids'].append(team)
            self.statistics.database['entries'][team] = {}
            self.statistics.database['entries'][team]['dkp'] = len(data['dkp'])
            self.statistics.database['entries'][team]['history'] = len(data['history'])
            self.statistics.database['entries'][team]['loot'] = len(data['loot'])

        self.statistics.database['group'] = {}
        for team, data in self.__db['group'].items():
            self.statistics.database['group'][team] = []
            for group in data:
                self.statistics.database['group'][team].append(group)

    def _set_addon_config(self, config: dict):
        self.__db['config'] = config


    def _get_addon_config(self, key_list: list):
        if isinstance(key_list, (int, float, str)):
            key_list = [key_list]
        
        if not isinstance(key_list, list) or len(key_list) == 0:
            return None

        tmp = self.__db['config']
        for key in key_list:
            tmp = tmp.get(key)
            if not isinstance(tmp, dict):
                break

        return tmp
        
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

            if not group in team_data.keys():
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
        now = timestamp_now(True)
        for team, team_data in self.__db['global'].items():
            BotLogger().get().debug(team)
            for dkp in team_data['dkp'].values():
                dkp.set_inactive()
                history = self._get_history(dkp.name(), team)
                if history and isinstance(history, list):
                    BotLogger().get().debug("history len {0} \n".format(len(history)))
                    for history_entry in history:
                        BotLogger().get().debug("dkp: {0} | now: {1} | timestamp: {2} | diff {3} ({4}) | {5} \n".format(history_entry.dkp(), now, history_entry.timestamp(), abs(now - history_entry.timestamp()), inactive_time, abs(now - history_entry.timestamp()) <= inactive_time))
                        if history_entry.dkp() > 0:
                            dkp.set_latest_history_entry(history_entry)
                            if abs(now - history_entry.timestamp()) <= inactive_time:
                                dkp.set_active()
                            break

    # This method handles response differently. ERROR status is printed also
    def build_database(self, input_string, info):
        BotLogger().get().info('Building database for server {0}'.format(self.__guild_id))

        start = timestamp_now()

        saved_variable = None
        try:
            saved_variable = self.__get_saved_variables(input_string)
            if saved_variable is None:
                raise AttributeError
        except AttributeError :
            BotLogger().get().error("Error Parsing .lua file.")
            return Response(ResponseStatus.ERROR, BasicCritical("Error Parsing .lua file. Check if you have provided proper savedvariable file.").get())

        if not isinstance(saved_variable, dict):
            BotLogger().get().error("No SavedVariables found in .lua file.")
            return Response(ResponseStatus.ERROR, BasicCritical("No SavedVariables found in .lua file. Check if you have provided proper savedvariable file.").get())

        self.__init_db_structure()

        self.__db['info']['comment'] = info.get('comment')
        self.__db['info']['date'] = info.get('date')
        self.__db['info']['author'] = info.get('author')

        if not self._build_config_database(saved_variable):
            BotLogger().get().error("Configuration Database building failed. Please validate your settings.")
            return Response(ResponseStatus.ERROR, BasicError("Configuration Database building failed. Please validate your settings.").get())
        if not self._build_dkp_database(saved_variable):
            BotLogger().get().error("DKP Database building failed.")
            return Response(ResponseStatus.ERROR, BasicError("DKP Database building failed. Please check your `server-side` and `guild-name` settings.").get())
        if not self._build_loot_database(saved_variable):
            BotLogger().get().error("Loot Database building failed.")
            return Response(ResponseStatus.ERROR, BasicError("Loot Database building failed. Please check your `server-side` and `guild-name` settings.").get())
        if not self._build_history_database(saved_variable):
            BotLogger().get().error("DKP History Database building failed.")
            return Response(ResponseStatus.ERROR, BasicError("DKP History Database building failed. Please check your `server-side` and `guild-name` settings.").get())

        self._finalize_database()

        BotLogger().get().info('Building complete in {:04.2f} seconds'.format(
            timestamp_now() - start))

        self.__log_database_statistics()

        for team in self.__db['global']:
            for table in team:
                if len(table) <= 0:
                    BotLogger().get().error("Global Database building failed.")
                    return Response(ResponseStatus.ERROR, BasicError("Global Database building failed.").get())

        for team in self.__db['group']:
            if len(team) <= 0:
                BotLogger().get().error("Group Database building failed.")
                return Response(ResponseStatus.ERROR, BasicError("Group Database building failed.").get())

        self.__db_loaded = True

        return Response(ResponseStatus.SUCCESS, BasicSuccess("Database building complete.").get())

    # Setting Handlers
    def __set_config(self, group, config, value):
        internal_group = getattr(self.__config, group, None)
        if internal_group:
            if hasattr(internal_group, config):
                setattr(internal_group, config, value)
                new_value = getattr(internal_group, config)
                if isinstance(new_value, bool):
                    return (new_value and (value in ['true', True])) or (not new_value and (value in ['false', False]))
                elif isinstance(new_value, int):
                    try:
                        return new_value == int(value)
                    except ValueError:
                        return False
                else:
                    return new_value == value

        return False

    def __set_config_boolean(self, group, config, value):  # pylint: disable=unused-argument
        value_sanitized = value.lower()
        if value_sanitized in ["true", "1", 1, True]:
            value_sanitized = True
        elif value in ["false", "0", 0, False]:
            value_sanitized = False
        else:
            return False

        if self.__set_config(group, config, value_sanitized):
            self.__config.store()
            self._configure()
            return True
        else:
            return False

    @staticmethod
    def __generic_response(success, config, value):
        if success:
            return Response(ResponseStatus.SUCCESS, BasicSuccess("Successfuly set **{0}** to **{1}**".format(config, value)).get())
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Unsupported value **{1}** provided for **{0}**".format(config, value)).get())

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

    def call_help(self, param, request_info):  # pylint: disable=unused-argument
        params = self._parse_param(param)
        num_params = len(params)
        embed = RawEmbed()
        supported_groups = ['general', 'dkp', 'history', 'items', 'administration']
        if num_params == 0 or ((num_params == 1) and ((params[0] not in supported_groups) or (params[0] == 'administration' and not request_info['is_privileged']))):
            embed.build(None, "Help", "WoW DKP Bot allows querying DKP standings, history and loot data directly through the discord.\n"
                    "All commands and values are case insensitive.\n\n"
                    "You can preceed any command with double prefix `{0}{0}` instead of single one to get the response in DM.\n"
                    "Request will be removed by the bot afterwards.\n\n"
                    "To get more information on supported commands type"
                    "```{0}help group (e.g. {0}help dkp)```"
                    "Supported command groups:".format(self.__prefix), None, get_bot_color(), None)
            commands  = "```{0}help```".format(self.__prefix)
            commands += "```{0}info```".format(self.__prefix)
            embed.add_field(":information_source: General", commands, True)
            commands  = "```{0}dkp #####```".format(self.__prefix)
            embed.add_field(":crossed_swords: DKP", commands, True)
            commands  = "```{0}dkphistory player```".format(self.__prefix)
            commands += "```{0}loot player```".format(self.__prefix)
            embed.add_field(":scroll: History", commands, True)
            commands  = "```{0}raidloot```".format(self.__prefix)
            commands += "```{0}item```".format(self.__prefix)
            commands += preformatted_block('Supporter only commands', 'css')
            embed.add_field(":mag: Items", commands, True)
            if request_info['is_privileged']:
                commands  = "```{0}config```".format(self.__prefix)
                commands += "```{0}display```".format(self.__prefix)
                embed.add_field(":a:  Administration", commands, False)

        else:
            embed.build(None, "Commands", None, None, get_bot_color(), None)
            # General
            if 'general' in params:
                help_string  = 'Display this help. You can also get it by @mentioning the bot.\n{0}\n'.format(preformatted_block(self.get_prefix() + "help", ''))
                help_string += 'Get basic information about the bot.\n{0}\n'.format(preformatted_block(self.get_prefix() + "info", ''))
                embed.add_field("General", help_string, False)
            # DKP
            if 'dkp' in params:
                help_string  = 'Display summary information for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "dkp", ''))
                help_string += 'Display summary information for specified `player`.\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "dkp player", ''))
                help_string += 'Display dkp list for all active players.\nPlayers are assumed active if they gained positive DKP within last 45 days.\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "dkp all", ''))
                help_string += 'Display current DKP for as many players, classes or aliases mixed together as you wish.\n{0}'.format(
                    preformatted_block("{0}dkp class/alias/player\nExamples:\n{0}dkp hunter tanks joe\n{0}dkp rogue druid\n{0}dkp joe andy".format(self.get_prefix()), ''))
                help_string += preformatted_block('Supported aliases:\n* tanks\n* healers\n* dps\n* casters\n* physical\n* ranged\n* melee', '')
                help_string += preformatted_block('Supporter only command', 'css')
                embed.add_field("DKP", help_string, False)
            # History
            if 'history' in params:
                help_string = 'Display DKP history for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "dkphistory", ''))
                help_string += 'Display DKP history  for specified `player`.\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "dkphistory player", ''))
                help_string += 'Display latest loot for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "loot", ''))
                help_string += 'Display latest loot  for specified `player`.\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "loot player", ''))
                embed.add_field("History", help_string, False)
            # Items - Supporter only
            if 'items' in params:
                help_string  = 'Display latest 30 loot entries from raids.\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "raidloot", '') + preformatted_block('Supporter only command', 'css'))
                help_string += 'Find loot entries matching `name`. Supports partial match.\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "item name", '') + preformatted_block('Supporter only command', 'css'))
                embed.add_field("Items", help_string, False)
            # Administration
            if request_info['is_privileged'] and 'administration' in params:
                help_string = preformatted_block('Administrator only commands', 'css')
                help_string  = 'Generic bot configuration (including server and guild)\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "config", ''))
                help_string += 'Display related configuration\n{0}\n'.format(
                    preformatted_block(self.get_prefix() + "display", ''))
                embed.add_field("Administration", help_string, False)

        # Pseudo-Footer: Discord link
        embed.add_field("\u200b", get_bot_links(), False)
        return Response(ResponseStatus.SUCCESS, embed.get())

    def call_info(self, param, request_info): #pylint: disable=unused-argument
        embed = RawEmbed()
        embed.build(None, "Info", None, None, get_bot_color(), None)
        info_string  = "WoW DKP Bot allows querying DKP standings, history and loot data directly through the discord."
        info_string += "This is achieved by parsing uploaded saved variable .lua files of popular addons: `MonolithDKP`, `EssentialDKP` and `CommunityDKP` to a discord channel.\n"
        embed.add_field("\u200b", info_string, False)
        info_string = "Due to many possible usages of the addons and discord limitations bot data may exceed maxium accetable size. To mitigate this issue extensive `display` configuration is available to tweak response sizes."
        embed.add_field("\u200b", info_string, False)
        info_string = "If you want to become supporter and get access to `supporter only commands` or you need help configuring the bot checkout the {0}.\n\n".format(SUPPORT_SERVER)
        embed.add_field("\u200b", info_string, False)
        #embed.add_field("\u200b", info_string, False)
        # Pseudo-Footer: Discord link
        embed.add_field("\u200b", get_bot_links(), False)
        return Response(ResponseStatus.SUCCESS, embed.get())

    def call_config(self, param, request_info):
        if not request_info['is_privileged']:
            return Response(ResponseStatus.IGNORE)

        params = self._parse_param(param)
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
            embed.build(None, "Available configurations", "All commands and values are case insensitive.", None, 16553987, None)
            # bot-type
            string = "Set bot type to handle specified addon\n"
            string += preformatted_block("Usage:     {0}config bot-type Type\n".format(self.__prefix))
            string += preformatted_block("Current:   {0}\n".format(self.__config.guild_info.bot_type.lower()))
            string += preformatted_block("Supported: essential monolith community")
            embed.add_field("bot-type", string, False)
            # server-side
            string = "Set ingame server and side data required by some addons\n"
            string += preformatted_block("Usage:     {0}config server-side ServerName Side\nExample:   {0}config server-side Dragon's Call Alliance\n".format(self.__prefix))
            data = self.__config.guild_info.server_side.split("-")
            if len(data) == 2:
                string2 = "Current:   {0}".format(' '.join(data).lower())
            else:
                string2 = "Current:   none"
            string += preformatted_block(string2)
            embed.add_field("server-side", string, False)
            # guild-name
            string = "Set ingame guild name required by some addons\n"
            string += preformatted_block("Usage:     {0}config guild-name GuildName\nExample:   {0}config guild-name Some Guild".format(self.__prefix))
            data = self.__config.guild_info.guild_name
            if len(data) > 0:
                string2 = "Current:   {0}".format(data.lower())
            else:
                string2 = "Current:   none"
            string += preformatted_block(string2)
            embed.add_field("guild-name", string, False)
            # team
            string = "Register channel to handle specified team number (starting from 0). Limited to 8 channels. If no #channel is mentioned then the current one will be used. Bot must have access to the channel. Calling without any parameters will result in available team list.\n"
            string += preformatted_block("Usage:     {0}config team Id #channel\nExample:   {0}config team 0".format(self.__prefix))
            num_teams = len(self._channel_team_map)
            if num_teams > 0:
                string += preformatted_block("Current:") + "\n"
                for channel, team in self._channel_team_map.items():
                    string += "`Team {1}` <#{0}>\n".format(channel, team)
            else:
                string += preformatted_block("Current:   none") + "\n"
            embed.add_field("team", string, False)
            # smart-roles
            string = "Configure `smart roles`. This feature modifies group alias requests (e.g. tank, healer) to be based on class and talent specialisation instead of class only. This result may be inaccurate.\n"
            string += preformatted_block("Usage:     {0}config smart-roles value".format(self.__prefix))
            string += preformatted_block("Current:   {0}\n".format(self.__smart_roles))
            string += preformatted_block("Supported: {0}\n".format("True False"))
            embed.add_field("smart-roles", string, False)
            # register
            string = "Register channel as the only one on which lua saved variable upload will be accepted. If no #channel is mentioned then the current one will be used. Bot must have access to the channel.\n"
            string += preformatted_block("Usage:     {0}config register #channel".format(self.__prefix))
            if self.__config.guild_info.file_upload_channel == 0:
                string += preformatted_block("Current:   any")
            else:
                string += preformatted_block("Current:") + "\n"
                string += "<#{0}>".format(self.__config.guild_info.file_upload_channel)
            embed.add_field("register", string, False)
            # announcement
            string = "Register channel as announcement channel on which bot will post message on new DKP standings upload. If no #channel is mentioned then the current one will be used. You can also @mention a role which will be mentioned during the announcement. Bot must have access to the channel.\n"
            string += preformatted_block("Usage:     {0}config announcement #channel @role".format(self.__prefix))
            if self.__config.guild_info.announcement_channel == 0:
                string += preformatted_block("Current:   none")
            else:
                string += preformatted_block("Current:") + "\n"
                string += "<#{0}>".format(self.__config.guild_info.announcement_channel)
                if self.__config.guild_info.announcement_mention_role != 0:
                    string += " <@&{0}>".format(self.__config.guild_info.announcement_mention_role)
            embed.add_field("announcement", string, False)
            # prefix
            string = "Change bot prefix\n"
            string += preformatted_block("Usage:     {0}config prefix *".format(self.__prefix))
            string += preformatted_block("Current:   {0}\n".format(self.__prefix))
            string += preformatted_block("Supported: {0}\n".format(' '.join(self.get_supported_prefixes())))
            embed.add_field("prefix", string, False)
            # dm-response
            string = "Swap default response channel to DM (direct message)\n"
            string += preformatted_block("Usage:     {0}config dm-response value".format(self.__prefix))
            string += preformatted_block("Current:   {0}\n".format(self.__direct_message_response))
            string += preformatted_block("Supported: {0}\n".format("True False"))
            embed.add_field("dm-response", string, False)
            # block-response-modifier
            string = "Block response modifier `{0}` for users without administrator privileges\n".format(2 * self.__prefix)
            string += preformatted_block("Usage:     {0}config block-response-modifier value".format(self.__prefix))
            string += preformatted_block("Current:   {0}\n".format(self.__block_response_modifier))
            string += preformatted_block("Supported: {0}\n".format("True False"))
            embed.add_field("block-response-modifier", string, False)
            # reload
            string = "Reload the bot. This is required to apply some configuration changes. Afterwards bot reparses database with new `server-side` and `guild-name` configuration.\n"
            string += preformatted_block("Usage:     {0}config reload".format(self.__prefix))
            embed.add_field("reload", string, False)
            # default
            string = "Instantly reset bot configuration to default - this also resets `prefix` and `bot type`\n"
            string += preformatted_block("Usage:     {0}config default".format(self.__prefix))
            embed.add_field("default", string, False)

            # Pseudo-Footer: Discord link
            embed.add_field("\u200b", get_bot_links(), False)

            return Response(ResponseStatus.SUCCESS, embed.get())
        return Response(ResponseStatus.IGNORE)

    def call_display(self, param, request_info):
        if not request_info['is_privileged']:
            return Response(ResponseStatus.IGNORE)

        param = self._parse_param(param)
        params = list(map(lambda p: p.lower().replace("-", "_"), param))

        num_params = len(params)
        if num_params <= 1:
            display_info = self.__config.get_configs_data()
            embed = RawEmbed()
            embed.build(None, "Available display settings",
                        "Configure number of data displayed in single request. All commands and values are case insensitive.", None, 16553987, None)

            for category, data in display_info.items():
                string = ""
                string += "```swift\n"
                string += "Category: {0}\n\n".format(category)
                string += data['value']
                string += "```"
                embed.add_field(data['title'], string, False)

            string = "```swift\nUsage:\n\n{0}display Category Config Value```".format(self.__prefix)
            string += "```swift\nExample:\n\n{0}display loot-history multiple-columns True```".format(self.__prefix)
            embed.add_field("\u200b", string, False)

            # Pseudo-Footer: Discord link
            embed.add_field("\u200b", get_bot_links(), False)

            return Response(ResponseStatus.SUCCESS, embed.get())

        if num_params >= 3:
            category = params[0]
            config = params[1]
            value = params[2]
            if category in self.__config.get_directly_accessible_configs():
                if self.__set_config(category, config, value):
                    self.__config.store()
                    self._configure()
                    return Response(ResponseStatus.SUCCESS, BasicSuccess("Successfuly set **{0} {1}** to **{2}**".format(param[0], param[1], param[2])).get())
                else:
                    return Response(ResponseStatus.SUCCESS, BasicError("Unsupported value **{2}** provided for **{0} {1}**".format(param[0], param[1], param[2])).get())
            else:
                return Response(ResponseStatus.SUCCESS, BasicError("Invalid category **{0}**".format(param[0])).get())

        return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    ### Config handlers ###

    def config_call_bot_type(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params == 2:
            value = params[1]
            if value in ['community', 'monolith', 'essential', 'cepgp']:
                current = self.__config.guild_info.bot_type
                if value == current:
                    return Response(ResponseStatus.SUCCESS,  BasicSuccess('Retaining current bot type').get())

                self.__config.guild_info.bot_type = value
                new = self.__config.guild_info.bot_type

                if new == value:
                    if value == 'cepgp':
                        self.__config.guild_info.filename = "CEPGP.lua"
                    else:
                        self.__config.guild_info.filename = value.capitalize() + 'DKP.lua'
                    self._reconfigure()
                    return Response(ResponseStatus.RELOAD, self.__guild_id)
                else:
                    return Response(ResponseStatus.ERROR, 'Unexpected error during bot type setup')
            else:
                return Response(ResponseStatus.SUCCESS, BasicError('Unsupported bot type').get())
        else:
            return Response(ResponseStatus.SUCCESS, BasicSuccess("Invalid number of parameters").get())

    def config_call_prefix(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params == 2:
            value = params[1]
            if value in self.get_supported_prefixes():
                self.__config.guild_info.prefix = value
                new = self.__config.guild_info.prefix
                if new == value:
                    self._reconfigure()
                    return Response(ResponseStatus.SUCCESS, BasicSuccess('Set prefix to `{0}`'.format(value)).get())
                else:
                    return Response(ResponseStatus.ERROR, 'Unexpected error during prefix change')
            else:
                return Response(ResponseStatus.SUCCESS, BasicError('Unsupported prefix').get())
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_default(self, params, num_params, request_info): #pylint: disable=unused-argument
        self.__config.default()
        return Response(ResponseStatus.RELOAD, self.__guild_id)

    def config_call_reload(self, params, num_params, request_info): #pylint: disable=unused-argument
        return Response(ResponseStatus.RELOAD, self.__guild_id)

    def config_call_register(self, params, num_params, request_info): #pylint: disable=unused-argument
        channel = request_info['channel']['id']
        if len(request_info['mentions']['channels']) > 0:
            channel = request_info['mentions']['channels'][0]
        self.__register_file_upload_channel(channel)
        return Response(ResponseStatus.SUCCESS,
                        BasicSuccess('Registered to expect Saved Variable lua file on channel <#{0}>'.format(channel)).get())

    def config_call_announcement(self, params, num_params, request_info): #pylint: disable=unused-argument
        channel = request_info['channel']['id']
        if len(request_info['mentions']['channels']) > 0:
            channel = request_info['mentions']['channels'][0]
        role = 0
        role_response = "No mentionable role provided."
        if len(request_info['mentions']['roles']) > 0:
            role = request_info['mentions']['roles'][0]
            role_response = "<@&{0}> will be mentioned in the announcement.".format(role)

        self.__register_announcement(channel, role)
        response  = 'Registered channel <#{0}> to announce updated DKP standings.\n'.format(channel)
        response += role_response
        return Response(ResponseStatus.SUCCESS, BasicSuccess(response).get())

    def config_call_server_side(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params >= 3:
            server = ' '.join(params[1:-1]).lower()
            side = str(params[-1]).lower()
            if side not in ['alliance', 'horde']:
                return Response(ResponseStatus.SUCCESS, BasicError("Last parameter must be either `Alliance` or `Horde`").get())

            value = "{0}-{1}".format(server, side)
            if len(value) > 50:
                return Response(ResponseStatus.SUCCESS, BasicError('Data is too long.').get())

            self.__config.guild_info.server_side = value
            new = self.__config.guild_info.server_side
            if new == value:
                self._reconfigure()
                return Response(ResponseStatus.SUCCESS, BasicSuccess('Server-side data set to `{0} {1}`'.format(server, side)).get())
            else:
                return Response(ResponseStatus.ERROR, 'Unexpected error during server-side change.')
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_guild_name(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params >= 2:
            value = ' '.join(params[1:]).lower()
            if len(value) > 50:
                return Response(ResponseStatus.ERROR, BasicError('Data is too long.').get())

            self.__config.guild_info.guild_name = value
            new = self.__config.guild_info.guild_name
            if new == value:
                self._reconfigure()
                return Response(ResponseStatus.SUCCESS, BasicSuccess('Guild Name set to `{0}`'.format(value)).get())
            else:
                return Response(ResponseStatus.ERROR, 'Unexpected error during guild name change.')
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_team(self, params, num_params, request_info): #pylint: disable=unused-argument
        channel = request_info['channel']['id']
        if len(request_info['mentions']['channels']) > 0:
            channel = request_info['mentions']['channels'][0]
        if num_params == 1:
            teams = self._get_addon_config(["teams"])
            if isinstance(teams, dict) and len(teams) > 0:
                team_data  = "```"
                team_data += "Id   Name\n"
                for team_id, team_info in teams.items():
                    team_data += "{0:2}   {1}\n".format(team_id, team_info.get('name'))
                team_data += "```"
                return Response(ResponseStatus.SUCCESS, BasicInfo(team_data).get())
            else:
                return Response(ResponseStatus.SUCCESS, BasicError("No teams found").get())
        elif num_params >= 2:
            if self._set_channel_team_mapping(channel, params[1]):
                error_text = ""
            else:
                error_text = "Exceeded maximum number of channels. Removing oldest assignment."
            return Response(ResponseStatus.SUCCESS, BasicSuccess('Registered channel <#{0}> to handle team {1}. {2}'.format(channel, params[1], error_text)).get())
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_smart_roles(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params == 2:
            success = self.__set_config_boolean('guild_info', 'smart_roles', params[1])
            return self.__generic_response(success, "smart-roles", params[1])
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_dm_response(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params == 2:
            success = self.__set_config_boolean('guild_info', 'direct_message_response', params[1])
            return self.__generic_response(success, "dm-response", params[1])
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_block_response_modifier(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params == 2:
            success = self.__set_config_boolean('guild_info', 'block_response_modifier', params[1])
            return self.__generic_response(success, "block-response-modifier", params[1])
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())