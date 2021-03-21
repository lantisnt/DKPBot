import re

from dkp_bot import DKPBot, Response, ResponseStatus
from player_db_models import PlayerInfo, PlayerInfoBasic, PlayerDKPHistory, PlayerLoot
from player_role import RoleFilter
from display_templates import (
    SupporterOnlyResponse,
    BasicError,
    BasicInfo,
    SinglePlayerProfile,
    DKPMultipleResponse,
    HistoryMultipleResponse,
    PlayerLootMultipleResponse,
    LootMultipleResponse,
    ItemValueMultipleResponse,
)
from bot_logger import BotLogger, trace, trace_func_only, for_all_methods
from raidhelper import RaidHelper
from statistics import Statistics


@for_all_methods(trace, trace_func_only)
class EssentialDKPBot(DKPBot):

    _CONFIG_SV = "MonDKP_DB"
    _DKP_SV = "MonDKP_DKPTable"
    _LOOT_SV = "MonDKP_Loot"
    _HISTORY_SV = "MonDKP_DKPHistory"
    _45_DAYS_SECONDS = 3888000

    # Matches either a,b,c,d or A / B or A \ B
    __item_id_name_find = re.compile(
        "^[^:]*:*(\d*).*\[([^\]]*)", re.I
    )  # pylint: disable=anomalous-backslash-in-string

    def __init__(self, guild_id, config):
        super().__init__(guild_id, config)
        self._configure()

    ###

    def _configure(self):
        super()._configure()
        config = self._get_config()
        # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile(
            "Essential DKP Profile", self._timezone
        )

        self._multiple_dkp_output_builder = DKPMultipleResponse(
            "DKP values",
            config.dkp.fields,
            config.dkp.entries_per_field,
            config.dkp.separate_messages,
            config.dkp.multiple_columns,
            config.dkp.enable_icons,
            config.dkp.value_suffix,
            config.dkp.alternative_display_mode,
            self._timezone,
        )

        self._multiple_history_output_builder = HistoryMultipleResponse(
            "Latest DKP history",
            config.dkp_history.fields,
            config.dkp_history.entries_per_field,
            config.dkp_history.separate_messages,
            config.dkp_history.multiple_columns,
            config.dkp_history.enable_icons,
            config.dkp_history.value_suffix,
            config.dkp_history.alternative_display_mode,
            self._timezone,
        )

        self._multiple_player_loot_output_builder = PlayerLootMultipleResponse(
            "Latest loot history",
            config.loot_history.fields,
            config.loot_history.entries_per_field,
            config.loot_history.separate_messages,
            config.loot_history.multiple_columns,
            config.loot_history.enable_icons,
            config.loot_history.value_suffix,
            config.loot_history.alternative_display_mode,
            self._timezone,
        )

        self._multiple_loot_output_builder = LootMultipleResponse(
            "Latest 30 items awarded",
            config.latest_loot.fields,
            config.latest_loot.entries_per_field,
            config.latest_loot.separate_messages,
            config.latest_loot.multiple_columns,
            config.latest_loot.enable_icons,
            config.latest_loot.value_suffix,
            config.latest_loot.alternative_display_mode,
            self._timezone,
        )

        self._multiple_item_search_output_builder = LootMultipleResponse(
            "Search results",
            config.item_search.fields,
            config.item_search.entries_per_field,
            config.item_search.separate_messages,
            config.item_search.multiple_columns,
            config.item_search.enable_icons,
            config.item_search.value_suffix,
            config.item_search.alternative_display_mode,
            self._timezone,
        )

        self._multiple_item_value_output_builder = ItemValueMultipleResponse(
            "Item value",
            config.item_value.fields,
            config.item_value.entries_per_field,
            config.item_value.separate_messages,
            config.item_value.multiple_columns,
            config.item_value.enable_icons,
            config.item_value.value_suffix,
            config.item_value.alternative_display_mode,
            self._timezone,
        )

        self._update_views_info()

    def _build_dkp_output_single(self, info):
        if not info or not isinstance(info, PlayerInfoBasic):
            return None

        return self._single_player_profile_builder.build(
            info, info.ingame_class()
        ).get()

    def _build_dkp_output_multiple(self, output_result_list, requester):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        if not requester:
            requester = ""

        return self._multiple_dkp_output_builder.build(
            output_result_list, requester
        ).get()

    def _build_history_output_multiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self._multiple_history_output_builder.build(output_result_list).get()

    def _build_player_loot_output_multiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self._multiple_player_loot_output_builder.build(output_result_list).get()

    def _build_loot_output_multiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self._multiple_loot_output_builder.build(output_result_list).get()

    def _build_item_search_output_multiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self._multiple_item_search_output_builder.build(output_result_list).get()

    def _build_item_value_output_multiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self._multiple_item_value_output_builder.build(output_result_list).get()

    def _get_addon_thumbnail(self):
        return "https://cdn.discordapp.com/attachments/765089790295015425/822883951822635028/essentiallogo.png"

    ### Database - Variables parsing ###

    def _get_item_id_name(self, loot):
        # [0] -> id [1] -> name
        return list(filter(None, type(self).__item_id_name_find.findall(loot)))

    def _fill_history(self, players, dkp, timestamp, reason, index, team):
        if not players:
            BotLogger().get().debug("Empty players")
            return

        if not dkp:
            BotLogger().get().debug("Empty DKP data")
            return

        if isinstance(players, str) and isinstance(dkp, (int, float)):
            player_info = self._get_dkp(players, team)
            if player_info is None:
                return
            self._add_history(
                players,
                PlayerDKPHistory(player_info, dkp, timestamp, reason, index),
                team,
            )
        elif isinstance(players, list) and isinstance(dkp, (int, float)):
            for player in players:
                player_info = self._get_dkp(player, team)
                if player_info is None:
                    continue
                self._add_history(
                    player,
                    PlayerDKPHistory(player_info, dkp, timestamp, reason, index),
                    team,
                )
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
                self._add_history(
                    player,
                    PlayerDKPHistory(
                        player_info, float(dkp.pop(0)), timestamp, reason, index
                    ),
                    team,
                )
        else:
            BotLogger().get().warning(
                "Unexpected combination: type(players): {0} type(dkp): {1}".format(
                    str(type(players)), str(type(dkp))
                )
            )

    def _generate_player_info(self, entry):
        if entry is None:
            BotLogger().get().debug("Player entry is None")
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

        spec = entry.get("spec")
        if spec is None:
            return None

        return PlayerInfo(
            player, dkp, lifetime_gained, lifetime_spent, ingame_class, role, spec
        )

    def _generate_player_loot(self, entry, team):
        if not isinstance(entry, dict):
            BotLogger().get().debug("Loot entry is not a dict")
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

        item_info = self._get_item_id_name(loot)

        if not item_info or not isinstance(item_info, list) or len(item_info) != 1:
            BotLogger().get().warning(
                "ERROR in loot entry: %s %s %s %s %s : [%s]",
                player.player(),
                date,
                cost,
                loot,
                item_info,
                entry,
            )
            return None

        if (
            not item_info[0]
            or not isinstance(item_info[0], tuple)
            or len(item_info[0]) != 2
        ):
            BotLogger().get().warning("ERROR in loot item_info[0] " + str(item_info[0]))
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
            if (
                len(dkp) == 1
            ):  # Some weird old MonolithDKP -X% only entry that I have no idea how to parse
                return None
        elif not isinstance(dkp, (int, float)):
            BotLogger().get().debug("DKP data is not a numeric value [%s]", dkp)
            return None

        self._fill_history(players, dkp, date, reason, index, team)

    # Called 1st
    def _build_config_database(self, saved_variable):
        super()._build_config_database(None)

        if saved_variable is None:
            BotLogger().get().debug("Saved variable missing")
            return False

        team = DKPBot.DEFAULT_TEAM

        config_list = saved_variable.get(self._CONFIG_SV)
        if not config_list:
            BotLogger().get().debug("Config missing")
            return False

        self._set_addon_config(config_list)

        return True

    # Called 2nd
    def _build_dkp_database(self, saved_variable):
        super()._build_dkp_database(None)

        if saved_variable is None:
            BotLogger().get().debug("Saved variable missing")
            return False

        team = DKPBot.DEFAULT_TEAM

        dkp_list = saved_variable.get(self._DKP_SV)
        if not dkp_list:
            BotLogger().get().debug("DKP variable missing")
            return False

        # dict because there may be ["seed"] field...
        if isinstance(dkp_list, dict):
            dkp_list = dkp_list.values()
        elif not isinstance(dkp_list, list):
            BotLogger().get().debug("DKP variable is not a list")
            return False

        for entry in dkp_list:
            info = self._generate_player_info(entry)
            if info is None:
                continue

            self._set_dkp(info.name(), info, team)
            self._set_group_dkp(info.ingame_class(), info, team)

        return True

    # Called 3rd
    def _build_loot_database(self, saved_variable):
        super()._build_loot_database(None)

        if saved_variable is None:
            BotLogger().get().debug("Saved variable missing")
            return False

        team = DKPBot.DEFAULT_TEAM

        loot_list = saved_variable.get(self._LOOT_SV)

        if not loot_list:
            BotLogger().get().debug("Loot variable missing")
            return False

        # dict because there is ["seed"] field...
        if isinstance(loot_list, dict):
            loot_list = loot_list.values()
        elif not isinstance(loot_list, list):
            BotLogger().get().debug("Loot variable is not a list")
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

    # Called 4th
    def _build_history_database(self, saved_variable):
        super()._build_history_database(None)

        if saved_variable is None:
            BotLogger().get().debug("Saved variable missing")
            return False

        team = DKPBot.DEFAULT_TEAM

        history = saved_variable.get(self._HISTORY_SV)

        if not history:
            BotLogger().get().debug("History variable missing")
            return False

        # dict because there is ["seed"] field...
        if isinstance(history, dict):
            history = history.values()
        elif not isinstance(history, list):
            BotLogger().get().debug("History variable is not a list")
            return False

        for entry in history:
            self._generate_player_history(entry, team)

        self._sort_history()
        self._set_player_latest_positive_history_and_activity(self._45_DAYS_SECONDS)

        return True

    # Called after whole database is built

    def _finalize_database(self):
        self._update_views_info()

    def _update_views_info(self):
        # Database
        self._single_player_profile_builder.set_database_info(self._db_get_info())
        self._multiple_dkp_output_builder.set_database_info(self._db_get_info())
        self._multiple_dkp_output_builder.config_filtering(True)
        self._multiple_history_output_builder.set_database_info(self._db_get_info())
        self._multiple_player_loot_output_builder.set_database_info(self._db_get_info())
        self._multiple_loot_output_builder.set_database_info(self._db_get_info())
        self._multiple_item_search_output_builder.set_database_info(self._db_get_info())
        self._multiple_item_value_output_builder.set_database_info(self._db_get_info())
        # Global
        rounding = self._get_addon_config(["modes", "rounding"])
        self._single_player_profile_builder.set_info(rounding)
        self._multiple_dkp_output_builder.set_info(rounding)
        self._multiple_history_output_builder.set_info(rounding)
        self._multiple_player_loot_output_builder.set_info(rounding)
        self._multiple_loot_output_builder.set_info(rounding)
        self._multiple_item_search_output_builder.set_info(rounding)
        self._multiple_item_value_output_builder.set_info(rounding)

    ### Commands ###

    def _get_dkp_target_results(self, team, targets, original, smart_roles_decoder):

        output_result_list_single = []
        output_result_list_group = []
        if smart_roles_decoder is not None:  # smart roles
            for target in targets:  # iterate to get all single player mixins
                info = self._get_dkp(target, team)
                if isinstance(info, PlayerInfoBasic):
                    output_result_list_single.append(info)
            for target in self._classes:  # Get data for all classess supported
                group_info = self._get_group_dkp(target, team)
                if group_info and len(group_info) > 0:
                    for info in group_info:
                        if info and isinstance(info, PlayerInfoBasic):
                            output_result_list_group.append(info)
            # Filter out the required data
            output_result_list_group = smart_roles_decoder(output_result_list_group)
            # Add classes that are not result of aliases
            output_result_list_class = []

            for target in original:
                if target in self._classes:
                    group_info = self._get_group_dkp(target, team)
                    if group_info and len(group_info) > 0:
                        for info in group_info:
                            if info and isinstance(info, PlayerInfoBasic):
                                output_result_list_class.append(info)
            output_result_list_group = (
                output_result_list_group + output_result_list_class
            )
        else:  # regular division
            for target in targets:
                # Single player
                info = self._get_dkp(target, team)
                if isinstance(info, PlayerInfoBasic):
                    output_result_list_single.append(info)
                else:
                    # Group request
                    group_info = self._get_group_dkp(target, team)
                    if group_info and len(group_info) > 0:
                        for info in group_info:
                            if info and isinstance(info, PlayerInfoBasic):
                                output_result_list_group.append(info)

        # Filter non unique
        return list(set(output_result_list_single + output_result_list_group))

    def call_dkp(self, param, request_info):
        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        team = self._get_channel_team_mapping(request_info["channel"]["id"])

        output_result_list = []
        targets, aliases, original, int_list = self._parse_player_param(param)

        # Smart Roles Filter preparation
        smart_roles_filter = None
        if self.smart_roles():
            smart_roles_filter = RoleFilter(aliases)

        # Handle Raid-Helper integration
        signed = []
        if len(int_list) > 0:
            for event_id in int_list:
                if event_id > 0:
                    raid_user_list = RaidHelper().get_event_signups(event_id)
                    for raid_user in raid_user_list:
                        # TODO Handles only mains for now
                        signed.append(raid_user.main())
        raid_helper_filter = len(signed) > 0

        if "all" in original:
            output_result_list = self._get_team_dkp(self.DEFAULT_TEAM)
        else:
            if len(targets) == len(int_list) and raid_helper_filter:
                output_result_list = self._get_dkp_target_results(
                    team, signed, original, smart_roles_filter
                )
            elif len(targets) > 0:
                output_result_list = self._get_dkp_target_results(
                    team, targets, original, smart_roles_filter
                )
                if self.is_premium() and raid_helper_filter:
                    output_result_list = list(
                        filter(lambda t: (t.name().lower() in signed), output_result_list)
                    )
            else:
                if not self.is_premium():
                    return Response(ResponseStatus.SUCCESS, SupporterOnlyResponse().get())
                else:
                    return Response(
                        ResponseStatus.SUCCESS,
                        BasicError("Unable to find data for {0}.".format(param)).get(),
                    )

        BotLogger().get().debug("Output Result List: %s", output_result_list)
        if len(output_result_list) == 1:
            data = self._build_dkp_output_single(output_result_list[0])
        elif len(output_result_list) > 0:
            output_result_list.sort(key=lambda info: info.dkp(), reverse=True)
            data = self._build_dkp_output_multiple(
                output_result_list, request_info["author"]["name"]
            )
        else:
            data = BasicError(
                "{0}'s was not found in database.".format(param.capitalize())
            ).get()

        return Response(ResponseStatus.SUCCESS, data)

    @staticmethod
    def _calculate_pagination(config, int_list):
        if config.separate_messages == 0:
            return 0

        pagination = 0
        if len(int_list) > 0:
            pagination = min(int_list)
            if pagination > 10000:
                pagination = 10000

        return (
            pagination
            * config.entries_per_field
            * config.fields
            * config.separate_messages
        )

    def call_history(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        targets, aliases, original, int_list = self._parse_player_param(param)
        output_result_list = []

        if len(targets) > 0:
            team = self._get_channel_team_mapping(request_info["channel"]["id"])
            for target in targets:
                # Single player
                info = self._get_history(target, team)
                if info and isinstance(info, list):
                    output_result_list = info
                    break  # Yes single only
        else:
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Unable to find data for {0}.".format(param)).get(),
            )

        BotLogger().get().debug("Output Result List: %s", output_result_list)
        if len(output_result_list) > 0:
            pagination = type(self)._calculate_pagination(
                self._get_config().dkp_history, int_list
            )
            output_result_list = output_result_list[pagination:]
            if len(output_result_list) > 0:
                data = self._build_history_output_multiple(output_result_list)
            else:
                data = BasicError("Requested too old history data.").get()
        else:
            data = BasicError(
                "{0}'s history was not found in database.".format(param.capitalize())
            ).get()

        return Response(ResponseStatus.SUCCESS, data)

    def call_loot(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        targets, aliases, original, int_list = self._parse_player_param(param)
        output_result_list = []

        if len(targets) > 0:
            team = self._get_channel_team_mapping(request_info["channel"]["id"])
            for target in targets:
                # Single player
                info = self._get_player_loot(target, team)
                if info and isinstance(info, list):
                    output_result_list = info
                    break  # Yes single only
        else:
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Unable to find data for {0}.".format(param)).get(),
            )

        pagination = type(self)._calculate_pagination(
            self._get_config().loot_history, int_list
        )
        output_result_list = output_result_list[pagination:]

        BotLogger().get().debug("Output Result List: %s", output_result_list)
        if len(output_result_list) > 0:
            data = self._build_player_loot_output_multiple(output_result_list)
        else:
            data = BasicError(
                "{0}'s loot was not found in database.".format(param.capitalize())
            ).get()

        return Response(ResponseStatus.SUCCESS, data)

    def call_raidloot(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_premium():
            return Response(ResponseStatus.SUCCESS, SupporterOnlyResponse().get())

        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        output_result_list = self._get_loot(
            self._get_channel_team_mapping(request_info["channel"]["id"])
        )

        _, _, _, int_list = self._parse_player_param(param)

        pagination = type(self)._calculate_pagination(
            self._get_config().latest_loot, int_list
        )
        output_result_list = output_result_list[pagination:]

        BotLogger().get().debug("Output Result List: %s", output_result_list)
        if len(output_result_list) > 0:
            data = self._build_loot_output_multiple(output_result_list)
        else:
            data = BasicError("Unable to find loot data.").get()

        return Response(ResponseStatus.SUCCESS, data)

    def call_item(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_premium():
            return Response(ResponseStatus.SUCCESS, SupporterOnlyResponse().get())

        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        if len(param) < 3:
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Query too short. Please specify at least 3 letters.").get(),
            )

        output_result_list = self._find_loot(
            param, self._get_channel_team_mapping(request_info["channel"]["id"])
        )

        BotLogger().get().debug("Output Result List: %s", output_result_list)
        if len(output_result_list) > 0:
            data = self._build_item_search_output_multiple(output_result_list)
        else:
            data = BasicError("No loot matching `{0}` found.".format(param)).get()

        return Response(ResponseStatus.SUCCESS, data)

    def call_value(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_premium():
            return Response(ResponseStatus.SUCCESS, SupporterOnlyResponse().get())

        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        if len(param) < 3:
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Query too short. Please specify at least 3 letters.").get(),
            )

        output_result_list_intermediate = self._find_loot(
            param, self._get_channel_team_mapping(request_info["channel"]["id"])
        )
        BotLogger().get().debug(
            "Output Result List Intermediate: %s", output_result_list_intermediate
        )

        output_result_list = []
        if len(output_result_list_intermediate) > 0:
            value = Statistics()
            for item in output_result_list_intermediate:
                value.data[(item.item_id(), item.item_name())] = item.dkp()
            for (_id, _name), _value in value.data.items():
                output_result_list.append((_id, _name, _value))

        BotLogger().get().debug("Output Result List: %s", output_result_list)
        if len(output_result_list) > 0:
            data = self._build_item_value_output_multiple(output_result_list)
        else:
            data = BasicError("No loot matching `{0}` found.".format(param)).get()

        return Response(ResponseStatus.SUCCESS, data)

    def config_call_server_side(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo(
                "Server and Side setting are not used in `essential` mode."
            ).get(),
        )

    def config_call_guild_name(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Guild Name setting is not used in `essential` mode.").get(),
        )

    def config_call_team(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Multiple teams are not used in `essential` mode.").get(),
        )
