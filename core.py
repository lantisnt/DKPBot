import sys
import io
import atexit
import pickle
import asyncio
import pytz
from configparser import ConfigParser

import discord

import build_info
import dkp_bot
import bot_factory
import bot_memory_manager
from bot_config import BotConfig
from bot_logger import BotLogger, trace
from display_templates import BasicSuccess, BasicError, BasicInfo, BasicCritical
from loop_activity import LoopActivity
from bot_utility import SPLIT_DELIMITERS
import footprint
import superuser
import raidhelper

MAX_ATTACHMENT_BYTES = 5*1024*1024#5MB #3145728 # 3MB

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
client = discord.Client(chunk_guilds_at_startup=False)
bots = {}
activity = LoopActivity("")
activity.update({
    'booting'   : 'booting...'
})
super_user = superuser.Superuser()

async def discord_update_activity():
    BotLogger().get().info("Presence awaiting ready")
    await client.wait_until_ready()
    BotLogger().get().info("Presence running")
    while True:
        await client.change_presence(activity=activity.next())
        await asyncio.sleep(30)

def get_config(filepath):
    config = ConfigParser()
    config.read(filepath)

    section = "General"
    token = config.get(section, 'token')
    su_id = config.getint(section, 'su-id')
    in_memory_objects_limit = config.get(section, 'in-memory-objects-limit')
    section = "Directories"
    config_dir = config.get(section, 'config')
    storage_dir = config.get(section, 'storage')
    log_dir = config.get(section, 'log')
    section = "Raid-Helper"
    raidhelper_api_endpoint = config.get(section, 'endpoint')
    raidhelper_api_token = config.get(section, 'token')

    return (token, config_dir, storage_dir, in_memory_objects_limit, log_dir, su_id, raidhelper_api_endpoint, raidhelper_api_token)

# Cleanup
def cleanup():
    for bot in bots.values():
        if isinstance(bot, dkp_bot.DKPBot):
            bot.shutdown()
    BotLogger().get().info("Bye Bye!")

# Main
def main(control: ScriptControl):
    # Get Config
    (token, config_dir, storage_dir, in_memory_objects_limit, log_dir, su_id, raidhelper_api_endpoint, raidhelper_api_token) = get_config(sys.argv[1])
    control.initialize(token, config_dir, storage_dir, in_memory_objects_limit)
    # Initialize Logs
    BotLogger().initialize(log_dir)
    # Initialize super user
    super_user.initialize(su_id, bots)
    # Initialize Memory Manager
    bot_memory_manager.Manager().initialize(control.in_memory_objects_limit, bots, pickle_data, unpickle_data)
    # Initialize Raid Helper Integration
    raidhelper.RaidHelper().initialize(raidhelper_api_endpoint, raidhelper_api_token)
    # Register atexit script
    atexit.register(cleanup)
    # Create inifite task
    client.loop.create_task(discord_update_activity())
    # Run client listener
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
@trace
def pickle_data(uid, data):
    with open("{0}/pickle.{1}.bin".format(script_control.storage_dir, uid), "wb") as file_pointer:
        pickle.dump(data, file_pointer)

@trace
def unpickle_data(uid):
    data = None
    with open("{0}/pickle.{1}.bin".format(script_control.storage_dir, uid), "rb") as file_pointer:
        data = pickle.load(file_pointer)
    return data

# Discord related
@trace
def normalize_author(author):
    if isinstance(author, discord.Member):
        if author.nick:
            normalized = author.nick
        else:
            normalized = author
    else:
        normalized = author

    normalized = "{0}".format(normalized)
    for delimiter in SPLIT_DELIMITERS:
        normalized = normalized.split(delimiter)[0].strip()

    return normalized

@trace
def get_request_info(message: discord.Message):
    # Normalize author
    author = normalize_author(message.author)

    # Check if user is privileged user (administrator)
    is_privileged = False
    if isinstance(message.author, discord.Member):
        is_privileged = message.author.permissions_in(message.channel).administrator

    request_info = {
        'server' : {
            'name' : message.guild.name,
            'id' : message.guild.id
        },
        'author': {
            'name' : author,
            'id'   : message.author.id,
            'raw'  : message.author.name
        },
        'channel' : {
            'name' : message.channel.name,
            'id' : message.channel.id
        },
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
            #bot_permissions =  client.user.permissions_in(channel_mention)
            #if bot_permissions.read_messages and bot_permissions.send_messages:
            request_info['mentions']['channels'].append(channel_mention.id)

    return request_info

@trace
async def discord_get_response_channel(message, direct_message: bool):
    response_channel = message.channel
    if direct_message:
        dm_channel = await message.author.create_dm()
        if dm_channel is None:
            BotLogger().get().error('Unable to create DM channel with {0}'.format(
                    message.author))
        else:
            BotLogger().get().debug("Responding on DM channel")
            return dm_channel
    BotLogger().get().debug('Responding on guild channel')
    return response_channel

@trace
async def discord_build_embed(data):
    return discord.Embed().from_dict(data)

@trace
async def discord_build_file(data):
    return discord.File(data)

@trace
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
                BotLogger().get().debug("Responding on channel %d with message: %s", channel.id, response)
                await channel.send(response)
            elif isinstance(response, dict):
                BotLogger().get().debug("Responding on channel %d with embed: %s", channel.id, response)
                await channel.send(embed=await discord_build_embed(response))
            elif isinstance(response, io.IOBase):
                BotLogger().get().debug("Responding on channel %d with file", channel.id)
                await channel.send(file=await discord_build_file(response))
            elif isinstance(response, tuple):
                message = response[0]
                extra = response[1]
                if isinstance(message, str):
                    if isinstance(extra, dict):
                        BotLogger().get().debug("Responding on channel %d with message: %s and embed %s", channel.id, message, extra)
                        await channel.send(message, embed=await discord_build_embed(extra))
                    elif isinstance(extra, io.IOBase):
                        BotLogger().get().debug("Responding on channel %d with message: %s and file", channel.id, message)
                        await channel.send(message, file=await discord_build_file(extra))
    except (discord.errors.Forbidden, discord.errors.NotFound) as exception:
        BotLogger().get().warning(str(exception))
    except discord.HTTPException as exception:
        exception = str(exception).lower()
        if (exception.find("size exceeds maximum") != -1) or (exception.find("or fewer in length") != -1) and not self_call:
            embed = BasicError("Response data exceeded Discord limits. Please limit the response in `display` configuration.")
            BotLogger().get().debug("Response data exceeded Discord limits for response on channel %d", channel.id)
            await discord_respond(channel, embed.get(), True)
        else:
            BotLogger().get().warning(str(exception))

@trace
async def discord_delete(handle):
    try:
        if isinstance(handle, discord.Message):
            BotLogger().get().debug("Removing message (%d) from channel [%s (%d)]", handle.id, handle.channel.name, handle.channel.id)
            await handle.delete()  
    except (discord.errors.Forbidden, discord.errors.NotFound, discord.errors.HTTPException) as exception:
        BotLogger().get().warning(str(exception))

@trace
async def discord_announce(bot: dkp_bot.DKPBot, channels):
    announcement_channel = None
    for channel in channels:
        if channel.id == bot.get_announcement_channel():
            announcement_channel = channel
            break
    if announcement_channel is not None:
        await discord_respond(announcement_channel, bot.get_announcement())
        return

    BotLogger().get().debug("Announcement channel not found")

@trace
async def discord_attachment_check(bot: dkp_bot.DKPBot, message: discord.Message, author: str, announce: bool):
    if len(message.attachments) > 0:
        for attachment in message.attachments:
            if bot.check_attachment_name(attachment.filename) and attachment.size < MAX_ATTACHMENT_BYTES:
                attachment_bytes = await attachment.read()
                info = {
                    'comment': discord.utils.escape_markdown(message.clean_content)[:75],
                    'date': message.created_at.replace(tzinfo=pytz.timezone('UTC')).astimezone(bot.get_timezone()).strftime("%b %d %a %H:%M"),
                    'author': normalize_author(author)
                }
                BotLogger().get().info('Building database for server [%s (%d)]', message.guild.name, message.guild.id)
                response = bot.build_database(attachment_bytes.decode('utf-8', errors='replace'), info)
                if response.status == dkp_bot.ResponseStatus.SUCCESS:
                    if announce and bot.is_announcement_channel_registered(): # announce
                        await discord_announce(bot, message.guild.channels)
                    await discord_respond(message.channel, response.data)
                elif response.status == dkp_bot.ResponseStatus.ERROR:
                    await discord_respond(message.channel, response.data)
                return response.status
            else:
                BotLogger().get().debug("Ignoring file [%s] with size [%d B] on channel [%s (%d)] in [%s (%d)]", 
                attachment.filename, attachment.size, message.channel.name, message.channel.id,
                message.guild.name, message.guild.id)
    return dkp_bot.ResponseStatus.IGNORE

## Discord + Bot interactions
@trace
async def spawn_bot(guild):
    try:
        BotLogger().get().info("Spawn bot for %s (%d).", guild.name, guild.id)
        config_filename = "{0}/{1}.ini".format(script_control.config_dir, guild.id)
        bot = bot_factory.new(guild.id, BotConfig(config_filename))
        if bot:
            if guild.id in bots.keys():
                BotLogger().get().info("Bot for %s (%d) already exists. Recreating.", guild.name, guild.id)
                del bots[guild.id]
            bots[guild.id] = bot
            for channel in guild.text_channels:
                try:  # in case we dont have access we still want to check other channels not die here
                    if (bot.is_channel_registered() and bot.check_channel(channel.id)) or not bot.is_channel_registered():
                        async for message in channel.history(limit=50):
                            status = await discord_attachment_check(bot, message, message.author, False)
                            if status in [dkp_bot.ResponseStatus.SUCCESS, dkp_bot.ResponseStatus.ERROR]:
                                break
                except discord.Forbidden:
                    continue
            # We call it here so we will have it tracked from beginning
            bot_memory_manager.Manager().Handle(guild.id, True)
            BotLogger().get().info("Bot for server [{0} ({1})] total footprint: {2} B".format(guild.name, guild.id, footprint.total_size(bot)))
            return True

    except Exception as exception:
        handle_exception("spawn_bot()", exception)
        return False

@trace
async def handle_bot_response(message: discord.Message, request_info: dict, response: dkp_bot.Response):
    if response and isinstance(response, dkp_bot.Response):
        ## SUCCESS
        if response.status == dkp_bot.ResponseStatus.SUCCESS:
            response_channel = await discord_get_response_channel(message, response.direct_message)
            if response.direct_message:
                if isinstance(response_channel, discord.DMChannel):
                    await discord_respond(response_channel, response.data)
                    await discord_delete(message)
                else:
                    BotLogger().get().warning("Unable to respond on DM to message %s", message)
                    await discord_respond(response_channel, BasicError("Unable to respond to DM request.").get())
            else:
                await discord_respond(response_channel, response.data)
        ## ERROR
        elif response.status == dkp_bot.ResponseStatus.ERROR:
            BotLogger().get().error(response.data)
        ## RELOAD
        elif response.status == dkp_bot.ResponseStatus.RELOAD:
            guild = None
            if response.data in bots.keys():
                for _guild in client.guilds:
                    if _guild.id == response.data:
                        guild = _guild
            if guild is not None:
                response_channel = await discord_get_response_channel(message, response.direct_message)
                spawned = await spawn_bot(guild) # Respawn bot
                if spawned:
                    await discord_respond(response_channel, BasicSuccess("Reloaded bot successfuly.").get())
                else:
                    await discord_respond(response_channel, BasicCritical("Unable to reload bot. Please report this issue to the author. Previous one will continue to be usable.").get())
            else:
                BotLogger().get().error("Reload invalid bot id %s on channel [%s (%d)]", response.data, message.channel.name, message.channel.id)
        ## DELEGATE
        elif (response.status == dkp_bot.ResponseStatus.DELEGATE):
            return super_user.handle(response.data[0], response.data[1], request_info)
#        elif (response.status == dkp_bot.ResponseStatus.SHUTDOWN):
#            cleanup()

    return None

# Discord API
@trace
@client.event
async def on_guild_join(guild):
    try:
        await spawn_bot(guild)
        update_activity_data()
    except Exception as exception:
        handle_exception("on_guild_join()", exception)

@trace
@client.event
async def on_connect():
    BotLogger().get().info("Connected to discord gateway")

@trace
@client.event
async def on_disconnect():
    BotLogger().get().info("Disconnected from discord gateway")

@trace
@client.event
async def on_ready():
    try:
        if script_control.is_initialized():
            return

        BotLogger().get().info("Starting initializing bot for {0} servers".format(len(client.guilds)))

        for guild in client.guilds:
            await spawn_bot(guild)

        initialize_activity_data()
        update_activity_data()

        script_control.set_initialized()
        BotLogger().get().info("Ready!")

    except Exception as exception:
        handle_exception("on_ready()", exception)

@trace
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
            if script_control.is_initialized():
                BotLogger().get().critical("Missing bot for %s (%d)", message.guild.name, message.guild.id)
            return

        request_info = get_request_info(message)
        BotLogger().get().debug("Request from user [%s (%d)] in [%s (%d)] info %s", message.author, message.author.id, message.guild.name, message.guild.id, request_info)

        response = None
        if client.user in message.mentions:
            # Handle bot mention
            response = bot.call_help("", request_info)
        else:
            # Handle command
            response = bot.handle(message.clean_content, request_info)

        delegation_limit = 2
        while ((response is not None) and (delegation_limit > 0)):
            response = await handle_bot_response(message, request_info, response)
            delegation_limit = delegation_limit - 1

        # No command response
        # Check if we have attachment on registered channel
        if (bot.is_channel_registered() and bot.check_channel(message.channel.id)) or not bot.is_channel_registered():
            await discord_attachment_check(bot, message, message.author, True)

    except Exception as exception:
        handle_exception(message.content, exception)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(1)
    main(script_control)
