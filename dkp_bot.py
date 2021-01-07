import re
import json
import collections
from enum import Enum
import pytz

from savedvariables_parser import SavedVariablesParser
from bot_config import BotConfig
from bot_logger import BotLogger, trace, trace_func_only, for_all_methods
from bot_utility import timestamp_now
from statistics import Statistics
import bot_memory_manager
from display_templates import SUPPORT_SERVER
from display_templates import get_bot_color, get_bot_links, preformatted_block
from display_templates import SupportReminder, RawEmbed, BasicCritical, BasicError, BasicSuccess, BasicAnnouncement, BasicInfo, BotDisabledResponse

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

@for_all_methods(trace, trace_func_only)
class DKPBot:
    DEFAULT_TEAM = "0"
    REMINDER_FREQUENCY = 25
    __POSITIVE_ENTRY_THRESHOLD = 2

    __param_parser = re.compile("\s*([\d\w\-!?+.:<>|*^'\"]*)[\s[\/\,]*")  # pylint: disable=anomalous-backslash-in-string
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


    def __init__(self, guild_id: int, config: BotConfig):
        self.__enabled = True
        self.__db = {}
        self.__config = config
        self.__guild_id = int(guild_id)
        self.__channel = 0
        self.__announcement_channel = 0
        self.__announcement_mention_role = 0
        self._channel_team_map = collections.OrderedDict()
        self.__db_loaded = False
        self.__reminder_command_count = self.REMINDER_FREQUENCY
        self.__init_db_structure()
        self.statistics = Statistics()
        self._timezone = pytz.timezone("Europe/Paris")

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
        self._timezone = pytz.timezone(self.__config.guild_info.timezone)

    def _reconfigure(self):
        self.__config.store()
        self._configure()

    def shutdown(self):
        BotLogger().get().info("Shutting down bot for [%d]", self.__guild_id)
        self.disable()
        self.__config.store()

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

    def get_timezone(self):
        return self._timezone

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
            (channel, team) = self._channel_team_map.popitem(False)
            BotLogger().get().info("Removing mapping of team %s from channel %s", team, channel)
            in_limit = False

        self._channel_team_map[str(channel_id)] = str(team)
        self.__config.guild_info.channel_team_map = json.dumps(self._channel_team_map)
        self._reconfigure()

        return in_limit

    # Timezone
    def _update_timezone(self, timezone):
        self.__config.guild_info.timezone = str(timezone)
        self._reconfigure()

    ### Command handling and parsing ###

    def _parse_param(self, param):
        # Remove empty strings
        targets = list(filter(None, type(self).__param_parser.findall(param)))
        # Lowercase all
        params = list(map(lambda x: x.strip().lower(), targets))
        BotLogger().get().debug("Parse param result: %s", params)
        return params

    def _parse_player_param(self, param):
        # Remove empty strings
        original = list(filter(None, type(self).__param_parser.findall(param)))
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
        # Int list
        int_list = self._get_int_list(original)
        BotLogger().get().debug("Parse player param results. [targets: %s] [aliases: %s] [original: %s] [int_list: %s]", targets, aliases, original, int_list)
        return (targets, aliases, original, int_list)

    def _get_int_list(self, original: list):
        int_list = []
        for param in original:
            try:
                param_int = int(param)
                int_list.append(param_int)
            except ValueError:
                continue
        return int_list

    def __reminder_injection(self, response: Response):
        if self.is_premium():
            return response

        if not isinstance(response, Response):
            return response

        if response.direct_message:
            return response

        self.__reminder_command_count = self.__reminder_command_count - 1
        if self.__reminder_command_count == 0:
            self.__reminder_command_count = self.REMINDER_FREQUENCY
            if not isinstance(response.data, list):
                response.data = [response.data]
            response.data.append(SupportReminder().get())
            BotLogger().get().info("Injecting reminder for server %s", self.__guild_id)

        return response

    def __parse_command(self, string):
        if isinstance(string, str):
            args = string.split(" ")
            if len(args) > 1:
                command = args[0]
                params = " ".join(args[1:])
                return (command, params)
            elif len(args) == 1:
                command = args[0]
                params = None
                return (command, params)
            else:
                return None
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
            if not self.is_enabled():
                return Response(ResponseStatus.SUCCESS, BotDisabledResponse().get())
            BotLogger().get().info("Calling [%s] with param [%s] for [%d]", sanitized_command, param, self.__guild_id)
            bot_memory_manager.Manager().Handle(self.__guild_id)  # pylint: disable=no-value-for-parameter
            start = timestamp_now()
            response = callback(param, request_info)  # pylint: disable=not-callable
            self.statistics.data[sanitized_command] = (1000 * (timestamp_now() - start)) # miliseconds
            response.direct_message = direct_message
            response = self.__reminder_injection(response)
            return response
        elif sanitized_command.startswith('su_'):
            return Response(ResponseStatus.DELEGATE, (sanitized_command, param))
        else:
            BotLogger().get().debug("Unknown command [%s] for [%d]", sanitized_command, self.__guild_id)
            return Response(ResponseStatus.IGNORE)

    def handle(self, message, request_info):
        if len(message) > 0 and message[0] == self.__prefix:
            (command, param) = self.__parse_command(message)
            if command is not None:
                if param is None:
                    param = request_info['author']['name']
                return self.__handle_command(command.lower(), param.lower(), request_info)
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
            BotLogger().get().warning("Unknown team %s", team)
            return None
        return team_data['dkp'].get(player.lower())

    def _get_team_dkp(self, team):
            team_data = self.__db['global'].get(team)
            if team_data is None:
                BotLogger().get().warning("Unknown team %s", team)
                return None
            team_dkp_data = []
            for entry in team_data['dkp'].values():
                team_dkp_data.append(entry)
            return team_dkp_data

    def _search_dkp(self, player, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            BotLogger().get().warning("Unknown team %s", team)
            return None
        players = team_data['dkp'].keys()
        players = [p for p in players if p.lower().startswith(player)]
        return players

    def _get_player_loot(self, player, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            BotLogger().get().warning("Unknown team %s", team)
            return None
        return team_data['player_loot'].get(player.lower())

    def _get_loot(self, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            BotLogger().get().warning("Unknown team %s", team)
            return None
        return team_data['loot']

    def _get_history(self, player, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            BotLogger().get().warning("Unknown team %s", team)
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
            BotLogger().get().warning("Unknown team %s", team)
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
            BotLogger().get().warning("Unknown team %s", team)
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

    def _add_history_to_all_players(self, entry, team):
        team_data = self.__db['global'].get(team)
        if team_data is None:
            self.__init_team_structure(team)
            team_data = self.__db['global'].get(team)

            for player in team_data:
                self._add_history(player.name(), entry, team)

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
            for dkp in team_data['dkp'].values():
                dkp.set_inactive()
                positive_entry_count = 0
                history = self._get_history(dkp.name(), team)
                if history and isinstance(history, list):
                    for history_entry in history:
                        if history_entry.dkp() > 0:
                            if positive_entry_count == 0:
                                dkp.set_latest_history_entry(history_entry)
                            if abs(now - history_entry.timestamp()) <= inactive_time:
                                positive_entry_count = positive_entry_count +  1
                                if positive_entry_count >= self.__POSITIVE_ENTRY_THRESHOLD:
                                    dkp.set_active()
                                    break
                            else:
                                break

    # This method handles response differently. ERROR status is printed also
    def build_database(self, input_string, info):
        if not self.is_enabled():
            return Response(ResponseStatus.SUCCESS, BotDisabledResponse().get())

        start = timestamp_now()

        saved_variable = None
        try:
            saved_variable = self.__get_saved_variables(input_string)
            if saved_variable is None:
                raise AttributeError
        except AttributeError :
            BotLogger().get().error("Error Parsing .lua file.")
            return Response(ResponseStatus.SUCCESS, BasicCritical("Error Parsing .lua file. Check if you have provided proper savedvariable file.").get())

        if not isinstance(saved_variable, dict):
            BotLogger().get().error("No SavedVariables found in .lua file.")
            return Response(ResponseStatus.SUCCESS, BasicCritical("No SavedVariables found in .lua file. Check if you have provided proper savedvariable file.").get())

        self.__init_db_structure()

        self.__db['info']['comment'] = info.get('comment')
        self.__db['info']['date'] = info.get('date')
        self.__db['info']['author'] = info.get('author')

        if not self._build_config_database(saved_variable):
            BotLogger().get().error("Configuration Database building failed. Please validate your settings.")
            return Response(ResponseStatus.SUCCESS, BasicError("Configuration Database building failed. Please validate your settings.").get())
        if not self._build_dkp_database(saved_variable):
            BotLogger().get().error("Profile Database building failed.")
            return Response(ResponseStatus.SUCCESS, BasicError("Profile Database building failed. Please validate your settings.").get())
        if not self._build_loot_database(saved_variable):
            BotLogger().get().error("Loot Database building failed.")
            return Response(ResponseStatus.SUCCESS, BasicError("Loot Database building failed. Please validate your settings.").get())
        if not self._build_history_database(saved_variable):
            BotLogger().get().error("History Database building failed.")
            return Response(ResponseStatus.SUCCESS, BasicError("History Database building failed. Please validate your settings.").get())

        self._finalize_database()

        BotLogger().get().info('Building complete in {:04.2f} seconds'.format(
            timestamp_now() - start))

        self.__log_database_statistics()

        for team in self.__db['global']:
            for table in team:
                if len(table) <= 0:
                    BotLogger().get().error("Global Database building failed.")
                    return Response(ResponseStatus.SUCCESS, BasicError("Global Database building failed.").get())

        for team in self.__db['group']:
            if len(team) <= 0:
                BotLogger().get().error("Group Database building failed.")
                return Response(ResponseStatus.SUCCESS, BasicError("Group Database building failed.").get())

        self.__db_loaded = True

        return Response(ResponseStatus.SUCCESS, BasicSuccess("Database building complete.").get())

    # Setting Handlers
    def __set_config(self, group, config, value):
        internal_group = getattr(self.__config, group, None)
        if internal_group:
            if hasattr(internal_group, config):
                setattr(internal_group, config, value)
                new_value = getattr(internal_group, config)
                BotLogger().get().debug("Setting %s %s to %s. New value: %s", group, config, value, new_value)
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

        BotLogger().get().debug("Setting boolean %s %s to %s", group, config, value_sanitized)

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

    def _build_help_internal(self, is_privileged, standings):
        embed = RawEmbed()
        embed.build(None, "Help", "WoW DKP Bot allows querying DKP/EPGP standings, history and loot data directly through the discord.\n"
                "All commands and values are case insensitive.\n\n"
                "You can preceed any command with double prefix `{0}{0}` instead of single one to get the response in DM.\n"
                "Request will be removed by the bot afterwards.\n\n"
                "To get more information on supported commands type"
                "```{0}help group (e.g. {0}help {1})```"
                "Supported command groups:".format(self.__prefix, standings.lower()), None, get_bot_color(), None)
        commands  = "```{0}help```".format(self.__prefix)
        commands += "```{0}info```".format(self.__prefix)
        embed.add_field(":information_source: General", commands, True)
        commands  = "```{0}{1} #####```".format(self.__prefix, standings.lower())
        embed.add_field(":crossed_swords: {0}".format(standings.upper()), commands, True)
        commands  = "```{0}history player```".format(self.__prefix)
        commands += "```{0}loot player```".format(self.__prefix)
        embed.add_field(":scroll: History", commands, True)
        commands  = "```{0}raidloot```".format(self.__prefix)
        commands += "```{0}item```".format(self.__prefix)
        commands += preformatted_block('Supporter only commands', 'css')
        embed.add_field(":mag: Items", commands, True)
        if is_privileged:
            commands  = "```{0}config```".format(self.__prefix)
            commands += "```{0}display```".format(self.__prefix)
            embed.add_field(":a:  Administration", commands, False)
        embed.add_field("\u200b", get_bot_links(), False)
        return embed.get()

    def _help_internal(self, is_privileged):
        return Response(ResponseStatus.SUCCESS, self._build_help_internal(is_privileged, 'dkp'))

    def _help_handler_internal(self, title, help_string):
        embed = RawEmbed()
        embed.build(None, "Commands", None, None, get_bot_color(), None)
        embed.add_field(title, help_string, False)
        # Pseudo-Footer: Discord link
        embed.add_field("\u200b", get_bot_links(), False)
        return embed.get()

    ### Command callbacks ###

    def call_help(self, param, request_info):  # pylint: disable=unused-argument
        params = self._parse_param(param)
        num_params = len(params)

        if num_params == 0:
            return self._help_internal(request_info['is_privileged'])

        command = params[0]

        method = "help_call_" + command.replace("-", "_").lower()
        callback = getattr(self, method, None)
        if callback and callable(callback):
            return callback(request_info['is_privileged'])
        else:
            return self._help_internal(request_info['is_privileged'])

    def call_info(self, param, request_info): # pylint: disable=unused-argument
        embed = RawEmbed()
        embed.build(None, "Info", None, None, get_bot_color(), None)
        info_string  = "WoW DKP Bot allows querying DKP/EPGP standings, history and loot data directly through the discord."
        info_string += "This is achieved by parsing uploaded saved variable .lua files of popular addons: `MonolithDKP`, `EssentialDKP`, `CommunityDKP` and `CEPGP` to a discord channel.\n"
        embed.add_field("\u200b", info_string, False)
        info_string = "Due to many possible usages of the addons and discord limitations bot data may exceed maxium accetable size. To mitigate this issue extensive `display` configuration is available to tweak response sizes."
        embed.add_field("\u200b", info_string, False)
        info_string = "For bot to work properly you will need to upload saved variable file of your addon every time you want to update the data."
        embed.add_field("\u200b", info_string, False)
        info_string = "If you want to become supporter and get access to `supporter only commands` or you need help configuring the bot checkout the {0}.\n\n".format(SUPPORT_SERVER)
        embed.add_field("\u200b", info_string, False)
        # Pseudo-Footer: Discord link
        embed.add_field("\u200b", get_bot_links(), False)
        return Response(ResponseStatus.SUCCESS, embed.get())

    def call_config(self, param, request_info):
        if not request_info['is_privileged']:
            BotLogger().get().warning("Unprivileged access to config: %s", request_info)
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
            embed = RawEmbed()
            embed.build(None, "Available configurations", "All commands and values are case insensitive.", None, 16553987, None)
            # bot-type
            string = "Set bot type to handle specified addon\n"
            string += preformatted_block("Usage:     {0}config bot-type Type\n".format(self.__prefix))
            string += preformatted_block("Current:   {0}\n".format(self.__config.guild_info.bot_type.lower()))
            string += preformatted_block("Supported: essential monolith community cepgp")
            embed.add_field("bot-type", string, False)
            # timezone
            string = "Configure bot timezone. Supports most **cannonical** timezones. For reference check [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)."
            string += preformatted_block("Usage:     {0}config timezone CanonicalTimezone".format(self.__prefix))
            string += preformatted_block("Current:   {0}\n".format(self._timezone))
            embed.add_field("timezone", string, False)
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
            string += preformatted_block("Supported: {0}\n".format(' '.join(type(self).get_supported_prefixes())))
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
            BotLogger().get().warning("Unprivileged access to display: %s", request_info)
            return Response(ResponseStatus.IGNORE)

        param = self._parse_param(param)
        params = list(map(lambda p: p.lower().replace("-", "_"), param))

        num_params = len(params)
        if num_params <= 1:
            display_info = self.__config.get_configs_data()
            embed = RawEmbed()
            embed.build(None, "Available display settings",
                        "Configure number of data displayed in single request. All commands and values are case insensitive. All EPGP settings are handled by DKP configurations.", None, 16553987, None)

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

    ### Help handlers ###

    def help_call_general(self, is_privileged): # pylint: disable=unused-argument
        help_string  = 'Display this help. You can also get it by @mentioning the bot.\n{0}\n'.format(preformatted_block(self.get_prefix() + "help", ''))
        help_string += 'Get basic information about the bot.\n{0}\n'.format(preformatted_block(self.get_prefix() + "info", ''))

        return Response(ResponseStatus.SUCCESS, self._help_handler_internal("General", help_string))

    def help_call_dkp(self, is_privileged): # pylint: disable=unused-argument
        help_string  = 'Display summary information for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "dkp", ''))
        help_string += 'Display summary information for specified `player`.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "dkp player", ''))
        help_string += 'Display dkp list for all active players.\nPlayers are assumed active if they gained positive DKP within last 45 days.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "dkp all", ''))
        help_string += 'Display current DKP for as many players, classes or aliases mixed together as you wish.\n{0}'.format(
            preformatted_block("{0}dkp class/alias/player\nExamples:\n{0}dkp hunter tanks joe\n{0}dkp rogue druid\n{0}dkp joe andy".format(self.get_prefix()), ''))
        help_string += preformatted_block('Supported aliases:\n* tanks\n* healers\n* dps\n* casters\n* physical\n* ranged\n* melee', '')
        help_string += preformatted_block('Supporter only command', 'css') + "\n"
        help_string += 'Display summary information for players signed to `raidid` event in `Raid-Helper` bot. Supporters can also use it in conjunction with above mixnis.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "dkp raidid", ''))

        return Response(ResponseStatus.SUCCESS, self._help_handler_internal("DKP", help_string))
    
    def help_call_history(self, is_privileged): # pylint: disable=unused-argument
        help_string = 'Display DKP history for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "history", ''))
        help_string += 'Display DKP history  for specified `player`.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "history player", ''))
        help_string += 'Display latest loot for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "loot", ''))
        help_string += 'Display latest loot  for specified `player`.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "loot player", ''))

        return Response(ResponseStatus.SUCCESS, self._help_handler_internal("History", help_string))

    def help_call_items(self, is_privileged): # pylint: disable=unused-argument
        help_string  = 'Display latest 30 loot entries from raids.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "raidloot", '') + preformatted_block('Supporter only command', 'css'))
        help_string += 'Find loot entries matching `name`. Supports partial match.\n{0}\n'.format(
            preformatted_block(self.get_prefix() + "item name", '') + preformatted_block('Supporter only command', 'css'))

        return Response(ResponseStatus.SUCCESS, self._help_handler_internal("Items", help_string))

    def help_call_administration(self, is_privileged): # pylint: disable=unused-argument
        if is_privileged:
            help_string = preformatted_block('Administrator only commands', 'css')
            help_string  = 'Generic bot configuration (including server and guild)\n{0}\n'.format(
                preformatted_block(self.get_prefix() + "config", ''))
            help_string += 'Display related configuration\n{0}\n'.format(
                preformatted_block(self.get_prefix() + "display", ''))

            return Response(ResponseStatus.SUCCESS, self._help_handler_internal("Administration", help_string))
        else:
            BotLogger().get().warning("Unprivileged access to help administration: %s", request_info)
            return Response(ResponseStatus.IGNORE)

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
                    BotLogger().get().error("Unexpected error during bot type setup: %s", request_info)
                    return Response(ResponseStatus.SUCCESS, BasicCritical('Unexpected error during bot type setup').get())
            else:
                BotLogger().get().warning("Unsupported bot type %s", value)
                return Response(ResponseStatus.SUCCESS, BasicError('Unsupported bot type').get())
        else:
            return Response(ResponseStatus.SUCCESS, BasicSuccess("Invalid number of parameters").get())

    def config_call_prefix(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params == 2:
            value = params[1]
            if value in type(self).get_supported_prefixes():
                self.__config.guild_info.prefix = value
                new = self.__config.guild_info.prefix
                if new == value:
                    self._reconfigure()
                    return Response(ResponseStatus.SUCCESS, BasicSuccess('Set prefix to `{0}`'.format(value)).get())
                else:
                    BotLogger().get().error("Unexpected error during prefix change: %s", request_info)
                    return Response(ResponseStatus.SUCCESS, BasicCritical('Unexpected error during prefix change').get())
            else:
                BotLogger().get().warning("Unsupported prefix %s", value)
                return Response(ResponseStatus.SUCCESS, BasicError('Unsupported prefix').get())
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_default(self, params, num_params, request_info): #pylint: disable=unused-argument
        BotLogger().get().info("Defaulting bot configuration for [%d]", self.__guild_id)
        self.__config.default()
        return Response(ResponseStatus.RELOAD, self.__guild_id)

    def config_call_reload(self, params, num_params, request_info): #pylint: disable=unused-argument
        BotLogger().get().info("Reloading bot for [%d]", self.__guild_id)
        self._reconfigure()
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
                return Response(ResponseStatus.SUCCESS, BasicError('Data should not exceed 50 characters.').get())

            self.__config.guild_info.server_side = value
            new = self.__config.guild_info.server_side
            if new == value:
                self._reconfigure()
                return Response(ResponseStatus.SUCCESS, BasicSuccess('Server-side data set to `{0} {1}`'.format(server, side)).get())
            else:
                BotLogger().get().error("Unexpected error during server-side change: %s", request_info)
                return Response(ResponseStatus.SUCCESS, BasicCritical('Unexpected error during server-side change').get())
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_guild_name(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params >= 2:
            value = ' '.join(params[1:]).lower()
            if len(value) > 50:
                return Response(ResponseStatus.SUCCESS, BasicError('Data should not exceed 50 characters.').get())

            self.__config.guild_info.guild_name = value
            new = self.__config.guild_info.guild_name
            if new == value:
                self._reconfigure()
                return Response(ResponseStatus.SUCCESS, BasicSuccess('Guild Name set to `{0}`'.format(value)).get())
            else:
                BotLogger().get().error("Unexpected error during guild name change to %s", value)
                return Response(ResponseStatus.SUCCESS, 'Unexpected error during guild name change.')
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
            return type(self).__generic_response(success, "smart-roles", params[1])
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_dm_response(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params == 2:
            success = self.__set_config_boolean('guild_info', 'direct_message_response', params[1])
            return type(self).__generic_response(success, "dm-response", params[1])
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_block_response_modifier(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params == 2:
            success = self.__set_config_boolean('guild_info', 'block_response_modifier', params[1])
            return type(self).__generic_response(success, "block-response-modifier", params[1])
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

    def config_call_timezone(self, params, num_params, request_info): #pylint: disable=unused-argument
        if num_params == 3:
            params[1] = params[1] + "/" + params[2]
            num_params = 2

        if num_params == 2:
            success = False
            try:
                self._update_timezone(pytz.timezone(params[1]))
                success = True
            except pytz.exceptions.UnknownTimeZoneError:
                pass
            return type(self).__generic_response(success, "timezone", params[1])
        else:
            return Response(ResponseStatus.SUCCESS, BasicError("Invalid number of parameters").get())

