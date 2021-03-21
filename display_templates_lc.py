from player_db_models import PlayerInfoBasic, PlayerLootBasic
from bot_utility import get_date_from_timestamp
from bot_config import DisplayConfig
from bot_logger import trace, trace_func_only, for_all_methods
from display_templates import BaseResponse, MultipleResponse
from display_templates import (
    get_bot_links,
    get_bot_color,
    get_class_color,
    get_config_color,
    get_class_icon_string,
    preformatted_block,
    get_thumbnail,
    get_wowhead_item_link
)
import build_info


@trace
def get_lc_color():
    return 10204605

@trace
def get_rclc_thumbnail():
    return "https://cdn.discordapp.com/attachments/765089790295015425/810464766808031242/rclootcouncil.png"

@trace
def generate_loot_entries(loot_entry_list, enable_icons, alternative_display_mode, player, timezone):
    if loot_entry_list and isinstance(loot_entry_list, list):
        data = ""
        for loot_entry in loot_entry_list:
            data += generate_loot_entry(loot_entry, enable_icons, alternative_display_mode, player, timezone)
        return data
    return "- No data available -"



@trace
def generate_loot_entry(loot_entry, enable_icons, alternative_display_mode, player, timezone):
    if loot_entry and isinstance(loot_entry, PlayerLootBasic):
        row = ""
        row += "`{0:16}` - ".format(get_date_from_timestamp(loot_entry.timestamp()))
        row += get_wowhead_item_link(loot_entry.item_name(), loot_entry.item_id(), self._version)
        if player:
            if enable_icons:
                row += " - {0}".format(
                    get_class_icon_string(loot_entry.player().ingame_class(), None)
                )
            row += "{0}".format(loot_entry.player().name())
        row += "\n"
        return row
    return "- No data available -"


@for_all_methods(trace, trace_func_only)
class SinglePlayerProfile(BaseResponse):
    def build(self, info, thumbnail=None):
        self._embed.clear()

        if thumbnail:
            thumbnail = get_thumbnail(thumbnail)

        self._embed.build(
            author_name=self._title,
            title=info.player().name(),
            description=info.ingame_class(),
            thumbnail_url=thumbnail,
            color=get_class_color(info.ingame_class()),
            footer_text=self._get_footer(),
        )

        loot = info.get_latest_loot_entry()
        self._embed.add_field(
            "Last received loot:",
            generate_loot_entries(loot, False, False, False, self._timezone), 
            False,
        )

        return self

    def get(self):
        return self._embed.get()

@for_all_methods(trace, trace_func_only)
class RCLCMultipleResponse(MultipleResponse):
    def _prepare(self, data_list):
        pass

    def _display_filter(self, data):
        if data and isinstance(data, PlayerInfoBasic):
            return data.is_active()

        return False

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerInfoBasic):
            if self._enable_icons:
                row = "{0}".format(
                    get_class_icon_string(data.ingame_class(), None)
                )
            else:
                row = ""

            row += " "
            if requester == data.player().name():
                row += "**{0}**".format(data.player().name())
            else:
                row += "{0}".format(data.player().name())
            row += "\n"
            return row

        return ""

@for_all_methods(trace, trace_func_only)
class PlayerLootMultipleResponse(MultipleResponse):
    def _prepare(self, data_list):
        for data in data_list:
            if data and isinstance(data, PlayerLootBasic):
                self.__user = data.player().name()
                break

    # def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        if field_id == 0:
            self._embed.edit_field(field_id, self.__user)
        else:
            self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerLootBasic):
            return generate_loot_entry(data, self._enable_icons, self._alternative_display_mode, False, self._timezone)

        return ""

@for_all_methods(trace, trace_func_only)
class LootMultipleResponse(MultipleResponse):
    def _prepare(self, data_list):
        for data in data_list:
            if data and isinstance(data, PlayerLootBasic):
                self.__user = data.player().name()
                break

    # def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerLootBasic):
            return generate_loot_entry(data, self._enable_icons, self._alternative_display_mode, True, self._timezone)

        return ""
