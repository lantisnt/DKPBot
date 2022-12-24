# Copyright 2020-2023 Lantis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
from enum import Enum
from dkp_bot import DKPBot, Response, ResponseStatus
from essentialdkp_bot import EssentialDKPBot
from player_db_models import PlayerInfoBasic, PlayerLootBasic
from raidhelper import RaidHelper
from display_templates import (
    preformatted_block,
    get_bot_color,
    get_bot_links,
    SUPPORT_SERVER,
)
from display_templates import (
    RawEmbed,
    BasicError,
    BasicCritical,
    BasicAnnouncement,
    BasicInfo,
    BasicSuccess,
)
from display_templates_lc import (
    SinglePlayerProfile,
    RCLCMultipleResponse,
    PlayerLootMultipleResponse,
    LootMultipleResponse,
)
from bot_utility import timestamp_now
from bot_logger import BotLogger, trace, trace_func_only, for_all_methods


@for_all_methods(trace, trace_func_only)
class RCLCBot(EssentialDKPBot):

    _SV = "RCLootCouncilLootDB"

    rclc_loot_regex = re.compile("^.*?:(\d+).*?\[(.*?)\].*", re.I)

    def _configure(self):
        super()._configure()
        config = self._get_config()
        # # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile(
            "RCLootCouncil Profile", self._timezone, self._version
        )

        self._multiple_dkp_output_builder = RCLCMultipleResponse(
            "RCLootCouncil profiles",
            config.dkp.fields,
            config.dkp.entries_per_field,
            config.dkp.separate_messages,
            config.dkp.multiple_columns,
            config.dkp.enable_icons,
            config.dkp.value_suffix,
            config.dkp.alternative_display_mode,
            self._timezone, self._version
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
            self._timezone, self._version
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
            self._timezone, self._version
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
            self._timezone, self._version
        )

        self._update_views_info()

    def _get_addon_thumbnail(self):
        return "https://cdn.discordapp.com/attachments/765089790295015425/810464766808031242/rclootcouncil.png"

    def _transform_factionrealm(self, factionrealm):
        data = factionrealm.lower().split("-")
        return data[1].strip() + "-" + data[0].strip()

    def _parse_entry(self, playername, entry):
        name = playername.split("-")[0]
        if len(name) == 0:
            return None
        
        ingame_class = entry.get("class")
        if ingame_class is None:
            return None

        lootWon = entry.get("lootWon")
        if lootWon is None:
            return None

        timestamp_id = entry.get("id")
        if timestamp_id is None:
            return None
        
        try:
            timestamp = timestamp_id.split("-")[0]
        except ValueError:
            return None
        
        player = self._get_dkp(name, self.DEFAULT_TEAM)
        if player is None:
            info = PlayerInfoBasic(name, ingame_class, None, None)
            self._set_dkp(info.name(), info, self.DEFAULT_TEAM)
            self._set_group_dkp(info.ingame_class(), info, self.DEFAULT_TEAM)
            player = self._get_dkp(name, self.DEFAULT_TEAM)
        
        found = self.rclc_loot_regex.findall(lootWon)
        if found and isinstance(found, list) and len(found) == 1 and len(found[0]) == 2:
            loot = PlayerLootBasic(player, found[0][0], found[0][1], timestamp)
            self._add_loot(loot, self.DEFAULT_TEAM)
            self._add_player_loot(loot.player().name(), loot, self.DEFAULT_TEAM)

    def _set_player_activity(
        self, inactive_time=200000000000
    ):
        now = timestamp_now(True)
        for entry in self._get_team_dkp(self.DEFAULT_TEAM):
            entry.set_inactive()
            loot = self._get_player_loot(entry.name(), self.DEFAULT_TEAM)
            if loot and isinstance(loot, list):
                for loot_entry in loot:
                    if loot_entry.timestamp() - now <= inactive_time:
                        entry.set_active()
                        break

    ### Database - Variables parsing ###

    # Called 1st
    def _build_config_database(self, saved_variable):  # pylint: disable=unused-argument
        self._set_addon_config({})
        return True

    # Called 2nd
    def _build_dkp_database(self, saved_variable):
        return True

    # Called 3rd
    def _build_loot_database(self, saved_variable):
        if saved_variable is None:
            return False

        addon_data = saved_variable.get(self._SV)
        if addon_data is None or not addon_data or not isinstance(addon_data, dict):
            return False

        factionrealm = addon_data.get("factionrealm")
        if (
            factionrealm is None
            or not factionrealm
            or not isinstance(factionrealm, dict)
        ):
            return False

        server_side = self._get_config().guild_info.server_side
        for factionrealm_name, player in factionrealm.items():
            transformed = self._transform_factionrealm(factionrealm_name)
            if server_side == transformed:
                for playername, entries in player.items():
                    if not isinstance(entries, list):
                        continue
                    for entry in entries:
                        self._parse_entry(playername, entry)

                self._sort_loot()
                self._sort_player_loot()
                self._set_player_latest_loot(5)
                self._set_player_activity(self._45_DAYS_SECONDS * 2)
                return True

        return False

    # Called 4th
    def _build_history_database(self, saved_variable):
        return True 

    ### Parent commands ###

    def config_call_guild_name(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Guild Name setting is not used in `rclc` mode.").get(),
        )

    def config_call_team(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Multiple teams are not used in `rclc` mode.").get(),
        )

    ### RCLC commands ###

    def config_call_server_side(self, params, num_params, request_info):
        return DKPBot.config_call_server_side(self, params, num_params, request_info)

    def call_dkp(self, param, request_info):
        return Response(ResponseStatus.IGNORE)

    def call_history(self, param, request_info):
        return Response(ResponseStatus.IGNORE)

    def call_rc(self, param, request_info):  # pylint: disable=unused-argument
        if not self.is_database_loaded():
            return Response(
                ResponseStatus.SUCCESS,
                BasicError("Database does not exist. Please upload .lua file.").get(),
            )

        targets, aliases, original, int_list = self._parse_player_param(param)

        ## Handle Raid-Helper integration
        signed = []
        if len(int_list) > 0:
            for event_id in int_list:
                if event_id > 0:
                    raid_user_list = RaidHelper().get_event_signups(event_id)
                    for raid_user in raid_user_list:
                        # TODO Handles only mains for now
                        signed.append(raid_user.main())

        raid_helper_filter = len(signed) > 0

        output_result_list = []
        if "all" in original:
            output_result_list = self._get_team_dkp(self.DEFAULT_TEAM)
        else:
            if len(targets) == len(int_list) and raid_helper_filter:
                output_result_list = self._get_dkp_target_results(
                    self.DEFAULT_TEAM, signed, original, None
                )
            elif len(targets) > 0:
                output_result_list = self._get_dkp_target_results(
                    self.DEFAULT_TEAM, targets, original, None
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
            output_result_list.sort(key=lambda info: info.name(), reverse=False)
            data = self._build_dkp_output_multiple(
                output_result_list, request_info["author"]["name"]
            )
        else:
            data = BasicError(
                "{0}'s was not found in database.".format(param.capitalize())
            ).get()

        return Response(ResponseStatus.SUCCESS, data)

    ### Help handlers ###

    def _help_internal(self, is_privileged):
        return Response(
            ResponseStatus.SUCCESS, self._build_help_internal(is_privileged, "rc", ["history", "value"])
        )

    def help_call_dkp(self, is_privileged):  # pylint: disable=unused-argument
        return self._help_internal(is_privileged)

    def help_call_rc(self, is_privileged):  # pylint: disable=unused-argument
        help_string = "Display summary information for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "rc", "")
        )
        help_string += (
            "Display summary information for specified `player`.\n{0}\n".format(
                preformatted_block(self.get_prefix() + "rc player", "")
            )
        )
        help_string += "Display list of all active players.\nPlayers are assumed active if they received any item within last 90 days.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "rc all", "")
        )
        help_string += "Display list of as many players, classes or aliases mixed together as you wish.\n{0}".format(
            preformatted_block(
                "{0}rc class/alias/player\nExamples:\n{0}rc hunter tanks joe\n{0}rc rogue druid\n{0}rc joe andy".format(
                    self.get_prefix()
                ),
                "",
            )
        )
        help_string += preformatted_block(
            "Supported aliases:\n* tanks\n* healers\n* dps\n* casters\n* physical\n* ranged\n* melee",
            "",
        )
        help_string += preformatted_block("Supporter only command", "css") + "\n"
        help_string += "Display summary information for players signed to `raidid` event in `Raid-Helper` bot. Supporters can also use it in conjunction with above mixnis.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "rc raidid", "")
        )

        return Response(
            ResponseStatus.SUCCESS, self._help_handler_internal("RC", help_string)
        )

    def help_call_history(self, is_privileged):  # pylint: disable=unused-argument
        help_string = "Display latest loot for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "loot", "")
        )
        help_string += "Display latest loot for specified `player`.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "loot player", "")
        )
        help_string += "Display N-th loot page for specified `player`.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "loot player N", "")
        )
        return Response(
            ResponseStatus.SUCCESS, self._help_handler_internal("History", help_string)
        )

    def help_call_items(self, is_privileged):  # pylint: disable=unused-argument
        help_string = "Display latest 30 loot entries from raids.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "raidloot", "")
            + preformatted_block("Supporter only command", "css")
        )
        help_string += "Display N-th page of loot entries from raids.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "raidloot N", "")
            + preformatted_block("Supporter only command", "css")
        )
        help_string += (
            "Find loot matching `name`. Supports partial match.\n{0}\n".format(
                preformatted_block(self.get_prefix() + "item name", "")
                + preformatted_block("Supporter only command", "css")
            )
        )

        return Response(
            ResponseStatus.SUCCESS, self._help_handler_internal("Items", help_string)
        )