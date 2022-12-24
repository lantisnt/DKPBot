# Copyright 2020-2023 Lantis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

# TODO update for WoTLK
class Role:
    __tank = False
    __dps = True  # So we won't filter at least in single group?
    __healer = False
    __ranged = False
    __caster = False
    __spec_id = -1

    def __init__(
        self,
        tank: bool,
        dps: bool,
        healer: bool,
        ranged: bool,
        caster: bool,
        spec_id: int = -1,
    ):
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
        if spec_id in [0, 1, 2]:
            self.__spec_id = spec_id

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

    def spec_id(self):
        return self.__spec_id

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


__role_re = re.compile("^.*?\(*(\d+)\/(\d+)\/(\d+)\)*.*")


def __get(class_name: str, talents: list):
    class_name = class_name.lower()

    if class_name in ["mage", "warlock"]:
        return Role(False, True, False, True, True, 0)

    if class_name == "rogue":
        return Role(False, True, False, False, False, 0)

    if class_name == "hunter":
        return Role(False, True, False, True, False, 0)

    # Warrior
    # (a/b/1+) - tank
    # everything else: dps
    if class_name == "warrior":
        if talents[2] > 0:
            return Role(True, False, False, False, False, 2)
        else:
            return Role(False, True, False, False, False, 0)

    # Druid:
    # (30+/a/b) - dps
    # (a/21+/b) - dps and tank
    # (a/b/21+) - healer
    # everything else: dps and tank
    if class_name == "druid":
        if talents[0] >= 30:
            return Role(False, True, False, True, True, 0)
        elif talents[1] >= 21:
            return Role(True, True, False, False, False, 1)
        elif talents[2] >= 21:
            return Role(False, False, True, True, True, 2)
        else:
            return Role(True, True, False, False, False)
    # Priest
    # (a/b/30+) - dps
    # everything else healer
    if class_name == "priest":
        if talents[2] >= 30:
            return Role(False, True, False, True, True, 2)
        else:
            return Role(False, False, True, True, True, 0)

    # Paladin:
    # (20+/a/b) - holy
    # (a/b/25+) - ret (dps)
    # (a/31+/b) - prot (tank)
    # everything else: holy
    if class_name == "paladin":
        if talents[0] >= 20:
            return Role(False, False, True, True, True, 0)
        elif talents[2] >= 25:
            return Role(False, True, False, False, False, 2)
        elif talents[1] >= 31:
            return Role(True, False, False, False, False, 1)
        else:
            return Role(True, True, True, True, True)

    # Shaman:
    # (31+/a/b) - dps ranged
    # (a/31+/b) - dps melee
    # (a/b/30+) - heal
    # everything else: dps and heal
    if class_name == "shaman":
        if talents[0] >= 31:
            return Role(False, True, False, True, True, 0)
        elif talents[1] >= 31:
            return Role(False, True, False, False, False, 1)
        elif talents[2] >= 30:
            return Role(False, False, True, True, True, 2)
        else:
            return Role(False, True, True, True, True)

    return Role(False, False, False, False, False)


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
                    if talent_value < 0 or talent_value > 61:
                        talent_value = 0
                except ValueError as exception:
                    talent_value = 0
                talents[t] = talent_value
    return __get(class_name, talents)


class RoleFilter:
    __dps = False
    __tank = False
    __healer = False
    __ranged = False
    __melee = False
    __caster = False
    __physical = False
    __aliases = []

    def __init__(self, aliases):
        self.__dps = "dps" in aliases
        self.__tank = "tank" in aliases or "tanks" in aliases
        self.__healer = "healer" in aliases or "healers" in aliases
        self.__caster = "caster" in aliases or "casters" in aliases
        self.__physical = "physical" in aliases
        self.__ranged = "range" in aliases or "ranged" in aliases
        self.__melee = "melee" in aliases
        self.__aliases = aliases

    def get_aliases(self):
        return self.__aliases

    def filter(self, player_info_list):
        dps_list = []
        tank_list = []
        healer_list = []
        ranged_list = []
        melee_list = []
        caster_list = []
        physical_list = []

        if self.__dps:
            dps_list = list(filter(lambda p: p.role().is_dps(), player_info_list))

        if self.__tank:
            tank_list = list(filter(lambda p: p.role().is_tank(), player_info_list))

        if self.__healer:
            healer_list = list(filter(lambda p: p.role().is_healer(), player_info_list))

        if self.__ranged:
            ranged_list = list(
                filter(
                    lambda p: p.role().is_dps() and p.role().is_ranged(),
                    player_info_list,
                )
            )

        if self.__melee:
            melee_list = list(
                filter(
                    lambda p: (p.role().is_dps() or p.role().is_tank())
                    and not p.role().is_ranged(),
                    player_info_list,
                )
            )

        if self.__caster:
            caster_list = list(
                filter(
                    lambda p: p.role().is_dps() and p.role().is_caster(),
                    player_info_list,
                )
            )

        if self.__physical:
            physical_list = list(
                filter(
                    lambda p: (p.role().is_dps() or p.role().is_tank())
                    and not p.role().is_caster(),
                    player_info_list,
                )
            )

        return (
            dps_list
            + tank_list
            + healer_list
            + ranged_list
            + melee_list
            + caster_list
            + physical_list
        )

    def __call__(self, player_info_list):
        return self.filter(player_info_list)