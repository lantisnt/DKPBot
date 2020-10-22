from dkp_bot import Response, ResponseStatus, Statistics
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

    def __unauthorized(self, command, param, request_info):
        BotLogger().get().error("Unauthorized access by user {0} (`{1}`) from server {2} (`{3}`) on channel {4} (`{5}`) requesting `{6}` with params {7}".format(
            request_info['author']['raw'],
            request_info['author']['id'],
            request_info['server']['name'],
            request_info['server']['id'],
            request_info['channel']['name'],
            request_info['channel']['id'],
            command, param))
        return Response(ResponseStatus.IGNORE)

    def __is_authorized(self, request_info):
        return self.is_init and request_info['author']['id'] == self.__su_id

    def handle(self, command, param, request_info):
        if not self.__is_authorized(request_info):
            return self.__unauthorized(command, param, request_info)

        callback = getattr(self, command, None)
        if callback and callable(callback):
            response = callback(param)  # pylint: disable=not-callable
            return response
        else:
            return Response(ResponseStatus.IGNORE)

    def su_dbinfo(self, param):
        params = param.split(" ")
        if len(params) > 0:
            bot_id = int(params[0])
            if bot_id in self.__bots:
                return Response(ResponseStatus.SUCCESS, self.__bots[bot_id].statistics.print_database())
            else:
                return Response(ResponseStatus.SUCCESS, BasicCritical("Server id has no bot.").get())

        else:
            return Response(ResponseStatus.SUCCESS, BasicCritical("Server id not specified.").get())

    def su_cmdstats(self, param):
        params = param.split(" ")
        if len(params) > 0:
            bot_id = int(params[0])
            if bot_id in self.__bots:
                return Response(ResponseStatus.SUCCESS, self.__bots[bot_id].statistics.print_commands())
            else:
                return Response(ResponseStatus.SUCCESS, BasicCritical("Server id has no bot.").get())

        else:
            return Response(ResponseStatus.SUCCESS, BasicCritical("Server id not specified.").get())

    def su_globalstats(self, param):
        global_command_stats = Statistics.Commands()
        for bot in self.__bots.values():
            global_command_stats += bot.statistics.commands

        string  = "```c\n"
        string += Statistics.format(global_command_stats.get(), -2)
        string += "```"

        return Response(ResponseStatus.SUCCESS, string)
