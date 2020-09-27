import bot_config, dkp_bot, essentialdkp_bot

def New(guild_id, config):
    if not isinstance(config, bot_config.BotConfig):
        return None

    if config.GuildInfo.BotType == 'MonolithDKP':
        return essentialdkp_bot.EssentialDKPBot(guild_id, config)
    elif config.GuildInfo.BotType == 'EssentialDKP':
        return essentialdkp_bot.EssentialDKPBot(guild_id, config)
    elif  config.GuildInfo.BotType == 'CommunityDKP':
        return None
    else:
        return None
    
    