"""
Bot to simulate a hockey game using the principles of number guessing

Copyright (c) 2021 NotAName

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import json
import logging
import sys
import traceback

import asyncpg
import nextcord
from nextcord.ext import commands

from discord_db_client import create_bot


async def login():
    """Logs into Discord and PostgreSQL and runs the bot."""
    # Sets up logging
    logger = logging.Logger("fake_hockey_bot")
    logger.setLevel(logging.INFO)
    nextcord_logger = logging.getLogger("nextcord")
    nextcord_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename="bot.log", encoding="utf-8", mode="w")
    handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    logger.addHandler(handler)
    nextcord_logger.addHandler(handler)
    def excepthook(e_type, e_value, e_traceback):
        if issubclass(e_type, KeyboardInterrupt):
            logger.info("KeyboardInterrupt detected, stopping!")
            print("\nStopping!", file=sys.stderr)
            return
        logger.critical("".join(traceback.format_exception(e_type, e_value, tb=e_traceback)))
        sys.__excepthook__(e_type, e_value, e_traceback)
    
    sys.excepthook = excepthook

    logger.info("Starting bot...")

    # Opens credentials.json and extracts bot token
    logger.info("Opening credentials.json...")
    with open("credentials.json", "r") as credentials_file:
        credentials = json.load(credentials_file)
    logger.info("credentials.json found!")
    token = credentials["discord_token"]
    logger.info("Discord token found (but not verified)!")

    # Initializes some configuration objects
    activity = nextcord.Activity(type=nextcord.ActivityType.watching, name="your hockey games!")
    intents = nextcord.Intents.default()
    intents.members = True
    logger.info("Connecting to database...")
    db = await asyncpg.connect(**credentials["postgresql_creds"], server_settings={"application_name": "Fake Hockey Bot"})
    logger.info(f"Connection successful as user {credentials['postgresql_creds']['user']} "
                f"to database {credentials['postgresql_creds']['database']} "
                f"at server {credentials['postgresql_creds']['host']}:{credentials['postgresql_creds']['port']}")

    # Initializes client object
    client = await create_bot(command_prefix="!", activity=activity, help_command=commands.MinimalHelpCommand(), intents=intents, db=db, logger=logger)

    @client.event
    async def on_ready():
        # Saves connection and info to logs
        logger.info(f"Connected to Discord as {client.user} (ID: {client.user.id})")
        print(f"Logged in as\n{client.user}\n{client.user.id}")

    @client.event
    async def on_error(event, *args):
        """Prints out on_message listener errors to a logging channel."""
        exception = traceback.format_exc()
        print(f"Exception in {event}:", file=sys.stderr)
        print(exception, file=sys.stderr)
        logging.error(exception)
        if event == "on_message":
            message = args[0]
            log_channel = nextcord.utils.get(message.guild.channels, name="logs")
            errordesc = f"```py\n{exception}\n```"
            embed = nextcord.Embed(color=0xff0000, title="Error", description=errordesc)
            await log_channel.send(content=f"Game error in channel {message.channel.mention}", embed=embed)
    
    @client.event
    async def on_command(ctx):
        logger.debug(f"{ctx.author} called command {ctx.command.name} with args {ctx.args} in channel {ctx.message.channel.id}")
    
    async def on_command_completion(ctx):
        logger.debug(f"Command {ctx.command.name} called by {ctx.author} completed without uncaught errors")

    @client.event
    async def on_command_error(ctx, error):
        """Basic error handling, including generic messages to send for common errors"""
        error: Exception = getattr(error, "original", error)
        if ctx.command.has_error_handler():  # See TeamManagement.roster_error in cogs.py
            return

        if isinstance(error, commands.CommandNotFound):
            return await ctx.reply(f"Error: Your command was not recognized. Please refer to {client.command_prefix}help for more info.")
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply("Error: You did not provide the required argument(s). Make sure you typed the command correctly.")
        if isinstance(error, commands.CheckFailure):
            return await ctx.reply("Error: You do not have permission to use this command.")

        else:
            formatted_error = "".join(traceback.format_exception(type(error), error, tb=error.__traceback__))
            logger.error(formatted_error)
            print(f"Exception in command {ctx.command}:", file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            embed = nextcord.Embed(color=0xff0000, title="Error", description=f"```py\n{formatted_error}\n```")
            app_info = await client.application_info()
            embed.set_footer(text=f"Please contact {app_info.owner} for help.")
            await ctx.send(embed=embed)

    @client.command()
    @commands.is_owner()
    async def reload(ctx):
        status_message = await ctx.reply("Reloading bot...\n`cogs.py:` ❌\n`listener.py`: ❌")
        logger.warning("Reload command called! Reloading bot...")
        client.reload_extension("cogs")
        await status_message.edit(content="Reloading bot...\n`cogs.py:` ✅\n`listener.py`: ❌")
        client.reload_extension("listener")
        await status_message.edit(content="Bot reloaded!\n`cogs.py:` ✅\n`listener.py`: ✅")
        logger.warning("Bot reloaded!")

    # Adds cogs and runs bot
    client.load_extension("cogs")
    client.load_extension("listener")
    try:
        await client.start(token)
    except KeyboardInterrupt:
        await db.close()
        await client.close()


if __name__ == '__main__':
    asyncio.run(login())
