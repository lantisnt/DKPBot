import re
from enum import Enum
from dkp_bot import DKPBot, Response, ResponseStatus
from essentialdkp_bot import EssentialDKPBot
from player_db_models import PlayerInfoEPGP, PlayerEPGPHistory, PlayerLootEPGP
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
from display_templates_epgp import (
    SinglePlayerProfile,
    EPGPMultipleResponse,
    HistoryMultipleResponse,
    PlayerLootMultipleResponse,
    LootMultipleResponse,
    ItemValueMultipleResponse,
)
from bot_logger import BotLogger, trace, trace_func_only, for_all_methods


@for_all_methods(trace, trace_func_only)
class CEPGPBot(EssentialDKPBot):

    _SV = "CEPGP"
    __BACKUP = "bot"
    TRAFFIC_HOLDER = u"\u200b"  # Non-printed space ^^

    epgp_value_regex = re.compile(
        ".*?([EPG]{2,4})\s*\+?(-?\d+)%?.*?(?:(?: - (.*))|(?:\s*\((.*)\)))?", re.I
    )

    def _configure(self):
        super()._configure()
        config = self._get_config()
        # # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile(
            "CEPGP Profile", self._timezone
        )

        self._multiple_dkp_output_builder = EPGPMultipleResponse(
            "EPGP values",
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
            "Latest EPGP history",
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

    def _get_addon_thumbnail(self):
        return "https://cdn.discordapp.com/attachments/765089790295015425/822884836887887913/cepgplogo.png"

    ### Database - Variables parsing ###

    def _generate_player_info(self, player_entry, data):
        if not player_entry or not data:
            return None

        player = player_entry.split("-")[0]
        if len(player) == 0:
            return None

        ep = 0
        gp = 0
        if len(data) > 0:
            tmp = data.split(",")
            if len(tmp) == 2:
                ep = float(tmp[0])
                gp = float(tmp[1])
            else:
                BotLogger().get().debug("Invalid backup entry %s", player_entry)
        else:
            BotLogger().get().debug("Invalid backup entry %s", player_entry)

        return PlayerInfoEPGP(player, ep, gp)

    def _parse_traffic_entry(
        self,
        target=None,
        source=None,
        desc=None,
        EPB=None,
        EPA=None,
        GPB=None,
        GPA=None,
        item_link=None,
        timestamp=None,
        id=None,
        unit_guid=None,
    ):
        # Workaround for old / invalid traffic structure
        param_list = [
            target,
            source,
            desc,
            EPB,
            EPA,
            GPB,
            GPA,
            item_link,
            timestamp,
            id,
            unit_guid,
        ]
        if None in param_list:
            BotLogger().get().debug("Old traffic structure %s", param_list)
            return

        # Check for target
        if not target or target is None or len(target) < 2 or target == "":
            # Raid target is treated same as "" as we can't know who was in raid.
            # For Guild target we assume Guild = everyone
            has_target = False
        else:
            has_target = not (target.lower() == "raid")

        is_target_guild = target.lower() == "guild"
        is_target_raid = target.lower() == "raid"

        # Check for item id and name to see if we have Loot Entry
        item_info = self._get_item_id_name(item_link)
        if item_info and isinstance(item_info, list) and len(item_info) == 1:
            if (
                item_info[0]
                and isinstance(item_info[0], tuple)
                and len(item_info[0]) == 2
            ):
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
                        player_loot = PlayerLootEPGP(
                            player, item_id, item_name, gp_cost, timestamp
                        )
                        self._add_loot(player_loot, self.DEFAULT_TEAM)
                        self._add_player_loot(
                            player_loot.player().name(), player_loot, self.DEFAULT_TEAM
                        )
                else:
                    player = self._get_dkp(self.TRAFFIC_HOLDER, self.DEFAULT_TEAM)
                    player_loot = PlayerLootEPGP(
                        player, item_id, item_name, 0, timestamp
                    )
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

            is_percentage = desc.find("%") >= 0

            value_type = found[0][0].lower()
            if value_type == "ep":
                ep = value
                gp = 0
            elif value_type == "gp":
                ep = 0
                gp = value
            elif value_type == "epgp":
                ep = value
                gp = value

            if is_target_guild:
                # Target is guild then we attach it to every player
                history = PlayerEPGPHistory(
                    self.TRAFFIC_HOLDER,
                    ep,
                    gp,
                    is_percentage,
                    timestamp,
                    reason,
                    source,
                )
                self._add_history_to_all_players(history, self.DEFAULT_TEAM)
            elif has_target:
                player = self._get_dkp(target, self.DEFAULT_TEAM)
                history = PlayerEPGPHistory(
                    target, ep, gp, is_percentage, timestamp, reason, source
                )
                self._add_history(target, history, self.DEFAULT_TEAM)

            return

        BotLogger().get().debug("Unknown way to parse entry %s", param_list)

    def _set_player_latest_positive_history_and_activity(
        self, inactive_time=200000000000
    ):
        for entry in self._get_team_dkp(self.DEFAULT_TEAM):
            if entry.ep() <= 0:
                entry.set_inactive()
            history = self._get_history(entry.name(), self.DEFAULT_TEAM)
            if history and isinstance(history, list):
                for history_entry in history:
                    if history_entry.ep() > 0:
                        entry.set_latest_history_entry(history_entry)
                        break

    # Called 1st
    def _build_config_database(self, saved_variable):  # pylint: disable=unused-argument
        self._set_addon_config({})
        return True

    # Called 2nd
    def _build_dkp_database(self, saved_variable):
        if saved_variable is None:
            BotLogger().get().debug("Missing saved_variable")
            return False

        addon_data = saved_variable.get(self._SV)
        if addon_data is None or not addon_data or not isinstance(addon_data, dict):
            BotLogger().get().debug("Missing %s", self._SV)
            return False

        backups_list = addon_data.get("Backups")
        if (
            backups_list is None
            or not backups_list
            or not isinstance(backups_list, dict)
        ):
            BotLogger().get().debug("Missing Backups")
            return False

        backup = None
        for _backup in list(backups_list.keys()):
            if _backup.lower() == self.__BACKUP:
                backup = _backup

        epgp_list = []
        if backup is None:
            epgp_list = backups_list[list(backups_list.keys())[0]]
            BotLogger().get().warning("Missing `bot` backup. Using first found.")
        else:
            epgp_list = backups_list[backup]

        if len(epgp_list) == 0:
            BotLogger().get().debug("Empty backup.")
            return False

        for player, data in epgp_list.items():
            info = self._generate_player_info(player, data)
            if isinstance(info, PlayerInfoEPGP):
                self._set_dkp(info.name(), info, self.DEFAULT_TEAM)

        # Fake DKP entry to hold Raid / Guild (group) traffic
        info = PlayerInfoEPGP(self.TRAFFIC_HOLDER, 0, 0)
        info.set_inactive()
        self._set_dkp(info.name(), info, self.DEFAULT_TEAM)

        # Main <-> Alt linking
        alt_data = addon_data.get("Alt")
        if isinstance(alt_data, dict):
            alt_links = alt_data.get("Links")
            if isinstance(alt_links, dict) and len(alt_links) > 0:
                for player, alt_list in alt_links.items():
                    main = self._get_dkp(player, self.DEFAULT_TEAM)
                    if main is not None:
                        alt_list_objects = []
                        for _alt in alt_list:
                            alt = self._get_dkp(_alt, self.DEFAULT_TEAM)
                            if alt is not None:
                                alt.set_main(main)
                                alt_list_objects.append(alt)
                            else:
                                alt_list_objects.append(_alt)  # Append name
                        main.link_alts(alt_list_objects)

        return True

    # Called 3rd
    def _build_loot_database(self, saved_variable):
        if saved_variable is None:
            return False

        addon_data = saved_variable.get(self._SV)
        if addon_data is None or not addon_data or not isinstance(addon_data, dict):
            return False

        traffic_list = addon_data.get("Traffic")
        if (
            traffic_list is None
            or not traffic_list
            or not isinstance(traffic_list, list)
        ):
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
        return True  # This is being handled within loot database as all is based on traffic

    ### Parent commands ###

    def config_call_server_side(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Server and Side setting are not used in `cepgp` mode.").get(),
        )

    def config_call_guild_name(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Guild Name setting is not used in `cepgp` mode.").get(),
        )

    def config_call_team(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Multiple teams are not used in `cepgp` mode.").get(),
        )

    ### CEPGP commands ###

    def call_info(self, param, request_info):  # pylint: disable=unused-argument
        embed = RawEmbed()
        embed.build(None, "Info", None, None, get_bot_color(), None)
        info_string = "WoW DKP Bot allows querying DKP/EPGP/RCLootCouncil standings, history and loot data directly through the discord."
        info_string += "This is achieved by parsing uploaded saved variable .lua files of popular addons: `MonolithDKP`, `EssentialDKP`, `CommunityDKP`, `CEPGP` and `RCLootCouncil` to a discord channel.\n"
        embed.add_field("\u200b", info_string, False)
        info_string = "Due to many possible usages of the addons and discord limitations bot data may exceed maxium accetable size. To mitigate this issue extensive `display` configuration is available to tweak response sizes."
        embed.add_field("\u200b", info_string, False)
        info_string = "For bot to work properly you will need to upload saved variable file of your addon every time you want to update the data."
        embed.add_field("\u200b", info_string, False)
        info_string = "Due to holding current standings in Officer Notes `CEPGP` requires one additional step before: do an ingame backup named `bot` and `/reload` before uploading the file."
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
            ResponseStatus.SUCCESS, self._build_help_internal(is_privileged, "epgp")
        )

    def help_call_dkp(self, is_privileged):  # pylint: disable=unused-argument
        return self._help_internal(is_privileged)

    def help_call_epgp(self, is_privileged):  # pylint: disable=unused-argument
        help_string = "Display summary information for the requester.\nUses Discord server nickname if set, Discord username otherwise.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "epgp", "")
        )
        help_string += (
            "Display summary information for specified `player`.\n{0}\n".format(
                preformatted_block(self.get_prefix() + "epgp player", "")
            )
        )
        help_string += "Display dkp list for all active players.\nPlayers are assumed active if they gained positive EP within last 45 days.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "epgp all", "")
        )
        help_string += "Display summary information for players signed to `raidid` event in `Raid-Helper` bot.\n{0}\n".format(
            preformatted_block(self.get_prefix() + "epgp raidid", "")
        )

        return Response(
            ResponseStatus.SUCCESS, self._help_handler_internal("EPGP", help_string)
        )
