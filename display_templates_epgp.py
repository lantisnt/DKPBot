from player_db_models import PlayerInfoEPGP, PlayerEPGPHistory, PlayerLootEPGP
from bot_utility import get_date_from_timestamp
from bot_config import DisplayConfig
from display_templates import BaseResponse, MultipleResponse
import build_info

INVITE = "[Invite Bot](http://wowdkpbot.com/invite)"
SUPPORT_SERVER = "[Support Server](http://{0})".format(build_info.SUPPORT_SERVER)
DONATE = "[Donate](http://wowdkpbot.com/donate)"
def get_bot_links():
    return INVITE + " | " + SUPPORT_SERVER + " | " + DONATE

def get_bot_color():
    return 10204605

def get_config_color():
    return 16553987

def get_epgp_color():
    return 10204605

def get_plus_minus_icon_string(plus=True):
    if plus:
        return "<:plus:782168773875728384>"
    else:
        return "<:minus:782168774035374080>"

def get_thumbnail():
    return "https://cdn.discordapp.com/attachments/765089790295015425/784450070945857626/CEPGP.png"

def preformatted_block(string: str, language='swift'):
    return "```" + language + "\n" + string + "```"

def get_points_format_string(rounding=1, enable_icons=True, value_suffix=True, alternative_display_mode=False):
    pass

def get_history_format_string(rounding=1, enable_icons=True, value_suffix=True, alternative_display_mode=False):
    pass

def get_loot_format_string(rounding=1, enable_icons=True, value_suffix=True, alternative_display_mode=False):
    pass

def generate_epgp_history_entry(history_entry, format_string=None, enable_icons=True, value_suffix=True, alternative_display_mode=False):
    if history_entry and isinstance(history_entry, PlayerEPGPHistory):
        if not format_string:
            format_string = "`{{0:{0}.0f}}{1} {{1:{2}.0f}}{3}`".format(
            len(str(int(history_entry.ep()))), " EP" if value_suffix else "",
            len(str(int(history_entry.gp()))), " GP" if value_suffix else "")
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

def generate_loot_entry(loot_entry, format_string=None, player=False, enable_icons=True, value_suffix=True):
    if loot_entry and isinstance(loot_entry, PlayerLootEPGP):
        if not format_string:
            format_string = "`{{0:{0}.0f}}{1}`".format(
            len(str(int(loot_entry.gp()))), " GP" if value_suffix else "")
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

class SinglePlayerProfile(BaseResponse):

    def build(self, info, thumbnail=None):
        self._embed.clear()

        self._embed.build(
            author_name=self._title,
            title=info.player().name(),
            description="",
            thumbnail_url=get_thumbnail(),
            color=get_epgp_color(),
            footer_text=self._get_footer()
        )

        self._embed.add_field("Effort Points:", "`{0:.0f} EP`".format(info.ep()), True)
        self._embed.add_field("Gear Points:", "`{0:.0f} GP`".format(info.gp()), True)
        self._embed.add_field("Priority:", "`{0:.2f} PR`".format(info.pr()), True)
        self._embed.add_field("Last EP award:",
                            generate_epgp_history_entry(info.get_latest_history_entry(), enable_icons=False, value_suffix=True), False)
        self._embed.add_field("Last received loot:",
                            generate_loot_entry(info.get_latest_loot_entry(), enable_icons=False, value_suffix=True), False)
        return self

    def get(self):
        return self._embed.get()

class MultipleResponse(MultipleResponse):

    def _prepare(self, data_list):
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

        if self._value_suffix:
            self._value_format_string = "`{{0:{0}.0f}}{1} {{1:{2}.0f}}{3} {{2:{4}.2f}}{5}`".format(
                ep_width, " EP" if self._value_suffix else "",
                gp_width, " GP" if self._value_suffix else "",
                pr_width, " PR" if self._value_suffix else "")
        else:
            self._value_format_string = "`{{0:{0}.0f}}/{{1:{1}.0f}} {{2:{2}.2f}}`".format(ep_width, gp_width, pr_width)

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
            row += self._value_format_string.format(data.ep(), data.gp(), data.pr())
            row += " "
            if requester == data.player().name():
                row += "**{0}**".format(data.player().name())
            else:
                row += "{0}".format(data.player().name())
            row += "\n"
            return row

        return ""

class HistoryMultipleResponse(MultipleResponse):

    __user = None

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
        
        self._value_format_string = "`{{0:{0}.0f}}{1} {{1:{2}.0f}}{3}`".format(
            ep_width, " EP" if self._value_suffix else "",
            gp_width, " GP" if self._value_suffix else "")

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
            return generate_epgp_history_entry(data, self._value_format_string, enable_icons=self._enable_icons, value_suffix=self._value_suffix)

        return ""

class PlayerLootMultipleResponse(MultipleResponse):

    __user = None

    def _prepare(self, data_list):
        # Prepare format string
        def get_gp(i):
            return i.gp()

        data_list_min = min(data_list, key=get_gp)
        data_list_max = max(data_list, key=get_gp)
        
        value_width = max(len(str(int(data_list_min.gp()))),
                          len(str(int(data_list_max.gp()))))
        self._value_format_string = "`{{0:{0}.0f}}{1}`".format(value_width, " GP" if self._value_suffix else "")

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
            return generate_loot_entry(data, self._value_format_string, enable_icons=self._enable_icons, value_suffix=self._value_suffix)

        return ""

class LootMultipleResponse(MultipleResponse):

    __user = None

    def _prepare(self, data_list):
        # Prepare format string
        def get_gp(i):
            return i.gp()

        data_list_min = min(data_list, key=get_gp)
        data_list_max = max(data_list, key=get_gp)
        
        value_width = max(len(str(int(data_list_min.gp()))),
                          len(str(int(data_list_max.gp()))))
        self._value_format_string = "`{{0:{0}.0f}}{1}`".format(value_width, " GP" if self._value_suffix else "")

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
            return generate_loot_entry(data, self._value_format_string, True, enable_icons=self._enable_icons, value_suffix=self._value_suffix)

        return ""