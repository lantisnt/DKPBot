import re

from dkp_bot import DKPBot, Response, ResponseStatus
from player_db_models import PlayerInfo, PlayerDKPHistory, PlayerLoot
from display_templates import BasicError, SinglePlayerProfile, DKPMultipleResponse, HistoryMultipleResponse, PlayerLootMultipleResponse, LootMultipleResponse
from bot_logger import BotLogger

class EssentialDKPBot(DKPBot):

    _DKP_SV = "MonDKP_DKPTable"
    _LOOT_SV = "MonDKP_Loot"
    _HISTORY_SV = "MonDKP_DKPHistory"
    _45_DAYS_SECONDS = 3888000

    __item_id_name_find = None

    __singleDkpOutputBuilder = None
    _multiple_dkp_output_builder = None
    _multiple_history_output_builder = None
    _multiple_player_loot_output_builder = None
    _multiple_loot_output_builder = None

    def __init__(self, guild_id, config):
        super().__init__(guild_id, config)
        # Matches either a,b,c,d or A / B or A \ B
        self.__item_id_name_find = re.compile("^[^:]*:*(\d*).*\[([^\]]*)")  # pylint: disable=anomalous-backslash-in-string
        self._configure()
    ###

    def _configure(self):
        super()._configure()
        # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile("Essential DKP Profile")

        self._multiple_dkp_output_builder = DKPMultipleResponse("DKP values", self._get_config().dkp.fields, self._get_config(
        ).dkp.entries_per_field, self._get_config().dkp.separate_messages, self._get_config().dkp.multiple_columns)

        self._multiple_history_output_builder = HistoryMultipleResponse("Latest DKP history", self._get_config().dkp_history.fields, self._get_config(
        ).dkp_history.entries_per_field, self._get_config().dkp_history.separate_messages, self._get_config().dkp_history.multiple_columns)

        self._multiple_player_loot_output_builder = PlayerLootMultipleResponse("Latest loot history", self._get_config().loot_history.fields,
        self._get_config().loot_history.entries_per_field, self._get_config().loot_history.separate_messages,
        self._get_config().loot_history.multiple_columns)

        self._multiple_loot_output_builder = LootMultipleResponse("Latest 30 items awarded", self._get_config().latest_loot.fields, self._get_config(
        ).latest_loot.entries_per_field, self._get_config().latest_loot.separate_messages, self._get_config().latest_loot.multiple_columns)

        self._multiple_item_search_output_builder = LootMultipleResponse("Search results", self._get_config().item_search.fields, self._get_config(
        ).item_search.entries_per_field, self._get_config().item_search.separate_messages, self._get_config().item_search.multiple_columns)

        self._update_views_db_info()

    def __build_dkp_output_single(self, info):
        if not info or not isinstance(info, PlayerInfo):
            return None

        return self._single_player_profile_builder.build(info, info.ingame_class()).get()

    def __build_dkp_output_multiple(self, output_result_list, requester):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        if not requester:
            requester = ""

        return self._multiple_dkp_output_builder.build(output_result_list, requester).get()

    def __build_history_output_multiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self._multiple_history_output_builder.build(output_result_list).get()

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

    def _fill_history(self, players, dkp, timestamp, reason, index, team):
        if not players:
            return

        if not dkp:
            return

        if isinstance(players, str) and isinstance(dkp, (int, float)):
            player_info = self._get_dkp(players, team)
            if player_info is None:
                return
            self._add_history(players, PlayerDKPHistory(
                player_info, dkp, timestamp, reason, index), team)
        elif isinstance(players, list) and isinstance(dkp, (int, float)):
            for player in players:
                player_info = self._get_dkp(player, team)
                if player_info is None:
                    return
                self._add_history(player, PlayerDKPHistory(
                    player_info, dkp, timestamp, reason, index), team)
        elif isinstance(players, list) and isinstance(dkp, list):
            # Remove the % entry
            del players[-1]
            del dkp[-1]
            # In case of unequal length we only add as many entries as there are players
            for player in players:
                player_info = self._get_dkp(player, team)
                if player_info is None:
                    dkp.pop(0)
                    continue
                self._add_history(player, PlayerDKPHistory(
                    player_info, float(dkp.pop(0)), timestamp, reason, index), team)

    def _generate_player_info(self, entry):
        if entry is None:
            return None

        player = entry.get("player")
        if player is None:
            return None

        dkp = entry.get("dkp")
        if dkp is None:
            return None

        lifetime_gained = entry.get("lifetime_gained")
        if lifetime_gained is None:
            return None

        lifetime_spent = entry.get("lifetime_spent")
        if lifetime_spent is None:
            return None

        ingame_class = entry.get("class")
        if ingame_class is None:
            return None

        role = entry.get("role")
        if role is None:
            return None

        return PlayerInfo(player, dkp, lifetime_gained,
                          lifetime_spent, ingame_class, role)

    def _generate_player_loot(self, entry, team):
        if entry is None:
            return None

        if not isinstance(entry, dict):
            return None

        player = entry.get("player")
        if player is None:
            return None

        player = self._get_dkp(player, team)
        if player is None:
            return None

        cost = entry.get("cost")
        if cost is None:
            return None

        loot = entry.get("loot")
        if loot is None:
            return None

        date = entry.get("date")
        if date is None:
            return None

        ## Skip deletetion and deleted entries ##
        if entry.get("deletes") or entry.get("deletedby"):
            return None

        if not isinstance(loot, str):
            return None

        item_info = list(filter(None, self.__item_id_name_find.findall(loot)))  # [0] -> id [1] -> name

        if not item_info or not isinstance(item_info, list) or len(item_info) != 1:
            BotLogger().get().warning("ERROR in entry: " + str(player.player()) + " " + str(date) + " " + str(cost) + " " + str(loot))
            return None

        if not item_info[0] or not isinstance(item_info[0], tuple) or len(item_info[0]) != 2:
            BotLogger().get().warning("ERROR in item_info[0] " + str(item_info[0]))
            return None

        return PlayerLoot(player, item_info[0][0], item_info[0][1], cost, date)

    def _generate_player_history(self, entry, team):
        if entry is None:
            return None

        if not isinstance(entry, dict):
            return None

        players = entry.get("players")
        if players is None:
            return None

        dkp = entry.get("dkp")
        if dkp is None:
            return None

        date = entry.get("date")
        if date is None:
            return None

        reason = entry.get("reason")
        if reason is None:
            return None

        index = entry.get("index")
        if index is None:
            return None

        ## Skip deletetion and deleted entries ##
        if entry.get("deletes") or entry.get("deletedby"):
            return None

        if not isinstance(players, str):
            return None
        if not isinstance(date, int):
            return None
        if not isinstance(reason, str):
            return None

        players = list(map(lambda p: p.lower(), players.split(",")))
        if not isinstance(players, list):
            return None

        if isinstance(dkp, str):
            # multiple entries
            dkp = list(map(lambda d: d, dkp.split(",")))
            if len(dkp) == 1:  # Some weird old MonolithDKP -X% only entry that I have no idea how to parse
                return None
        elif not isinstance(dkp, (int, float)):
            return None

        self._fill_history(players, dkp, date, reason, index, team)

    # Called 1st
    def _build_dkp_database(self, saved_variable):
        super()._build_dkp_database(None)

        if saved_variable is None:
            return False

        team = DKPBot.DEFAULT_TEAM

        dkp_list = saved_variable.get(self._DKP_SV)
        if not dkp_list:
            return False

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

    # Called 2nd
    def _build_loot_database(self, saved_variable):
        super()._build_loot_database(None)

        if saved_variable is None:
            return False

        team = DKPBot.DEFAULT_TEAM

        loot_list = saved_variable.get(self._LOOT_SV)

        if not loot_list:
            return False

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

    # Called 3rd
    def _build_history_database(self, saved_variable):
        super()._build_history_database(None)

        if saved_variable is None:
            return False

        team = DKPBot.DEFAULT_TEAM

        history = saved_variable.get(self._HISTORY_SV)

        if not history:
            return False

        if isinstance(history, dict): # dict because there is ["seed"] field...
            history = history.values()
        elif not isinstance(history, list):
            return False

        for entry in history:
            self._generate_player_history(entry, team)

        self._sort_history()
        self._set_player_latest_positive_history_and_activity(self._45_DAYS_SECONDS)

        return True

    # Called after whole database is built

    def _finalize_database(self):
        self._update_views_db_info()

    def _update_views_db_info(self):
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

    ### Commands ###

    def call_dkp(self, param, request_info):
        if not self.is_database_loaded():
            return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())
        targets = self._parse_param(param)
        output_result_list = []
        if len(targets) > 0:
            team = self._get_channel_team_mapping(request_info['channel']['id'])
            for target in targets:
                # Single player
                info = self._get_dkp(target, team)
                if isinstance(info, PlayerInfo):
                    output_result_list.append(info)
                else:
                    # Group request
                    group_info = self._get_group_dkp(target, team)
                    if group_info and len(group_info) > 0:
                        for info in group_info:
                            if info and isinstance(info, PlayerInfo):
                                output_result_list.append(info)
        else:
            return Response(ResponseStatus.ERROR, BasicError("Unable to find data for {0}.".format(param)).get())

        if len(output_result_list) == 1:
            data = self.__build_dkp_output_single(output_result_list[0])
        elif len(output_result_list) > 0:
            output_result_list.sort(key=lambda info: info.dkp(), reverse=True)
            data = self.__build_dkp_output_multiple(output_result_list, request_info['author']['name'])
        else:
            data = BasicError("{0}'s DKP was not found in database.".format(
                param.capitalize())).get()

        return Response(ResponseStatus.SUCCESS, data)

    def call_dkphistory(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_database_loaded():
            return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

        targets = self._parse_param(param)
        output_result_list = []

        if len(targets) > 0:
            team = self._get_channel_team_mapping(request_info['channel']['id'])
            for target in targets:
                # Single player
                info = self._get_history(target, team)
                if info and isinstance(info, list):
                    output_result_list = info
                    break  # Yes single only
        else:
            return Response(ResponseStatus.ERROR, "Unable to find data for {0}.".format(param))

        if len(output_result_list) > 0:
            data = self.__build_history_output_multiple(output_result_list)
        else:
            data = BasicError("{0}'s DKP history was not found in database.".format(
                param.capitalize())).get()

        return Response(ResponseStatus.SUCCESS, data)

    def call_loot(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_database_loaded():
            return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

        targets = self._parse_param(param)
        output_result_list = []

        if len(targets) > 0:
            team = self._get_channel_team_mapping(request_info['channel']['id'])
            for target in targets:
                # Single player
                info = self._get_player_loot(target, team)
                if info and isinstance(info, list):
                    output_result_list = info
                    break  # Yes single only
        else:
            return Response(ResponseStatus.ERROR, "Unable to find data for {0}.".format(param))

        if len(output_result_list) > 0:
            data = self.__build_player_loot_output_multiple(output_result_list)
        else:
            data = BasicError("{0}'s DKP loot was not found in database.".format(
                param.capitalize())).get()

        return Response(ResponseStatus.SUCCESS, data)

    def call_raidloot(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_premium():
            return Response(ResponseStatus.IGNORE)

        if not self.is_database_loaded():
            return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

        output_result_list = self._get_loot(self._get_channel_team_mapping(request_info['channel']['id']))

        if len(output_result_list) > 0:
            data = self.__build_loot_output_multiple(output_result_list)
        else:
            data = BasicError("Unable to find data loot data.").get()

        return Response(ResponseStatus.SUCCESS, data)

    def call_item(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_premium():
            return Response(ResponseStatus.IGNORE)

        if not self.is_database_loaded():
            return Response(ResponseStatus.SUCCESS, BasicError("Database does not exist. Please upload .lua file.").get())

        if len(param) < 3:
            return Response(ResponseStatus.SUCCESS, BasicError("Query too short. Please specify at least 3 letters.").get())

        output_result_list = self._find_loot(param, self._get_channel_team_mapping(request_info['channel']['id']))

        if len(output_result_list) > 0:
            data = self.__build_item_search_output_multiple(output_result_list)
        else:
            data = BasicError("No loot matching `{0}` found.".format(param)).get()

        return Response(ResponseStatus.SUCCESS, data)

    def config_call_server_side(self, params, num_params, request_info):
        return Response(ResponseStatus.SUCCESS, BasicError("Server and Side setting is not required.").get())

    def config_call_guild_name(self, params, num_params, request_info):
        return Response(ResponseStatus.SUCCESS, BasicError("Guild Name setting is not required.").get())

    def config_call_team(self, params, num_params, request_info):
        return Response(ResponseStatus.SUCCESS, BasicError("Multiple teams are not supported.").get())
