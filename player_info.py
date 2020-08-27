class PlayerInfo:
    __player = ""
    __dkp = 0
    __lifetime_gained = 0
    __ingame_class = ""
    __role = ""

    def __init__(self, player, dkp, lifetime_gained, ingame_class, role):
        self.__player = str(player).lower().capitalize()
        self.__dkp = float(dkp)
        self.__lifetime_gained = float(lifetime_gained)
        self.__ingame_class = str(ingame_class).lower().capitalize()
        self.__role = str(role).lower().capitalize()


    def Player(self):
        return self.__player
    
    def Dkp(self):
        return self.__dkp
    
    def LifetimeGained(self):
        return self.__lifetime_gained

    def Class(self):
        return self.__ingame_class

    def Role(self):
        return self.__role