import json

from bot_utility import get_all_names
from player_db_models import PlayerInfo

def get_example_data():
    try:
        with open('signups.json') as json_file:
            return json.load(json_file)
    except Exception as e:
        print(str(e))
        return {}

class RaidHelper:

    @staticmethod
    def execute_query():
        return get_example_data()

    @staticmethod
    def decode_signed_list(json_response):
        if json_response is None:
            return []
        
        signed = json_response.get("signed")
        if signed is None:
            return []
        
        return get_all_names(signed)

    @staticmethod
    def get_event_signups(event_id):
        # execute query
        json_response = RaidHelper.execute_query()
        # get name list from query
        return RaidHelper.decode_signed_list(json_response)
