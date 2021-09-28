from dkp_bot import DKPBot
from player_db_models import PlayerInfoCLM, PlayerLoot, PlayerDKPHistory
from essentialdkp_bot import EssentialDKPBot
from display_templates import SinglePlayerProfile
from bot_logger import trace, trace_func_only, for_all_methods, BotLogger


@for_all_methods(trace, trace_func_only)
class CLMBot(EssentialDKPBot):

    _SV = "CLM_DB"

    def _configure(self):
        super()._configure()
        # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile(
            "Classic Loot Manager Profile", self._timezone, self._version
        )

    def _get_addon_thumbnail(self):
        return "https://cdn.discordapp.com/attachments/843129642298376252/892049790731436082/CLM-dark-v4.png"

    def __get_data(self, data_dict):
        server_side = self._get_config().guild_info.server_side
        guild_name = self._get_config().guild_info.guild_name

        if not (server_side and guild_name):
            BotLogger().get().debug(
                "server_side [%s] guild_name [%s]", server_side, guild_name
            )
            return None

        # Decode server-side first
        if not data_dict:
            BotLogger().get().debug("Missing data_dict")
            return None

        if not isinstance(data_dict, dict):
            BotLogger().get().debug("Data_dict is not a Dict")
            return None

        tmp = server_side.split("-")
        clm_side_server_guild = tmp[1] + " " + tmp[0] + " " + guild_name
        side_server_guild_key = None
        for side_server_guild in data_dict.keys():
            if side_server_guild.lower() == clm_side_server_guild:
                side_server_guild_key = side_server_guild
                break

        if side_server_guild_key is None:
            BotLogger().get().debug("Server-Side or Guild not found in file")
            return None

        tmp_data = data_dict.get(side_server_guild_key)
        if tmp_data is None:
            BotLogger().get().debug("Actual data not found in file")
            return None

        integration = tmp_data.get("integration")
        if integration is None:
            BotLogger().get().debug("Integration not found in file")
            return None

        data = integration.get("wowdkpbot")
        if data is None:
            BotLogger().get().debug("Data not found in file")
            return None

        return data

    # Called 1st
    def _build_config_database(self, saved_variable):  # pylint: disable=unused-argument
        super()._build_config_database(None)
        config_list = {
            'modes' : {
                'rounding' : 2 # Fill with actual data
            },
            'teams' : {}
        }

        data = self.__get_data(saved_variable.get(self._SV))
        if data is None:
            BotLogger().get().debug("Config not found in file")
            return False

        rosters = data.get("rosters")
        if rosters is None:
            BotLogger().get().debug("No rosters found")
            return False

        for name in rosters.keys():
            config_list['teams'][name.lower()] = {'name' : name}

        self._set_addon_config(config_list)

        return True

    # Called 2nd -> Fully parse information
    def _build_dkp_database(self, saved_variable):
        super()._build_dkp_database(None)
        data = self.__get_data(saved_variable.get(self._SV))
        if data is None:
            return False

        profiles = data.get("profiles")
        if profiles is None:
            BotLogger().get().debug("No profiles found")
            return False

        rosters = data.get("rosters")
        if rosters is None:
            BotLogger().get().debug("No rosters found")
            return False

        for team, teamData in rosters.items():
            team = team.lower() # to have it common with the keys
            for GUID, playerData in teamData.items():
                info = self._generate_player_info(profiles.get(GUID), playerData.get('dkp'))
                if info is None:
                    continue

                self._set_dkp(info.name(), info, team)
                self._set_group_dkp(info.ingame_class(), info, team)

        return True

    # Called 3nd
    def _build_loot_database(self, saved_variable):
        super()._build_loot_database(None)
        data = self.__get_data(saved_variable.get(self._SV))
        if data is None:
            return False

        profiles = data.get("profiles")
        if profiles is None:
            BotLogger().get().debug("No profiles found")
            return False

        rosters = data.get("rosters")
        if rosters is None:
            BotLogger().get().debug("No rosters found")
            return False

        for team, teamData in rosters.items():
            team = team.lower() # to have it common with the keys
            for GUID, playerData in teamData.items():
                for entry in playerData.get('loot'):
                    player_loot = self._generate_player_loot(entry, team, profiles.get(GUID))
                    if player_loot is None:
                        continue
    
                    self._add_loot(player_loot, team)
                    self._add_player_loot(player_loot.player().name(), player_loot, team)

        self._sort_loot()
        self._sort_player_loot()
        self._set_player_latest_loot()
        self.dump_database()
        return True

    # Called 4rd
    def _build_history_database(self, saved_variable):
        super()._build_history_database(None)
        data = self.__get_data(saved_variable.get(self._SV))
        if data is None:
            return False

        profiles = data.get("profiles")
        if profiles is None:
            BotLogger().get().debug("No profiles found")
            return False

        rosters = data.get("rosters")
        if rosters is None:
            BotLogger().get().debug("No rosters found")
            return False

        for team, teamData in rosters.items():
            team = team.lower() # to have it common with the keys
            for GUID, playerData in teamData.items():
                for entry in playerData.get('history'):
                    history = self._generate_player_history(entry, team, profiles.get(GUID), profiles)
                    if history is None:
                        continue
                    self._add_history(history.player().name(), history, team)

        self._sort_history()
        self._set_player_latest_positive_history_and_activity(self._45_DAYS_SECONDS)

        return True

    def _get_channel_team_mapping(self, channel_id):
        team = self._channel_team_map.get(str(channel_id))
        if team is None:
            return DKPBot.DEFAULT_TEAM

        return team

    def _generate_player_info(self, entry, dkp):
        if entry is None:
            BotLogger().get().debug("Player entry is None")
            return None

        player = entry.get("name")
        if player is None:
            return None

        ingame_class = entry.get("class")
        if ingame_class is None:
            return None

        main = entry.get("main")
        if main is None:
            return None

        spec = entry.get("spec")
        if spec is None:
            return None

        info = PlayerInfoCLM(player, dkp, ingame_class, spec)
        if main != "":
            info.set_main(main)

        return info

    def _generate_player_loot(self, entry, team, player):
        if not isinstance(entry, dict):
            return None

        if not isinstance(player, dict):
            return None 

        player = self._get_dkp(player.get("name"), team)
        if player is None:
            return None

        value = entry.get("value")
        if value is None:
            return None

        item_id = entry.get("id")
        if item_id is None:
            return None

        item_name = entry.get("name")
        if item_name is None:
            return None

        time = entry.get("time")
        if time is None:
            return None

        return PlayerLoot(player, item_id, item_name, value, time)

    def _generate_player_history(self, entry, team, player, profiles):
        if not isinstance(entry, dict):
            return None

        if not isinstance(player, dict):
            return None 

        player = self._get_dkp(player.get("name"), team)
        if player is None:
            return None

        creator = entry.get("creator")
        if creator is None:
            return None

        creator = profiles.get(creator)
        if creator is None:
            creator = "Unknown"
        else:
            creator = creator.get("name")
            if creator is None:
                creator = "Unknown"

        value = entry.get("value")
        if value is None:
            return None

        reason = entry.get("reason")
        if reason is None:
            return None

        percentage = False
        if reason == 101:
            percentage = True
            value = -float(value)

        reason = self.__decode_reason(reason)

        time = entry.get("time")
        if time is None:
            return None

        return PlayerDKPHistory(player, value, time, reason, creator, percentage)

    def __decode_reason(self, reason):
        data = {
            1: "On Time Bonus",
            2: "Boss Kill Bonus",
            3: "Raid Completion Bonus",
            4: "Progression Bonus",
            5: "Standby Bonus",
            6: "Unexcused absence",
            7: "Correcting error",
            8: "Manual adjustment",
            100: "Import",
            101: "Decay",
            102: "Interval Bonus"
        }
        decoded = data.get(reason)
        if decoded is None:
            decoded = "Unknown"
        return decoded

    def config_call_server_side(self, params, num_params, request_info):
        return DKPBot.config_call_server_side(self, params, num_params, request_info)

    def config_call_guild_name(self, params, num_params, request_info):
        return DKPBot.config_call_guild_name(self, params, num_params, request_info)

    def config_call_team(self, params, num_params, request_info):
        return DKPBot.config_call_team(self, params, num_params, request_info)
