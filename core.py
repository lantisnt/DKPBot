import os, sys, traceback, io, pytz, pickle

import discord

import dkp_bot, bot_factory, bot_memory_manager
from bot_config import BotConfig

import footprint

PERFORMANCE_TEST_ENABLED = False
PERFORMANCE_TEST_BOTS = 45
PERFORMANCE_TEST_DONE = False

MEMORY_LIMIT = 2
TOKEN = 0
CFG_DIR = "/tmp"
STORAGE_DIR = "/tmp"

## Global objects
client = discord.Client()
bots = {}
initialized = False

## Error handling
def handle_exception(text):
    print("=== EXCEPTION ===")
    print(text)
    print("=== TRACEBACK ===")
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback, limit=15, file=sys.stdout)
    print("====== END ======")


## Data related
def pickle_data(uid, data):
    global STORAGE_DIR
    with open("{0}/pickle.{1}.bin".format(STORAGE_DIR, uid), "wb") as fp:
        pickle.dump(data, fp)

def unpickle_data(uid):
    global STORAGE_DIR
    data = None
    with open("{0}/pickle.{1}.bin".format(STORAGE_DIR, uid), "rb") as fp:
        data = pickle.load(fp)
    return data

## Performance analysis
def PERFORMANCE_TEST_INJECTION(gid, attachment):
    global PERFORMANCE_TEST_ENABLED
    global PERFORMANCE_TEST_DONE

    if not PERFORMANCE_TEST_ENABLED:
        return

    if PERFORMANCE_TEST_DONE:
        return

    if gid == 746131486234640444:
        for i in range(1, PERFORMANCE_TEST_BOTS + 1):
            bots[i] = bot_factory.New(i, BotConfig('1.ini'))
            bots[i].BuildDatabase(attachment, {})
            bot_memory_manager.Manager().Handle(i, True)
        PERFORMANCE_TEST_DONE = True

## Discord related

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
    if len(message.attachments) > 0:
        for attachment in message.attachments:
            if bot.CheckAttachmentName(attachment.filename):
                attachment_bytes = await attachment.read()
                info = {
                    'comment': message.content[:50],
                    'date': message.created_at.astimezone(pytz.timezone("Europe/Paris")).strftime("%b %d %a %H:%M"),
                    'author': normalized_author,
                }
                PERFORMANCE_TEST_INJECTION(message.guild.id, str(attachment_bytes, 'utf-8'))
                response = bot.BuildDatabase(
                    str(attachment_bytes, 'utf-8'), info)
                print("Bot for server {0} total footprint: {1} B".format(
                    message.guild.name, footprint.total_size(bot)))
                if response.status == dkp_bot.ResponseStatus.SUCCESS:
                    await discord_respond(message.channel, response.data)
                elif response.status == dkp_bot.ResponseStatus.ERROR:
                    print('ERROR: {0}'.format(response.data))
                return response.status

    return dkp_bot.ResponseStatus.IGNORE

async def spawn_bot(guild):
    config_filename = "{0}/{1}.ini".format(CFG_DIR, guild.id)
    bot = bot_factory.New(guild.id, BotConfig(config_filename))
    if bot:
        bots[guild.id] = bot
        for channel in guild.text_channels:
            try: # in case we dont have access we still want to check other channels not die here
                if (bot.IsChannelRegistered() and bot.CheckChannel(message.channel.id)) or not bot.IsChannelRegistered():
                    async for message in channel.history(limit=50):
                        status = await discord_attachment_parse(bot, message, normalize_author(message.author))
                        if status == dkp_bot.ResponseStatus.SUCCESS:
                            break
            except discord.Forbidden:
                continue
        bot_memory_manager.Manager().Handle(guild.id, True) # We call it here so we will have it tracked from beginning

## Discord API

@client.event
async def on_guild_join(guild):
    try:
        await spawn_bot(guild)

    except (SystemExit, Exception):
        handle_exception("on_guild_join()")

@client.event
async def on_ready():
    try:
        if initialized:
            return

        for guild in client.guilds:
            await spawn_bot(guild)

    except (SystemExit, Exception):
        handle_exception("on_ready()")

    initialized = True
    print("Ready!")

@client.event
async def on_message(message):
    try:
        # Don't react to own messages
        if message.author == client.user:
            return

        # Block DMChannel at all
        if isinstance(message.channel, discord.DMChannel):
            return

        # Check if we have proper bot for the requester
        bot = bots.get(message.guild.id)
        if not isinstance(bot, dkp_bot.DKPBot):
            return
        
        # Normalize author
        author = normalize_author(message.author)

        # Check if user is privileged user (administrator)
        is_privileged = False
        if isinstance(message.author, discord.Member):
            is_privileged = message.author.permissions_in(
                message.channel).administrator

        request_info = {
            'name': author,
            'is_privileged': is_privileged
        }

        # Handle !command
        response = bot.Handle(message.content, request_info)
        if response and isinstance(response, dkp_bot.Response):
            if response.status == dkp_bot.ResponseStatus.SUCCESS:
                response_channel = message.channel
                if response.dm:
                    dm_channel = message.author.dm_channel
                    if dm_channel == None:
                        await message.author.create_dm()
                        dm_channel = message.author.dm_channel
                        if dm_channel == None:
                            print('ERROR: Unable to create DM channel with {0}'.format(
                                message.author))
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
                    await discord_respond(message.channel, 'Registered to expect SavedVariable lua file on channel {0.name}'.format(message.channel))

                return

        # No ?!command response
        # Check if we have attachment on registered channel
        if (bot.IsChannelRegistered() and bot.CheckChannel(message.channel.id)) or not bot.IsChannelRegistered():
            await discord_attachment_parse(bot, message, normalize_author(message.author))

    except (SystemExit, Exception):
        handle_exception(message.content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        exit(1)
    
    TOKEN = sys.argv[1]
    if len(sys.argv) > 2:
        CFG_DIR = sys.argv[2]
    if len(sys.argv) > 3:
        STORAGE_DIR = sys.argv[3]
    
    bot_memory_manager.Manager().Initialize(MEMORY_LIMIT, bots, pickle_data, unpickle_data)

    PERFORMANCE_TEST_DONE = False

    initialized = False

    client.run(TOKEN)
