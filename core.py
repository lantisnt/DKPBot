import os, sys, traceback, io, pytz

import discord
import dkp_bot, bot_factory
from bot_config import BotConfig

TOKEN = 0
CFG_DIR = "/tmp"

client = discord.Client()
bots = {}

def normalize_author(author):
    if isinstance(author, discord.Member):
        if author.nick:
            normalized = author.nick
        else:
            normalized = author
    else:
        normalized = author
        
    normalized = "{0}".format(normalized)
    normalized = normalized.split("#")[0].strip()
    normalized = normalized.split("/")[0].strip()
    normalized = normalized.split("\\")[0].strip()

    return normalized

async def discord_build_embed(data):
    return discord.Embed().from_dict(data)

async def discord_build_file(data):
    return discord.File(data)

async def discord_respond(channel, responses):
    if not responses:
        return

    if not isinstance(responses, list):
        response_list = []
        response_list.append(responses)
    else:
        response_list = responses

    for response in response_list:
        if isinstance(response, str):
            await channel.send(response)
        elif isinstance(response, dict):
            await channel.send(embed=await discord_build_embed(response))
        elif isinstance(response, io.IOBase):
            await channel.send(file=await discord_build_file(response))

async def discord_attachment_parse(bot, message, normalized_author):
    try:
    if len(message.attachments) > 0:
        for attachment in message.attachments:
            if bot.CheckAttachmentName(attachment.filename) and bot.CheckChannel(message.channel.id):
                attachment_bytes = await attachment.read()
                info = {
                    'comment' : message.content[:50],
                    'date' : message.created_at.astimezone(pytz.timezone("Europe/Paris")).strftime("%b %d %a %H:%M"),
                    'author' : normalized_author,
                }
                response = bot.BuildDatabase(
                    str(attachment_bytes, 'utf-8'), info)
                if response.status == dkp_bot.ResponseStatus.SUCCESS:
                    await discord_respond(message.channel, response.data)
                elif response.status == dkp_bot.ResponseStatus.ERROR:
                    print('ERROR: {0}'.format(response.data))
                return response.status
    except Forbidden:
        pass
    
    return dkp_bot.ResponseStatus.IGNORE

@client.event
async def on_ready():
    try:
        for guild in client.guilds:
            config_filename = "{0}/{1}.ini".format(CFG_DIR, guild.id)
            bot = bot_factory.New(BotConfig(config_filename))
            if bot:
                bots[guild.id] = bot
                for channel in guild.text_channels:
                    if (bot.IsChannelRegistered() and bot.CheckChannel(message.channel.id)) or not bot.IsChannelRegistered():
                        async for message in channel.history(limit=50):
                            status = await discord_attachment_parse(bot, message, normalize_author(message.author))
                            if status == dkp_bot.ResponseStatus.SUCCESS:
                                break
            else:
                continue
    
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=10, file=sys.stdout)
        traceback.print_exc()


@client.event
async def on_message(message):
    try:
        # TODO very later on
        #if enabled != True:
        #    return

        # Don't react to own messages
        if message.author == client.user:
            return

        # Block DMChannel at all
        if isinstance(message.channel, discord.DMChannel):
            #print('Received message {0.content} from {1} on DMChannel: {0.channel.id}'.format(message, message.author))
            return
        
        # Check if we have proper bot for the requester
        bot = bots.get(message.guild.id)
        if not isinstance(bot, dkp_bot.DKPBot):
            return

        # Normalize author
        author = normalize_author(message.author)

        # Debug message receive print
        #print('Received message {0.content} from {1} on channel: {0.channel.id}'.format(message, author))
        # await message.channel.send('Received message {0.content} from {1} on channel: {0.channel.id}'.format(message, author))

        # Check if user is privileged user (administrator)
        is_privileged = False
        if isinstance(message.author, discord.Member):
            is_privileged = message.author.permissions_in(
                message.channel).administrator

        requester_info = {
            'name'  : author,
            'is_privileged' : is_privileged
        }

        # Handle ?!command
        response = bot.Handle(message.content, requester_info)
        if response and isinstance(response, dkp_bot.Response):
            if response.status == dkp_bot.ResponseStatus.SUCCESS:
                response_channel = message.channel
                if response.dm:
                    dm_channel = message.author.dm_channel
                    if dm_channel == None:
                        await message.author.create_dm()
                        dm_channel = message.author.dm_channel
                        if dm_channel == None:
                             print('ERROR: Unable to create DM channel with {0}'.format(message.author))
                             return
                    response_channel = dm_channel
                await discord_respond(response_channel, response.data)
                if response.dm:
                    await message.delete()
            elif response.status == dkp_bot.ResponseStatus.ERROR:
                print('ERROR: {0}'.format(response.data))
                return
            elif response.status == dkp_bot.ResponseStatus.REQUEST:
                if response.data == dkp_bot.Request.CHANNEL_ID:
                    bot.RegisterChannel(message.channel.id)
                    await discord_respond(message.channel, 'Registed to expect SavedVariable lua file on channel {0.name}'.format(message.channel))

                return

        # No ?!command response
        # Check if we have attachment on registered channel
        if (bot.IsChannelRegistered() and bot.CheckChannel(message.channel.id)) or not bot.IsChannelRegistered():
            await discord_attachment_parse(bot, message, normalize_author(message.author))

    except (SystemExit, Exception):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=15, file=sys.stdout)

if __name__ == "__main__":
    if len(sys.argv) < 3: exit(1)
    TOKEN = sys.argv[1]
    CFG_DIR = sys.argv[2]
    client.run(TOKEN)
