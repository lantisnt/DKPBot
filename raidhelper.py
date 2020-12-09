import requests
from bot_logger import BotLogger
from bot_utility import split_names
from player_db_models import PlayerInfo

class RaidUser:
    def __init__(self, userid = 0, username = "", spec = "", role = "", entrydate = "", raidid = 0, id = 0):
        self.id = userid
        self.__username = username

        self.names = split_names(self.__username.strip("*"))
        self.names = list(filter(lambda x: len(x) >= 2 and len(x) <= 12, self.names))

    def name(self):
        if len(self.names) > 0:
            return self.names[0]
        else:
            return ""

    def main(self):
        return self.name()

    def alt(self):
        if len(self.names) > 1:
            return self.names[1]
        else:
            return ""

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if len(self.names) > 1:
            return self.main() + " / " + self.alt()
        else:
            return self.main()

class RaidHelper:

    class __RaidHelper: #pylint: disable=invalid-name, attribute-defined-outside-init

        RAIDS_ENDPOINT = "/api/raids/"
        
        def initialize(self, endpoint, token):
            self.__token = token
            self.__endpoint = endpoint

        def execute_query(self, target):
            try:
                response = requests.get(self.__endpoint + self.RAIDS_ENDPOINT + target, headers={"Authorization": "Bearer " + self.__token})
                if response.status_code == 200:
                    return response.json()
                else:
                    BotLogger().get().warning(str(response))
                    return None
            except requests.exceptions.RequestException as exc:
                BotLogger().get().error(str(exc))
                return None

        def decode_signed_list(self, json_response):
            if json_response is None:
                return []
            
            raidusers = json_response.get("raidusers")
            if raidusers is None:
                return []

            signed = []
            for raiduser in raidusers:
                signed.append(RaidUser(**raiduser))

            return signed

        def get_event_signups(self, event_id):
            # execute query
            json_response = self.execute_query(str(event_id))
            if json_response is None:
                return []
            # get name list from query
            return self.decode_signed_list(json_response)

    instance = None

    def __new__(cls):  # __new__ always a classmethod
        if not RaidHelper.instance:
            RaidHelper.instance = RaidHelper.__RaidHelper()
        return RaidHelper.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name, value):
        return setattr(self.instance, name, value)