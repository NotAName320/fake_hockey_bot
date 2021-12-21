"""
Creates an async PostgreSQL connection that can be accessed with a discord.py commands client

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

import datetime
import json
import random as r

import aiohttp
import nextcord
from asyncpg import Connection
from nextcord.ext import commands


class Bot(commands.Bot):
    """Represents both a connection to the PostgreSQL Client and Discord."""
    def __init__(self, **kwargs):
        super().__init__(command_prefix=kwargs.pop("command_prefix"),
                         help_command=kwargs.pop("help_command"),
                         activity=kwargs.pop("activity"),
                         intents=kwargs.pop("intents"))

        self.db: Connection = kwargs.pop("db")

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
    bot = Bot(**kwargs)
    await bot.db.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
    return bot
