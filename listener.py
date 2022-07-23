"""
Game listener and processor for Fake Hockey Bot
Copyright (C) 2022 NotAName

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import datetime

import nextcord
from nextcord.ext import commands, tasks

from discord_db_client import Bot
from util import home_away_opposite


class Listener(commands.Cog):
    """Handles game-related functions, and manages game-related tasks and caches."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.check_for_deadline.start()

    @tasks.loop(hours=1)
    async def check_for_deadline(self):
        deadlines = await self.bot.db.fetch("""SELECT stadium, deadline, hometeam, awayteam, homedelays, awaydelays,
                                               waitingon_side, waitingon_pos FROM games WHERE game_active IS FALSE""")
        for game in deadlines:
            erring_team = game["hometeam"] if game["waitingon_side"] == "HOME" else game["awayteam"]
            other_team = home_away_opposite(game["waitingon_side"])
            if game["deadline"] - datetime.timedelta(hours=7) < nextcord.utils.utcnow() < game["deadline"] - datetime.timedelta(hours=6):
                stadium = self.bot.get_channel(game["stadium"])
                await stadium.send(f"Warning: ")

    @check_for_deadline.before_loop
    async def before_deadline_check(self):
        """Don't start deadline checks until fully logged into the API"""
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.check_for_deadline.cancel()

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
