"""
Creates an async PostgreSQL connection that can be accessed with a discord.py commands client
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
import json
import random as r

import aiohttp
import nextcord
from asyncpg import Connection
from nextcord.ext import commands


class Bot(commands.Bot):
    """Represents both a connection to the PostgreSQL Client and Discord. Do not create this object directly; use create_bot() instead."""
    def __init__(self, **kwargs):
        # Set some flags
        allowed_mentions = nextcord.AllowedMentions.all()
        allowed_mentions.replied_user = False
        intents = nextcord.Intents.default()
        intents.members = True
        intents.message_content = True

        self.db: Connection = kwargs.pop("db")
        self.logger = kwargs.pop("logger")
        self.statements = lambda: None  # Best way to create an object that accepts attributes
        super().__init__(**kwargs, allowed_mentions=allowed_mentions, intents=intents)

    async def write(self, query: str, *args):
        """Write something to the database."""
        async with self.db.transaction():
            await self.db.execute(query, *args)

    async def webhook_template(self, webhook_name: str, template_name: str, **kwargs):
        webhook = await self.db.fetchrow("""SELECT webhookurl, templates FROM webhooks WHERE webhookname = $1""", webhook_name)
        async with aiohttp.ClientSession() as session:
            webhook_model = nextcord.Webhook.from_url(url=webhook["webhookurl"], session=session)
            await webhook_model.send(content=webhook["templates"][template_name].format(**kwargs))

    async def webhook_template_tweet(self, webhook_name: str, template_name: str, **kwargs):
        webhook = await self.db.fetchrow("""SELECT webhookurl, twitter_handle, twittername, avatar, templates FROM webhooks WHERE webhookname = $1""", webhook_name)
        embed = nextcord.Embed(description=webhook["templates"][template_name].format(**kwargs), color=0x1DA1F2, timestamp=datetime.datetime.now())
        embed.set_footer(text="Fake Twitter", icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png")
        embed.add_field(name="Retweets", value=str(r.randint(100, 2500)))
        embed.add_field(name="Likes", value=str(r.randint(100, 2500)))
        embed.set_author(name=f"{webhook['twittername']} (@{webhook['twitter_handle']})", icon_url=str(webhook["avatar"]))
        async with aiohttp.ClientSession() as session:
            webhook_model = nextcord.Webhook.from_url(url=webhook["webhookurl"], session=session)
            await webhook_model.send(embed=embed)


async def create_bot(**kwargs) -> Bot:
    """Creates a Bot object."""
    bot = Bot(**kwargs)
    await bot.db.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    team_exists = await bot.db.prepare("""SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = UPPER($1))""")
    setattr(bot.statements, "team_exists", team_exists.fetchval)
    get_role_id = await bot.db.prepare("""SELECT roleid FROM teams WHERE teamid = UPPER($1)""")

    async def role_from_id(guild_id: int, team_id: str):
        return nextcord.utils.get(bot.get_guild(guild_id).roles, id=await get_role_id.fetchval(team_id))

    def emoji_from_id(guild_id: int, team_id: str):
        return nextcord.utils.get(bot.get_guild(guild_id).emojis, name=team_id) or nextcord.utils.get(bot.get_guild(guild_id).emojis, name="UNKNOWN")
    bot.role_from_id = role_from_id
    bot.emoji_from_id = emoji_from_id
    return bot
