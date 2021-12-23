"""
Cogs for Fake Hockey Bot

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

from asyncio import TimeoutError
import inspect
from typing import Optional

import nextcord
from nextcord.ext import commands

from discord_db_client import Bot


QUESTION_MARK = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Question_mark2.svg/1580px-Question_mark2.svg.png"


class TeamManagement(commands.Cog, name="Team Management"):
    """Create and manage teams."""
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="teaminfo")
    async def team_info(self, ctx, team_id: str):
        """Lists information about a certain team."""
        team_id = team_id.upper()
        team_record = await self.bot.db.fetchrow("""SELECT roleid, logourl, city, name, channelid FROM teams WHERE teamid = $1""", team_id)
        # Fetch members of a team here
        if team_record is None:
            return await ctx.reply("Error: your team ID is invalid.")
        if team_record["channelid"] is None:
            home_stadium = "*None*"
        else:
            home_stadium = self.bot.get_channel(team_record["channelid"]).mention
        color = nextcord.utils.get(ctx.guild.roles, id=team_record["roleid"]).color
        embed = nextcord.Embed(color=color, title=f"{team_record['city']} {team_record['name']} Info")
        embed.set_thumbnail(url=QUESTION_MARK if team_record["logourl"] is None else team_record["logourl"])
        embed.add_field(name="Team ID", value=team_id, inline=False)
        embed.add_field(name="City", value=team_record["city"])
        embed.add_field(name="Name", value=team_record["name"], inline=True)
        embed.add_field(name="Home Stadium", value=home_stadium, inline=True)
        embed.add_field(name="Forward", value="*None*", inline=True)
        embed.add_field(name="Defenseman", value="*None*", inline=True)
        embed.add_field(name="Goalie", value="*None*", inline=True)
        return await ctx.reply(embed=embed)

    @commands.command(name="createteam")
    @commands.has_role("bot operator")
    async def create_team(self, ctx, team_id: str):
        if len(team_id) > 3:
            return await ctx.reply("Error: Team ID too long. Team IDs must be a maximum of 3 characters.")
        team_id = team_id.upper()
        role = await ctx.guild.create_role(name="Team Name", hoist=True)
        # await self.bot.statements.add_new_team.fetch(team_id, role.id)
        await self.bot.write("""INSERT INTO teams (teamid, roleid) VALUES ($1, $2)""", team_id, role.id)
        embed = nextcord.Embed(color=0, title="Team Name Info")
        embed.set_thumbnail(url=QUESTION_MARK)
        embed.add_field(name="Team ID", value=team_id, inline=False)
        embed.add_field(name="City", value="Team")
        embed.add_field(name="Name", value="Name", inline=True)
        embed.add_field(name="Home Stadium", value="*None*", inline=True)
        embed.add_field(name="Forward", value="*None*", inline=True)
        embed.add_field(name="Defenseman", value="*None*", inline=True)
        embed.add_field(name="Goalie", value="*None*", inline=True)
        await ctx.reply(content=f"Team Created. Use command `{self.bot.command_prefix}editteam` to change team attributes.", embed=embed)

    @commands.group(name="editteam")
    @commands.has_role("bot operator")
    async def edit_team(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.reply("Please specify what attribute of the team you want to change!\n"
                                   "Valid attributes are:\n"
                                   "city: String\n"
                                   "name: String\n"
                                   "stadium: Text Channel\n"
                                   "logo: String of a valid image URL\n"
                                   "color: 6 character string (hex code without #)\n\n"
                                   f"To add or remove players, use the `{self.bot.command_prefix}roster` command instead.")

    @edit_team.command()
    async def city(self, ctx, team_id: str, *, new_city: str):
        team_id = team_id.upper()
        team_record = await self.bot.db.fetchrow("""SELECT name, roleid FROM teams WHERE teamid = $1""", team_id)
        if team_record is None:
            return await ctx.reply("Error: your team ID is invalid.")
        await self.bot.write("""UPDATE teams SET city = $1 WHERE teamid = $2""", new_city, team_id)
        role = nextcord.utils.get(ctx.guild.roles, id=team_record["roleid"])
        await role.edit(name=f"{new_city} {team_record['name']}")
        return await ctx.reply(f"Success: Team name is now {new_city} {team_record['name']}")

    @edit_team.command()
    async def name(self, ctx, team_id: str, *, new_name: str):
        team_id = team_id.upper()
        team_record = await self.bot.db.fetchrow("""SELECT city, roleid FROM teams WHERE teamid = $1""", team_id)
        if team_record is None:
            return await ctx.reply("Error: your team ID is invalid.")
        await self.bot.write("""UPDATE teams SET name = $1 WHERE teamid = $2""", new_name, team_id)
        role = nextcord.utils.get(ctx.guild.roles, id=team_record["roleid"])
        await role.edit(name=f"{team_record['city']} {new_name}")
        return await ctx.reply(f"Success: Team name is now {team_record['city']} {new_name}")

    @edit_team.command()
    async def stadium(self, ctx, team_id: str, new_stadium: nextcord.TextChannel):
        team_id = team_id.upper()
        team_exists = await self.bot.db.fetchval("""SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)""", team_id)
        if not team_exists:
            return await ctx.reply("Error: your team ID is invalid.")
        await self.bot.write("""UPDATE teams SET channelid = $1 WHERE teamid = $2""", new_stadium.id, team_id)
        return await ctx.reply(f"Success: {new_stadium.mention} is now the specified team's home stadium.")

    @edit_team.command()
    async def logo(self, ctx, team_id: str, *, logo_url: str):
        team_id = team_id.upper()
        team_exists = await self.bot.db.fetchval("""SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)""", team_id)
        if not team_exists:
            return await ctx.reply("Error: your team ID is invalid.")
        await self.bot.write("""UPDATE teams SET logourl = $1 WHERE teamid = $2""", logo_url, team_id)
        return await ctx.reply(f"Success: Changed the specified team's logo.")

    @edit_team.command(aliases=['colour'])
    async def color(self, ctx, team_id: str, *, new_color: str):
        team_id = team_id.upper()
        role_id = await self.bot.db.fetchval("""SELECT roleid FROM teams WHERE teamid = $1""", team_id)
        if role_id is None:
            return await ctx.reply("Error: your team ID is invalid.")
        role = nextcord.utils.get(ctx.guild.roles, id=role_id)
        await role.edit(color=int(new_color, 16))
        return await ctx.reply(f"Success: Team color changed.")


class PlayerManagement(commands.Cog, name="Player Management"):
    """Manage and edit individual players."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.active_registrations = []

    @commands.command()
    async def register(self, ctx):
        player_already_registered = await self.bot.db.fetchval("""SELECT EXISTS(SELECT 1 FROM players WHERE playerid = $1)""", ctx.author.id)
        if player_already_registered:
            return await ctx.reply(f"Error: You have already registered. Please ask a commissioner for help with changing your player.")
        if ctx.author.id in self.active_registrations:
            return await ctx.reply("Error: You have an active registration process still going on. Reply to your registration message with \"ABORT\" and run this command again to start over.")
        embed = nextcord.Embed(color=0, title="New Player Registration")
        embed.set_thumbnail(url=ctx.author.avatar.url)
        embed.set_footer(text="Reply with \"ABORT\" at any time to cancel registration or start over.")
        embed.add_field(name="First Name", value="*None*")
        embed.add_field(name="Last Name", value="*None*")
        embed.add_field(name="Position", value="*None*")
        initial_message = await ctx.author.send(content="Player registration has started. Please reply to this message with what you want your `First Name` to be.", embed=embed)
        await ctx.reply("Please check your DMs for more details.")
        self.active_registrations.append(ctx.author.id)

        async def abort(abort_message):
            self.active_registrations.remove(ctx.author.id)
            embed.clear_fields()
            embed.description = "Registration aborted."
            await initial_message.edit(content="Registration aborted.", embed=embed)
            return await abort_message.reply("Registration aborted successfully!")

        def check(m):
            return m.channel == initial_message.channel

        def reaction_check(reaction, user):
            return reaction.message.channel == initial_message.channel and user == ctx.author and reaction.emoji in ["✅", "❌"]

        try:
            message = await self.bot.wait_for("message", timeout=600.0, check=check)
            first_name = message.content
            if first_name == "ABORT":
                return await abort(message)
            embed.set_field_at(0, name="First Name", value=first_name)
            await initial_message.edit(content="Please reply to this message with what you want your `Last Name` to be.", embed=embed)
            message = await self.bot.wait_for("message", timeout=600.0, check=check)
            last_name = message.content
            if last_name == "ABORT":
                return await abort(message)
            embed.set_field_at(1, name="Last Name", value=last_name)
            await initial_message.edit(content="Please reply to this message with what you want your `Position` to be. You can choose from:\n"
                                               "Forward (offense)\n"
                                               "Defenseman (defense)\n"
                                               "Goalie", embed=embed)
            while True:
                message = await self.bot.wait_for("message", timeout=600.0, check=check)
                position = message.content.upper()
                if position == "ABORT":
                    return await abort(message)
                if position not in ["GOALIE", "FORWARD", "DEFENSEMAN"]:
                    await message.reply("Error: Please type a valid position in your message. Positions include:\n"
                                        "Forward (offense)\n"
                                        "Defenseman (defense)\n"
                                        "Goalie")
                    continue
                embed.set_field_at(2, name="Position", value=position.title())
                break
            archetype = None
            formatted_archetype = None  # Seperate value formatted_archetype will track simplified archetype name for database
            if position != "GOALIE":
                embed.add_field(name="Archetype", value="*None*")
                if position == "DEFENSEMAN":
                    await initial_message.edit(content="Please reply to this message with what you want your `Archetype` to be. You can choose from:\n"
                                                       "Enforcer (bonus to passing ranges)\n"
                                                       "Offensive Defenseman (bonus to shooting ranges)\n"
                                                       "Finesser (bonus to deking ranges)", embed=embed)
                else:
                    await initial_message.edit(content="Please reply to this message with what you want your `Archetype` to be. You can choose from:\n"
                                                       "Playmaker (bonus to passing ranges)\n"
                                                       "Sniper (bonus to shooting ranges)\n"
                                                       "Dangler (bonus to deking ranges)", embed=embed)
                while True:
                    message = await self.bot.wait_for("message", timeout=600.0, check=check)
                    archetype = message.content.upper()
                    if archetype == "ABORT":
                        return await abort(message)
                    if archetype in ["ENFORCER", "PLAYMAKER"]:
                        formatted_archetype = "PASSER"
                    if archetype in ["OFFENSIVE DEFENSEMAN", "SNIPER"]:
                        formatted_archetype = "SHOOTER"
                    if archetype in ["FINESSER", "DANGLER"]:
                        formatted_archetype = "DEKER"
                    if formatted_archetype is None:
                        await message.reply("Error: Please type a valid archetype in your message. Archetypes include:"
                                            "Playmaker (bonus to passing ranges)\n"
                                            "Sniper (bonus to shooting ranges)\n"
                                            "Dangler (bonus to deking ranges)")
                        continue
                    embed.set_field_at(3, name="Archetype", value=archetype.title())
                    break
            await initial_message.add_reaction("✅")
            await initial_message.add_reaction("❌")
            await initial_message.edit(content="Your application has finished. Send it to the Commissioners' Office for approval?", embed=embed)
            approval_reaction = await self.bot.wait_for("reaction_add", timeout=600.0, check=reaction_check)
            if approval_reaction == "❌":
                return await abort(initial_message)
            self.active_registrations.remove(ctx.author.id)
            await initial_message.edit("Registration finished. Sending to Commissioners' Office.")
            await self.bot.write("""INSERT INTO players
                                    (playerid, playerposition, playertype, firstname, lastname)
                                    VALUES ($1, $2, $3, $4, $5)""",
                                 ctx.author.id, position, formatted_archetype, first_name, last_name)
            approval_channel = nextcord.utils.get(ctx.message.guild.channels, name="new-player-approvals")
            embed = nextcord.Embed(color=0, title="New Application")
            embed.set_thumbnail(url=ctx.author.avatar.url)
            embed.add_field(name="Name", value=f"{first_name} {last_name}")
            embed.add_field(name="Position", value=position.title())
            if archetype is not None:
                embed.add_field(name="Archetype", value=archetype.title())
            embed.add_field(name="User", value=ctx.author.mention, inline=False)
            return await approval_channel.send(content=f"New application received. "
                                                       f"Issue command `{self.bot.command_prefix}approve {ctx.author.id}` to approve the application and "
                                                       f"`{self.bot.command_prefix}reject {ctx.author.id} [reason]` to reject.", embed=embed)
        except TimeoutError:
            self.active_registrations.remove(ctx.author.id)
            embed.clear_fields()
            embed.description = "Registration timed out."
            await initial_message.edit(content="Registration automatically abandoned.", embed=embed)
            return await ctx.author.send("There have been 10 minutes since the last reply.\nRegistration has automatically terminated. Please restart the registration process.")

    @commands.command()
    @commands.has_role("bot operator")
    async def approve(self, ctx, player_id: int):
        player = await self.bot.db.fetchrow("""SELECT playerposition, playertype, lastname, approved FROM players WHERE playerid = $1""", player_id)
        player_member = nextcord.utils.get(ctx.message.guild.members, id=player_id)
        if player is None:
            return await ctx.reply("Error: Player not found.")
        if player["approved"]:
            return await ctx.reply("Error: Player already approved.")
        if player_member is None:
            await self.bot.write("""DELETE FROM players WHERE playerid = $1""", player_id)
            return await ctx.reply("Error: Player has left the server. Application automatically deleted from database.")
        await player_member.send("Your application has been approved by a member of the Commissioners' Office.\nYou are now free to sign with a team.")
        await player_member.add_roles(nextcord.utils.get(ctx.message.guild.roles, name=player["playerposition"].title()))
        await self.bot.webhook_template_tweet("media", f"{player['playerposition'].lower()}_joined_{player['playertype'].lower()}", user=player_member.mention, last_name=player["lastname"])
        await self.bot.write("""UPDATE players SET approved = 't' WHERE playerid = $1""", player_id)
        return await ctx.reply("Player successfully approved.")
    
    @commands.command()
    @commands.has_role("bot operator")
    async def reject(self, ctx, player_id: int, * , reason: Optional[str] = None):
        player_approved = await self.bot.db.fetchval("""SELECT approved FROM players WHERE playerid = $1""", player_id)
        player_member = nextcord.utils.get(ctx.message.guild.members, id=player_id)
        if player_approved is None:
            return await ctx.reply("Error: Player not found.")
        if player_approved:
            return await ctx.reply(f"Error: Player already approved. Please use command {self.bot.command_prefix}deleteplayer to delete the player.")
        await self.bot.write("""DELETE FROM players WHERE playerid = $1""", player_id)
        if player_member is None:
            return await ctx.reply("Error: Player has left the server. Application automatically deleted from database.")
        if reason:
            await player_member.send(f"Your application has been rejected by a member of the Commissioners' Office.\nThe reason provided was: {reason}\nPlease reregister.")
        else:
            await player_member.send("Your application has been rejected by a member of the Commissioners' Office.\nNo reason was provided.\nPlease reregister.")
        return await ctx.reply("Player rejected.")



class Eval(commands.Cog):
    """Eval class"""
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def eval(self, ctx, *, arg: str):
        """Evaluate a string."""
        result = eval(arg)
        if inspect.isawaitable(result):
            result = await result
        embed = nextcord.Embed(color=0, title="Eval", description=f"```py\n{result}\n```")
        await ctx.reply(embed=embed)



def setup(bot: Bot):
    bot.add_cog(TeamManagement(bot))
    bot.add_cog(PlayerManagement(bot))
    bot.add_cog(Eval(bot))
