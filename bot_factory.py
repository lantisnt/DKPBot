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

import bot_config
import essentialdkp_bot
import monolithdkp_bot
import communitydkp_bot
import classicepgp_bot
import rclc_bot
import clm_bot
from bot_logger import BotLogger


def new(guild_id, config: bot_config.BotConfig):
    if not isinstance(config, bot_config.BotConfig):
        return None

    BotLogger().get().info("Creating new [%s] bot.", config.guild_info.bot_type)
    if config.guild_info.bot_type == "monolith":
        return monolithdkp_bot.MonolithDKPBot(guild_id, config)
    elif config.guild_info.bot_type == "essential":
        return essentialdkp_bot.EssentialDKPBot(guild_id, config)
    elif config.guild_info.bot_type == "community":
        return communitydkp_bot.CommunityDKPBot(guild_id, config)
    elif config.guild_info.bot_type == "cepgp":
        return classicepgp_bot.CEPGPBot(guild_id, config)
    elif config.guild_info.bot_type == "rclc":
        return rclc_bot.RCLCBot(guild_id, config)
    elif config.guild_info.bot_type == "clm":
        return clm_bot.CLMBot(guild_id, config)
    else:
        return None
