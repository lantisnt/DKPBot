import player_role
from player_role import Role
from bot_logger import trace, trace_func_only, for_all_methods
from bot_utility import get_width

@for_all_methods(trace, trace_func_only)
class PlayerInfoLC:
    def __init__(
        self, player, ingame_class, role, spec
    ):
        self._player = str(player).lower().capitalize()
        self._ingame_class = str(ingame_class).lower().capitalize()
        if ingame_class is None or spec is None:
            self._smart_role = Role(True, True, True, True, True, 0)
        else:
            self._smart_role = player_role.get(ingame_class, spec)
        self._active = True
        self._latest_loot_entry = None

    def name(self):
        return self._player

    def player(self):
        return self

    def ingame_class(self):
        return self._ingame_class

    def role(self):
        return self._smart_role

    def set_inactive(self):
        self._active = False

    def set_active(self):
        self._active = True

    def is_active(self):
        return self._active

    def set_latest_loot_entry(self, loot_entry):
        if loot_entry and isinstance(loot_entry, list):
            self._latest_loot_entry = loot_entry

    def get_latest_loot_entry(self):
        return self._latest_loot_entry

    def __str__(self):
        return "{0} {1} {3} | Active: {2}".format(
            self._player,
            self._ingame_class,
            self._active,
            self._smart_role,
        )

    __repr__ = __str__

    def __hash__(self):
        return hash(str(self))

@for_all_methods(trace, trace_func_only)
class PlayerInfo(PlayerInfoLC):
    def __init__(
        self, player, dkp, lifetime_gained, lifetime_spent, ingame_class, role, spec
    ):
        super().__init__(player, ingame_class, role,spec)
        self._dkp = float(dkp)
        self._lifetime_gained = abs(float(lifetime_gained))
        self._lifetime_spent = abs(float(lifetime_spent))
        self._latest_history_entry = None

    def dkp(self):
        return self._dkp

    def lifetime_gained(self):
        return self._lifetime_gained

    def lifetime_spent(self):
        return self._lifetime_spent

    def ingame_class(self):
        return self._ingame_class

    def set_latest_loot_entry(self, loot_entry):
        if loot_entry and isinstance(loot_entry, PlayerLoot):
            self._latest_loot_entry = loot_entry

    def get_latest_loot_entry(self):
        return self._latest_loot_entry

    def set_latest_history_entry(self, history_entry):
        if history_entry and isinstance(history_entry, PlayerDKPHistory):
            self._latest_history_entry = history_entry

    def get_latest_history_entry(self):
        return self._latest_history_entry

    def width(self):
        return get_width(self.dkp())

    def __str__(self):
        return "{0} ({1} - {6}) {2} ({3}/{4}) DKP | Active: {5}".format(
            self._player,
            self._ingame_class,
            self._dkp,
            self._lifetime_gained,
            self._lifetime_spent,
            self._active,
            self._smart_role,
        )

    __repr__ = __str__

    def __hash__(self):
        return hash(str(self))

    ### Overriding comparison to use DKP ###

    def __eq__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.dkp()
        return self.dkp() == other

    def __neq__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.dkp()
        return self.dkp() != other

    def __lt__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.dkp()
        return self.dkp() < other

    def __le__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.dkp()
        return self.dkp() <= other

    def __gt__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.dkp()
        return self.dkp() > other

    def __ge__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.dkp()
        return self.dkp() >= other


@for_all_methods(trace, trace_func_only)
class PlayerInfoEPGP(PlayerInfo):
    def __init__(self, player, ep, gp):
        super().__init__(player, ep, gp, 0 if gp == 0 else ep / gp, None, None, None)
        self._alts = []
        self._main = None

    def ep(self):
        return self.dkp()

    def gp(self):
        return self.lifetime_gained()

    def pr(self):
        return self.lifetime_spent()

    def alts(self):
        return self._alts

    def main(self):
        return self._main

    def is_alt(self):
        return self._main is not None

    def ep_width(self):
        return get_width(self.ep())

    def gp_width(self):
        return get_width(self.gp())

    def pr_width(self):
        return get_width(self.pr())

    def set_latest_loot_entry(self, loot_entry):
        if loot_entry and isinstance(loot_entry, PlayerLootEPGP):
            self._latest_loot_entry = loot_entry

    def set_latest_history_entry(self, history_entry):
        if history_entry and isinstance(history_entry, PlayerEPGPHistory):
            self._latest_history_entry = history_entry

    def set_main(self, main):
        self._main = main

    def link_alts(self, alt_list):
        if isinstance(alt_list, list):
            for alt in alt_list:
                if not isinstance(alt, PlayerInfoEPGP):
                    self._alts.append(
                        PlayerInfoEPGP(alt, 0, 0)
                    )  # Create dummy object for not existing alts
                else:
                    self._alts.append(alt)

    def __str__(self):
        if self._main is None:
            return "{0}: {1} EP {2} GP {3} PR Alts: {4}".format(
                self._name,
                self._dkp,
                self._lifetime_gained,
                self._lifetime_spent,
                str(self._alts),
            )
        else:
            return "{0}: {1} EP {2} GP {3} PR Alt of {4}".format(
                self._name,
                self._dkp,
                self._lifetime_gained,
                self._lifetime_spent,
                self._main.name(),
            )


@for_all_methods(trace, trace_func_only)
class PlayerLootLC:
    def __init__(self, player, item_id, item_name, timestamp):
        if not isinstance(
            player, (PlayerInfo, PlayerInfoEPGP, PlayerInfoLC)
        ):  # Workaround as we expect player to be connected to the Player
            player = PlayerInfo(str(player), 0, -1, -1, "UNKNOWN", "UNKNOWN", None)
        self._player = player
        self._item_id = int(item_id)
        self._item_name = str(item_name)
        self._timestamp = int(timestamp)

    def player(self):
        return self._player

    def item_id(self):
        return self._item_id

    def item_name(self):
        return self._item_name

    def timestamp(self):
        return self._timestamp

    def width(self):
        return get_width(self.dkp())

    def __str__(self):
        return "{0}: {1} {2}({3})".format(
            self._timestamp,
            self._player.name(),
            self._item_name,
            self._item_id
        )

    __repr__ = __str__

    def __hash__(self):
        return hash(str(self))

@for_all_methods(trace, trace_func_only)
class PlayerLoot(PlayerLootLC):
    def __init__(self, player, item_id, item_name, dkp, timestamp):
        super().__init__(player, item_id, item_name, timestamp)

        self._dkp = float(abs(dkp))

    def dkp(self):
        return self._dkp

    def __str__(self):
        return "{0}: {1} {2}({3}) for {4} DKP".format(
            self._timestamp,
            self._player.name(),
            self._item_name,
            self._item_id,
            self._dkp,
        )

    __repr__ = __str__

    def __hash__(self):
        return hash(str(self))


@for_all_methods(trace, trace_func_only)
class PlayerLootEPGP(PlayerLoot):
    def gp(self):
        return self.dkp()

    def __str__(self):
        return "{0}: {1} {2}({3}) for {4} GP".format(
            self._timestamp,
            self._player.name(),
            self._item_name,
            self._item_id,
            self._dkp,
        )


# @for_all_methods(trace, trace_func_only)
class PlayerDKPHistory:
    def __init__(self, player, dkp, timestamp, reason, index):
        if not isinstance(
            player, (PlayerInfo, PlayerInfoEPGP)
        ):  # Workaround as we expect player to be connected to the Player DKP
            player = PlayerInfo(str(player), 0, -1, -1, "UNKNOWN", "UNKNOWN", None)
        self._player = player
        self._dkp = float(dkp)
        self._timestamp = int(timestamp)
        self._reason = str(reason)
        officer = str(index.split("-")[0])
        self._officer = officer.lower().capitalize()

    def player(self):
        return self._player

    def dkp(self):
        return self._dkp

    def timestamp(self):
        return self._timestamp

    def reason(self):
        return self._reason

    def officer(self):
        return self._officer

    def width(self):
        return get_width(self.dkp())

    def __str__(self):
        return "{0}: {1} {2} DKP ({3}) by {4}".format(
            self._timestamp, self._player.name(), self._dkp, self._reason, self._officer
        )

    __repr__ = __str__

    def __hash__(self):
        return hash(str(self))

    ### Overriding comparison to use dkp ###

    # def __eq__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.dkp()
    #     return self.dkp() == other

    # def __neq__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.dkp()
    #     return self.dkp() != other

    # def __lt__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.dkp()
    #     return self.dkp() < other

    # def __le__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.dkp()
    #     return self.dkp() <= other

    # def __gt__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.dkp()
    #     return self.dkp() > other

    # def __ge__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.dkp()
    #     return self.dkp() >= other


@for_all_methods(trace, trace_func_only)
class PlayerEPGPHistory(PlayerDKPHistory):
    def __init__(self, player, ep, gp, is_percentage, timestamp, reason, officer):
        super().__init__(player, ep, timestamp, reason, officer)
        self._gp = float(gp)
        self._is_percentage = bool(is_percentage)

    def ep(self):
        return self.dkp()

    def gp(self):
        return self._gp

    def ep_width(self):
        return get_width(self.ep())

    def gp_width(self):
        return get_width(self.gp())

    def is_percentage(self):
        return is_percentage

    def __str__(self):
        return "{0}: {1} {2} EP {3} GP ({4}) by {5}".format(
            self._timestamp,
            self._player.name(),
            self._dkp,
            self._gp,
            self._reason,
            self._officer,
        )
