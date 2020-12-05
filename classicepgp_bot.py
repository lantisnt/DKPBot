from dkp_bot import DKPBot, Response, ResponseStatus
from essentialdkp_bot import EssentialDKPBot
from player_db_models import PlayerInfoEPGP
from display_templates_epgp import SinglePlayerProfile, EPGPMultipleResponse

class CEPGPBot(EssentialDKPBot):

    _SV = "CEPGP"
    __BACKUP = "bot"

    def _configure(self):
        super()._configure()
        # # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile("CEPGP Profile")

        self._multiple_dkp_output_builder = EPGPMultipleResponse("EPGP values", self._get_config().dkp.fields,
        self._get_config().dkp.entries_per_field, self._get_config().dkp.separate_messages,
        self._get_config().dkp.multiple_columns, self._get_config().dkp.enable_icons, self._get_config().dkp.value_suffix)

        # self._multiple_history_output_builder = HistoryMultipleResponse("Latest DKP history", self._get_config().dkp_history.fields,
        # self._get_config().dkp_history.entries_per_field, self._get_config().dkp_history.separate_messages,
        # self._get_config().dkp_history.multiple_columns, self._get_config().dkp_history.enable_icons, self._get_config().dkp_history.value_suffix)

        # self._multiple_player_loot_output_builder = PlayerLootMultipleResponse("Latest loot history", self._get_config().loot_history.fields,
        # self._get_config().loot_history.entries_per_field, self._get_config().loot_history.separate_messages,
        # self._get_config().loot_history.multiple_columns, self._get_config().loot_history.enable_icons, self._get_config().loot_history.value_suffix)

        # self._multiple_loot_output_builder = LootMultipleResponse("Latest 30 items awarded", self._get_config().latest_loot.fields,
        # self._get_config().latest_loot.entries_per_field, self._get_config().latest_loot.separate_messages,
        # self._get_config().latest_loot.multiple_columns, self._get_config().latest_loot.enable_icons, self._get_config().latest_loot.value_suffix)

        # self._multiple_item_search_output_builder = LootMultipleResponse("Search results", self._get_config().item_search.fields,
        # self._get_config().item_search.entries_per_field, self._get_config().item_search.separate_messages,
        # self._get_config().item_search.multiple_columns, self._get_config().item_search.enable_icons, self._get_config().item_search.value_suffix)

        # self._update_views_info()

    ### Display ###

    def __build_epgp_output_single(self, info):
        if not info or not isinstance(info, PlayerInfoEPGP):
            return None

        return self._single_player_profile_builder.build(info, None).get()

    def __build_epgp_output_multiple(self, output_result_list, requester):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        if not requester:
            requester = ""

        return self._multiple_dkp_output_builder.build(output_result_list, requester).get()

    ### Database - Variables parsing ###

    def _fill_history(self, players, dkp, timestamp, reason, index, team):
        pass

    def _generate_player_info(self, player, data):
        if not player or not data:
            return None

        player = player.split("-")[0]
        if len(player) == 0:
            return None

        ep = 0
        gp = 0
        if len(data) > 0:
            tmp = data.split(",")
            if len(tmp) == 2:
                ep = float(tmp[0])
                gp = float(tmp[1])
        return PlayerInfoEPGP(player, ep, gp)

    def _generate_player_loot(self, entry, team):
        pass
        #return PlayerLoot(player, item_info[0][0], item_info[0][1], cost, date)

    def _generate_player_history(self, entry, team):
        pass

    # Called 1st
    def _build_config_database(self, saved_variable):  # pylint: disable=unused-argument
        self._set_addon_config({})
        return True

    # Called 2nd
    def _build_dkp_database(self, saved_variable):
        if saved_variable is None:
            return False

        addon_data = saved_variable.get(self._SV)
        if addon_data is None or not addon_data or not isinstance(addon_data, dict):
            return False

        backups_list = addon_data.get("Backups")
        if backups_list is None or not backups_list or not isinstance(backups_list, dict):
            return False

        epgp_list = []
        if self.__BACKUP in backups_list.keys():
            epgp_list = backups_list[self.__BACKUP]
        else:
            epgp_list = backups_list[list(backups_list.keys())[-1]]

        if len(epgp_list) == 0:
            return False
        print(epgp_list)
        for player, data in epgp_list.items():
            info = self._generate_player_info(player, data)
            if isinstance(info, PlayerInfoEPGP):
                print(info)
                self._set_dkp(info.name(), info, self.DEFAULT_TEAM)
        
        return True

    # Called 3rd
    def _build_loot_database(self, saved_variable):
        return True

    # Called 4th
    def _build_history_database(self, saved_variable):
        return True

    def _update_views_info(self):
        # ## Database
        print(self._db_get_info())
        self._single_player_profile_builder.set_database_info(
            self._db_get_info())
        self._multiple_dkp_output_builder.set_database_info(
            self._db_get_info())
        # self._multiple_history_output_builder.set_database_info(
        #     self._db_get_info())
        # self._multiple_player_loot_output_builder.set_database_info(
        #     self._db_get_info())
        # self._multiple_loot_output_builder.set_database_info(
        #     self._db_get_info())
        # self._multiple_item_search_output_builder.set_database_info(
        #     self._db_get_info())
        # ## Global
        # rounding = self._get_addon_config(["modes", "rounding"])
        # self._single_player_profile_builder.set_info(rounding)
        # self._multiple_dkp_output_builder.set_info(rounding)
        # self._multiple_history_output_builder.set_info(rounding)
        # self._multiple_player_loot_output_builder.set_info(rounding)
        # self._multiple_loot_output_builder.set_info(rounding)
        # self._multiple_item_search_output_builder.set_info(rounding)
        
    def call_dkp(self, param, request_info):
        return Response(ResponseStatus.IGNORE)

    def call_dkphistory(self, param, request_info):  # pylint: disable=unused-argument
        return Response(ResponseStatus.IGNORE)

    def call_loot(self, param, request_info):  # pylint: disable=unused-argument
        return Response(ResponseStatus.IGNORE)
        # if not self.is_database_loaded():
        #     return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

        # targets, aliases, original = self._parse_player_param(param)
        # output_result_list = []

        # if len(targets) > 0:
        #     team = self._get_channel_team_mapping(request_info['channel']['id'])
        #     for target in targets:
        #         # Single player
        #         info = self._get_player_loot(target, team)
        #         if info and isinstance(info, list):
        #             output_result_list = info
        #             break  # Yes single only
        # else:
        #     return Response(ResponseStatus.ERROR, "Unable to find data for {0}.".format(param))

        # if len(output_result_list) > 0:
        #     data = self.__build_player_loot_output_multiple(output_result_list)
        # else:
        #     data = BasicError("{0}'s DKP loot was not found in database.".format(
        #         param.capitalize())).get()

        # return Response(ResponseStatus.SUCCESS, data)

    def call_raidloot(self, param, request_info):  # pylint: disable=unused-argument
        return Response(ResponseStatus.IGNORE)
    #     if not self.is_premium():
    #         return Response(ResponseStatus.SUCCESS,BasicInfo("```css\nSupporter only command```\n Want your server to get access to the commands and support bot development? Check the instructions on discord - link below.").get())

    #     if not self.is_database_loaded():
    #         return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

    #     output_result_list = self._get_loot(self._get_channel_team_mapping(request_info['channel']['id']))

    #     if len(output_result_list) > 0:
    #         data = self.__build_loot_output_multiple(output_result_list)
    #     else:
    #         data = BasicError("Unable to find data loot data.").get()

    #     return Response(ResponseStatus.SUCCESS, data)

    # def call_item(self, param, request_info):  # pylint: disable=unused-argument
    #     if not self.is_premium():
    #         return Response(ResponseStatus.SUCCESS, BasicInfo("```css\nSupporter only command```\n Want your server to get access to the commands and support bot development? Check the instructions on discord - link below.").get())

    #     if not self.is_database_loaded():
    #         return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

    #     if len(param) < 3:
    #         return Response(ResponseStatus.SUCCESS, BasicError("Query too short. Please specify at least 3 letters.").get())

    #     output_result_list = self._find_loot(param, self._get_channel_team_mapping(request_info['channel']['id']))

    #     if len(output_result_list) > 0:
    #         data = self.__build_item_search_output_multiple(output_result_list)
    #     else:
    #         data = BasicError("No loot matching `{0}` found.".format(param)).get()

    #     return Response(ResponseStatus.SUCCESS, data)

    def config_call_server_side(self, params, num_params, request_info):
        return Response(ResponseStatus.SUCCESS, BasicInfo("Server and Side setting are not used in `cepgp` mode.").get())

    def config_call_guild_name(self, params, num_params, request_info):
        return Response(ResponseStatus.SUCCESS, BasicInfo("Guild Name setting is not used in `cepgp` mode.").get())

    def config_call_team(self, params, num_params, request_info):
        return Response(ResponseStatus.SUCCESS, BasicInfo("Multiple teams are not used in `cepgp` mode.").get())

    ### CEPGP commands ###
    def call_epgp(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_database_loaded():
            return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

        targets, aliases, original = self._parse_player_param(param)

        output_result_list = []
        if 'all' in original:
            output_result_list = self._get_team_dkp(self.DEFAULT_TEAM)
        else:
            for target in targets:
                # Single player
                print(target)
                info = self._get_dkp(target, self.DEFAULT_TEAM)
                print(info)
                if isinstance(info, PlayerInfoEPGP):
                    output_result_list.append(info)

        if len(output_result_list) == 1:
            data = self.__build_epgp_output_single(output_result_list[0])
            print("single data")
            print(data)
        elif len(output_result_list) > 0:
            output_result_list.sort(key=lambda info: info.dkp(), reverse=True)
            data = self.__build_epgp_output_multiple(output_result_list, request_info['author']['name'])
        else:
            data = BasicError("{0}'s DKP was not found in database.".format(
                param.capitalize())).get()

        return Response(ResponseStatus.SUCCESS, data)