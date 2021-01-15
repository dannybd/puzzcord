""" Puzzboss-only commands """
import discord
from discord.ext import commands
from discord.ext.commands import guild_only, has_any_role, MemberConverter, errors
import logging
import puzzboss_interface
import re
import typing

from discord_info import *


class Puzzboss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(hidden=True, usage="[sneaky]")
    async def admin(self, ctx):
        """Administrative commands, mostly puzzboss-only"""
        if ctx.invoked_subcommand:
            return
        await ctx.send("Sneaky things happen here 👀")

    @has_any_role("Role Verifier", "Puzzleboss", "Puzztech")
    @guild_only()
    @commands.command(name="whois", aliases=["finduser"], hidden=True)
    async def whois_alias(
        self,
        ctx,
        member: typing.Optional[discord.Member],
        *,
        query: typing.Optional[str],
    ):
        """Looks up a user in Discord and Puzzleboss. (Regex supported)"""
        return await self.whois(ctx, member=member, query=query)

    @has_any_role("Role Verifier", "Puzzleboss", "Puzztech")
    @guild_only()
    @admin.command(name="whois", aliases=["finduser"])
    async def whois(
        self,
        ctx,
        member: typing.Optional[discord.Member],
        *,
        query: typing.Optional[str],
    ):
        """Looks up a user in Discord and Puzzleboss. (Regex supported)"""
        response = ""
        discord_result = ""
        if member:
            discord_result = self._lookup_discord_user(member)
            response += f"{discord_result}\n\n"
            query = member.display_name

        if not query:
            await ctx.send(response)
            return

        response += "Checking Puzzleboss accounts... "
        try:
            regex = re.compile(query, re.IGNORECASE)
        except Exception as e:
            regex = re.compile(r"^$")
        query = query.lower()

        def solver_matches(name, fullname):
            if query in name.lower():
                return True
            if regex.search(name):
                return True
            if query in fullname.lower():
                return True
            if regex.search(fullname):
                return True
            return False

        connection = puzzboss_interface.SQL._get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    name,
                    fullname
                FROM solver
                ORDER BY name
                """,
            )
            solvers = cursor.fetchall()
            cursor.execute(
                """
                SELECT
                    solver_name as solver,
                    discord_name as discord
                FROM discord_users
                ORDER BY id
                """,
            )
            discord_users = {row["solver"]: row["discord"] for row in cursor.fetchall()}
        results = []
        for solver in solvers:
            if solver_matches(**solver):
                solver_tag = "`{name} ({fullname})`".format(**solver)
                if solver["name"] in discord_users:
                    solver_tag += " [Discord user `{}`]".format(
                        discord_users[solver["name"]]
                    )
                results.append(solver_tag)

        if not results:
            response += "0 results found in Puzzleboss for that query."
        elif len(results) == 1:
            response += "1 match found:\n\n{}".format(results[0])
        else:
            response += "{} matches found:\n\n{}".format(
                len(results), "\n".join(results)
            )
        try:
            await ctx.send(response)
        except:
            response = f"{discord_result}\n\nChecking Puzzleboss accounts... Error! 😔\n"
            response += (
                "Sorry, too many matches ({}) found to display in Discord. "
                + "Please narrow your query."
            ).format(len(results))
            await ctx.send(response)

    def _lookup_discord_user(self, member: discord.Member):
        member_tag = (
            "Discord user `{0.display_name} ({0.name}#{0.discriminator})`"
        ).format(member)
        if member.bot:
            return f"{member_tag} is a bot, like me :)"
        connection = puzzboss_interface.SQL._get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    solver_name
                FROM discord_users
                WHERE discord_id = %s
                ORDER BY update_time DESC
                LIMIT 1
                """,
                (member.id,),
            )
            discord_user = cursor.fetchone()
            not_found = f"{member_tag} does not seem to be verified yet!"
            if not discord_user:
                return not_found
            name = discord_user["solver_name"]
            cursor.execute(
                """
                SELECT
                    name,
                    fullname
                FROM solver
                WHERE name = %s
                LIMIT 1
                """,
                (name,),
            )
            solver = cursor.fetchone()
            if not solver:
                return not_found
            return ("{0} is Puzzleboss user `{1} ({2})`").format(
                member_tag, solver["name"], solver["fullname"]
            )

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @guild_only()
    @commands.command(name="newpuzzboss", aliases=["boss"], hidden=True)
    async def newpuzzboss_alias(self, ctx, newboss: discord.Member):
        """[puzzboss only] Designates a new person as Puzzleboss"""
        return await self.newpuzzboss(ctx, newboss)

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @guild_only()
    @admin.command(aliases=["boss"])
    async def newpuzzboss(self, ctx, newboss: discord.Member):
        """[puzzboss only] Designates a new person as Puzzleboss"""
        puzzboss_role = ctx.guild.get_role(PUZZBOSS_ROLE)
        current_puzzbosses = puzzboss_role.members
        if newboss in current_puzzbosses:
            await ctx.send("{0.mention} is already Puzzleboss!".format(newboss))
            return
        betaboss_role = ctx.guild.get_role(BETABOSS_ROLE)
        puzztech_role = ctx.guild.get_role(PUZZTECH_ROLE)
        if betaboss_role not in newboss.roles and puzztech_role not in newboss.roles:
            await ctx.send("{0.mention} should be a Beta Boss first!".format(newboss))
            return
        author = ctx.author
        if puzzboss_role not in author.roles and puzztech_role not in author.roles:
            await ctx.send(
                (
                    "Sorry, {0.mention}, only the current "
                    + "Puzzboss and Puzztechs can run this."
                ).format(author)
            )
            return
        if puzzboss_role in author.roles:
            await author.remove_roles(puzzboss_role)
        await newboss.add_roles(puzzboss_role)
        await ctx.send(
            (
                "{0.mention} has annointed {1.mention} as the new {2.mention}! "
                + "Use {2.mention} to get their attention."
            ).format(author, newboss, puzzboss_role)
        )

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @commands.command(name="newround", aliases=["nr"], hidden=True)
    async def newround_alias(self, ctx, *, round_name: str):
        """[puzzboss only] Creates a new round"""
        return await self.newround(ctx, round_name=round_name)

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @admin.command(aliases=["nr"])
    async def newround(self, ctx, *, round_name: str):
        """[puzzboss only] Creates a new round"""
        logging.info("{0.command}: Creating a new round: {1}".format(ctx, round_name))
        response = await puzzboss_interface.REST.post("/rounds/" + round_name)
        status = response.status
        if status == 200:
            await ctx.send("Round created!")
            return
        if status == 500:
            await ctx.send("Error. This is likely because the round already exists.")
            return
        await ctx.send("Error. Something weird happened, try the PB UI directly.")

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @guild_only()
    @commands.command(
        name="solved", aliases=["solve", "answer", "answered"], hidden=True
    )
    async def solved_alias(
        self, ctx, channel: typing.Optional[discord.TextChannel], *, answer: str
    ):
        """[puzzboss only] Mark a puzzle as solved and archive its channel"""
        return await self.solved(ctx, channel=channel, answer=answer)

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @guild_only()
    @admin.command(aliases=["solve", "answer", "answered"])
    async def solved(
        self, ctx, channel: typing.Optional[discord.TextChannel], *, answer: str
    ):
        """[puzzboss only] Mark a puzzle as solved and archive its channel"""
        logging.info("{0.command}: Marking a puzzle as solved".format(ctx))
        apply_to_self = channel is None
        if apply_to_self:
            channel = ctx.channel
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(channel)
        if not puzzle:
            await ctx.send(
                "Error: Could not find a puzzle for channel {0.mention}".format(channel)
            )
            await ctx.message.delete()
            return
        response = await puzzboss_interface.REST.post(
            "/puzzles/{name}/answer".format(**puzzle), {"data": answer.upper()}
        )
        if apply_to_self:
            await ctx.message.delete()

    @solved.error
    @solved_alias.error
    async def solved_error(self, ctx, error):
        puzzboss_role = ctx.guild.get_role(PUZZBOSS_ROLE)
        if isinstance(error, errors.MissingAnyRole):
            await ctx.send(
                "This command is available to {0.mention} only.".format(puzzboss_role)
            )
            return
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send(
                "Usage: `!solved ANSWER`\n"
                + "If you're calling this from a different channel, "
                + "add the mention in there, like "
                + "`!solved #easypuzzle ANSWER`"
            )
            return
        await ctx.send(
            (
                "Error! Something went wrong, please ping @dannybd. "
                + "In the meantime {0.mention} should use the "
                + "web Puzzleboss interface to mark this as solved."
            ).format(puzzboss_role)
        )

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @guild_only()
    @commands.command(name="unverified", hidden=True)
    async def unverified_alias(self, ctx):
        """Lists not-yet-verified team members"""
        return await self.unverified(ctx)

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @guild_only()
    @admin.command()
    async def unverified(self, ctx):
        """Lists not-yet-verified team members"""
        connection = puzzboss_interface.SQL._get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    DISTINCT discord_id
                FROM discord_users
                """,
            )
            verified_discord_ids = [int(row["discord_id"]) for row in cursor.fetchall()]
        visitor_role = ctx.guild.get_role(VISITOR_ROLE)
        members = [
            "{0.name}#{0.discriminator} ({0.display_name})".format(member)
            for member in ctx.guild.members
            if visitor_role not in member.roles
            and member.id not in verified_discord_ids
            and not member.bot
        ]
        if not members:
            await ctx.send(
                "Looks like all team members are verified, nice!\n\n"
                + "(If this is unexpected, try adding the Team Member "
                + "role to someone first.)"
            )
            return
        await ctx.send(
            "Folks needing verification ({0}):\n\n{1}".format(
                len(members), "\n".join(members)
            )
        )

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @commands.command(name="verify", hidden=True)
    async def verify_alias(
        self, ctx, member: typing.Union[discord.Member, str], *, username: str
    ):
        """Verifies a team member with their email
        Usage: !verify @member username[@wind-up-birds.org]
        """
        return await self.verify(ctx, member, username=username)

    @has_any_role("Beta Boss", "Puzzleboss", "Puzztech")
    @guild_only()
    @admin.command()
    async def verify(
        self, ctx, member: typing.Union[discord.Member, str], *, username: str
    ):
        """Verifies a team member with their email
        Usage: !verify @member username[@wind-up-birds.org]
        """
        verifier_role = ctx.guild.get_role(794318951235715113)
        if verifier_role not in ctx.author.roles:
            await ctx.send(
                (
                    "Sorry, only folks with the @{0.name} "
                    + "role can use this command."
                ).format(verifier_role)
            )
            return
        if not isinstance(member, discord.Member) and " " in username:
            # Let's perform some surgery, and stitch the actual member name
            # back together.
            parts = username.split()
            username = parts[-1]
            member = " ".join([member] + parts[:-1])
            try:
                converter = MemberConverter()
                member = await converter.convert(ctx, member)
            except:
                pass

        if not isinstance(member, discord.Member):
            await ctx.send(
                (
                    "Sorry, the Discord name has to be _exact_, "
                    + "otherwise I'll fail. `{}` isn't recognizable to me "
                    + "as a known Discord name.\n\n"
                    + "TIP: If their display name has spaces or symbols in it, "
                    + 'wrap the name in quotes: `!verify "foo bar" FooBar`'
                ).format(member)
            )
            return
        username = username.replace("@wind-up-birds.org", "")
        logging.info(
            "{0.command}: Marking user {1.display_name} as PB user {2}".format(
                ctx, member, username
            )
        )
        connection = puzzboss_interface.SQL._get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, fullname
                FROM solver
                WHERE name LIKE %s
                LIMIT 1
                """,
                (username,),
            )
            solvers = cursor.fetchall()
            if not solvers:
                await ctx.send(
                    (
                        "Error: Couldn't find a {0}@wind-up-birds.org, "
                        + "please try again."
                    ).format(username)
                )
                return
            solver = solvers[0]
            logging.info(
                "{0.command}: Found solver {1}".format(ctx, solver["fullname"])
            )
            cursor.execute(
                """
                INSERT INTO discord_users
                    (solver_id, solver_name, discord_id, discord_name)
                VALUES
                    (%s, %s, %s, %s)
                """,
                (
                    solver["id"],
                    solver["name"],
                    str(member.id),
                    "{0.name}#{0.discriminator}".format(member),
                ),
            )
            logging.info("{0.command}: Committing row".format(ctx))
            connection.commit()
            logging.info("{0.command}: Committed row successfully!".format(ctx))
        member_role = ctx.guild.get_role(HUNT_MEMBER_ROLE)
        if member_role not in member.roles:
            logging.info("{0.command}: Adding member role!".format(ctx))
            await member.add_roles(member_role)
        await ctx.send(
            "**{0.display_name}** is now verified as **{1}**!".format(
                member, solver["name"]
            )
        )

    @verify.error
    @verify_alias.error
    async def verify_error(self, ctx, error):
        if isinstance(error, errors.MissingRequiredArgument):
            await ctx.send(
                "Usage: `!verify [Discord display name] [Puzzleboss username]`\n"
                + "If the person's display name has spaces or weird symbols "
                + "in it, try wrapping it in quotes, like\n"
                + '`!verify "Fancy Name" FancyPerson`'
            )
            return
        await ctx.send(
            "Error! Something went wrong, please ping @dannybd. "
            + "In the meantime it should be safe to just add this person "
            + "to the server by giving them the Team Member role."
        )


def setup(bot):
    cog = Puzzboss(bot)
    bot.add_cog(cog)
