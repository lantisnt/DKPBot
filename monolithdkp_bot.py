# Copyright 2020-2023 Lantis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

        self._update_views_info()

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
