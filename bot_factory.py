import bot_config, dkp_bot, essentialdkp_bot

def New(config):
    if not isinstance(config, bot_config.BotConfig):
        return None

    if config.GuildInfo.BotType == 'MonolithDKP':
        return essentialdkp_bot.EssentialDKPBot(config)
    elif config.GuildInfo.BotType == 'EssentialDKP':
        return essentialdkp_bot.EssentialDKPBot(config)
    elif  config.GuildInfo.BotType == 'CommunityDKP':
        return None
    else:
        return None
    
    