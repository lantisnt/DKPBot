from player_db_models import PlayerInfoEPGP, PlayerDKPHistory, PlayerLoot
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

def generate_dkp_history_entry(history_entry, format_string=None, rounding=1, enable_icons=True, value_suffix=True):
    if history_entry and isinstance(history_entry, PlayerDKPHistory):
        if not format_string:
            format_string = "`{{0:{0}.{1}f}}{2}`".format(
                len(str(int(history_entry.dkp()))), rounding, " DKP" if value_suffix else "")

        row = ""
        if enable_icons:
            row += get_plus_minus_icon_string(history_entry.dkp() > 0) + " "
        row += "`{0:16}` - ".format(get_date_from_timestamp(history_entry.timestamp()))
        row += format_string.format(history_entry.dkp())
        row += " - {0} _by {1}_".format(history_entry.reason(),
                                      history_entry.officer())
        row += "\n"
        return row
    return "- No data available -"

def generate_loot_entry(loot_entry, format_string=None, player=False, rounding=1, enable_icons=True, value_suffix=True):
    if loot_entry and isinstance(loot_entry, PlayerLoot):
        if not format_string:
            format_string = "`{{0:{0}.{1}f}}{2}`".format(
                len(str(int(loot_entry.dkp()))), rounding, " DKP" if value_suffix else "")
        row = ""
        row += "`{0:16}` - ".format(get_date_from_timestamp(loot_entry.timestamp()))
        row += format_string.format(loot_entry.dkp())
        row += " - [{0}](https://classic.wowhead.com/item={1})".format(loot_entry.item_name(),
                                      loot_entry.item_id())
        if player:
            row += " - "
            if enable_icons:
                row += "{0}".format(get_class_icon_string(loot_entry.player().ingame_class(), loot_entry.player().role().spec_id()))
            row += "{0}".format(loot_entry.player().name())
        row += "\n"
        return row
    return "- No data available -"

class SinglePlayerProfile(BaseResponse):

    def build(self, info, thumbnail=None):
        self._embed.clear()
        print("in build")
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
        #self._embed.add_field("Last DKP award:",
        #                     generate_dkp_history_entry(info.get_latest_history_entry(), rounding=self._rounding, enable_icons=False, value_suffix=True), False)
        #self._embed.add_field("Last received loot:",
        #                     generate_loot_entry(info.get_latest_loot_entry(), rounding=self._rounding, enable_icons=False, value_suffix=True), False)
        print(self.get())
        return self

    def get(self):
        return self._embed.get()

class EPGPMultipleResponse(MultipleResponse):

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

        self._value_format_string = "`{{0:{0}.0f}}{1}` - `{{1:{2}.0f}}{3}`".format(
            ep_width, " EP" if self._value_suffix else "",
            gp_width, " GP" if self._value_suffix else "")

    # def _display_filter(self, data):
    #     if data and isinstance(data, PlayerInfo):
    #         return data.is_active()

    #     return False

    def _build_row(self, data, requester):
        if data and isinstance(data, PlayerInfoEPGP):
            # if self._enable_icons:
            #     row = "{0}".format(get_class_icon_string(data.ingame_class(), data.role().spec_id()))
            # else:
            row = ""
            row += self._value_format_string.format(data.ep(), data.gp())
            row += " "
            if requester == data.player().name():
                row += "**{0}**".format(data.player().name())
            else:
                row += "{0}".format(data.player().name())
            row += "\n"
            return row

        return ""