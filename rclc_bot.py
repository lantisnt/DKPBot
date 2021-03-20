import re
from enum import Enum
from dkp_bot import DKPBot, Response, ResponseStatus
from essentialdkp_bot import EssentialDKPBot
from player_db_models import PlayerInfoLC, PlayerLootLC
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
    PlayerLootMultipleResponse,
    LootMultipleResponse,
)
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
            "RCLootCouncil Profile", self._timezone
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

        self._update_views_info()

    def _transform_factionrealm(factionrealm):
        data = factionrealm.lower().split("-")
        return data[1].strip() + "-" + data[0].strip()

    def _get_loot_info(lootString):


    def _parse_entry(playername, entry):
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
        
        player = self._get_dkp(name, self.DEFAULT_TEAM)
        if player is None:
            info = PlayerInfoLC(name, ingame_class)
            self._set_dkp(info.name(), info, self.DEFAULT_TEAM)
        
        found = self.epgp_value_regex.findall(lootWon)
        if found and isinstance(found, list) and len(found) == 1 and len(found[0]) == 2:
            loot = PlayerLootLC(player, item_id, item_name, timestamp):
            self._add_loot(loot, self.DEFAULT_TEAM)
            self._add_player_loot(player_loot.player().name(), loot, self.DEFAULT_TEAM)

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
            traffic_list is None
            or not factionrealm
            or not isinstance(factionrealm, dict)
        ):
            return False

        server_side = self._get_config().guild_info.server_side

        for factionrealm_name, player in factionrealm:
            transformed = self._transform_factionrealm
            if server_side == transformed:
                for playername, entries in player.items():
                    for i, entry in entries,items():
                        self._parse_entry(playername, entry)

                self._sort_loot()
                self._sort_player_loot()
                self._set_player_latest_loot()
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

    def call_info(self, param, request_info):  # pylint: disable=unused-argument
        embed = RawEmbed()
        embed.build(None, "Info", None, None, get_bot_color(), None)
        info_string = "WoW DKP Bot allows querying DKP/EPGP/RCLootCouncil standings, history and loot data directly through the discord."
        info_string += "This is achieved by parsing uploaded saved variable .lua files of popular addons: `MonolithDKP`, `EssentialDKP`, `CommunityDKP` and `CEPGP` to a discord channel.\n"
        embed.add_field("\u200b", info_string, False)
        info_string = "Due to many possible usages of the addons and discord limitations bot data may exceed maxium accetable size. To mitigate this issue extensive `display` configuration is available to tweak response sizes."
        embed.add_field("\u200b", info_string, False)
        info_string = "For bot to work properly you will need to upload saved variable file of your addon every time you want to update the data."
        embed.add_field("\u200b", info_string, False)
        info_string = "If you want to become supporter and get access to `supporter only commands` or you need help configuring the bot checkout the {0}.\n\n".format(
            SUPPORT_SERVER
        )
        embed.add_field("\u200b", info_string, False)
        # Pseudo-Footer: Discord link
        embed.add_field("\u200b", get_bot_links(), False)
        return Response(ResponseStatus.SUCCESS, embed.get())

    def call_dkp(self, param, request_info):
        return Response(ResponseStatus.IGNORE)

    def call_epgp(self, param, request_info):  # pylint: disable=unused-argument
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
            if raid_helper_filter:
                targets = signed

            if self.is_premium() or raid_helper_filter:
                for target in targets:
                    info = self._get_dkp(target, self.DEFAULT_TEAM)
                    if isinstance(info, PlayerInfoEPGP):
                        output_result_list.append(info)
            else:
                for target in targets:
                    info = self._get_dkp(target, self.DEFAULT_TEAM)
                    if isinstance(info, PlayerInfoEPGP):
                        output_result_list.append(info)
                        break

        if len(output_result_list) == 1:
            data = self._build_dkp_output_single(output_result_list[0])
        elif len(output_result_list) > 0:
            output_result_list.sort(key=lambda info: info.ep(), reverse=True)
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
            ResponseStatus.SUCCESS, self._build_help_internal(is_privileged, "rc")
        )

    def help_call_dkp(self, is_privileged):  # pylint: disable=unused-argument
        return self._help_internal(is_privileged)

    def help_call_rclc(self, is_privileged):  # pylint: disable=unused-argument
        help_string = "Display summary information for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "rc", "")
        )
        help_string += (
            "Display summary information for specified `player`.\n{0}\n".format(
                preformatted_block(self.get_prefix() + "rc player", "")
            )
        )

        return Response(
            ResponseStatus.SUCCESS, self._help_handler_internal("RCLootCouncil", help_string)
        )
