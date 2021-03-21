from dkp_bot import Response, ResponseStatus
from essentialdkp_bot import EssentialDKPBot
from display_templates import BasicInfo, SinglePlayerProfile
from bot_logger import trace, trace_func_only, for_all_methods


@for_all_methods(trace, trace_func_only)
class MonolithDKPBot(EssentialDKPBot):
    def _configure(self):
        super()._configure()
        # Data outputs
        self._single_player_profile_builder = SinglePlayerProfile(
            "Monolith DKP Profile", self._timezone, self._version
        )

    def _get_addon_thumbnail(self):
        return "https://cdn.discordapp.com/attachments/765089790295015425/822883954771230720/monolithlogo.png"

    def config_call_server_side(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Server and Side setting are not used in `monolith` mode.").get(),
        )

    def config_call_guild_name(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Guild Name setting is not used in `monolith` mode.").get(),
        )

    def config_call_team(self, params, num_params, request_info):
        return Response(
            ResponseStatus.SUCCESS,
            BasicInfo("Multiple teams are not used in `monolith` mode.").get(),
        )
