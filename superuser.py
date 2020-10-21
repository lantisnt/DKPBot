from dkp_bot import Response, ResponseStatus
from bot_logger import BotLogger
from display_templates import BasicSuccess, BasicCritical

class Superuser:
    __su_id = 0
    __bots = {}

    def __init__(self, su_id=0, bots=None):
        self.initialize(su_id, bots)

    def initialize(self, su_id, bots):
        if isinstance(su_id, int):
            self.__su_id = su_id

        if isinstance(bots, dict):
            self.__bots = bots

    def is_init(self):
        return (self.__su_id != 0) and (self.__bots is not None) and (len(self.__bots) > 0)

    def __unauthorized(self, command, params, request_info):
        BotLogger().get().error("Unauthorized access by user {0} ({1}) from server {2} ({3}) on channel {4} ({5}) requesting {6} with params {7}".format(
            request_info['author']['raw'],
            request_info['author']['id'],
            request_info['server']['name'],
            request_info['server']['id'],
            request_info['channel']['name'],
            request_info['channel']['id'],
            command, params))
        return Response(ResponseStatus.IGNORE)

    def __is_authorized(self, request_info):
        return self.is_init and request_info['author']['id'] == self.__su_id

    def handle(self, command, params, request_info):
        if not self.__is_authorized(request_info):
            return self.__unauthorized(command, params, request_info)

        callback = getattr(self, command, None)
        if callback and callable(callback):
            response = callback(params)  # pylint: disable=not-callable
            return response
        else:
            return Response(ResponseStatus.IGNORE)

    def su_stats(self, params):
        if len(params) > 0:
            bot_id = int(params[0])
            BotLogger().get().info(self.__bots.keys())
            if bot_id in self.__bots:
                stats = self.__bots[bot_id].statistics
                return Response(ResponseStatus.SUCCESS, BasicSuccess(str(stats)).get())
            else:
                return Response(ResponseStatus.SUCCESS, BasicCritical("Server id has no bot.").get())

        else:
            return Response(ResponseStatus.SUCCESS, BasicCritical("Server id not specified.").get())


