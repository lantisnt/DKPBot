import re
from enum import Enum
from dkp_bot import DKPBot, Response, ResponseStatus
from essentialdkp_bot import EssentialDKPBot
from player_db_models import PlayerInfoEPGP, PlayerEPGPHistory, PlayerLootEPGP
from display_templates import BasicError, BasicCritical, BasicAnnouncement, BasicInfo, BasicSuccess
from display_templates_epgp import SinglePlayerProfile, MultipleResponse, HistoryMultipleResponse, PlayerLootMultipleResponse, LootMultipleResponse

class CEPGPBot(EssentialDKPBot):

    _SV = "CEPGP"
    __BACKUP = "BOT"
    TRAFFIC_HOLDER = u"\u200b" # Non-printed space ^^

    epgp_value_regex = re.compile(".*?([EPG]{2,4})\s*\+?(-?\d+)%?.*?(?:(?: - (.*))|(?:\s*\((.*)\)))?", re.I)

    def _configure(self):
        super()._configure()
        # # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile("CEPGP Profile")

        self._multiple_dkp_output_builder = MultipleResponse("EPGP values", self._get_config().dkp.fields,
        self._get_config().dkp.entries_per_field, self._get_config().dkp.separate_messages,
        self._get_config().dkp.multiple_columns, self._get_config().dkp.enable_icons, self._get_config().dkp.value_suffix)

        self._multiple_history_output_builder = HistoryMultipleResponse("Latest EPGP history", self._get_config().dkp_history.fields,
        self._get_config().dkp_history.entries_per_field, self._get_config().dkp_history.separate_messages,
        self._get_config().dkp_history.multiple_columns, self._get_config().dkp_history.enable_icons, self._get_config().dkp_history.value_suffix)

        self._multiple_player_loot_output_builder = PlayerLootMultipleResponse("Latest loot history", self._get_config().loot_history.fields,
        self._get_config().loot_history.entries_per_field, self._get_config().loot_history.separate_messages,
        self._get_config().loot_history.multiple_columns, self._get_config().loot_history.enable_icons, self._get_config().loot_history.value_suffix)

        self._multiple_loot_output_builder = LootMultipleResponse("Latest 30 items awarded", self._get_config().latest_loot.fields,
        self._get_config().latest_loot.entries_per_field, self._get_config().latest_loot.separate_messages,
        self._get_config().latest_loot.multiple_columns, self._get_config().latest_loot.enable_icons, self._get_config().latest_loot.value_suffix)

        self._multiple_item_search_output_builder = LootMultipleResponse("Search results", self._get_config().item_search.fields,
        self._get_config().item_search.entries_per_field, self._get_config().item_search.separate_messages,
        self._get_config().item_search.multiple_columns, self._get_config().item_search.enable_icons, self._get_config().item_search.value_suffix)

        self._update_views_info()

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

    def __build_history_output_multiple(self, output_result_list, requester):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        if not requester:
            requester = ""

        return self._multiple_history_output_builder.build(output_result_list, requester).get()

    def __build_player_loot_output_multiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self._multiple_player_loot_output_builder.build(output_result_list).get()

    def __build_loot_output_multiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self._multiple_loot_output_builder.build(output_result_list).get()

    def __build_item_search_output_multiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self._multiple_item_search_output_builder.build(output_result_list).get()

    ### Database - Variables parsing ###

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

    def _parse_traffic_entry(self, target, source, desc, EPB, EPA, GPB, GPA, item_link, timestamp, id, unit_guid):
        # Check for target
        if not target or target is None or len(target) < 2 or target == "":
            # Raid target is treated same as "" as we can't know who was in raid.
            # For Guild target we assume Guild = everyone
            has_target = False
        else:
            has_target = not (target.lower() == 'raid')

        is_target_guild = target.lower() == 'guild'
        is_target_raid = target.lower() == 'raid'

        # Check for item id and name to see if we have Loot Entry
        print(item_link)
        item_info = self._get_item_id_name(item_link)
        print(item_info)
        if item_info and isinstance(item_info, list) and len(item_info) == 1:
            if item_info[0] and isinstance(item_info[0], tuple) and len(item_info[0]) == 2:
                # We have found 1 item entry in ItemLink
                item_id = item_info[0][0]
                item_name = item_info[0][1]
                gp_cost = 0
                try:
                    gp_cost = float(GPA) - float(GPB)
                except ValueError:
                    pass
                if has_target:
                    player = self._get_dkp(target, self.DEFAULT_TEAM)
                    if player is not None:
                        player_loot = PlayerLootEPGP(player, item_id, item_name, gp_cost, timestamp)
                        self._add_loot(player_loot, self.DEFAULT_TEAM)
                        self._add_player_loot(player_loot.player().name(), player_loot, self.DEFAULT_TEAM)
                else:
                    player = self._get_dkp(self.TRAFFIC_HOLDER, self.DEFAULT_TEAM)
                    player_loot = PlayerLootEPGP(player, item_id, item_name, 0, timestamp)
                    self._add_loot(player_loot, self.DEFAULT_TEAM)
                    # We dont add this to TRAFFIC_HOLDER because it will never be accessed
                return

        # Check for EP/GP value entry
        found = self.epgp_value_regex.findall(desc)
        if found and isinstance(found, list) and len(found) == 1 and len(found[0]) == 4:
            reason = found[0][2] if len(found[0][2]) > 0 else found[0][3]

            value = 0
            try:
                value = float(found[0][1])
            except ValueError:
                pass
            
            is_percentage = (desc.find("%") >= 0)

            value_type = found[0][0].lower()
            if value_type == 'ep':
                ep = value
                gp = 0
            elif value_type == 'gp':
                ep = 0
                gp = value
            elif value_type == 'epgp':
                ep = value
                gp = value
    
            if is_target_guild:
                # Target is guild then we attach it to every player
                history = PlayerEPGPHistory(self.TRAFFIC_HOLDER, ep, gp, is_percentage, timestamp, reason, source)
                self._add_history_to_all_players(history, self.DEFAULT_TEAM)
            elif has_target:
                player = self._get_dkp(target, self.DEFAULT_TEAM)
                history = PlayerEPGPHistory(target, ep, gp, is_percentage, timestamp, reason, source)
                self._add_history(target, history, self.DEFAULT_TEAM)

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
            epgp_list = backups_list[list(backups_list.keys())[0]]

        if len(epgp_list) == 0:
            return False

        for player, data in epgp_list.items():
            info = self._generate_player_info(player, data)
            if isinstance(info, PlayerInfoEPGP):
                self._set_dkp(info.name(), info, self.DEFAULT_TEAM)

        # Fake DKP entry to hold Raid / Guild (group) traffic
        info = PlayerInfoEPGP(self.TRAFFIC_HOLDER, 0, 0)
        info.set_inactive()
        self._set_dkp(info.name(), info, self.DEFAULT_TEAM)

        return True

    # Called 3rd
    def _build_loot_database(self, saved_variable):
        if saved_variable is None:
            return False

        addon_data = saved_variable.get(self._SV)
        if addon_data is None or not addon_data or not isinstance(addon_data, dict):
            return False

        traffic_list = addon_data.get("Traffic")
        if traffic_list is None or not traffic_list or not isinstance(traffic_list, list):
            return False
        
        for traffic in traffic_list:
            self._parse_traffic_entry(*traffic)

        self._sort_loot()
        self._sort_player_loot()
        self._set_player_latest_loot()
        self._sort_history()
        self._set_player_latest_positive_history_and_activity(self._45_DAYS_SECONDS)

        return True

    # Called 4th
    def _build_history_database(self, saved_variable):
        return True # This is being handled within loot database as all is based on traffic

    def _update_views_info(self):
        # ## Database
        self._single_player_profile_builder.set_database_info(
            self._db_get_info())
        self._multiple_dkp_output_builder.set_database_info(
            self._db_get_info())
        self._multiple_history_output_builder.set_database_info(
            self._db_get_info())
        self._multiple_player_loot_output_builder.set_database_info(
            self._db_get_info())
        self._multiple_loot_output_builder.set_database_info(
            self._db_get_info())
        self._multiple_item_search_output_builder.set_database_info(
            self._db_get_info())
        
    def call_dkp(self, param, request_info):
        return Response(ResponseStatus.IGNORE)

    ### CEPGP commands ###
    def call_epgp(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_database_loaded():
            return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

        targets, aliases, original, int_list = self._parse_player_param(param)

        output_result_list = []
        if 'all' in original:
            output_result_list = self._get_team_dkp(self.DEFAULT_TEAM)
        else:
            for target in targets:
                # Single player
                info = self._get_dkp(target, self.DEFAULT_TEAM)
                if isinstance(info, PlayerInfoEPGP):
                    output_result_list.append(info)

        if len(output_result_list) == 1:
            data = self.__build_epgp_output_single(output_result_list[0])
        elif len(output_result_list) > 0:
            output_result_list.sort(key=lambda info: info.dkp(), reverse=True)
            data = self.__build_epgp_output_multiple(output_result_list, request_info['author']['name'])
        else:
            data = BasicError("{0}'s DKP was not found in database.".format(
                param.capitalize())).get()

        return Response(ResponseStatus.SUCCESS, data)

    def call_epgphistory(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_database_loaded():
            return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

        targets, aliases, original, int_list = self._parse_player_param(param)
        output_result_list = []

        for target in targets:
            # Single player
            info = self._get_history(target, self.DEFAULT_TEAM)
            if info and isinstance(info, list):
                output_result_list = info
                break  # Yes single only
            else:
                return Response(ResponseStatus.ERROR, "Unable to find data for {0}.".format(param))

        if len(output_result_list) > 0:
            data = self.__build_history_output_multiple(output_result_list, request_info['author']['name'])
        else:
            data = BasicError("{0}'s EPGP history was not found in database.".format(
                param.capitalize())).get()

        return Response(ResponseStatus.SUCCESS, data)