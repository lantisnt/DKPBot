class PlayerInfo:
    __player = ""
    __dkp = 0
    __lifetime_gained = 0
    __lifetime_spent = 0
    __ingame_class = ""
    __role = ""
    __latest_history_entry = None
    # __lastLoot = None

    def __init__(self, player, dkp, lifetime_gained, lifetime_spent, ingame_class, role):
        self.__player = str(player).lower().capitalize()
        self.__dkp = float(dkp)
        self.__lifetime_gained = abs(float(lifetime_gained))
        self.__lifetime_spent = abs(float(lifetime_spent))
        self.__ingame_class = str(ingame_class).lower().capitalize()
        self.__role = str(role).lower().capitalize()

    def Player(self):
        return self.__player

    def Dkp(self):
        return self.__dkp

    def LifetimeGained(self):
        return self.__lifetime_gained

    def LifetimeSpent(self):
        return self.__lifetime_spent

    def Class(self):
        return self.__ingame_class

    def Role(self):
        return self.__role

    def SetLatestHistoryEntry(self, history_entry):
        if history_entry and isinstance(history_entry, PlayerDKPHistory):
            self.__latest_history_entry = history_entry

    def GetLatestHistoryEntry(self):
        return self.__latest_history_entry

    def __str__(self):
        return "{0} ({1}) {2} ({3}/{4}) DKP".format(self.Player(), self.Class(), self.Dkp(), self.LifetimeGained(), self.LifetimeSpent())

    ### Overriding comparison to use DKP ###

    def __eq__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.Dkp()
        return self.Dkp() == other

    def __neq__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.Dkp()
        return self.Dkp() != other

    def __lt__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.Dkp()
        return self.Dkp() < other

    def __le__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.Dkp()
        return self.Dkp() <= other

    def __gt__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.Dkp()
        return self.Dkp() > other

    def __ge__(self, other):
        if isinstance(other, PlayerInfo):
            other = other.Dkp()
        return self.Dkp() >= other


class PlayerLoot:
    __player = ""
    __item_id = 0
    __item_name = ""
    __dkp = 0
    __timestamp = 0

    def __init__(self, player, item_id, item_name, dkp, timestamp):
        self.__player = str(player).lower().capitalize()
        self.__item_id = int(item_id)
        self.__item_name = str(item_name)
        self.__dkp = float(abs(dkp))
        self.__timestamp = int(timestamp)

    def Player(self):
        return self.__player

    def ItemId(self):
        return self.__item_id

    def ItemName(self):
        return self.__item_name

    def Dkp(self):
        return self.__dkp

    def Timestamp(self):
        return self.__timestamp

    def __str__(self):
        return "{0}: {1} {2}({3}) for {4} DKP".format(self.Timestamp(), self.Player(), self.ItemName(), self.ItemId(), self.Dkp())


class PlayerDKPHistory:
    __player = ""
    __dkp = 0
    __timestamp = ""
    __reason = ""
    __officer = ""

    def __init__(self, player, dkp, timestamp, reason, index):
        self.__player = str(player).lower().capitalize()
        self.__dkp = float(dkp)
        self.__timestamp = int(timestamp)
        self.__reason = str(reason)
        officer = str(index.split("-")[0])
        self.__officer = officer.lower().capitalize()

    def Player(self):
        return self.__player

    def Dkp(self):
        return self.__dkp

    def Timestamp(self):
        return self.__timestamp

    def Reason(self):
        return self.__reason

    def Officer(self):
        return self.__officer

    def __str__(self):
        return "{0}: {1} {2} DKP ({3}) by {4}".format(self.Timestamp(), self.Player(), self.Dkp(), self.Reason(), self.Officer())

    ### Overriding comparison to use Dkp ###

    # def __eq__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.Dkp()
    #     return self.Dkp() == other

    # def __neq__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.Dkp()
    #     return self.Dkp() != other

    # def __lt__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.Dkp()
    #     return self.Dkp() < other

    # def __le__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.Dkp()
    #     return self.Dkp() <= other

    # def __gt__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.Dkp()
    #     return self.Dkp() > other

    # def __ge__(self, other):
    #     if isinstance(other, PlayerDKPHistory):
    #         other = other.Dkp()
    #     return self.Dkp() >= other
