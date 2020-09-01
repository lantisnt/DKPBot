class PlayerInfo:
    __player = ""
    __dkp = 0
    __lifetime_gained = 0
    __lifetime_spent = 0
    __ingame_class = ""
    __role = ""
    # __lastDkp = None
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


class PlayerDKPHistory:
    __player = 0
    __dkp = 0
    __timestamp = ""
    __reason = ""

    def __init__(self, player, dkp, timestamp, reason):
        self.__player = str(player).lower().capitalize()
        self.__dkp = float(dkp)
        self.__timestamp = int(timestamp)
        self.__reason = str(reason)

    def Player(self):
        return self.__player

    def Dkp(self):
        return self.__dkp

    def Timestamp(self):
        return self.__timestamp

    def Reason(self):
        return self.__reason

    ### Overriding comparison to use timestamp ###

    def __eq__(self, other):
        if isinstance(other, PlayerDKPHistory):
            other = other.Timestamp()
        return self.Timestamp() == other

    def __neq__(self, other):
        if isinstance(other, PlayerDKPHistory):
            other = other.Timestamp()
        return self.Timestamp() != other

    def __lt__(self, other):
        if isinstance(other, PlayerDKPHistory):
            other = other.Timestamp()
        return self.Timestamp() < other

    def __le__(self, other):
        if isinstance(other, PlayerDKPHistory):
            other = other.Timestamp()
        return self.Timestamp() <= other

    def __gt__(self, other):
        if isinstance(other, PlayerDKPHistory):
            other = other.Timestamp()
        return self.Timestamp() > other

    def __ge__(self, other):
        if isinstance(other, PlayerDKPHistory):
            other = other.Timestamp()
        return self.Timestamp() >= other



