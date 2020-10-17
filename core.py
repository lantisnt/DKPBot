import sys
import io
import pickle
import asyncio
import pytz

import discord

import build_info
import dkp_bot
import bot_factory
import bot_memory_manager
from bot_config import BotConfig
from bot_logger import BotLogger
from display_templates import BasicSuccess, BasicError
from loop_activity import LoopActivity
import footprint

MAX_ATTACHMENT_BYTES = 3145728 # 3MB

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
activity = LoopActivity("")
activity.update({
    'booting'   : 'booting...'
})

async def discord_update_activity():
    await client.wait_until_ready()
    while True:
        await client.change_presence(activity=activity.next())
        await asyncio.sleep(30)


# Main
def main(control: ScriptControl):
    control.initialize(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    BotLogger().initialize(sys.argv[5])
    bot_memory_manager.Manager().initialize(control.in_memory_objects_limit, bots, pickle_data, unpickle_data)

    client.loop.create_task(discord_update_activity())
    client.run(control.token)

# Utility
def initialize_activity_data():
    activity.remove('booting')
    activity.update({
        "version"   : "{0}".format(build_info.VERSION),
        "discord"   : "{0}".format(build_info.SUPPORT_SERVER),
        "help"      : "@mention me for help"
    })

def update_activity_data():
    activity.update({"servers" : "{0} servers".format(len(client.guilds))})

# Error handling

def handle_exception(note, exception):
    BotLogger().get().error("=== EXCEPTION ===")
    BotLogger().get().error(note)
    BotLogger().get().error(exception, exc_info=True, stack_info=True)
    BotLogger().get().error("====== END ======")


# Data related
def pickle_data(uid, data):
    with open("{0}/pickle.{1}.bin".format(script_control.storage_dir, uid), "wb") as file_pointer:
        pickle.dump(data, file_pointer)


def unpickle_data(uid):
    data = None
    with open("{0}/pickle.{1}.bin".format(script_control.storage_dir, uid), "rb") as file_pointer:
        data = pickle.load(file_pointer)
    return data

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

def get_request_info(message: discord.Message):
    # Normalize author
    author = normalize_author(message.author)

    # Check if user is privileged user (administrator)
    is_privileged = False
    if isinstance(message.author, discord.Member):
        is_privileged = message.author.permissions_in(message.channel).administrator

    request_info = {
        'author': author,
        'channel': message.channel.id,
        'is_privileged': is_privileged,
        'mentions' : {
            'roles'    : [],
            'channels' : []
        }
    }

    for role_mention in message.role_mentions:
        if role_mention.mentionable:
            request_info['mentions']['roles'].append(role_mention.id)

    for channel_mention in message.channel_mentions:
        if isinstance(channel_mention, discord.TextChannel):
            bot_permissions =  channel_mention.permissions_in(client.user)
            if bot_permissions.read_messages and bot_permissions.send_messages:
                request_info['mentions']['channels'].append(channel_mention.id)

    return request_info

async def discord_get_response_channel(message, direct_message: bool):
    response_channel = message.channel
    if direct_message:
        dm_channel = message.author.dm_channel
        if dm_channel is None:
            await message.author.create_dm()
            dm_channel = message.author.dm_channel
            if dm_channel is None:
                BotLogger().get().error('Unable to create DM channel with {0}'.format(
                    message.author))
            else:
                response_channel = dm_channel
        else:
            response_channel = dm_channel

    return response_channel

async def discord_build_embed(data):
    return discord.Embed().from_dict(data)


async def discord_build_file(data):
    return discord.File(data)


async def discord_respond(channel, responses, self_call=False):
    try:
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
            elif isinstance(response, tuple):
                message = response[0]
                extra = response[1]
                if isinstance(message, str):
                    if isinstance(extra, dict):
                        await channel.send(message, embed=await discord_build_embed(extra))
                    elif isinstance(extra, io.IOBase):
                        await channel.send(message, file=await discord_build_file(extra))
    except discord.HTTPException as exception:
        exception = str(exception).lower()
        if (exception.find("size exceeds maximum") != -1) or (exception.find("or fewer in length") != -1) and not self_call:
            embed = BasicError("Response data exceeded Discord limits. Please limit the response in display configuration.")
            await discord_respond(channel, embed.get(), True)
        else:
            pass # log here

async def discord_attachment_parse(bot: dkp_bot.DKPBot, message: discord.Message, normalized_author: str, announce: bool):
    if len(message.attachments) > 0:
        for attachment in message.attachments:
            if bot.check_attachment_name(attachment.filename) and attachment.size < MAX_ATTACHMENT_BYTES:
                attachment_bytes = await attachment.read()
                info = {
                    'comment': discord.utils.escape_markdown(message.clean_content)[:50],
                    'date': message.created_at.astimezone(pytz.timezone("Europe/Paris")).strftime("%b %d %a %H:%M"),
                    'author': normalized_author
                }

                response = bot.build_database(attachment_bytes.decode('utf-8', errors='replace'), info)
                if response.status == dkp_bot.ResponseStatus.SUCCESS:
                    if announce and bot.is_announcement_channel_registered(): # announce
                        announcement_channel = None
                        for channel in message.guild.channels:
                            if channel.id == bot.get_announcement_channel():
                                announcement_channel = channel
                                break
                        if announcement_channel is not None:
                            await discord_respond(announcement_channel, bot.get_announcement())
                        else: # some misshap, handle default way
                            await discord_respond(message.channel, response.data)
                    else: # otherwise write standard message to upload channel
                        await discord_respond(message.channel, response.data)
                elif response.status == dkp_bot.ResponseStatus.ERROR:
                    BotLogger().get().error(response.data)
                return response.status

    return dkp_bot.ResponseStatus.IGNORE

async def spawn_bot(guild):
    try:
        config_filename = "{0}/{1}.ini".format(script_control.config_dir, guild.id)
        bot = bot_factory.new(guild.id, BotConfig(config_filename))
        if bot:
            if guild.id in bots.keys():
                del bots[guild.id]
            bots[guild.id] = bot
            for channel in guild.text_channels:
                try:  # in case we dont have access we still want to check other channels not die here
                    if (bot.is_channel_registered() and bot.check_channel(channel.id)) or not bot.is_channel_registered():
                        async for message in channel.history(limit=50):
                            status = await discord_attachment_parse(bot, message, normalize_author(message.author), False)
                            if status == dkp_bot.ResponseStatus.SUCCESS:
                                break
                except discord.Forbidden:
                    continue
            # We call it here so we will have it tracked from beginning
            bot_memory_manager.Manager().Handle(guild.id, True)
            BotLogger().get().info("Bot for server {0} total footprint: {1} B".format(
                        guild.name.encode('ascii', 'ignore').decode(), footprint.total_size(bot)))

    except (SystemExit, Exception) as exception:
        handle_exception("spawn_bot()", exception)

# Discord API

@client.event
async def on_guild_join(guild):
    try:
        await spawn_bot(guild)
        update_activity_data()
    except (SystemExit, Exception) as exception:
        handle_exception("on_guild_join()", exception)


@client.event
async def on_ready():
    try:
        if script_control.is_initialized():
            return

        for guild in client.guilds:
            await spawn_bot(guild)

        initialize_activity_data()
        update_activity_data()

        script_control.set_initialized()
        BotLogger().get().info("Ready!")

    except (SystemExit, Exception) as exception:
        handle_exception("on_ready()", exception)


@client.event
async def on_message(message):
    try:
        # Don't react to own messages
        if message.author == client.user:
            return

        # Block DMChannel at all
        if isinstance(message.channel, discord.DMChannel):
            return

        # Add per-server ratelimiting


        # Check if we have proper bot for the requester
        bot = bots.get(message.guild.id)
        if not isinstance(bot, dkp_bot.DKPBot):
            return

        request_info = get_request_info(message)
        # request_info = {
        #     'author': author,
        #     'channel': message.channel.id,
        #     'is_privileged': is_privileged
        # }

        if client.user in message.mentions:
            # Handle bot mention
            response = bot.call_help("", request_info)
        else:
            # Handle command
            response = bot.handle(message.clean_content, request_info)

        if response and isinstance(response, dkp_bot.Response):
            if response.status == dkp_bot.ResponseStatus.SUCCESS:
                response_channel = await discord_get_response_channel(message, response.direct_message)
                await discord_respond(response_channel, response.data)
                if isinstance(response_channel, discord.DMChannel):
                    await message.delete()
            elif response.status == dkp_bot.ResponseStatus.ERROR:
                BotLogger().get().error(response.data)
                return
            elif response.status == dkp_bot.ResponseStatus.REQUEST:
                if response.data == dkp_bot.Request.RESPAWN:
                    response_channel = await discord_get_response_channel(message, response.direct_message)
                    await spawn_bot(message.guild) # Respawn bot
                    await discord_respond(response_channel, BasicSuccess("Bot created successfuly").get())
                else:
                    BotLogger().get().error("Requested but not respawn. This should not happen atm")

        # No command response
        # Check if we have attachment on registered channel
        if (bot.is_channel_registered() and bot.check_channel(message.channel.id)) or not bot.is_channel_registered():
            await discord_attachment_parse(bot, message, normalize_author(message.author), True)

    except (SystemExit, Exception) as exception:
        handle_exception(message.content, exception)


if __name__ == "__main__":
    if len(sys.argv) != 6:
        sys.exit(1)
    main(script_control)
