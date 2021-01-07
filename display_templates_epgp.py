from player_db_models import PlayerInfoEPGP, PlayerEPGPHistory, PlayerLootEPGP
from bot_utility import get_date_from_timestamp
from bot_config import DisplayConfig
from bot_logger import trace, trace_func_only, for_all_methods
from display_templates import BaseResponse, MultipleResponse
from display_templates import get_bot_links, get_bot_color, get_config_color, get_plus_minus_icon_string, preformatted_block
import build_info

@trace
def get_epgp_color():
    return 10204605

@trace
def get_thumbnail():
    return "https://cdn.discordapp.com/attachments/765089790295015425/784450070945857626/CEPGP.png"

@trace
def get_points_format_string(ep_width, gp_width, pr_width, value_suffix):
    if value_suffix:
        return "`{{0:{0}.0f}}{1} {{1:{2}.0f}}{3} {{2:{4}.2f}}{5}`".format(
            ep_width, " EP" if value_suffix else "",
            gp_width, " GP" if value_suffix else "",
            pr_width, " PR" if value_suffix else "")
    else:
        return "`{{0:{0}.0f}}/{{1:{1}.0f}} {{2:{2}.2f}}`".format(ep_width, gp_width, pr_width)

@trace
def get_history_format_string(ep_width, gp_width, value_suffix):
    return "`{{0:{0}.0f}}{1} {{1:{2}.0f}}{3}`".format(
            ep_width, " EP" if value_suffix else "",
            gp_width, " GP" if value_suffix else "")

@trace
def get_loot_format_string(ep_width, value_suffix):
    return "`{{0:{0}.0f}}{1}`".format(ep_width, " GP" if value_suffix else "")

@trace
def generate_epgp_history_entry(history_entry, format_string, enable_icons, alternative_display_mode):
    if history_entry and isinstance(history_entry, PlayerEPGPHistory):
        row = ""
        if enable_icons:
            row += get_plus_minus_icon_string(history_entry.ep() >= 0 or history_entry.gp() <= 0) + " "
        row += "`{0:16}` - ".format(get_date_from_timestamp(history_entry.timestamp()))
        row += format_string.format(history_entry.ep(), history_entry.gp())
        row += " - {0} _by {1}_".format(history_entry.reason(),
                                      history_entry.officer())
        row += "\n"
        return row
    return "- No data available -"

@trace
def generate_loot_entry(loot_entry, format_string, enable_icons, alternative_display_mode, player):
    if loot_entry and isinstance(loot_entry, PlayerLootEPGP):
        row = ""
        row += "`{0:16}` - ".format(get_date_from_timestamp(loot_entry.timestamp()))
        row += format_string.format(loot_entry.dkp())
        row += " - [{0}](https://classic.wowhead.com/item={1})".format(loot_entry.item_name(),
                                      loot_entry.item_id())
        if player:
            row += " - "
            row += "{0}".format(loot_entry.player().name())
        row += "\n"
        return row
    return "- No data available -"

@for_all_methods(trace, trace_func_only)
class SinglePlayerProfile(BaseResponse):

    def build(self, info, thumbnail=None):
        self._embed.clear()

        self._embed.build(
            author_name=self._title,
            title=info.player().name(),
            description="Alt of **{0}**".format(info.main().name()) if info.is_alt() else "Main",
            thumbnail_url=get_thumbnail(),
            color=get_epgp_color(),
            footer_text=self._get_footer()
        )

        self._embed.add_field("Effort Points:", "`{0:.0f} EP`".format(info.ep()), True)
        self._embed.add_field("Gear Points:", "`{0:.0f} GP`".format(info.gp()), True)
        self._embed.add_field("Priority:", "`{0:.2f} PR`".format(info.pr()), True)
        history = info.get_latest_history_entry()
        self._embed.add_field("Last EP award:",
                              generate_epgp_history_entry(history, get_history_format_string(
                                0 if history is None else history.ep_width(),
                                0 if history is None else history.gp_width(),
                                True), False, False), False)
        loot = info.get_latest_loot_entry()
        self._embed.add_field("Last received loot:",
                              generate_loot_entry(loot, get_loot_format_string(
                                0 if loot is None else loot.width(), 
                                True), False, False, False), False)
        alts = info.alts()
        if isinstance(alts, list) and len(alts) > 0:
            self._embed.add_field("Alts:", "\n".join(["`{0}`".format(a.name()) for a in alts]), False)

        return self

    def get(self):
        return self._embed.get()

class EPGPMultipleResponse(MultipleResponse):

    def _prepare(self, data_list):

        self._enable_filtering = True

        # Prepare format string
        def get_ep(i):
            return i.ep()

        def get_gp(i):
            return i.gp()

        def get_pr(i):
            return i.pr()

        data_list.sort(key=get_pr, reverse=True)

        data_list_ep_min = min(data_list, key=get_ep)
        data_list_ep_max = max(data_list, key=get_ep)
        data_list_gp_min = min(data_list, key=get_gp)
        data_list_gp_max = max(data_list, key=get_gp)
        data_list_pr_min = min(data_list, key=get_pr)
        data_list_pr_max = max(data_list, key=get_pr)

        ep_width = max(len(str(int(data_list_ep_min.ep()))), len(str(int(data_list_ep_max.ep()))))
        gp_width = max(len(str(int(data_list_gp_min.gp()))), len(str(int(data_list_gp_max.gp()))))
        pr_width = max(len(str(int(data_list_pr_min.pr()))), len(str(int(data_list_pr_max.pr()))))

        self._value_format_string = get_points_format_string(ep_width, gp_width, pr_width, self._value_suffix)

    def _display_filter(self, data):
        if data and isinstance(data, PlayerInfoEPGP):
            return data.is_active()

        return False

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerInfoEPGP):
            # if self._enable_icons:
            #     row = "{0}".format(get_class_icon_string(data.ingame_class(), data.role().spec_id()))
            # else:
            row = ""
            if self._alternative_display_mode:
                if requester == data.player().name():
                    row += "**{0}**".format(data.player().name())
                else:
                    row += "{0}".format(data.player().name())
                row += "\n"
                row += self._value_format_string.format(data.ep(), data.gp(), data.pr())
            else:
                row += self._value_format_string.format(data.ep(), data.gp(), data.pr())
                row += " "
                if requester == data.player().name():
                    row += "**{0}**".format(data.player().name())
                else:
                    row += "{0}".format(data.player().name())
            row += "\n"
            return row

        return ""

@for_all_methods(trace, trace_func_only)
class HistoryMultipleResponse(MultipleResponse):

    def _prepare(self, data_list):
        # Prepare format string
        def get_ep(i):
            return i.ep()

        def get_gp(i):
            return i.gp()

        data_list_ep_min = min(data_list, key=get_ep)
        data_list_ep_max = max(data_list, key=get_ep)
        data_list_gp_min = min(data_list, key=get_gp)
        data_list_gp_max = max(data_list, key=get_gp)
        
        ep_width = max(len(str(int(data_list_ep_min.ep()))), len(str(int(data_list_ep_max.ep()))))
        gp_width = max(len(str(int(data_list_gp_min.gp()))), len(str(int(data_list_gp_max.gp()))))
        
        self._value_format_string = get_history_format_string(ep_width, gp_width, self._value_suffix)

        for data in data_list:
            if data and isinstance(data, PlayerEPGPHistory):
                self.__user = data.player().name()
                break

    #def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        if field_id == 0:
            self._embed.edit_field(field_id, self.__user)
        else:
            self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerEPGPHistory):
            return generate_epgp_history_entry(data, self._value_format_string, self._enable_icons, self._alternative_display_mode)

        return ""

@for_all_methods(trace, trace_func_only)
class PlayerLootMultipleResponse(MultipleResponse):

    def _prepare(self, data_list):
        # Prepare format string
        def get_gp(i):
            return i.gp()

        data_list_min = min(data_list, key=get_gp)
        data_list_max = max(data_list, key=get_gp)
        
        gp_width = max(len(str(int(data_list_min.gp()))),
                          len(str(int(data_list_max.gp()))))
        self._value_format_string = get_loot_format_string(gp_width, self._value_suffix)

        for data in data_list:
            if data and isinstance(data, PlayerLootEPGP):
                self.__user = data.player().name()
                break

    #def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        if field_id == 0:
            self._embed.edit_field(field_id, self.__user)
        else:
            self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerLootEPGP):
            return generate_loot_entry(data, self._value_format_string, self._enable_icons, self._alternative_display_mode, False)

        return ""

@for_all_methods(trace, trace_func_only)
class LootMultipleResponse(MultipleResponse):

    def _prepare(self, data_list):
        # Prepare format string
        def get_gp(i):
            return i.gp()

        data_list_min = min(data_list, key=get_gp)
        data_list_max = max(data_list, key=get_gp)
        
        gp_width = max(len(str(int(data_list_min.gp()))),
                          len(str(int(data_list_max.gp()))))
        self._value_format_string = get_loot_format_string(gp_width, self._value_suffix)

        for data in data_list:
            if data and isinstance(data, PlayerLootEPGP):
                self.__user = data.player().name()
                break

    #def _override_response_loop(self, response_id):
    #    self._embed.set_title(self.__user)

    def _override_field_loop(self, response_id, field_id):
        self._embed.edit_field(field_id, name="\u200b")

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerLootEPGP):
            return generate_loot_entry(data, self._value_format_string, self._enable_icons, self._alternative_display_mode, True)

        return ""