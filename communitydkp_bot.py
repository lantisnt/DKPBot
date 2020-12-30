from dkp_bot import DKPBot
from essentialdkp_bot import EssentialDKPBot
from display_templates import SinglePlayerProfile
from bot_logger import trace, trace_func_only, for_all_methods

@for_all_methods(trace, trace_func_only)
class CommunityDKPBot(EssentialDKPBot):

    _CONFIG_SV = "CommDKP_DB"
    _DKP_SV = "CommDKP_DKPTable"
    _LOOT_SV = "CommDKP_Loot"
    _HISTORY_SV = "CommDKP_DKPHistory"

    def _configure(self):
        super()._configure()
        # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile("Community DKP Profile")


    def __get_configured_teams(self, server_list):
        server_side = self._get_config().guild_info.server_side
        guild_name = self._get_config().guild_info.guild_name

        if not (server_side and guild_name):
            return None

        # Decode server-side first
        if not server_list:
            return None

        if not isinstance(server_list, dict):
            return None

        server_side_key = None
        for server_side_lua in server_list.keys():
            if server_side_lua.lower() == server_side:
                server_side_key = server_side_lua
                break

        if server_side_key is None:
            return None

        # Decode guilds
        guilds = server_list.get(server_side_key)
        if not guilds:
            return None

        guild_name_key = None
        for guild_name_lua in guilds.keys():
            if guild_name_lua.lower() == guild_name:
                guild_name_key = guild_name_lua
                break

        if guild_name_key is None:
            return None

        return guilds.get(guild_name_key)

    # Called 1st
    def _build_config_database(self, saved_variable):  # pylint: disable=unused-argument
        super()._build_loot_database(None)
        config_list = self.__get_configured_teams(saved_variable.get(self._CONFIG_SV))
        if config_list is None:
            return False

        self._set_addon_config(config_list)

        return True

    # Called 2st
    def _build_dkp_database(self, saved_variable):
        super()._build_dkp_database(None)
        teams = self.__get_configured_teams(saved_variable.get(self._DKP_SV))
        if teams is None:
            return False

        for team, dkp_list in teams.items():
            if isinstance(dkp_list, dict): # dict because there may be ["seed"] field...
                dkp_list = dkp_list.values()
            elif not isinstance(dkp_list, list):
                return False

            for entry in dkp_list:
                info = self._generate_player_info(entry)
                if info is None:
                    continue

                self._set_dkp(info.name(), info, team)
                self._set_group_dkp(info.ingame_class(), info, team)

        return True

    # Called 3nd
    def _build_loot_database(self, saved_variable):
        super()._build_loot_database(None)
        teams = self.__get_configured_teams(saved_variable.get(self._LOOT_SV))
        if teams is None:
            return False

        for team, loot_list in teams.items():
            if isinstance(loot_list, dict): # dict because there is ["seed"] field...
                loot_list = loot_list.values()
            elif not isinstance(loot_list, list):
                return False

            for entry in loot_list:
                player_loot = self._generate_player_loot(entry, team)
                if player_loot is None:
                    continue

                self._add_loot(player_loot, team)
                self._add_player_loot(player_loot.player().name(), player_loot, team)

        self._sort_loot()
        self._sort_player_loot()
        self._set_player_latest_loot()

        return True

    # Called 4rd
    def _build_history_database(self, saved_variable):
        super()._build_history_database(None)
        teams = self.__get_configured_teams(saved_variable.get(self._HISTORY_SV))
        if teams is None:
            return False

        for team, history in teams.items():
            if isinstance(history, dict): # dict because there is ["seed"] field...
                history = history.values()
            elif not isinstance(history, list):
                return False

            for entry in history:
                self._generate_player_history(entry, team)

        self._sort_history()
        self._set_player_latest_positive_history_and_activity(self._45_DAYS_SECONDS)

        return True

    def _get_channel_team_mapping(self, channel_id):
        team = self._channel_team_map.get(str(channel_id))
        if team is None:
            return DKPBot.DEFAULT_TEAM

        return team

    def config_call_server_side(self, params, num_params, request_info):
        return DKPBot.config_call_server_side(self, params, num_params, request_info)

    def config_call_guild_name(self, params, num_params, request_info):
        return DKPBot.config_call_guild_name(self, params, num_params, request_info)

    def config_call_team(self, params, num_params, request_info):
        return DKPBot.config_call_team(self, params, num_params, request_info)
