import sys
import io
import atexit
import pickle
import asyncio
import pytz
from configparser import ConfigParser

import disnake
from disnake.ext import commands

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

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 5MB #3145728 # 3MB

class ScriptControl:
    __initialized = False
    token = 0
    config_dir = "/tmp"
    storage_dir = "/tmp"
    in_memory_objects_limit = 2

    def initialize(
        self, token, config_dir="/tmp", storage_dir="/tmp", in_memory_objects_limit=2
    ):
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
# client = disnake.Client(chunk_guilds_at_startup=False)
discord_bot = commands.Bot(command_prefix="", test_guilds=[746131486234640444]) 
# discord_bot = commands.InteractionBot(command_prefix="", test_guilds=[746131486234640444]) # no messages parsing # TBD
bots = {}
activity = LoopActivity("")
activity.update({"booting": "booting..."})
super_user = superuser.Superuser()


async def discord_update_activity():
    BotLogger().get().info("Presence awaiting ready")
    await discord_bot.wait_until_ready()
    BotLogger().get().info("Presence running")
    while True:
        await discord_bot.change_presence(activity=activity.next())
        await asyncio.sleep(30)


def get_config(filepath):
    config = ConfigParser()
    config.read(filepath)

    section = "General"
    token = config.get(section, "token")
    su_id = config.getint(section, "su-id")
    in_memory_objects_limit = config.get(section, "in-memory-objects-limit")
    section = "Directories"
    config_dir = config.get(section, "config")
    storage_dir = config.get(section, "storage")
    log_dir = config.get(section, "log")
    section = "Raid-Helper"
    raidhelper_api_endpoint = config.get(section, "endpoint")
    raidhelper_api_token = config.get(section, "token")

    return (
        token,
        config_dir,
        storage_dir,
        in_memory_objects_limit,
        log_dir,
        su_id,
        raidhelper_api_endpoint,
        raidhelper_api_token,
    )


# Cleanup
def cleanup():
    for bot in bots.values():
        if isinstance(bot, dkp_bot.DKPBot):
            bot.shutdown()
    BotLogger().get().info("Bye Bye!")


# Main
def main(control: ScriptControl):
    # Get Config
    (
        token,
        config_dir,
        storage_dir,
        in_memory_objects_limit,
        log_dir,
        su_id,
        raidhelper_api_endpoint,
        raidhelper_api_token,
    ) = get_config(sys.argv[1])
    control.initialize(token, config_dir, storage_dir, in_memory_objects_limit)
    # Initialize Logs
    BotLogger().initialize(log_dir)
    # Initialize super user
    super_user.initialize(su_id, bots)
    # Initialize Memory Manager
    bot_memory_manager.Manager().initialize(
        control.in_memory_objects_limit, bots, pickle_data, unpickle_data
    )
    # Initialize Raid Helper Integration
    raidhelper.RaidHelper().initialize(raidhelper_api_endpoint, raidhelper_api_token)
    # Register atexit script
    atexit.register(cleanup)
    # Create inifite task
    discord_bot.loop.create_task(discord_update_activity())
    # Run client listener
    discord_bot.run(control.token)


# Utility
def initialize_activity_data():
    activity.remove("booting")
    activity.update(
        {
            "version": "{0}".format(build_info.VERSION),
            "discord": "{0}".format(build_info.SUPPORT_SERVER),
            "slash": "Check out new /slash commands!",
        }
    )


def update_activity_data():
    activity.update({"servers": "{0} servers".format(len(discord_bot.guilds))})


# Error handling


def handle_exception(note, exception):
    BotLogger().get().error("=== EXCEPTION ===")
    BotLogger().get().error(note)
    BotLogger().get().error(exception, exc_info=True, stack_info=True)
    BotLogger().get().error("====== END ======")


# Data related
@trace
def pickle_data(uid, data):
    with open(
        "{0}/pickle.{1}.bin".format(script_control.storage_dir, uid), "wb"
    ) as file_pointer:
        pickle.dump(data, file_pointer)


@trace
def unpickle_data(uid):
    data = None
    with open(
        "{0}/pickle.{1}.bin".format(script_control.storage_dir, uid), "rb"
    ) as file_pointer:
        data = pickle.load(file_pointer)
    return data


# Discord related
@trace
def normalize_author(author):
    if isinstance(author, disnake.Member):
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
def get_request_info(message: disnake.Message):
    # Normalize author
    author = normalize_author(message.author)

    # Check if user is privileged user (administrator)
    is_privileged = False
    if isinstance(message.author, disnake.Member):
        # is_privileged = message.author.permissions_in(message.channel).administrator
        is_privileged = message.channel.permissions_for(message.author).administrator

    request_info = {
        "server": {"name": message.guild.name, "id": message.guild.id},
        "author": {"name": author, "id": message.author.id, "raw": message.author.name},
        "channel": {"name": message.channel.name, "id": message.channel.id},
        "is_privileged": is_privileged,
        "mentions": {"roles": [], "channels": []},
    }

    for role_mention in message.role_mentions:
        if role_mention.mentionable:
            request_info["mentions"]["roles"].append(role_mention.id)

    for channel_mention in message.channel_mentions:
        if isinstance(channel_mention, disnake.TextChannel):
            # bot_permissions =  discord_bot.user.permissions_in(channel_mention)
            # if bot_permissions.read_messages and bot_permissions.send_messages:
            request_info["mentions"]["channels"].append(channel_mention.id)

    return request_info

@trace
def get_interaction_request_info(interaction: disnake.Interaction):
    # Normalize author
    author = normalize_author(interaction.author)

    # Check if user is privileged user (administrator)
    is_privileged = False
    if isinstance(interaction.author, disnake.Member):
        is_privileged = interaction.channel.permissions_for(interaction.author).administrator

    request_info = {
        "server": {"name": interaction.guild.name, "id": interaction.guild.id},
        "author": {"name": author, "id": interaction.author.id, "raw": interaction.author.name},
        "channel": {"name": interaction.channel.name, "id": interaction.channel.id},
        "is_privileged": is_privileged,
        "mentions": {"roles": [], "channels": []},
    }

    # for role_mention in interaction.role_mentions:
    #     if role_mention.mentionable:
    #         request_info["mentions"]["roles"].append(role_mention.id)

    # for channel_mention in message.channel_mentions:
    #     if isinstance(channel_mention, disnake.TextChannel):
    #         # bot_permissions =  discord_bot.user.permissions_in(channel_mention)
    #         # if bot_permissions.read_messages and bot_permissions.send_messages:
    #         request_info["mentions"]["channels"].append(channel_mention.id)

    return request_info


@trace
async def discord_get_response_channel(message, direct_message: bool):
    response_channel = message.channel
    if direct_message:
        dm_channel = await message.author.create_dm()
        if dm_channel is None:
            BotLogger().get().error(
                "Unable to create DM channel with {0}".format(message.author)
            )
        else:
            BotLogger().get().debug("Responding on DM channel")
            return dm_channel
    BotLogger().get().debug("Responding on guild channel")
    return response_channel


@trace
async def discord_build_embed(data):
    return disnake.Embed().from_dict(data)


@trace
async def discord_build_file(data):
    return disnake.File(data)


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
                BotLogger().get().debug(
                    "Responding on channel %d with message: %s", channel.id, response
                )
                await channel.send(response)
            elif isinstance(response, dict):
                BotLogger().get().debug(
                    "Responding on channel %d with embed: %s", channel.id, response
                )
                await channel.send(embed=await discord_build_embed(response))
            elif isinstance(response, io.IOBase):
                BotLogger().get().debug(
                    "Responding on channel %d with file", channel.id
                )
                await channel.send(file=await discord_build_file(response))
            elif isinstance(response, tuple):
                message = response[0]
                extra = response[1]
                if isinstance(message, str):
                    if isinstance(extra, dict):
                        BotLogger().get().debug(
                            "Responding on channel %d with message: %s and embed %s",
                            channel.id,
                            message,
                            extra,
                        )
                        await channel.send(
                            message, embed=await discord_build_embed(extra)
                        )
                    elif isinstance(extra, io.IOBase):
                        BotLogger().get().debug(
                            "Responding on channel %d with message: %s and file",
                            channel.id,
                            message,
                        )
                        await channel.send(
                            message, file=await discord_build_file(extra)
                        )
    except (disnake.errors.Forbidden, disnake.errors.NotFound) as exception:
        BotLogger().get().warning(str(exception))
    except disnake.HTTPException as exception:
        exception = str(exception).lower()
        if (
            (exception.find("size exceeds maximum") != -1)
            or (exception.find("or fewer in length") != -1)
            and not self_call
        ):
            embed = BasicError(
                "Response data exceeded Discord limits. Please limit the response in `display` configuration."
            )
            BotLogger().get().debug(
                "Response data exceeded Discord limits for response on channel %d",
                channel.id,
            )
            await discord_respond(channel, embed.get(), True)
        else:
            BotLogger().get().warning(str(exception))


@trace
async def discord_delete(handle):
    try:
        if isinstance(handle, disnake.Message):
            BotLogger().get().debug(
                "Removing message (%d) from channel [%s (%d)]",
                handle.id,
                handle.channel.name,
                handle.channel.id,
            )
            await handle.delete()
    except (
        disnake.errors.Forbidden,
        disnake.errors.NotFound,
        disnake.errors.HTTPException,
    ) as exception:
        BotLogger().get().warning(str(exception))


@trace
async def discord_announce(bot: dkp_bot.DKPBot, channels):
    announcement_channel = None
    for channel in channels:
        if channel.id == discord_bot.get_announcement_channel():
            announcement_channel = channel
            break
    if announcement_channel is not None:
        await discord_respond(announcement_channel, discord_bot.get_announcement())
        return

    BotLogger().get().debug("Announcement channel not found")


@trace
async def discord_attachment_check(
    bot: dkp_bot.DKPBot, message: disnake.Message, author: str, announce: bool
):
    if len(message.attachments) > 0:
        for attachment in message.attachments:
            if (
                bot.check_attachment_name(attachment.filename)
                and attachment.size < MAX_ATTACHMENT_BYTES
            ):
                attachment_bytes = await attachment.read()
                info = {
                    "comment": disnake.utils.escape_markdown(message.clean_content)[
                        :75
                    ],
                    "date": message.created_at.replace(tzinfo=pytz.timezone("UTC"))
                    .astimezone(bot.get_timezone())
                    .strftime("%b %d %a %H:%M"),
                    "author": normalize_author(author),
                }
                BotLogger().get().info(
                    "Building database for server [%s (%d)]",
                    message.guild.name,
                    message.guild.id,
                )
                response = bot.build_database(
                    attachment_bytes.decode("utf-8", errors="replace"), info
                )
                if response.status == dkp_bot.ResponseStatus.SUCCESS:
                    if (
                        announce and bot.is_announcement_channel_registered()
                    ):  # announce
                        await discord_announce(bot, message.guild.channels)
                    await discord_respond(message.channel, response.data)
                elif response.status == dkp_bot.ResponseStatus.ERROR:
                    await discord_respond(message.channel, response.data)
                return response.status
            else:
                BotLogger().get().debug(
                    "Ignoring file [%s] with size [%d B] on channel [%s (%d)] in [%s (%d)]",
                    attachment.filename,
                    attachment.size,
                    message.channel.name,
                    message.channel.id,
                    message.guild.name,
                    message.guild.id,
                )
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
                BotLogger().get().info(
                    "Bot for %s (%d) already exists. Recreating.", guild.name, guild.id
                )
                del bots[guild.id]
            bots[guild.id] = bot
            for channel in guild.text_channels:
                try:  # in case we dont have access we still want to check other channels not die here
                    if (
                        bot.is_channel_registered() and bot.check_channel(channel.id)
                    ) or not bot.is_channel_registered():
                        async for message in channel.history(limit=50):
                            status = await discord_attachment_check(
                                bot, message, message.author, False
                            )
                            if status in [
                                dkp_bot.ResponseStatus.SUCCESS,
                                dkp_bot.ResponseStatus.ERROR,
                            ]:
                                break
                except disnake.Forbidden:
                    continue
            # We call it here so we will have it tracked from beginning
            bot_memory_manager.Manager().Handle(guild.id, True)
            BotLogger().get().info(
                "Bot for server [{0} ({1})] total footprint: {2} B".format(
                    guild.name, guild.id, footprint.total_size(bot)
                )
            )
            return True

    except Exception as exception:
        handle_exception("spawn_bot()", exception)
        return False


@trace
async def handle_response_as_message(
    interaction: disnake.Interaction, request_info: dict, response: dkp_bot.Response
):
    if response and isinstance(response, dkp_bot.Response):
        ## SUCCESS
        if response.status == dkp_bot.ResponseStatus.SUCCESS:
            response_channel = await discord_get_response_channel(
                interaction, response.direct_message
            )
            if response.direct_message:
                if isinstance(response_channel, disnake.DMChannel):
                    await discord_respond(response_channel, response.data)
                    # await discord_delete(interaction)
                else:
                    BotLogger().get().warning(
                        "Unable to respond on DM to message %s", interaction
                    )
                    await discord_respond(
                        response_channel,
                        BasicError("Unable to respond to DM request.").get(),
                    )
            else:
                await discord_respond(response_channel, response.data)
        ## ERROR
        elif response.status == dkp_bot.ResponseStatus.ERROR:
            BotLogger().get().error(response.data)
        ## RELOAD
        elif response.status == dkp_bot.ResponseStatus.RELOAD:
            guild = None
            if response.data in bots.keys():
                bots[response.data].shutdown()
                for _guild in discord_bot.guilds:
                    if _guild.id == response.data:
                        guild = _guild
            if guild is not None:
                response_channel = await discord_get_response_channel(
                    interaction, response.direct_message
                )
                spawned = await spawn_bot(guild)  # Respawn bot
                if spawned:
                    await discord_respond(
                        response_channel,
                        BasicSuccess("Reloaded bot successfuly.").get(),
                    )
                else:
                    await discord_respond(
                        response_channel,
                        BasicCritical(
                            "Unable to reload bot. Please report this issue to the author. Previous one will continue to be usable."
                        ).get(),
                    )
            else:
                BotLogger().get().error(
                    "Reload invalid bot id %s on channel [%s (%d)]",
                    response.data,
                    interaction.channel.name,
                    interaction.channel.id,
                )
        ## DELEGATE
        elif response.status == dkp_bot.ResponseStatus.DELEGATE:
            return super_user.handle(response.data[0], response.data[1], request_info)

    return None


# Discord API
@trace
@discord_bot.event
async def on_guild_join(guild):
    try:
        await spawn_bot(guild)
        update_activity_data()
    except Exception as exception:
        handle_exception("on_guild_join()", exception)


@trace
@discord_bot.event
async def on_connect():
    BotLogger().get().info("Connected to discord gateway")


@trace
@discord_bot.event
async def on_disconnect():
    BotLogger().get().info("Disconnected from discord gateway")


@trace
@discord_bot.event
async def on_ready():
    try:
        if script_control.is_initialized():
            return

        BotLogger().get().info(
            "Starting initializing bot for {0} servers".format(len(discord_bot.guilds))
        )

        for guild in discord_bot.guilds:
            await spawn_bot(guild)

        initialize_activity_data()
        update_activity_data()

        script_control.set_initialized()
        BotLogger().get().info("Ready!")

    except Exception as exception:
        handle_exception("on_ready()", exception)


@trace
@discord_bot.event
async def on_message(message):
    try:
        # Don't react to own messages
        if message.author == discord_bot.user:
            return

        # Block DMChannel at all
        if isinstance(message.channel, disnake.DMChannel):
            return

        # Add per-server ratelimiting

        # Check if we have proper bot for the requester
        bot = bots.get(message.guild.id)
        if not isinstance(bot, dkp_bot.DKPBot):
            if script_control.is_initialized():
                BotLogger().get().critical(
                    "Missing bot for %s (%d)", message.guild.name, message.guild.id
                )
            return

        request_info = get_request_info(message)
        BotLogger().get().debug(
            "Request from user [%s (%d)] in [%s (%d)] info %s",
            message.author,
            message.author.id,
            message.guild.name,
            message.guild.id,
            request_info,
        )

        # response = None
        # if discord_bot.user in message.mentions:
        #     # Handle bot mention
        #     response = bot.call_help("", request_info)
        # else:
        # Handle command
        response = bot.handle(message.clean_content, request_info)

        delegation_limit = 2
        while (response is not None) and (delegation_limit > 0):
            response = await handle_response_as_message(message, request_info, response)
            delegation_limit = delegation_limit - 1

        # No command response
        # Check if we have attachment on registered channel
        if (
            bot.is_channel_registered() and bot.check_channel(message.channel.id)
        ) or not bot.is_channel_registered():
            await discord_attachment_check(bot, message, message.author, True)

    except Exception as exception:
        handle_exception(message.content, exception)

@trace
async def handle_call(interaction, params, request, private_response=False):
    await interaction.response.defer()
    fallback = True

    try:
        # pass
        # # Don't react to own messages
        # if interaction.author == discord_bot.user:
        #     return

        # Block DMChannel at all
        if isinstance(interaction.channel, disnake.DMChannel):
            return

        # # Add per-server ratelimiting

        # Check if we have proper bot for the requester
        bot = bots.get(interaction.guild.id)
        if not isinstance(bot, dkp_bot.DKPBot):
            if script_control.is_initialized():
                BotLogger().get().critical(
                    "Missing bot for %s (%d)", interaction.guild.name, interaction.guild.id
                )
            return

        request_info = get_interaction_request_info(interaction)
        BotLogger().get().debug(
            "Interaction with user [%s (%d)] in [%s (%d)] info %s -> (%s)",
            interaction.author,
            interaction.author.id,
            interaction.guild.name,
            interaction.guild.id,
            request_info,
            params
        )

        # response = None
        # if discord_bot.user in message.mentions:
        #     # Handle bot mention
        #     response = bot.call_help("", request_info)
        # else:
        # Handle command
        separator = " "
        if params is None:
            separator = ""
            params = ""

        response = bot.handle(bot.get_prefix() + request + separator + params, request_info)

        delegation_limit = 2
        while (response is not None) and (delegation_limit > 0):
            response = await handle_response_as_message(interaction, request_info, response)
            delegation_limit = delegation_limit - 1

        # No command response
        # Check if we have attachment on registered channel
        # if (
        #     bot.is_channel_registered() and bot.check_channel(interaction.channel.id)
        # ) or not bot.is_channel_registered():
        #     await discord_attachment_check(bot, interaction, interaction.author, True)
    except Exception as exception:
        handle_exception(params, exception)
    
    if fallback:
        await interaction.edit_original_message(content="Internal Error")

#########################
### DISCORD Menu CMDS ###
#########################

@discord_bot.message_command(name="DKP", guild_ids=[746131486234640444])
async def message_dkp(interaction: disnake.ApplicationCommandInteraction):
    await handle_call(interaction, normalize_author(interaction.author), 'dkp')

@discord_bot.message_command(name="EPGP", guild_ids=[746131486234640444])
async def message_epgp(interaction: disnake.ApplicationCommandInteraction):
    await handle_call(interaction, normalize_author(interaction.author), 'epgp')

@discord_bot.message_command(name="RCLC", guild_ids=[746131486234640444])
async def message_rc(interaction: disnake.ApplicationCommandInteraction):
    await handle_call(interaction, normalize_author(interaction.author), 'rc')

@discord_bot.message_command(name="Raid Loot", guild_ids=[746131486234640444])
async def message_raidloot(interaction: disnake.ApplicationCommandInteraction):
    await handle_call(interaction, "", 'raidloot')

##########################
### DISCORD Slash CMDS ###
##########################

@discord_bot.slash_command(description="Request player or group DKP.")
async def dkp(interaction: disnake.ApplicationCommandInteraction,
        target: str=commands.Param(description="Player name(s), class(es) or alias(es).", default=None),
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False),
    ):
    await handle_call(interaction, target, 'dkp')
    
@discord_bot.slash_command(description="Request player or group EPGP.")
async def epgp(interaction: disnake.ApplicationCommandInteraction,
        target: str=commands.Param(description="Player name(s), class(es) or alias(es).", default=None),
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False),
    ):
    await handle_call(interaction, target, 'epgp')

@discord_bot.slash_command(description="Request player RCLC Info.")
async def rc(interaction: disnake.ApplicationCommandInteraction,
        target: str=commands.Param(description="Player name.", default=None),
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False),
    ):
    await handle_call(interaction, target, 'rc')

@discord_bot.slash_command(description="Request player or point history.")
async def history(interaction: disnake.ApplicationCommandInteraction,
        target: str=commands.Param(description="Player name.", default=None),
        paging: int=commands.Param(description="Older data offset.", default=0),
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False),
    ):
    await handle_call(interaction, target, 'history')

@discord_bot.slash_command(description="Request player or loot history.")
async def loot(interaction: disnake.ApplicationCommandInteraction,
        target: str=commands.Param(description="Player name.", default=None),
        paging: int=commands.Param(description="Older data offset.", default=0),
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False),
    ):
    await handle_call(interaction, target, 'loot')

@discord_bot.slash_command(description="Request recent raid loot. Supporter only command.")
async def raidloot(interaction: disnake.ApplicationCommandInteraction,
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False),
    ):
    await handle_call(interaction, "", 'raidloot')

@discord_bot.slash_command(description="Search for item. Supporter only command.")
async def item(interaction: disnake.ApplicationCommandInteraction,
        item: str=commands.Param(description="Part of item name"),
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False),
    ):
    await handle_call(interaction, item, 'item')

@discord_bot.slash_command(description="Check item value. Supporter only command.")
async def value(interaction: disnake.ApplicationCommandInteraction,
        item: str=commands.Param(description="Part of item name"),
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False),
    ):
    await handle_call(interaction, item, 'value')

@discord_bot.slash_command(description="Help!")
async def help(interaction: disnake.ApplicationCommandInteraction,
        params: str=commands.Param(description="Raw text params - for now.", default="dummy"),
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False)
    ):
    await handle_call(interaction, "", 'help')

@discord_bot.slash_command(description="Info!")
async def info(interaction: disnake.ApplicationCommandInteraction,
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False)
    ):
    await handle_call(interaction, "", 'info')

### Config ###

@discord_bot.slash_command()
async def config(interaction):
    pass

@config.sub_command(name="summary", description="Display configuration summary. Administrator only command.")
async def config_summary(interaction: disnake.ApplicationCommandInteraction,
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False)
    ):
    await handle_call(interaction, None, 'config')

@config.sub_command(name="reload", description="Reload the bot. Required to apply some of the configuration changes. Administrator only command.")
async def config_reload(interaction: disnake.ApplicationCommandInteraction,
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False)
    ):
    await handle_call(interaction, "reload", 'config')

@config.sub_command(name="default", description="Instantly reset bot configuration to default. Administrator only command.")
async def config_default(interaction: disnake.ApplicationCommandInteraction,
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False)
    ):
    await handle_call(interaction, "default", 'config')

## Display ###

@discord_bot.slash_command(description="Update display settings. Administrator only command.")
async def display(interaction: disnake.ApplicationCommandInteraction,
        params: str=commands.Param(description="Raw text params - for now.", default="dummy"),
        private: bool=commands.Param(description="Hide the call and response from other users.", default=False)
    ):
    await handle_call(interaction, params, 'display')

####################

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(1)
    main(script_control)
