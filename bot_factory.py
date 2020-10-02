import bot_config
import essentialdkp_bot
import monolithdkp_bot


def new(guild_id, config: bot_config.BotConfig):
    if not isinstance(config, bot_config.BotConfig):
        return None

    if config.guild_info.bot_type == 'monolith':
        return monolithdkp_bot.MonolithDKPBot(guild_id, config)
    elif config.guild_info.bot_type == 'essential':
        return essentialdkp_bot.EssentialDKPBot(guild_id, config)
    elif config.guild_info.bot_type == 'community':
        return None
    else:
        return None
