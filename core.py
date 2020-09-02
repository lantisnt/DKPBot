import os
import sys
import traceback
import io

import discord

import dkp_bot
import essentialdkp_bot

TOKEN = os.environ['DISCORD_TOKEN']
#GUILD = os.environ['DISCORD_GUILD']

client = discord.Client()

bot = essentialdkp_bot.EssentialDKPBot()


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


@client.event
async def on_ready():
    try:
        for guild in client.guilds:
            print(guild.name)
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=10, file=sys.stdout)
        traceback.print_exc()


@client.event
async def on_message(message):
    try:
        # TODO very later on
        # if enabled != True:
        #    return

        # Don't react to own messages
        if message.author == client.user:
            return

        # Block DMChannel at all
        if isinstance(message.channel, discord.DMChannel):
            #print('Received message {0.content} from {1} on DMChannel: {0.channel.id}'.format(message, message.author))
            return

        # Normalize author
        author = None
        if isinstance(message.author, discord.Member):
            if message.author.nick:
                author = message.author.nick
            else:
                author = message.author
        else:
            author = message.author
        author = "{0}".format(author)
        author = author.split("#")[0].strip()
        author = author.split("/")[0].strip()
        author = author.split("\\")[0].strip()

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
                await discord_respond(message.channel, response.data)
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
            if len(message.attachments) > 0:
                for attachment in message.attachments:
                    if bot.CheckAttachmentName(attachment.filename):
                        attachment_bytes = await attachment.read()
                        print("Attachement on channel: {0}".format(message.channel.id))
                        response = bot.BuildDatabase(
                            str(attachment_bytes, 'utf-8'), message.content)
                        if response.status == dkp_bot.ResponseStatus.SUCCESS:
                            await discord_respond(message.channel, response.data)
                            return
                        elif response.status == dkp_bot.ResponseStatus.ERROR:
                            print('ERROR: {0}'.format(response.data))
                            return
    except (SystemExit, Exception):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=10, file=sys.stdout)
        traceback.print_exc()

client.run(TOKEN)
