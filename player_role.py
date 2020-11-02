import re

class Role:
    __dps = True # So we won't filter at least in single group?
    __tank = False
    __healer = False
    __ranged = False
    __caster = False

    def __init__(self, tank: bool, dps: bool, healer: bool, ranged: bool, caster: bool):
        if isinstance(tank, bool):
            self.__tank = tank
        if isinstance(dps, bool):
            self.__dps = dps
        if isinstance(healer, bool):
            self.__healer = healer
        if isinstance(ranged, bool):
            self.__ranged = ranged
        if isinstance(caster, bool):
            self.__caster = caster

    def is_tank(self):
        return self.__tank

    def is_dps(self):
        return self.__dps

    def is_healer(self):
        return self.__healer

    def is_ranged(self):
        return self.__ranged

    def is_caster(self):
        return self.__caster

    def __repr__(self):
        return str(self)

    def __str__(self):
        string = ""
        if self.__healer:
            return "Healer"

        if self.__tank:
            if self.__dps:
                return "Hybrid DPS Tank"
            else:
                return "Tank"

        if self.__caster:
                string += "Caster "
        else:
            string += "Physical "
        
        if self.__ranged:
            string += "ranged "
        else:
            string += "melee "
        string += "DPS"

        return string


__role_re = re.compile("^.*\((\d+)\/(\d+)\/(\d+)\).*")
def __get(class_name: str, talents: list):
    class_name = class_name.lower()
    print(class_name, talents)
    if class_name in ['mage', 'warlock']:
        return Role(False, True, False, True, True)

    if class_name == 'rogue':
        return Role(False, True, False, False, False)

    if class_name  == 'hunter':
        return Role(False, True, False, True, False)

    # Warrior
    # (a/b/1+) - tank
    # everything else: dps
    if class_name == 'warrior':
        if talents[2] > 0:
            return Role(True, False, False, False, False)
        else:
            return Role(False, True, False, False, False)

    # Druid:
    # (30+/a/b) - dps
    # (a/21+/b) - dps and tank
    # (a/b/21+) - healer
    # everything else: dps and tank
    if class_name == 'druid':
        if talents[0] >= 30:
            return Role(False, True, False, True, True)
        elif talents[1] >= 21:
            return Role(True, True, False, False, False)
        elif talents[2] >= 21:
            return Role(False, False, True, True, True)
        else:
            return Role(True, True, False, False, False)
    # Priest
    # (a/b/30+) - dps
    # everything else healer
    if class_name == 'priest':
        if talents[2] >= 30:
            return Role(False, True, False, True, True)
        else:
            return Role(False, False, True, True, True)

    # Paladin:
    # (20+/a/b) - holy
    # (a/b/25+) - ret (dps)
    # (a/31+/b) - prot (tank)
    # everything else: holy
    if class_name == 'paladin':
        if talents[0] >= 20:
            return Role(False, False, True, True, True)
        elif talents[2] >= 25:
            return Role(False, True, False, False, False)
        elif talents[1] >= 31:
            return Role(True, False, False, False, False)
        else:
            return Role(False, False, True, True, True)

    # Shaman:
    # (31+/a/b) - dps ranged
    # (a/31+/b) - dps melee
    # (a/b/30+) - heal
    # everything else: dps and heal
    if class_name == 'shaman':
        if talents[0] >= 31:
            return Role(False, True, False, True, True)
        elif talents[1] >= 31:
            return Role(False, True, False, False, False)
        elif talents[2] >= 30:
            return Role(False, False, True, True, True)
        else:
            return Role(False, False, True, True, True)

    return Role.DPS


def get(class_name: str, role_string: str):
    talents = [0, 0, 0]
    match = __role_re.match(role_string)
    if match is not None:
        detected_talents = match.groups()
        if len(talents) > 0:
            for t in range(0, len(talents)):
                talent_value = 0
                try:
                    talent_value = int(detected_talents[t])
                    if talent_value < 0 or talent_value > 51:
                        talent_value = 0
                except ValueError as exception:
                    talent_value = 0
                talents[t] = talent_value
    return __get(class_name, talents)
    
