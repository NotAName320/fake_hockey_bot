"""
Game listener and processor for Fake Hockey Bot

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

from nextcord.ext import commands

from discord_db_client import Bot


class Listener(commands.Cog):
    """Handles game-related functions, and manages game-related tasks and caches."""
    def __init__(self, bot: Bot):
        self.bot = bot

    def cog_unload(self):
        pass  # Tasks will be unloaded here when necessary. I have no clue why this isn't automatically done by nextcord
    
    @commands.Cog.listener(name="on_message")
    async def process_game(self, message):
        # Do not listen to messages that are sent by the bot itself or commands
        if message.content.startswith(self.bot.command_prefix) or message.author.id == self.bot.user.id:
            return
        
        if "cookie" in message.content.lower():
            await message.channel.send("🍪")


def setup(bot: Bot):
    bot.add_cog(Listener(bot))


def teardown(bot: Bot):
    bot.remove_cog("Listener")
