from dkp_bot import Response, ResponseStatus, Statistics
from bot_logger import BotLogger, trace, trace_func_only, for_all_methods
from display_templates import BasicError, BasicCritical, BasicInfo, BasicSuccess
from raidhelper import RaidHelper


@for_all_methods(trace, trace_func_only)
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
        return (
            (self.__su_id != 0) and (self.__bots is not None) and (len(self.__bots) > 0)
        )

    def __unauthorized(self, command, param, request_info):
        BotLogger().get().error(
            "Unauthorized access by user {0} (`{1}`) from server {2} (`{3}`) on channel {4} (`{5}`) requesting `{6}` with params {7}".format(
                request_info["author"]["raw"],
                request_info["author"]["id"],
                request_info["server"]["name"],
                request_info["server"]["id"],
                request_info["channel"]["name"],
                request_info["channel"]["id"],
                command,
                param,
            )
        )
        return Response(ResponseStatus.IGNORE)

    def __is_authorized(self, request_info):
        return self.is_init and request_info["author"]["id"] == self.__su_id

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
        response_list = []
        if len(params) > 0:
            for server_id in params:
                bot_id = None
                try:
                    bot_id = int(server_id)
                except TypeError:
                    response_list.append(
                        BasicCritical(
                            "Invalid server id: `{0}`".format(server_id)
                        ).get()
                    )

                if (bot_id is not None) and (bot_id in self.__bots):
                    response_list.append(
                        self.__bots[bot_id].statistics.print_database()
                    )
                else:
                    response_list.append(
                        BasicError("Server `{0}` has no bot.".format(server_id)).get()
                    )
            return Response(ResponseStatus.SUCCESS, response_list)
        else:
            return Response(
                ResponseStatus.SUCCESS, BasicCritical("Server id not specified.").get()
            )

    def su_cmdstats(self, param):
        params = param.split(" ")
        response_list = []
        if len(params) > 0:
            for server_id in params:
                bot_id = None
                try:
                    bot_id = int(server_id)
                except TypeError:
                    response_list.append(
                        BasicCritical(
                            "Invalid server id: `{0}`".format(server_id)
                        ).get()
                    )

                if (bot_id is not None) and (bot_id in self.__bots):
                    response_list.append(self.__bots[bot_id].statistics.print_data())
                else:
                    response_list.append(
                        BasicError("Server `{0}` has no bot.".format(server_id)).get()
                    )
            return Response(ResponseStatus.SUCCESS, response_list)
        else:
            return Response(
                ResponseStatus.SUCCESS, BasicCritical("Server id not specified.").get()
            )

    def su_config(self, param):
        params = param.split(" ")
        response_list = []
        if len(params) > 0:
            for server_id in params:
                bot_id = None
                try:
                    bot_id = int(server_id)
                except TypeError:
                    response_list.append(
                        BasicCritical(
                            "Invalid server id: `{0}`".format(server_id)
                        ).get()
                    )

                if (bot_id is not None) and (bot_id in self.__bots):
                    response = self.__bots[bot_id].call_config(
                        "dummy", {"is_privileged": True}
                    )
                    if response.status == ResponseStatus.SUCCESS:
                        response_list.append(response.data)
                else:
                    response_list.append(
                        BasicError("Server `{0}` has no bot.".format(server_id)).get()
                    )
            return Response(ResponseStatus.SUCCESS, response_list)
        else:
            return Response(
                ResponseStatus.SUCCESS, BasicCritical("Server id not specified.").get()
            )

    def su_display(self, param):
        params = param.split(" ")
        response_list = []
        if len(params) > 0:
            for server_id in params:
                bot_id = None
                try:
                    bot_id = int(server_id)
                except TypeError:
                    response_list.append(
                        BasicCritical(
                            "Invalid server id: `{0}`".format(server_id)
                        ).get()
                    )

                if (bot_id is not None) and (bot_id in self.__bots):
                    response = self.__bots[bot_id].call_display(
                        "dummy", {"is_privileged": True}
                    )
                    if response.status == ResponseStatus.SUCCESS:
                        response_list.append(response.data)
                else:
                    response_list.append(
                        BasicError("Server `{0}` has no bot.".format(server_id)).get()
                    )
            return Response(ResponseStatus.SUCCESS, response_list)
        else:
            return Response(
                ResponseStatus.SUCCESS, BasicCritical("Server id not specified.").get()
            )

    def su_reload(self, param):
        params = param.split(" ")
        response_list = []
        if len(params) > 0:
            for server_id in params:
                bot_id = None
                try:
                    bot_id = int(server_id)
                except TypeError:
                    response_list.append(
                        BasicCritical(
                            "Invalid server id: `{0}`".format(server_id)
                        ).get()
                    )

                if (bot_id is not None) and (bot_id in self.__bots):
                    return Response(ResponseStatus.RELOAD, bot_id)

            return Response(ResponseStatus.SUCCESS, response_list)
        else:
            return Response(
                ResponseStatus.SUCCESS, BasicCritical("Server id not specified.").get()
            )

    def su_globalstats(self, param):  # pylint: disable=unused-argument
        global_command_stats = Statistics.Data()
        for bot in self.__bots.values():
            global_command_stats += bot.statistics.data

        string = "```asciidoc\n=== Global Command Statistics ===```"
        if len(global_command_stats) > 0:
            string += "```c\n"
            string += Statistics.format(global_command_stats.get(), -2)
            string += "\nRaid-Helper: " + str(RaidHelper().stats())
            string += "```"
        else:
            string += "```asciidoc\n"
            string += "[ none ]"
            string += "```"

        return Response(ResponseStatus.SUCCESS, string)

    def su_rhlist(self, param):  # pylint: disable=unused-argument
        raid_user_list = RaidHelper().get_event_signups(int(param.split(" ")[0]))
        signed = []
        for raid_user in raid_user_list:
            signed.extend(raid_user.names)
        return Response(ResponseStatus.SUCCESS, BasicInfo("\n".join(signed)).get())

    def su_logging(self, param):  # pylint: disable=unused-argument
        params = param.split(" ")
        if len(params) == 1:
            if BotLogger().set_level(params[0].upper()):
                return Response(
                    ResponseStatus.SUCCESS,
                    BasicSuccess(
                        "Logging level set to: **{0}**".format(
                            BotLogger().get_level_name()
                        )
                    ).get(),
                )
            else:
                return Response(
                    ResponseStatus.SUCCESS,
                    BasicInfo(
                        "Current logging level: **{0}**\n`STDOUT` **{1}**\n`TRACE` **{2}**".format(
                            BotLogger().get_level_name(),
                            "Enabled" if BotLogger().stdout_enabled else "Disabled",
                            "Enabled" if BotLogger().trace_enabled else "Disabled",
                        )
                    ).get(),
                )
        elif len(params) == 2:
            config = params[0].lower()
            request = params[1].lower()
            if request in ["enable", "true", "on", "1", 1]:
                enable = True
            elif request in ["disable", "false", "off", "0", 0]:
                enable = False
            else:
                return Response(
                    ResponseStatus.SUCCESS,
                    BasicError("Unknown request. Try on/off.").get(),
                )

            if config == "stdout":
                BotLogger().config_stdout(enable)
            elif config == "trace":
                BotLogger().config_trace(enable)
            else:
                return Response(
                    ResponseStatus.SUCCESS,
                    BasicError("Unknown config. Try stdout/trace.").get(),
                )

            return Response(
                ResponseStatus.SUCCESS,
                BasicSuccess(
                    "`" + config.upper() + "` " + "Enabled" if enable else "Disabled"
                ).get(),
            )
        else:
            return Response(
                ResponseStatus.SUCCESS, BasicCritical("Invalid parameters").get()
            )
