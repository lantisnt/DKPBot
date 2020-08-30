from datetime import datetime
import re

from dkp_bot import DKPBot, Response, ResponseStatus
from player_db_models import PlayerInfo, PlayerDKPHistory

class EssentialDKPBot(DKPBot):

    __DKP_SV = "MonDKP_DKPTable"
    __LOOT_SV = "MonDKP_Loot"
    __HISTORY_SV = "MonDKP_DKPHistory"
    __30_DAYS_SECONDS = 2592000

    __group_player_find = None

    def __init__(self, inputFileName = "EssentialDKP.lua", channel = 0, enabled = False, parser = None):
        super().__init__(inputFileName, channel, enabled, parser)
        # Matches either a,b,c,d or A / B or A \ B
        self.__group_player_find = re.compile("\s*([\d\w]*)[\s[\/\,]*")

    ### 
    def __getNamesFromParam(self, param):
        # Remove empty strings
        targets = list(filter(None, self.__group_player_find.findall(param)))
        # Decode aliases
        targets = self.__decodeAliases(targets)
        # Remove duplicates either from input or introduced by aliases
        targets = list(dict.fromkeys(targets))
        # Lowercase all
        return list(map(lambda x:x.strip().lower(), targets))

    def __getIconString(self, c):
        if not c:
            return ""
        
        c = c.lower()

        if c == 'rogue':
            return "<:rogue:641645675045453824>"
        
        if c == 'warrior':
            return "<:warrior:641604892364111872>"

        if c == 'hunter':
            return "<:hunter:641604891969716225>"

        if c == 'druid':
            return "<:druid:641604891671920642>"

        if c == 'priest':
            return "<:priest:641604894154948638>"

        if c == 'paladin':
            return "<:paladin:641645675112693799>"

        if c == 'warlock':
            return "<:warlock:641604892171173928>"

        if c == 'mage':
            return "<:mage:641604891877310486>"

        return "<:essential:743883972206919790> "

    def __getClassColor(self, c):
        if not c:
            return 10204605
        
        c = c.lower()

        if c == 'rogue':
            return 16774505
        
        if c == 'warrior':
            return 13081710

        if c == 'hunter':
            return 11261043

        if c == 'druid':
            return 16743690

        if c == 'priest':
            return 16777215

        if c == 'paladin':
            return 16092346

        if c == 'warlock':
            return 8882157

        if c == 'mage':
            return 4245483

        return 10204605

################################################
############### BUILD DKP OUTPUT ###############
################################################
    def __buildDKPOutputSingle(self, info):
        if not info or not isinstance(info, PlayerInfo): return None

        data = {
            'author'        : {
                'name'      : "Essential DKP Profile"
            },
            'title'         : info.Player(),
            'description'   : info.Class(),
            'type'          : "rich",
            'timestamp'     : str(datetime.now().isoformat()),
            'thumbnail'     : {
                'url'       : "https://img.rankedboost.com/wp-content/uploads/2019/05/WoW-Classic-{0}-Guide.png".format(info.Class())
            },
            'color'         : self.__getClassColor(info.Class()),
            'footer'        : {
                'text' : "{0}".format(self._dbGetComment())
            },
            'fields' : []
        }

        field = {
            'name'      : "Current",
            'value'     : "`{0} DKP`".format(info.Dkp()),
            'inline'    : False
        }
        data['fields'].append(field)

        field = {
            'name'      : "Lifetime Gained",
            'value'     : "`{0} DKP`".format(info.LifetimeGained()),
            'inline'    : True
        }
        data['fields'].append(field)

        field = {
            'name'      : "Lifetime Spent",
            'value'     : "`{0} DKP`".format(info.LifetimeSpent()),
            'inline'    : True
        }
        data['fields'].append(field)

        return data


    def __buildDKPOutputMultiple(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list): return None
        ### 3 columns due to discord formating

        output_result_list_len = len(output_result_list)
        c = { 1 : [], 2 : [], 3 : [] }

        num_rows = int(output_result_list_len / 3)
        if num_rows == 0:
            num_rows = 1

        ## Split and reorder if needed
        column_reorder = True
        i = 1
        if column_reorder:
            for info in output_result_list:
                if i > (2 * num_rows):
                    c[3].append(info)
                elif i > num_rows:
                    c[2].append(info)
                else:
                    c[1].append(info)
                i = i + 1
        else: # row order
            for info in output_result_list:
                c[(i % 3) + 1].append(info)
                i = i + 1

        data = {
            'title'         : "DKP Values",
            'description'   : " ",
            'type'          : "rich",
#            'timestamp'     : str(datetime.now().isoformat()),
            'color'         : 10204605,
            'footer'        :
            {
                'text' : "Last updated {0} with comment: {1}".format(datetime.utcfromtimestamp(self._dbGetTimestamp()), self._dbGetComment())
            },
            'fields' : []
        }
        
        num_columns = 3
        if output_result_list_len < 3:
            num_columns = output_result_list_len

        for i in range(num_columns):
            min_title_value = (i * num_rows) + 1
            max_title_value = min((i + 1) * num_rows, output_result_list_len)

            if min_title_value != max_title_value:
                output_title = "{0} - {1}".format(min_title_value, max_title_value)
            else:
                output_title = "{0}".format(min_title_value)
            output_string = ''
                
            for info in c[i + 1]:
                output_string += "{0} `{1:6.1f}` {2}\n".format(self.__getIconString(info.Class()), info.Dkp(), info.Player())
                if len(output_string) > 950:
                    output_string += "{0} {1}\n".format(self.__getIconString(""),  "Limiting output")
                    break

            field = {
                'name'      : output_title,
                'value'     : output_string,
                'inline'    : True
            }

            if len(field['name']) > 0 and len(field['value']) > 0:
                data['fields'].append(field)

        return data


####################################################
############### BUILD HISTORY OUTPUT ###############
####################################################
    def __buildHistoryOutput(self, output_result_list):
        if not output_result_list or not isinstance(output_result_list, list): return None
        ### 3 columns due to discord formating

        output_result_list_len = len(output_result_list)
        c = { 1 : [], 2 : [], 3 : [] }

        num_rows = int(output_result_list_len / 3)
        if num_rows == 0:
            num_rows = 1

        ## Split and reorder if needed
        column_reorder = True
        i = 1
        if column_reorder:
            for info in output_result_list:
                if i > (2 * num_rows):
                    c[3].append(info)
                elif i > num_rows:
                    c[2].append(info)
                else:
                    c[1].append(info)
                i = i + 1
        else: # row order
            for info in output_result_list:
                c[(i % 3) + 1].append(info)
                i = i + 1

        data = {
            'title'         : "DKP History",
            'description'   : " ",
            'type'          : "rich",
#            'timestamp'     : str(datetime.now().isoformat()),
            'color'         : 10204605,
            'footer'        :
            {
                'text' : "Last updated {0} with comment: {1}".format(datetime.utcfromtimestamp(self._dbGetTimestamp()), self._dbGetComment())
            },
            'fields' : []
        }
        
        num_columns = 3
        if output_result_list_len < 3:
            num_columns = output_result_list_len

        for i in range(num_columns):
            min_title_value = (i * num_rows) + 1
            max_title_value = min((i + 1) * num_rows, output_result_list_len)

            if min_title_value != max_title_value:
                output_title = "{0} - {1}".format(min_title_value, max_title_value)
            else:
                output_title = "{0}".format(min_title_value)
            output_string = ''
                
            for history in c[i + 1]:
                output_string += "{0} `{1:6.1f}` {2}\n".format(datetime.fromtimestamp(history.Timestamp()), history.Dkp(), history.Player())
                if len(output_string) > 950:
                    output_string += "{0} {1}\n".format(self.__getIconString(""),  "Limiting output")
                    break

            field = {
                'name'      : output_title,
                'value'     : output_string,
                'inline'    : True
            }

            if len(field['name']) > 0 and len(field['value']) > 0:
                data['fields'].append(field)

        return data
###

    ### Database - Variables parsing ###

    def _fillHistory(self, players, dkp, timestamp, reason):
        if not players: return
        if not dkp: return

        if isinstance(players, str) and isinstance(dkp, int):
            self._addHistory(players, PlayerDKPHistory(players, dkp, timestamp, reason))
        elif isinstance(players, list) and isinstance(dkp, int):
            for player in players:
                self._addHistory(player, PlayerDKPHistory(player, dkp, timestamp, reason))
        elif isinstance(players, list) and isinstance(dkp, int):
            # In case of unequal length we only add as many entries as there are players
            limit = min(len(players), len(dkp))

            iterator = 1
            for player in players:
                self._addHistory(player, PlayerDKPHistory(player, float(dkp.pop()), timestamp, reason))
                if iterator == limit:
                    break

    # Called 1st
    def _buildDkpDatabase(self, sv):
        super()._buildDkpDatabase(None)

        dkp = sv.get(self.__DKP_SV)
        if not dkp: return

        if not isinstance(dkp, list): return

        # Ignore players not getting DKP in last 30 days TODO
        #if timestamp - updated > self.__30_DAYS_SECONDS: continue

        for entry in dkp:
            if not entry: return

            player = entry.get("player")
            if not player: continue

            dkp = entry.get("dkp")
            if not dkp: continue
            
            lifetime_gained = entry.get("lifetime_gained")
            if not lifetime_gained: continue
            
            lifetime_spent = entry.get("lifetime_spent")
            if not lifetime_spent: continue

            ingame_class = entry.get("class")
            if not ingame_class: continue

            role = entry.get("role")
            if not role: continue
            
            info = PlayerInfo(player, dkp, lifetime_gained, lifetime_spent, ingame_class, role)
            self._setDkp(player, info)
            self._setGroupDkp(info.Class(), info)

        self._dbSetTimestamp()

        # Sort all class DKP
        self._sortGroupDkp()

    # Called 2nd
    def _buildLootDatabase(self, sv):
        super()._buildLootDatabase(None)

        loot = sv.get(self.__LOOT_SV)
        if not loot: return

        if not isinstance(loot, list): return

    # Called 3rd
    def _buildHistoryDatabase(self, sv):
        super()._buildHistoryDatabase(None)
        history = sv.get(self.__HISTORY_SV)
        if not history: return
        if not isinstance(history, dict): return # dict because there is ["seed"] field...
        i = 1
        for entry in history.values():
            i = i + 1

            if isinstance(entry, int): continue

            players = entry.get("players")
            if not players: continue

            dkp = entry.get("dkp")
            if not dkp: continue

            date = entry.get("date")
            if not date: continue

            reason = entry.get("reason")
            if not reason: continue

            if not isinstance(players, str): continue
            if not isinstance(date, int): continue
            if not isinstance(reason, str): continue
            
            players = list(map(lambda p: p.lower(), players.split(",")))
            if not isinstance(players, list): continue

            if isinstance(dkp, str):
                # multiple entry
                dkp = list(map(lambda d: d, dkp.split(",")))
            elif not isinstance(dkp, int):
                continue

            self._fillHistory(players, dkp, date, reason)

        self._dbSetTimestamp()

    ### Essential related ###

    def __decodeAliases(self, groups):
        new_groups = groups.copy()
        for group in groups:
            if group == 'tank':
               new_groups.extend(['warrior', 'druid'])

            elif group == 'healer':
                new_groups.extend(['priest', 'paladin', 'druid', 'shaman'])
                
            elif group == 'dps':
                new_groups.extend(['warrior', 'rogue', 'hunter', 'mage', 'warlock', 'shaman'])
                
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
        help_string  = 'EssentialDKP Bot allows access to dkp information.\n'
        help_string += 'Currently supported commands:\n'
        help_string += '**{0}**\n Display this help\n'.format("?dkp")
        help_string += '**{0}**\n Display current DKP for [player] or the submitter if not specified.\n'.format("!dkp [player]")
        help_string += '**{0}**\n Display latest loot for [player] or the submitter if not specified.\n'.format("!dkploot [player]")
        help_string += '**{0}**\n Display DKP history for [player] or the submitter if not specified.'.format("!dkphistory [player]")
        if isPrivileged == True:
            help_string += '\n\n'
            help_string += 'Administrator only options:\n'
            help_string += '**{0}**\n Register current channel as EssentialDKP.lua file source.\n'.format("!dkpmanage register")
            help_string += '**{0}**\n Force reload data from newest EssentialDKP.lua file found in registered channel.'.format("!dkpmanage reload")
        return Response(ResponseStatus.SUCCESS, help_string)

    def call_dkp(self, param, isPrivileged):
        if not self.IsDatabaseLoaded(): return

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
            data = self.__buildDKPOutputMultiple(output_result_list)
        else:
            data = "{0}'s DKP was not found in database.".format(param.capitalize())

        return Response(ResponseStatus.SUCCESS, data)

    def call_dkphistory(self, param, isPrivileged):
        #return Response(ResponseStatus.SUCCESS, "Sorry :frowning: !dkphistory is not yet implemented.")
        targets = self.__getNamesFromParam(param)
        output_result_list = []

        if len(targets) > 0:
            for target in targets:
                # Single player
                info = self._getHistory(target)
                if info and isinstance(info, list):
                    output_result_list = info
                    break # Yes single only
        else:
            return Response(ResponseStatus.ERROR, "Unable to find data for {0}.".format(param))

        if len(output_result_list) > 0:
            data = self.__buildHistoryOutput(output_result_list)
        else:
            data = "{0}'s DKP history was not found in database.".format(param.capitalize())

        return Response(ResponseStatus.SUCCESS, data)

    def call_dkploot(self, param, isPrivileged):
        return Response(ResponseStatus.SUCCESS, "Sorry :frowning: !dkploot is not yet implemented.")

    