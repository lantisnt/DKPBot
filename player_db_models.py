import player_role
from player_role import Role

class PlayerInfo:
    __player = ""
    __dkp = 0
    __lifetime_gained = 0
    __lifetime_spent = 0
    __ingame_class = ""
    __smart_role = None
    _latest_loot_entry = None
    _latest_history_entry = None
    __active = True

    def __init__(self, player, dkp, lifetime_gained, lifetime_spent, ingame_class, role, spec):
        self.__player = str(player).lower().capitalize()
        self.__dkp = float(dkp)
        self.__lifetime_gained = abs(float(lifetime_gained))
        self.__lifetime_spent = abs(float(lifetime_spent))
        self.__ingame_class = str(ingame_class).lower().capitalize()
        if ingame_class is None or spec is None:
            self.__smart_role = Role(True, True, True, True, True, 0)
        else:
            self.__smart_role = player_role.get(ingame_class, spec)

    def name(self):
        return self.__player

    def player(self):
        return self

    def dkp(self):
        return self.__dkp

    def lifetime_gained(self):
        return self.__lifetime_gained

    def lifetime_spent(self):
        return self.__lifetime_spent

    def ingame_class(self):
        return self.__ingame_class

    def role(self):
        return self.__smart_role

    def set_inactive(self):
        self.__active = False

    def set_active(self):
        self.__active = True

    def is_active(self):
        return self.__active

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

    def __str__(self):
        return "{0} ({1} - {6}) {2} ({3}/{4}) DKP | Active: {5}\n".format(self.name(), self.ingame_class(), self.dkp(), self.lifetime_gained(), self.lifetime_spent(), self.__active, self.__smart_role)

    def __repr__(self):
        return self.__str__()

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

class PlayerInfoEPGP(PlayerInfo):

    def __init__(self, player, ep, gp):
         super().__init__(player, ep, gp, 0, None, None, None)

    def ep(self):
        return self.dkp()

    def gp(self):
        return self.lifetime_gained()

    def pr(self):
        if self.gp() == 0:
            return 0
        else:
            return self.ep()/self.gp()

    def set_latest_loot_entry(self, loot_entry):
        if loot_entry and isinstance(loot_entry, PlayerLootEPGP):
            self._latest_loot_entry = loot_entry

    def set_latest_history_entry(self, history_entry):
        if history_entry and isinstance(history_entry, PlayerEPGPHistory):
            self._latest_history_entry = history_entry
    def __str__(self):
        return "{0}: {1} EP {2} GP\n".format(self.name(), self.ep(), self.gp())

class PlayerLoot:
    __player = ""
    __item_id = 0
    __item_name = ""
    __dkp = 0
    __timestamp = 0

    def __init__(self, player, item_id, item_name, dkp, timestamp):
        if not isinstance(player, (PlayerInfo, PlayerInfoEPGP)): #Workaround as we expect player to be connected to the Player
           player = PlayerInfo(str(player), 0, -1, -1, "UNKNOWN", "UNKNOWN", None)
        self.__player = player
        self.__item_id = int(item_id)
        self.__item_name = str(item_name)
        self.__dkp = float(abs(dkp))
        self.__timestamp = int(timestamp)

    def player(self):
        return self.__player

    def item_id(self):
        return self.__item_id

    def item_name(self):
        return self.__item_name

    def dkp(self):
        return self.__dkp

    def timestamp(self):
        return self.__timestamp

    def __str__(self):
        return "{0}: {1} {2}({3}) for {4} DKP".format(self.timestamp(), self.player().name(), self.item_name(), self.item_id(), self.dkp())

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(str(self))

class PlayerLootEPGP(PlayerLoot):
    
    def gp(self):
        return self.dkp()

class PlayerDKPHistory:
    __player = ""
    __dkp = 0
    __timestamp = ""
    __reason = ""
    __officer = ""

    def __init__(self, player, dkp, timestamp, reason, index):
        if not isinstance(player, (PlayerInfo, PlayerInfoEPGP)): #Workaround as we expect player to be connected to the Player DKP
            player = PlayerInfo(str(player), 0, -1, -1, "UNKNOWN", "UNKNOWN", None)
        self.__player = player
        self.__dkp = float(dkp)
        self.__timestamp = int(timestamp)
        self.__reason = str(reason)
        officer = str(index.split("-")[0])
        self.__officer = officer.lower().capitalize()

    def player(self):
        return self.__player

    def dkp(self):
        return self.__dkp

    def timestamp(self):
        return self.__timestamp

    def reason(self):
        return self.__reason

    def officer(self):
        return self.__officer

    def __str__(self):
        return "{0}: {1} {2} DKP ({3}) by {4}".format(self.timestamp(), self.player().name(), self.dkp(), self.reason(), self.officer())

    def __repr__(self):
        return self.__str__()

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


class PlayerEPGPHistory(PlayerDKPHistory):
    def __init__(self, player, ep, gp, is_percentage, timestamp, reason, officer):
        super().__init__(player, ep, timestamp, reason, officer)
        self.__gp = float(gp)
        self.__is_percentage = bool(is_percentage)

    def ep(self):
        return self.dkp()

    def gp(self):
        return self.__gp

    def is_percentage(self):
        return is_percentage
