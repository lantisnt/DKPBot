import sys
import traceback
import io
import pickle
import pytz

import discord

import dkp_bot
import bot_factory
import bot_memory_manager
from bot_config import BotConfig

import footprint

# PERFORMANCE_TEST_ENABLED = False
# PERFORMANCE_TEST_BOTS = 45
# PERFORMANCE_TEST_DONE = False

MAX_ATTACHMENT_BYTES = 2097152 # 2MB

class ScriptControl():
    __initialized = False
    token = 0
    config_dir = "/tmp"
    storage_dir = "/tmp"
    in_memory_objects_limit = 2

    def initialize(self, token, config_dir="/tmp", storage_dir="/tmp", in_memory_objects_limit=2):
        self.token = token
        self.config_dir = config_dir
        self.storage_dir = storage_dir
        self.in_memory_objects_limit = in_memory_objects_limit

    def is_initialized(self):
        return self.__initialized

    def set_initialized(self):
        self.__initialized = True


# Global objects
script_control = ScriptControl()
client = discord.Client()
bots = {}

# Main


def main(control: ScriptControl):
    if len(sys.argv) > 3:
        control.initialize(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 2:
        control.initialize(sys.argv[1], sys.argv[2])
    else:
        control.initialize(sys.argv[1])

    bot_memory_manager.Manager().initialize(control.in_memory_objects_limit, bots, pickle_data, unpickle_data)

    client.run(control.token)

# Error handling


def handle_exception(text):
    print("=== EXCEPTION ===")
    print(text)
    print("=== TRACEBACK ===")
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback, limit=15, file=sys.stdout)
    print("====== END ======")


# Data related
def pickle_data(uid, data):
    with open("{0}/pickle.{1}.bin".format(script_control.storage_dir, uid), "wb") as file_pointer:
        pickle.dump(data, file_pointer)


def unpickle_data(uid):
    data = None
    with open("{0}/pickle.{1}.bin".format(script_control.storage_dir, uid), "rb") as file_pointer:
        data = pickle.load(file_pointer)
    return data

# Performance analysis


# def PERFORMANCE_TEST_INJECTION(gid, attachment):

#     if not PERFORMANCE_TEST_ENABLED:
#         return

#     if PERFORMANCE_TEST_DONE:
#         return

#     if gid == 746131486234640444:
#         for i in range(1, PERFORMANCE_TEST_BOTS + 1):
#             bots[i] = bot_factory.New(i, BotConfig('1.ini'))
#             bots[i].build_database(attachment, {})
#             bot_memory_manager.Manager().Handle(i, True)
#         PERFORMANCE_TEST_DONE = True

# Discord related


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


async def discord_attachment_parse(bot : dkp_bot.DKPBot, message: discord.Message, normalized_author: str):
    if len(message.attachments) > 0:
        for attachment in message.attachments:
            if bot.check_attachment_name(attachment.filename) and attachment.size < MAX_ATTACHMENT_BYTES:
                attachment_bytes = await attachment.read()
                info = {
                    'comment': message.content[:50],
                    'date': message.created_at.astimezone(pytz.timezone("Europe/Paris")).strftime("%b %d %a %H:%M"),
                    'author': normalized_author,
                }
#                PERFORMANCE_TEST_INJECTION(message.guild.id, str(attachment_bytes, 'utf-8'))
                response = bot.build_database(
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
    config_filename = "{0}/{1}.ini".format(script_control.config_dir, guild.id)
    bot = bot_factory.new(guild.id, BotConfig(config_filename))
    if bot:
        bots[guild.id] = bot
        for channel in guild.text_channels:
            try:  # in case we dont have access we still want to check other channels not die here
                if (bot.is_channel_registered() and bot.check_channel(message.channel.id)) or not bot.is_channel_registered():
                    async for message in channel.history(limit=50):
                        status = await discord_attachment_parse(bot, message, normalize_author(message.author))
                        if status == dkp_bot.ResponseStatus.SUCCESS:
                            break
            except discord.Forbidden:
                continue
        # We call it here so we will have it tracked from beginning
        bot_memory_manager.Manager().Handle(guild.id, True)

# Discord API


@client.event
async def on_guild_join(guild):
    try:
        await spawn_bot(guild)

    except (SystemExit, Exception):
        handle_exception("on_guild_join()")


@client.event
async def on_ready():
    try:
        if script_control.is_initialized():
            return

        for guild in client.guilds:
            await spawn_bot(guild)

    except (SystemExit, Exception):
        handle_exception("on_ready()")

    script_control.set_initialized()
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


        if client.user in message.mentions:
            # Handle bot mention
            response = bot.call_dkphelp(None, request_info)
        else:
            # Handle command
            response = bot.handle(message.content, request_info)

        if response and isinstance(response, dkp_bot.Response):
            if response.status == dkp_bot.ResponseStatus.SUCCESS:
                response_channel = message.channel
                if response.dm:
                    dm_channel = message.author.dm_channel
                    if dm_channel is None:
                        await message.author.create_dm()
                        dm_channel = message.author.dm_channel
                        if dm_channel is None:
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
                    bot.register_channel(message.channel.id)
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
    main(script_control)
