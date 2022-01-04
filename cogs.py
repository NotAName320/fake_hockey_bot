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
from typing import Optional, Union

import nextcord
from nextcord.ext import commands

from discord_db_client import Bot
from util import fancy_archetype_name


QUESTION_MARK = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Question_mark2.svg/1580px-Question_mark2.svg.png"


class TeamManagement(commands.Cog, name="Team Management"):
    """Create and manage teams."""
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="teaminfo")
    async def team_info(self, ctx, team_id: Optional[str] = None):
        """Displays information about a specified team."""
        if team_id is None:  # If user does not specify a team, try to fetch their current team (if they have one) rather than immediately throwing error
            author_associated_team = await self.bot.db.fetchval("""SELECT playerteam FROM players WHERE playerid = $1""", ctx.author.id)
            if author_associated_team is None:
                return await ctx.reply("Error: Please specify a team")
            team_id = author_associated_team
        team_id = team_id.upper()
        team_record = await self.bot.db.fetchrow("""SELECT roleid, logourl, city, name, channelid FROM teams WHERE teamid = $1""", team_id)
        if team_record is None:
            return await ctx.reply("Error: your team ID is invalid.")
        if team_record["channelid"] is None:
            home_stadium = "*None*"
        else:
            home_stadium = self.bot.get_channel(team_record["channelid"]).mention
        team_members = await self.bot.db.fetch("""SELECT playerid, playerposition FROM players WHERE playerteam = $1""", team_id)
        forward, defenseman, goalie = "*None*", "*None*", "*None*"
        for player in team_members:
            if player["playerposition"] == "FORWARD":
                forward = self.bot.get_user(player["playerid"]).mention if self.bot.get_user(player["playerid"]) else "Unknown player with ID " + player["playerid"]
            if player["playerposition"] == "DEFENSEMAN":
                defenseman = self.bot.get_user(player["playerid"]).mention if self.bot.get_user(player["playerid"]) else "Unknown player with ID " + player["playerid"]
            if player["playerposition"] == "GOALIE":
                goalie = self.bot.get_user(player["playerid"]).mention if self.bot.get_user(player["playerid"]) else "Unknown player with ID " + player["playerid"]
        color = nextcord.utils.get(ctx.guild.roles, id=team_record["roleid"]).color
        embed = nextcord.Embed(color=color, title=f"{team_record['city']} {team_record['name']} Team Info")
        embed.set_thumbnail(url=QUESTION_MARK if team_record["logourl"] is None else team_record["logourl"])
        embed.add_field(name="Team ID", value=team_id, inline=False)
        embed.add_field(name="City", value=team_record["city"])
        embed.add_field(name="Name", value=team_record["name"], inline=True)
        embed.add_field(name="Home Stadium", value=home_stadium, inline=True)
        embed.add_field(name="Forward", value=str(forward), inline=True)
        embed.add_field(name="Defenseman", value=str(defenseman), inline=True)
        embed.add_field(name="Goalie", value=str(goalie), inline=True)
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
        self.bot.logger.info(f"{ctx.author} created a new team with ID {team_id}")
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
        try:
            self.bot.logger.info(f"{ctx.author} changed/attempted to change"
                                 f"{ctx.message.content.split()[2].upper()}'s "
                                 f"{ctx.invoked_subcommand.name} to {' '.join(ctx.message.content.split()[3:])}")
        except IndexError:
            return

    @edit_team.command()
    async def city(self, ctx, team_id: str, *, new_city: str):
        team_id = team_id.upper()
        team_record = await self.bot.db.fetchrow("""SELECT name, roleid FROM teams WHERE teamid = $1""", team_id)
        if team_record is None:
            return await ctx.reply("Error: your team ID is invalid.")
        await self.bot.write("""UPDATE teams SET city = $1 WHERE teamid = $2""", new_city, team_id)
        role = nextcord.utils.get(ctx.guild.roles, id=team_record["roleid"])
        await role.edit(name=f"{new_city} {team_record['name']}")
        return await ctx.reply(f"Success: Team name is now {new_city} {team_record['name']}.")

    @edit_team.command()
    async def name(self, ctx, team_id: str, *, new_name: str):
        team_id = team_id.upper()
        team_record = await self.bot.db.fetchrow("""SELECT city, roleid FROM teams WHERE teamid = $1""", team_id)
        if team_record is None:
            return await ctx.reply("Error: your team ID is invalid.")
        await self.bot.write("""UPDATE teams SET name = $1 WHERE teamid = $2""", new_name, team_id)
        role = nextcord.utils.get(ctx.guild.roles, id=team_record["roleid"])
        await role.edit(name=f"{team_record['city']} {new_name}")
        return await ctx.reply(f"Success: Team name is now {team_record['city']} {new_name}.")

    @edit_team.command()
    async def stadium(self, ctx, team_id: str, new_stadium: nextcord.TextChannel):
        team_id = team_id.upper()
        if not await self.bot.statements.team_exists(team_id):
            return await ctx.reply("Error: your team ID is invalid.")
        await self.bot.write("""UPDATE teams SET channelid = $1 WHERE teamid = $2""", new_stadium.id, team_id)
        return await ctx.reply(f"Success: {new_stadium.mention} is now the specified team's home stadium.")

    @edit_team.command()
    async def logo(self, ctx, team_id: str, *, logo_url: str):
        team_id = team_id.upper()
        if not await self.bot.statements.team_exists(team_id):
            return await ctx.reply("Error: your team ID is invalid.")
        await self.bot.write("""UPDATE teams SET logourl = $1 WHERE teamid = $2""", logo_url, team_id)
        return await ctx.reply(f"Success: Changed the specified team's logo.")

    @edit_team.command(aliases=['colour'])
    async def color(self, ctx, team_id: str, new_color: str):
        team_id = team_id.upper()
        role_id = await self.bot.db.fetchval("""SELECT roleid FROM teams WHERE teamid = $1""", team_id)
        if role_id is None:
            return await ctx.reply("Error: your team ID is invalid.")
        role = nextcord.utils.get(ctx.guild.roles, id=role_id)
        await role.edit(color=int(new_color, 16))
        return await ctx.reply(f"Success: Team color changed.")

    @commands.group()
    @commands.has_role("bot operator")
    async def roster(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.reply(f"Error: Please specify what action you want to take:\n"
                                   f"`{self.bot.command_prefix}roster add [team_id] [player]` to add players,\n"
                                   f"`{self.bot.command_prefix}roster remove [team_id] [position]` to remove players by their position on a team, or\n"
                                   f"`{self.bot.command_prefix}roster remove [player]` to remove players by mention.")

    @roster.command()
    async def add(self, ctx, team_id: str, player: nextcord.Member):
        team_id = team_id.upper()
        if not await self.bot.statements.team_exists(team_id):
            return await ctx.reply("""Error: Team does not exist.""")
        player_record = await self.bot.db.fetchrow("""SELECT CONCAT(firstname, ' ', lastname) AS fullname, approved, playerposition FROM players WHERE playerid = $1""",
                                                   player.id)
        if player_record is None:
            return await ctx.reply("Error: Player has not registered.")
        if not player_record["approved"]:
            return await ctx.reply("Error: Player has not been approved.")
        team_position_filled = await self.bot.db.fetchval("""SELECT EXISTS(SELECT 1 FROM players WHERE playerteam = $1 AND playerposition = $2)""",
                                                          team_id, player_record['playerposition'])
        if team_position_filled:
            return await ctx.reply(f"Error: Position is already filled."
                                   f"Please use command `{self.bot.command_prefix}roster remove [{team_id.upper()}] [{player_record['playerposition'].lower()}]`"
                                   f"to remove existing player from team.")
        role_id = await self.bot.db.fetchval("""SELECT roleid FROM teams WHERE teamid = $1""", team_id)
        role = nextcord.utils.get(ctx.guild.roles, id=role_id)
        await player.add_roles(role)
        self.bot.logger.info(f"{ctx.author} added {player} to team {team_id}")
        await self.bot.write("""UPDATE players SET playerteam = $1 WHERE playerid = $2""", team_id, player.id)
        return await ctx.reply(f"Success: {player_record['fullname']} has been rostered for {team_id}.")

    @roster.command(aliases=["cut"])
    async def remove(self, ctx, team_id_or_player: Union[nextcord.Member, str], position: Optional[str] = None):
        if isinstance(team_id_or_player, str):
            if position is None:
                raise commands.MissingRequiredArgument(inspect.Parameter("position", inspect.Parameter.POSITIONAL_OR_KEYWORD))
            team_id_or_player = team_id_or_player.upper()
            position = position.upper()
            if not await self.bot.statements.team_exists(team_id_or_player):
                return await ctx.reply("""Error: Team does not exist.""")
            player_id = await self.bot.db.fetchval("""SELECT playerid FROM players WHERE playerteam = $1 AND playerposition = $2""", team_id_or_player, position)
            player_name = await self.bot.db.fetchval("""SELECT CONCAT(firstname, ' ', lastname) AS fullname FROM players WHERE playerid = $1""", player_id)
            role_id = await self.bot.db.fetchval("""SELECT roleid FROM teams WHERE teamid = $1""", team_id_or_player)  # TODO: Convert all this to one joined expression
            team_id_or_player = nextcord.utils.get(ctx.guild.members, id=player_id)
        else:
            player_id = team_id_or_player.id
            player_name = await self.bot.db.fetchval("""SELECT CONCAT(firstname, ' ', lastname) AS fullname FROM players WHERE playerid = $1""", player_id)
            role_id = await self.bot.db.fetchval("""SELECT roleid
                                                    FROM teams
                                                    WHERE teamid = (
                                                        SELECT playerteam FROM players WHERE playerid = $1
                                                    )""", team_id_or_player.id)
        await self.bot.write("""UPDATE players SET playerteam = $1 WHERE playerid = $2""", None, player_id)
        team_role = nextcord.utils.get(ctx.guild.roles, id=role_id)
        if team_id_or_player:
            await team_id_or_player.remove_roles(team_role)
        return await ctx.reply(f"Success: {player_name} has been removed from {team_role.name}.")

    @roster.error
    async def roster_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            return await ctx.reply(f"Error: You do not have permission to use this command. (Perhaps you meant to call `{self.bot.command_prefix}teaminfo`?)")
        # By doing this and adding a hasattr check in on_command_error we can make this work like a sort of override
        # This is since on_command_error fires no matter what after a local on_error so we can make that one just return out and run this one instead
        del ctx.command.on_error
        await self.bot.on_command_error(ctx, error)
        ctx.command.on_error = self.roster_error


class PlayerManagement(commands.Cog, name="Player Management"):
    """Manage and edit individual players."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.active_registrations = []

    @commands.command(name="playerinfo")
    async def player_info(self, ctx, player: Optional[nextcord.Member] = None, *, player_string: Optional[str] = None):
        """Displays information about a player."""
        player = ctx.author if player is None and player_string is None else player  # player defaults to the author if neither a string or mention is provided
        if player is None:
            players = await self.bot.db.fetch("""SELECT * FROM players WHERE TO_TSVECTOR(CONCAT(firstname, ' ', lastname)) @@ TO_TSQUERY($1)""",
                                              player_string.replace(" ", " & "))
        else:
            players = await self.bot.db.fetch("""SELECT * FROM players WHERE playerid = $1""", player.id)
        if len(players) == 0:
            return await ctx.reply("Error: Your search turned up no results.")
        if len(players) != 1:
            list_of_players = "\n".join(f"{x['firstname']} {x['lastname']} (ID: {x['playerid']})" for x in players)
            return await ctx.reply(f"Error: Your search turned up multiple results:\n{list_of_players}\nPlease refine your query or mention the user directly.")
        player_record = players[0]
        player = nextcord.utils.get(ctx.message.guild.members, id=player_record["playerid"])
        if player_record["playerteam"]:
            teaminfo = await self.bot.db.fetchrow("""SELECT city, name, roleid FROM teams WHERE teamid = $1""", player_record["playerteam"])
            team_full_name = f"{teaminfo['city']} {teaminfo['name']}"
            color = nextcord.utils.get(ctx.message.guild.roles, name=team_full_name).color
        else:
            team_full_name = "Free Agent"
            color = 0
        embed = nextcord.Embed(color=color, title=f"{player_record['firstname']} {player_record['lastname']} Player Info")
        embed.add_field(name="First Name", value=player_record["firstname"])
        embed.add_field(name="Last Name", value=player_record["lastname"])
        embed.add_field(name="Team", value=team_full_name)
        embed.add_field(name="Position", value=player_record["playerposition"].title())
        if player_record["playerposition"] != "GOALIE":
            embed.add_field(name="Archetype", value=fancy_archetype_name(player_record["playerposition"], player_record["playertype"]))
        if player is None:
            embed.set_thumbnail(url=QUESTION_MARK)
            embed.add_field(name="Discord User", value="*Not Found*")
            return await ctx.reply(content="Note: Player's Discord was not found, possibly because they left the server.", embed=embed)
        embed.set_thumbnail(url=player.avatar.url)
        embed.add_field(name="Discord User", value=player.mention)
        return await ctx.reply(embed=embed)

    @commands.command()
    async def register(self, ctx):
        player_already_registered = await self.bot.db.fetchval("""SELECT EXISTS(SELECT 1 FROM players WHERE playerid = $1)""", ctx.author.id)
        if player_already_registered:
            return await ctx.reply(f"Error: You have already registered. Please ask a commissioner for help with changing your player.")
        if ctx.author.id in self.active_registrations:
            return await ctx.reply("Error: You have an active registration process still going on."
                                   "Reply to your registration message with \"ABORT\" and run this command again to start over.")
        embed = nextcord.Embed(color=0, title="New Player Registration")
        embed.set_thumbnail(url=ctx.author.avatar.url)
        embed.set_footer(text="Reply with \"ABORT\" at any time to cancel registration or start over.")
        embed.add_field(name="First Name", value="*None*")
        embed.add_field(name="Last Name", value="*None*")
        embed.add_field(name="Position", value="*None*")
        initial_message = await ctx.author.send(content="Player registration has started."
                                                "Please reply to this message with what you want your `First Name` to be.",
                                                embed=embed)
        await ctx.reply("Please check your DMs for more details.")
        self.active_registrations.append(ctx.author.id)
        self.bot.logger.info(f"Registration process has started for {ctx.author}")

        async def abort(abort_message):
            self.active_registrations.remove(ctx.author.id)
            embed.clear_fields()
            embed.description = "Registration aborted."
            await initial_message.edit(content="Registration aborted.", embed=embed)
            self.bot.logger.info(f"{ctx.author} aborted registration")
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
            self.bot.logger.info(f"{ctx.author}'s registration timed out")
            return await ctx.author.send("There have been 10 minutes since the last reply.\n"
                                         "Registration has automatically terminated. Please restart the registration process.")

    @commands.command()
    @commands.has_role("bot operator")
    async def approve(self, ctx, player_id: int):
        player = await self.bot.db.fetchrow("""SELECT playerposition, playertype, lastname, approved FROM players WHERE playerid = $1""", player_id)
        player_member = nextcord.utils.get(ctx.guild.members, id=player_id)
        if player is None:
            return await ctx.reply("Error: Player not found.")
        if player["approved"]:
            return await ctx.reply("Error: Player already approved.")
        if player_member is None:
            await self.bot.write("""DELETE FROM players WHERE playerid = $1""", player_id)
            return await ctx.reply("Error: Player has left the server. Application automatically deleted from database.")
        await player_member.send("Your application has been approved by a member of the Commissioners' Office.\nYou are now free to sign with a team.")
        await player_member.add_roles(nextcord.utils.get(ctx.guild.roles, name=player["playerposition"].title()))
        await self.bot.webhook_template_tweet("media",
                                              f"{player['playerposition'].lower()}_joined{'_'+player['playertype'].lower() if player['playertype'] else ''}",
                                              user=player_member.mention,
                                              last_name=player["lastname"])
        await self.bot.write("""UPDATE players SET approved = 't' WHERE playerid = $1""", player_id)
        return await ctx.reply("Player successfully approved.")

    @commands.command()
    @commands.has_role("bot operator")
    async def reject(self, ctx, player_id: int, *, reason: Optional[str] = None):
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
            await player_member.send(f"Your application has been rejected by a member of the Commissioners' Office.\n"
                                     f"The reason provided was: {reason}\nPlease reregister.")
        else:
            await player_member.send("Your application has been rejected by a member of the Commissioners' Office.\nNo reason was provided.\nPlease reregister.")
        return await ctx.reply("Player rejected.")

    @commands.group(name="editplayer")
    @commands.has_role("bot operator")
    async def edit_player(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.reply("Please specify what attribute of the player you want to change!\n"
                                   "Valid attributes are:\n"
                                   "firstname: String\n"
                                   "lastname: String\n"
                                   "position: Forward, Defenseman, or Goalie\n"
                                   "archetype: Passer, Shooter, or Deker (Automatically set to NULL if position set to Goalie)\n\n"
                                   f"To add or remove the player from a team, use the `{self.bot.command_prefix}roster` command instead.")
        try:
            self.bot.logger.info(f"{ctx.author} changed/attempted to change"
                                 f"{ctx.message.content.split()[2].upper()}'s "
                                 f"{ctx.invoked_subcommand.name} to {' '.join(ctx.message.content.split()[3:])}")
        except IndexError:
            return

    @edit_player.command(name="firstname")
    async def first_name(self, ctx, player: nextcord.Member, *, new_name: str):
        player_last_name = await self.bot.db.fetchval("""SELECT lastname FROM players WHERE playerid = $1""", player.id)
        if player_last_name is None:
            return await ctx.reply("Error: Player has not registered. Please tell the player to register or add them manually.")
        await self.bot.write("""UPDATE players SET firstname = $1 WHERE playerid = $2""", new_name, player.id)
        return await ctx.reply(f"Success: Player name is now {new_name} {player_last_name}.")

    @edit_player.command(name="lastname")
    async def last_name(self, ctx, player: nextcord.Member, *, new_name: str):
        player_first_name = await self.bot.db.fetchval("""SELECT firstname FROM players WHERE playerid = $1""", player.id)
        if player_first_name is None:
            return await ctx.reply("Error: Player has not registered. Please tell the player to register or add them manually.")
        await self.bot.write("""UPDATE players SET lastname = $1 WHERE playerid = $2""", new_name, player.id)
        return await ctx.reply(f"Success: Player name is now {player_first_name} {new_name}.")

    @edit_player.command()
    async def position(self, ctx, player: nextcord.Member, position: str):
        position = position.upper()
        if position not in ["FORWARD", "DEFENSEMAN", "GOALIE"]:
            return await ctx.reply("Error: You did not enter a valid position. Please try again.")
        player_record = await self.bot.db.fetchrow("""SELECT CONCAT(firstname, ' ', lastname) AS fullname, playerteam, playerposition, playertype
                                                      FROM players WHERE playerid = $1""",
                                                   player.id)
        if player_record is None:
            return await ctx.reply("Error: Player has not registered. Please tell the player to register or add them manually.")
        if player_record["playerposition"] == position:
            return await ctx.reply("Error: Player is already this position.")
        if player_record["playerteam"]:
            target_position_filled = await self.bot.db.fetchval("""SELECT EXISTS(SELECT 1 FROM players WHERE playerteam = $1 AND playerposition = $2)""",
                                                                player_record["playerteam"], position)
            if target_position_filled:
                return await ctx.reply("Error: Cannot move player within team. Please either empty the target position or make the player a free agent.")
        if position == "GOALIE":
            new_archetype = None
        else:
            new_archetype = "PASSER" if player_record["playerposition"] == "GOALIE" else player_record["playertype"]
        await self.bot.write("""UPDATE players SET playerposition = $1, playertype = $2 WHERE playerid = $3""", position, new_archetype, player.id)
        old_role = nextcord.utils.get(ctx.guild.roles, name=player_record["playerposition"].title())
        new_role = nextcord.utils.get(ctx.guild.roles, name=position.title())
        await player.remove_roles(old_role)
        await player.add_roles(new_role)
        return await ctx.reply(f"Success: {player_record['fullname']}'s position changed to {position.title()}.")

    @edit_player.command()
    async def archetype(self, ctx, player: nextcord.Member, *, archetype: str):
        archetype = archetype.upper()
        if archetype in ["ENFORCER", "PLAYMAKER"]:
            archetype = "PASSER"
        if archetype in ["OFFENSIVE DEFENSEMAN", "SNIPER"]:
            archetype = "SHOOTER"
        if archetype in ["FINESSER", "DANGLER"]:
            archetype = "DEKER"
        if archetype not in ["PASSER", "SHOOTER", "DEKER"]:
            return await ctx.reply("Error: Valid archetype not found. Valid archetypes are: passer, shooter, deker")
        player_record = await self.bot.db.fetchrow("""SELECT CONCAT(firstname, ' ', lastname) AS fullname, playerposition, playertype
                                                      FROM players WHERE playerid = $1""",
                                                   player.id)
        if player_record is None:
            return await ctx.reply("Error: Player has not registered. Please tell the player to register or add them manually.")
        if player_record["playerposition"] == "GOALIE":
            return await ctx.reply("Error: Player is a goalie and does not have an archetype.")
        await self.bot.write("""UPDATE players SET playertype = $1 WHERE playerid = $2""", archetype, player.id)
        return await ctx.reply(f"Success: {player_record['fullname']}'s archetype changed to {fancy_archetype_name(player_record['playerposition'], archetype)}")


class MetaAdmin(commands.Cog):
    """Commands related to the functioning of the bot."""
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

    @commands.command(hidden=True)
    @commands.is_owner()
    async def logs(self, ctx):
        """Uploads the bot.log file."""
        return await ctx.reply(file=nextcord.File("bot.log"))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def test(self, ctx, arg: str):
        """A command used to test features. Usually does nothing."""
        pass


def setup(bot: Bot):
    bot.add_cog(TeamManagement(bot))
    bot.add_cog(PlayerManagement(bot))
    bot.add_cog(MetaAdmin(bot))
