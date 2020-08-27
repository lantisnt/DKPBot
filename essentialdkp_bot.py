from datetime import datetime
import re

from dkp_bot import DKPBot, Response, ResponseStatus
from player_info import PlayerInfo

class EssentialDKPBot(DKPBot):

    __DKP_SV = "MonDKP_DKPTable"
    __LOOT_SV = "MonDKP_Loot"
    __HISTORY_SV = "MonDKP_DKPHistory"
    __30_DAYS_SECONDS = 2592000

    def __init__(self, inputFileName = "EssentialDKP.lua", channel = 0, enabled = False, parser = None):
        super().__init__(inputFileName, channel, enabled, parser)

    ### 

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

    ### Database - Variables parsing ###
    def _buildDkpDatabase(self, sv):
        super()._buildDkpDatabase(None)
        #timestamp = int(time.time())

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
            
            ingame_class = entry.get("class")
            if not ingame_class: continue

            role = entry.get("role")
            if not role: continue
            
            info = PlayerInfo(player, dkp, lifetime_gained, ingame_class, role)
            self._setDkp(player, info)
            self._setGroupDkp(info.Class(), info)

        self._dbSetTimestamp()

        # Sort all class DKP
        self._sortGroupDkp()

    def _buildLootDatabase(self, sv):
        super()._buildLootDatabase(None)

        loot = sv.get(self.__LOOT_SV)
        if not loot: return

    def _buildHistoryDatabase(self, sv):
        super()._buildHistoryDatabase(None)

        history = sv.get(self.__HISTORY_SV)
        if not history: return


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

        # Matches either a,b,c,d or A / B or A \ B
        group_player_find = re.compile("\s*([\d\w]*)[\s[\/\,]*")
        # Remove empty strings
        targets = list(filter(None, group_player_find.findall(param)))
        # Decode aliases
        targets = self.__decodeAliases(targets)
        # Remove duplicates either from input or introduced by aliases
        targets = list(dict.fromkeys(targets))
        # Lowercase all
        targets = list(map(lambda x:x.strip().lower(), targets))
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
            return Response(ResponseStatus.ERROR, "Unable to find Main name for {0}.".format(param))

        output_result_list.sort(key=lambda info: info.Dkp(), reverse=True)

        ### 3 columns due to discord formating
        output_result_list_len = len(output_result_list)

        if output_result_list_len > 0:
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
                'timestamp'     : str(datetime.now().isoformat()),
                'color'         : 10204605,
                'footer'        :
                {
                    'text' : "Last updated {0} with comment: {1}".format(datetime.fromtimestamp(self._dbGetTimestamp()), self._dbGetComment())
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
                    if len(output_string) > 1500:
                        output_string += "{0} {1}\n".format(self.__getIconString(""),  "Limiting output")
                        break

                field = {
                    'name'      : output_title,
                    'value'     : output_string,
                    'inline'    : True
                    }

                if len(field['name']) > 0 and len(field['value']) > 0:
                    data['fields'].append(field)
        else:
            data = "{0} was not found in DKP database.".format(param.capitalize())

        return Response(ResponseStatus.SUCCESS, data)

    def call_dkphistory(self, param, isPrivileged):
        return Response(ResponseStatus.SUCCESS, "Sorry :frowning: !dkphistory is not yet implemented.")

    def call_dkploot(self, param, isPrivileged):
        return Response(ResponseStatus.SUCCESS, "Sorry :frowning: !dkploot is not yet implemented.")

    