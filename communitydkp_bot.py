from essentialdkp_bot import EssentialDKPBot
from display_templates import SinglePlayerProfile

class CommunityDKPBot(EssentialDKPBot):

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
        print("server_side: {0} | guild_name: {1}".format(server_side, guild_name))
        if not (server_side and guild_name):
            return None

        # Decode server-side first
        if not server_list:
            return None
        print("server_list len: {0} type: {1}".format(len(server_list), type(server_list)))
        if not isinstance(server_list, dict):
            return None

        server_side_key = None
        for server_side_lua in server_list.keys():
            print("keys server_side: {0}".format(server_side_lua.lower()))
            if server_side_lua.lower() == server_side:
                server_side_key = server_side_lua

                break

        if server_side_key is None:
            return None
        print(server_side_key)
        # Decode guilds
        guilds = server_list.get(server_side_key)
        if not guilds:
            return None
        print(guilds.keys())
        guild_name_key = None
        for guild_name_key in guilds.keys():
            print("keys guild_name: {0}".format(guild_name_key.lower()))
            if guild_name_key.lower() == guild_name:
                guild_name_key = guild_name
                break

        if guild_name_key is None:
            return None
        print(guild_name_key)
        teams = guilds.get(guild_name_key)
        print(teams)
        if not teams:
            return None
        print(teams)
        return teams

    # Called 1st
    def _build_dkp_database(self, saved_variable):
        super()._build_dkp_database(None)
        print("{0}".format(self._DKP_SV))
        print(saved_variable.keys())
        teams = self.__get_configured_teams(saved_variable.get(self._DKP_SV))
        if teams is None:
            return

        for team, dkp_list in teams.items():
            print("{0} : len() {1}".format(team, len(dkp_list)))
            for entry in dkp_list:
                info = self._generate_player_info(entry)
                if info is None:
                    continue

                self._set_dkp(info.name(), info, team)
                self._set_group_dkp(info.ingame_class(), info, team)

    # Called 2nd
    def _build_loot_database(self, saved_variable):
        super()._build_loot_database(None)
        print("{0}".format(self._LOOT_SV))
        print(saved_variable.keys())
        teams = self.__get_configured_teams(saved_variable.get(self._LOOT_SV))
        if teams is None:
            return

        for team, loot_list in teams.items():
            print("{0} : len() {1}".format(team, len(loot_list)))
            for entry in loot_list.values():
                player_loot = self._generate_player_loot(entry, team)
                if player_loot is None:
                    continue

                self._add_loot(player_loot, team)
                self._add_player_loot(player_loot().player().name(), player_loot, team)

        self._sort_loot()
        self._sort_player_loot()
        self._set_player_latest_loot()

    # Called 3rd
    def _build_history_database(self, saved_variable):
        super()._build_history_database(None)
        print("{0}".format(self._HISTORY_SV))
        print(saved_variable.keys())
        teams = self.__get_configured_teams(saved_variable.get(self._HISTORY_SV))
        if teams is None:
            return

        for team, history in teams.items():
            print("{0} : len() {1}".format(team, len(history)))
            for entry in history.values():
                self._generate_player_history(entry, team)

        self._sort_history()
        self._set_player_latest_positive_history_and_activity(self._45_DAYS_SECONDS)
