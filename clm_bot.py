from dkp_bot import DKPBot, Response, ResponseStatus
from player_db_models import PlayerInfoCLM, PlayerLoot, PlayerDKPHistory
from essentialdkp_bot import EssentialDKPBot
from bot_logger import trace, trace_func_only, for_all_methods, BotLogger
from display_templates import (
    SupporterOnlyResponse,
    BasicError,
    SinglePlayerProfile
)

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
            'teams' : {},
            'modes' :  { # backwards compatibility with super() class
                'rounding' : 2
                }
        }

        data = self.__get_data(saved_variable.get(self._SV))
        if data is None:
            BotLogger().get().debug("Config not found in file")
            return False

        configs = data.get("config")
        if configs is None:
            BotLogger().get().debug("No configs found")
            return False

        for name, config in configs.items():
            rounding = config.get('rounding')
            if rounding is None:
                rounding = 2
            config_list['teams'][name.lower()] = {'name' : name, 'rounding' : rounding}

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

        teamPlayerCache = {}
        for team, teamData in rosters.items():
            team = team.lower() # to have it common with the keys
            teamPlayerCache[team] = []
            for GUID, playerData in teamData.items():
                # ekhm this generates new each time. optimize one day?
                info = self._generate_player_info(profiles.get(GUID), playerData.get('dkp'))
                if info is None:
                    continue
                teamPlayerCache[team].append(info.name())
                self._set_dkp(info.name(), info, team)
                self._set_group_dkp(info.ingame_class(), info, team)

        # additional pass for alt-main linking as objects might be created in unknown order above
        for team, playerList in teamPlayerCache.items():
            for playerName in playerList:
                info = self._get_dkp(playerName, team)
                if info is None:
                    continue
                self._update_main(team, info, profiles)

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

    def _update_main(self, team, info, profiles):
        main = info.main()

        if type(main) is str: # Not yet parsed profile
            main = profiles.get(main)
            if not type(main) is dict:
                return None

            main = main.get('name')
            if main is None:
                return None

            main = self._get_dkp(main, team)
            info.set_main(main)
            if main is not None:
                main.increment_alts()

        elif type(main) is not PlayerInfoCLM: # already parsed profile has PlayerInfoCLM
            info.set_main(None)

        return None

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
        if main != "": # when creating set main to text, it will be re-parsed to object afterwards
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

    def _update_rounding_per_team_call(self, team):
        rounding = self._get_addon_config(["teams", team, "rounding"])
        if rounding is None:
            rounding = 2
        self._set_builder_info(rounding)

    # Overrides

    def call_dkp(self, param, request_info):
        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        team = self._get_channel_team_mapping(request_info["channel"]["id"])
        self._update_rounding_per_team_call(team)
        return super().call_dkp(param, request_info)

    def call_history(self, param, request_info):
        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        team = self._get_channel_team_mapping(request_info["channel"]["id"])
        self._update_rounding_per_team_call(team)
        return super().call_history(param, request_info)

    def call_loot(self, param, request_info):
        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        team = self._get_channel_team_mapping(request_info["channel"]["id"])
        self._update_rounding_per_team_call(team)
        return super().call_loot(param, request_info)

    def call_raidloot(self, param, request_info):
        if not self.is_premium():
            return Response(ResponseStatus.SUCCESS, SupporterOnlyResponse().get())

        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        team = self._get_channel_team_mapping(request_info["channel"]["id"])
        self._update_rounding_per_team_call(team)
        return super().call_raidloot(param, request_info)

    def call_item(self, param, request_info):
        if not self.is_premium():
            return Response(ResponseStatus.SUCCESS, SupporterOnlyResponse().get())

        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        team = self._get_channel_team_mapping(request_info["channel"]["id"])
        self._update_rounding_per_team_call(team)
        return super().call_item(param, request_info)

    def call_value(self, param, request_info):
        if not self.is_premium():
            return Response(ResponseStatus.SUCCESS, SupporterOnlyResponse().get())

        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        team = self._get_channel_team_mapping(request_info["channel"]["id"])
        self._update_rounding_per_team_call(team)
        return super().call_value(param, request_info)

    def config_call_server_side(self, params, num_params, request_info):
        return DKPBot.config_call_server_side(self, params, num_params, request_info)

    def config_call_guild_name(self, params, num_params, request_info):
        return DKPBot.config_call_guild_name(self, params, num_params, request_info)

    def config_call_team(self, params, num_params, request_info):
        return DKPBot.config_call_team(self, params, num_params, request_info)
