from datetime import datetime
import re

from dkp_bot import DKPBot, Response, ResponseStatus
from player_db_models import PlayerInfo, PlayerDKPHistory, PlayerLoot
from display_templates import SinglePlayerProfile, DKPMultipleResponse, HistoryMultipleResponse, PlayerLootMultipleResponse, LootMultipleResponse

class EssentialDKPBot(DKPBot):

    __DKP_SV = "MonDKP_DKPTable"
    __LOOT_SV = "MonDKP_Loot"
    __HISTORY_SV = "MonDKP_DKPHistory"
    __30_DAYS_SECONDS = 2592000

    __group_player_find = None
    __item_id_name_find = None

    __singleDkpOutputBuilder = None
    __multipleDkpOutputBuilder = None
    __multipleHistoryOutputBuilder = None
    __multiplePlayerLootOutputBuilder = None
    __multipleLootOutputBuilder = None

    def __init__(self, inputFileName="EssentialDKP.lua", channel=0, enabled=False, parser=None):
        super().__init__(inputFileName, channel, enabled, parser)
        # Matches either a,b,c,d or A / B or A \ B
        self.__group_player_find = re.compile("\s*([\d\w]*)[\s[\/\,]*")
        self.__item_id_name_find = re.compile("^[^:]*:*(\d*).*\[([^\]]*)")
        # Data outputs
        self.__singlePlayerProfileBuilder = SinglePlayerProfile(
            "Essential DKP Profile")

        self.__multipleDkpOutputBuilder = DKPMultipleResponse("DKP values", 6, 16, True, True)
        self.__multipleHistoryOutputBuilder = HistoryMultipleResponse("Latest DKP hstory", 1, 10, False, True)
        self.__multiplePlayerLootOutputBuilder = PlayerLootMultipleResponse("Latest loot history", 1, 10, False, True)
        self.__multipleLootOutputBuilder = LootMultipleResponse("Latest 30 items", 6, 5, False, False)
    ###

    def __getNamesFromParam(self, param):
        # Remove empty strings
        targets = list(filter(None, self.__group_player_find.findall(param)))
        # Decode aliases
        targets = self.__decodeAliases(targets)
        # Remove duplicates either from input or introduced by aliases
        targets = list(dict.fromkeys(targets))
        # Lowercase all
        return list(map(lambda x: x.strip().lower(), targets))

    def __buildDKPOutputSingle(self, info):
        if not info or not isinstance(info, PlayerInfo):
            return None

        # TODO host the images
        #thumbnail = "https://img.rankedboost.com/wp-content/uploads/2019/05/WoW-Classic-{0}-Guide.png".format(info.Class())
        return self.__singlePlayerProfileBuilder.Build(info, info.Class()).Get()

    def __buildDKPOutputMultiple(self, output_result_list, requester):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        if not requester:
            requester = ""

        return self.__multipleDkpOutputBuilder.Build(output_result_list, requester).Get()

    def __buildHistoryOutputMultiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self.__multipleHistoryOutputBuilder.Build(output_result_list).Get()

    def __buildPlayerLootOutputMultiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self.__multiplePlayerLootOutputBuilder.Build(output_result_list).Get()

    def __buildLootOutputMultiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self.__multipleLootOutputBuilder.Build(output_result_list).Get()

    ### Database - Variables parsing ###

    def _fillHistory(self, players, dkp, timestamp, reason, index):
        if not players:
            return

        if not dkp:
            return

        if isinstance(players, str) and isinstance(dkp, int):
            self._addHistory(players, PlayerDKPHistory(
                players, dkp, timestamp, reason, index))
        elif isinstance(players, list) and isinstance(dkp, int):
            for player in players:
                self._addHistory(player, PlayerDKPHistory(
                    player, dkp, timestamp, reason, index))
        elif isinstance(players, list) and isinstance(dkp, list):
            # Remove the % entry
            del players[-1]
            del dkp[-1]
            # In case of unequal length we only add as many entries as there are players
            for player in players:
                self._addHistory(player, PlayerDKPHistory(
                    player, float(dkp.pop(0)), timestamp, reason, index))

    # Called 1st
    def _buildDkpDatabase(self, sv):
        super()._buildDkpDatabase(None)

        dkp_list = sv.get(self.__DKP_SV)
        if not dkp_list:
            return

        if not isinstance(dkp_list, list):
            return

        # Ignore players not getting DKP in last 30 days TODO
        # if timestamp - updated > self.__30_DAYS_SECONDS: continue

        for entry in dkp_list:
            if entry == None:
                continue

            player = entry.get("player")
            if player == None:
                continue

            dkp = entry.get("dkp")
            if dkp == None:
                continue

            lifetime_gained = entry.get("lifetime_gained")
            if lifetime_gained == None:
                continue

            lifetime_spent = entry.get("lifetime_spent")
            if lifetime_spent == None:
                continue

            ingame_class = entry.get("class")
            if ingame_class == None:
                continue

            role = entry.get("role")
            if role == None:
                continue

            info = PlayerInfo(player, dkp, lifetime_gained,
                              lifetime_spent, ingame_class, role)
            self._setDkp(player, info)
            self._setGroupDkp(info.Class(), info)

        # Sort all class DKP
        #self._sortGroupDkp() # not sure if needed as we do a sort on each request due to mixins

    # Called 2nd
    def _buildLootDatabase(self, sv):
        super()._buildLootDatabase(None)

        loot_list = sv.get(self.__LOOT_SV)

        if not loot_list:
            return
        if not isinstance(loot_list, dict):
            return  # dict because there is ["seed"] field...

        for entry in loot_list.values():
            if entry == None:
                continue

            if not isinstance(entry, dict):
                continue

            player = entry.get("player")
            if player == None:
                continue

            player = self._getDkp(player)
            if player == None:
                continue
            
            cost = entry.get("cost")
            if cost == None:
                continue

            loot = entry.get("loot")
            if loot == None:
                continue

            date = entry.get("date")
            if date == None:
                continue

            ## Skip deletetion and deleted entries ##
            if entry.get("deletes") or entry.get("deletedby"):
                continue

            if not isinstance(loot, str):
                continue
            
            item_info = list(filter(None, self.__item_id_name_find.findall(loot))) #[0] -> id [1] -> name
            #print(item_info)
            if not item_info or not isinstance(item_info, list) or len(item_info) != 1:
                print("ERROR in entry: " + str(player.Player()) + " " + str(date) + " " + str(cost) + " " + str(loot))
                continue

            if not item_info[0] or not isinstance(item_info[0], tuple) or len(item_info[0]) != 2:
                print("ERROR in item_info[0] " + str(item_info[0]))
                continue

            player_loot =  PlayerLoot(player, item_info[0][0], item_info[0][1], cost, date)
            self._addLoot(player_loot)
            self._addPlayerLoot(player.Player(), player_loot)

        self._sortLoot()
        self._sortPlayerLoot()
        self._setPlayerLatestLoot()

    # Called 3rd
    def _buildHistoryDatabase(self, sv):
        super()._buildHistoryDatabase(None)
        history = sv.get(self.__HISTORY_SV)

        if not history:
            return
        if not isinstance(history, dict):
            return  # dict because there is ["seed"] field...

        for entry in history.values():
            if entry == None:
                continue

            if not isinstance(entry, dict):
                continue

            players = entry.get("players")
            if players == None:
                continue

            dkp = entry.get("dkp")
            if dkp == None:
                continue

            date = entry.get("date")
            if date == None:
                continue

            reason = entry.get("reason")
            if reason == None:
                continue

            index = entry.get("index")
            if index == None:
                continue

            ## Skip deletetion and deleted entries ##
            if entry.get("deletes") or entry.get("deletedby"):
                continue

            if not isinstance(players, str):
                continue
            if not isinstance(date, int):
                continue
            if not isinstance(reason, str):
                continue

            players = list(map(lambda p: p.lower(), players.split(",")))
            if not isinstance(players, list):
                continue

            if isinstance(dkp, str):
                # multiple entry
                dkp = list(map(lambda d: d, dkp.split(",")))
                if len(dkp) == 1: # Some weird old MonolithDKP -X% only entry that I have no idea how to parse
                    continue
            elif not isinstance(dkp, int):
                continue

            self._fillHistory(players, dkp, date, reason, index)

        self._sortHistory()
        self._setPlayerLatestPositiveHistory()


    # Called after whole database is built
    def _finalizeDatabase(self):
        self._dbSetTime()
        self.__singlePlayerProfileBuilder.SetDbInfo(
            self._dbGetTime(), self._dbGetComment())
        self.__multipleDkpOutputBuilder.SetDbInfo(
            self._dbGetTime(), self._dbGetComment())
        self.__multipleHistoryOutputBuilder.SetDbInfo(
            self._dbGetTime(), self._dbGetComment())
        self.__multiplePlayerLootOutputBuilder.SetDbInfo(
            self._dbGetTime(), self._dbGetComment())

        # TODO remove inactive

    ### Essential related ###

    def __decodeAliases(self, groups):
        new_groups = groups.copy()
        for group in groups:
            if group == 'all':
                return ['warrior', 'druid', 'priest', 'paladin', 'shaman', 'rogue', 'hunter', 'mage', 'warlock']

            if group == 'tank' or group == 'tanks':
                new_groups.extend(['warrior', 'druid'])

            elif group == 'healer' or group == 'healers':
                new_groups.extend(['priest', 'paladin', 'druid', 'shaman'])

            elif group == 'dps':
                new_groups.extend(
                    ['warrior', 'rogue', 'hunter', 'mage', 'warlock', 'shaman'])

            elif group == 'caster' or group == 'casters':
                new_groups.extend(['mage', 'warlock'])

            elif group == 'physical':
                new_groups.extend(['warrior', 'rogue', 'hunter', 'shaman'])

            elif group == 'range' or group == 'ranged':
                new_groups.extend(['mage', 'warlock'])

            elif group == 'melee':
                new_groups.extend(['warrior', 'rogue', 'shaman'])

        return new_groups

    ### Commands ###

    def help_dkp(self, param, requester_info):
        help_string = 'EssentialDKP Bot allows access to dkp information.\n'
        help_string += 'Currently supported commands:\n'
        help_string += '**{0}**\n Display this help\n'.format("?dkp")
        help_string += '**{0}**\n Display current DKP for [player] or the submitter if not specified.\n'.format(
            "!dkp [player]")
        help_string += '**{0}**\n Display current DKP for player, class or alias mixed together. Supported aliases: all, tanks, healers, dps, casters, physical, ranged, melee. Example: !dkp Shadowlifes,healers,mage\n'.format(
            "!dkp <class,alias,player>")
        help_string += '**{0}**\n Display latest loot for [player] or the submitter if not specified.\n'.format(
            "!loot [player]")
        help_string += '**{0}**\n Display DKP history for [player] or the submitter if not specified.'.format(
            "!history [player]")
        help_string += '**{0}**\n Display latest loot from raids.'.format(
            "!items")
        if requester_info['is_privileged'] == True:
            help_string += '\n\n'
            help_string += 'Administrator only options:\n'
            help_string += '**{0}**\n Register current channel as EssentialDKP.lua file source.\n'.format(
                "!dkpmanage register")
            help_string += '**{0}**\n Force reload data from newest EssentialDKP.lua file found in registered channel.'.format(
                "!dkpmanage reload")
        return Response(ResponseStatus.SUCCESS, help_string)

    def call_dkp(self, param, requester_info):
        if not self.IsDatabaseLoaded():
            return

        targets = self.__getNamesFromParam(param)
        output_result_list = []
        if len(targets) > 0:
            for target in targets:
                # Single player
                info = self._getDkp(target)
                if info and isinstance(info, PlayerInfo):
                    output_result_list.append(info)
                else:
                    # Group request
                    group_info = self._getGroupDkp(target)
                    if group_info and len(group_info) > 0:
                        for info in group_info:
                            if info and isinstance(info, PlayerInfo):
                                output_result_list.append(info)
        else:
            return Response(ResponseStatus.ERROR, "Unable to find data for {0}.".format(param))

        if len(output_result_list) == 1:
            data = self.__buildDKPOutputSingle(output_result_list[0])
        elif len(output_result_list) > 0:
            output_result_list.sort(key=lambda info: info.Dkp(), reverse=True)
            data = self.__buildDKPOutputMultiple(output_result_list, requester_info.get('name'))
        else:
            data = "{0}'s DKP was not found in database.".format(
                param.capitalize())

        return Response(ResponseStatus.SUCCESS, data)

    def call_history(self, param, requester_info):
        targets = self.__getNamesFromParam(param)
        output_result_list = []

        if len(targets) > 0:
            for target in targets:
                # Single player
                info = self._getHistory(target)
                if info and isinstance(info, list):
                    output_result_list = info
                    break  # Yes single only
        else:
            return Response(ResponseStatus.ERROR, "Unable to find data for {0}.".format(param))

        if len(output_result_list) > 0:
            data = self.__buildHistoryOutputMultiple(output_result_list)
        else:
            data = "{0}'s DKP history was not found in database.".format(
                param.capitalize())

        return Response(ResponseStatus.SUCCESS, data)

    def call_loot(self, param, requester_info):
        targets = self.__getNamesFromParam(param)
        output_result_list = []

        if len(targets) > 0:
            for target in targets:
                # Single player
                info = self._getPlayerLoot(target)
                if info and isinstance(info, list):
                    output_result_list = info
                    break  # Yes single only
        else:
            return Response(ResponseStatus.ERROR, "Unable to find data for {0}.".format(param))

        if len(output_result_list) > 0:
            data = self.__buildPlayerLootOutputMultiple(output_result_list)
        else:
            data = "{0}'s DKP loot was not found in database.".format(
                param.capitalize())

        return Response(ResponseStatus.SUCCESS, data)

    def call_items(self, param, requester_info):
        output_result_list = self._getLoot()

        if len(output_result_list) > 0:
            data = self.__buildLootOutputMultiple(output_result_list)
        else:
            data = "Unable to find data loot data."

        return Response(ResponseStatus.SUCCESS, data)

    ### Aliases ###

    def call_dkphistory(self, param, requester_info):
        return self.call_history(param, requester_info)

    def call_dkploot(self, param, requester_info):
        return self.call_loot(param, requester_info)

    def call_dkploothistory(self, param, requester_info):
        return self.call_items(param, requester_info)

    def call_item(self, param, requester_info):
        return self.call_items(param, requester_info)