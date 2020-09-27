import bot_config
import essentialdkp_bot


def new(guild_id, config: bot_config.BotConfig):
    if not isinstance(config, bot_config.BotConfig):
        return None

    if config.guild_info.bot_type == 'MonolithDKP':
        return essentialdkp_bot.EssentialDKPBot(guild_id, config)
    elif config.guild_info.bot_type == 'EssentialDKP':
        return essentialdkp_bot.EssentialDKPBot(guild_id, config)
    elif config.guild_info.bot_type == 'CommunityDKP':
        return None
    else:
        return None
