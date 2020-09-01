from datetime import datetime
import re

from dkp_bot import DKPBot, Response, ResponseStatus
from player_db_models import PlayerInfo, PlayerDKPHistory
from display_templates import SinglePlayerProfile, DKPMultipleResponse, HistoryMultipleResponse


class EssentialDKPBot(DKPBot):

    __DKP_SV = "MonDKP_DKPTable"
    __LOOT_SV = "MonDKP_Loot"
    __HISTORY_SV = "MonDKP_DKPHistory"
    __30_DAYS_SECONDS = 2592000

    __group_player_find = None

    __singleDkpOutputBuilder = None
    __multipleDkpOutputBuilder = None
    __multipleHistoryOutputBuilder = None

    def __init__(self, inputFileName="EssentialDKP.lua", channel=0, enabled=False, parser=None):
        super().__init__(inputFileName, channel, enabled, parser)
        # Matches either a,b,c,d or A / B or A \ B
        self.__group_player_find = re.compile("\s*([\d\w]*)[\s[\/\,]*")
        # Data outputs
        self.__singlePlayerProfileBuilder = SinglePlayerProfile(
            "Essential DKP Profile")

        self.__multipleDkpOutputBuilder = DKPMultipleResponse("DKP Values", 6, 16, True)
        self.__multipleHistoryOutputBuilder = HistoryMultipleResponse("Latest DKP History", 1, 10, False)
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

################################################
############### BUILD DKP OUTPUT ###############
################################################


    def __buildDKPOutputSingle(self, info):
        if not info or not isinstance(info, PlayerInfo):
            return None

        # TODO host the images
        thumbnail = "https://img.rankedboost.com/wp-content/uploads/2019/05/WoW-Classic-{0}-Guide.png".format(
            info.Class())
        return self.__singlePlayerProfileBuilder.Build(info, thumbnail).Get()

    def __buildDKPOutputMultiple(self, output_result_list, requester):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        if not requester:
            requester = ""

        return self.__multipleDkpOutputBuilder.Build(output_result_list, requester).Get()

####################################################
############### BUILD HISTORY OUTPUT ###############
####################################################


    def __buildHistoryOutputMultiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list):
            return None

        return self.__multipleHistoryOutputBuilder.Build(output_result_list).Get()
###

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
            # In case of unequal length we only add as many entries as there are players
            limit = min(len(players), len(dkp)) - 1
            for player in players:
                limit = limit - 1
                if limit <= 0:
                    break
                self._addHistory(player, PlayerDKPHistory(
                    player, float(dkp.pop()), timestamp, reason, index))

    # Called 1st
    def _buildDkpDatabase(self, sv):
        super()._buildDkpDatabase(None)

        dkp = sv.get(self.__DKP_SV)
        if not dkp:
            return

        if not isinstance(dkp, list):
            return

        # Ignore players not getting DKP in last 30 days TODO
        # if timestamp - updated > self.__30_DAYS_SECONDS: continue

        for entry in dkp:
            if not entry:
                return

            player = entry.get("player")
            if not player:
                continue

            dkp = entry.get("dkp")
            if not dkp:
                continue

            lifetime_gained = entry.get("lifetime_gained")
            if not lifetime_gained:
                continue

            lifetime_spent = entry.get("lifetime_spent")
            if not lifetime_spent:
                continue

            ingame_class = entry.get("class")
            if not ingame_class:
                continue

            role = entry.get("role")
            if not role:
                continue

            info = PlayerInfo(player, dkp, lifetime_gained,
                              lifetime_spent, ingame_class, role)
            self._setDkp(player, info)
            self._setGroupDkp(info.Class(), info)

        # Sort all class DKP
        self._sortGroupDkp()

    # Called 2nd
    def _buildLootDatabase(self, sv):
        super()._buildLootDatabase(None)

        loot = sv.get(self.__LOOT_SV)
        if not loot:
            return

        if not isinstance(loot, list):
            return

    # Called 3rd
    def _buildHistoryDatabase(self, sv):
        super()._buildHistoryDatabase(None)
        history = sv.get(self.__HISTORY_SV)
        if not history:
            return
        if not isinstance(history, dict):
            return  # dict because there is ["seed"] field...
        i = 1
        for entry in history.values():
            i = i + 1

            if not isinstance(entry, dict):
                continue

            players = entry.get("players")
            if not players:
                continue

            dkp = entry.get("dkp")
            if not dkp:
                continue

            date = entry.get("date")
            if not date:
                continue

            reason = entry.get("reason")
            if not reason:
                continue

            index = entry.get("index")
            if not index:
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
            elif not isinstance(dkp, int):
                continue

            self._fillHistory(players, dkp, date, reason, index)
            self._sortHistory()


    # Called after whole database is built
    def _finalizeDatabase(self):
        self._dbSetTime()
        self.__singlePlayerProfileBuilder.SetDbInfo(
            self._dbGetTime(), self._dbGetComment())
        self.__multipleDkpOutputBuilder.SetDbInfo(
            self._dbGetTime(), self._dbGetComment())
        self.__multipleHistoryOutputBuilder.SetDbInfo(
            self._dbGetTime(), self._dbGetComment())

    ### Essential related ###

    def __decodeAliases(self, groups):
        new_groups = groups.copy()
        for group in groups:
            if group == 'all':
                return ['warrior', 'druid', 'priest', 'paladin', 'shaman', 'rogue', 'hunter', 'mage', 'warlock']

            if group == 'tank':
                new_groups.extend(['warrior', 'druid'])

            elif group == 'healer':
                new_groups.extend(['priest', 'paladin', 'druid', 'shaman'])

            elif group == 'dps':
                new_groups.extend(
                    ['warrior', 'rogue', 'hunter', 'mage', 'warlock', 'shaman'])

            elif group == 'caster':
                new_groups.extend(['mage', 'warlock'])

            elif group == 'physical':
                new_groups.extend(['warrior', 'rogue', 'hunter', 'shaman'])

            elif group == 'range':
                new_groups.extend(['mage', 'warlock'])

            elif group == 'melee':
                new_groups.extend(['warrior', 'rogue', 'shaman'])

        return new_groups

    ### Commands ###

    def help_dkp(self, param, isPrivileged):
        help_string = 'EssentialDKP Bot allows access to dkp information.\n'
        help_string += 'Currently supported commands:\n'
        help_string += '**{0}**\n Display this help\n'.format("?dkp")
        help_string += '**{0}**\n Display current DKP for [player] or the submitter if not specified.\n'.format(
            "!dkp [player]")
        help_string += '**{0}**\n Display latest loot for [player] or the submitter if not specified.\n'.format(
            "!dkploot [player]")
        help_string += '**{0}**\n Display DKP history for [player] or the submitter if not specified.'.format(
            "!dkphistory [player]")
        if isPrivileged == True:
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
            output_result_list.sort(key=lambda info: info.Dkp(), reverse=False)
            data = self.__buildDKPOutputMultiple(output_result_list, requester_info.get('name'))
        else:
            data = "{0}'s DKP was not found in database.".format(
                param.capitalize())

        return Response(ResponseStatus.SUCCESS, data)

    def call_dkphistory(self, param, requester_info):
        # return Response(ResponseStatus.SUCCESS, "Sorry :frowning: !dkphistory is not yet implemented.")
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

    def call_dkploot(self, param, requester_info):
        return Response(ResponseStatus.SUCCESS, "Sorry {0} :frowning: !dkploot is not yet implemented.".format(str(requester_info.get('name'))))
