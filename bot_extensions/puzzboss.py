""" Puzzboss-only commands """
import discord
from discord.ext import commands
from discord.ext.commands import guild_only
import logging
import puzzboss_interface
import re
import typing

def puzzboss_only():
    async def predicate(ctx):
        # TODO: Make this more open to whoever's puzzbossing
        return 790341841916002335 in [role.id for role in ctx.author.roles]

    return commands.check(predicate)


def role_verifiers():
    async def predicate(ctx):
        roles = [role.id for role in ctx.author.roles]
        return 794318951235715113 in roles or 790341841916002335 in roles

    return commands.check(predicate)


class Puzzboss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.group(hidden=True, usage="[sneaky]")
    async def admin(self, ctx):
        """Administrative commands, mostly puzzboss-only"""


    @role_verifiers()
    @guild_only()
    @admin.command()
    async def whois(self, ctx, *, member: discord.Member):
        """Looks up a discord user"""
        return await self._whois(ctx, member)


    @role_verifiers()
    @guild_only()
    @commands.command(name="whois", hidden=True)
    async def do_whois(self, ctx, *, member: discord.Member):
        """Looks up a discord user"""
        return await self._whois(ctx, member)


    async def _whois(self, ctx, member):
        if member.bot:
            await ctx.send("{0.mention} is a bot, like me :)".format(member))
            return
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
            if not discord_user:
                await ctx.send("Sorry, couldn't find that user; they may not be verified yet.")
                return
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
                await ctx.send("Sorry, couldn't find that user; they may not be verified yet.")
                return
            await ctx.send(
                (
                    "Discord user `{0.display_name}` (`{0.name}#{0.discriminator}`) "
                    + "is PB user `{1}` (`{2}`)"
                ).format(member, solver["name"], solver["fullname"])
            )


    @role_verifiers()
    @guild_only()
    @admin.command()
    async def finduser(self, ctx, *, query: str):
        """Fuzzy user lookup in Puzzleboss. (Regex supported)"""
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
        results = []
        for solver in solvers:
            if solver_matches(**solver):
                results.append("{name} ({fullname})".format(**solver))
        if not results:
            await ctx.send("No results found for that query.")
            return
        if len(results) == 1:
            await ctx.send("Found 1 match:\n\n{}".format("\n".join(results)))
            return
        try:
            await ctx.send("Found {} matches:\n\n{}".format(len(results), "\n".join(results)))
        except:
            await ctx.send("Sorry, too many matches ({}) found to display in Discord. Please narrow your query.".format(len(results)))


    @puzzboss_only()
    @admin.command(aliases=["nr"])
    async def newround(self, ctx, *, round_name: str):
        """[puzztech only] Creates a new round"""
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


    @puzzboss_only()
    @guild_only()
    @admin.command()
    async def solved(self, ctx, channel: typing.Optional[discord.TextChannel], *, answer: str):
        """[puzztech only] Mark a puzzle as solved and archive its channel"""
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


    @role_verifiers()
    @guild_only()
    @admin.command()
    async def unverified(self, ctx):
        """Lists not-yet-verified team members"""
        connection = puzzboss_interface.SQL.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    DISTINCT discord_id
                FROM discord_users
                """,
            )
            verified_discord_ids = [int(row["discord_id"]) for row in cursor.fetchall()]
        member_role = ctx.guild.get_role(790341818885734430)
        members = [
            "{0.name}#{0.discriminator} ({0.display_name})".format(member)
            for member in ctx.guild.members
            if member_role in member.roles
            and member.id not in verified_discord_ids
            and not member.bot
        ]
        await ctx.send(
            "Folks needing verification ({0}):\n\n{1}".format(
                len(members), "\n".join(members)
            )
        )


    @role_verifiers()
    @commands.command(name="verify", hidden=True)
    async def do_verify(self, ctx, member: discord.Member, *, username: str):
        """Verifies a team member with their email
        Usage: !verify @member username[@wind-up-birds.org]
        """
        return await self._verify(ctx, member, username)


    @role_verifiers()
    @guild_only()
    @admin.command()
    async def verify(self, ctx, member: discord.Member, *, username: str):
        """Verifies a team member with their email
        Usage: !verify @member username[@wind-up-birds.org]
        """
        return await self._verify(ctx, member, username)


    async def _verify(self, ctx, member, username):
        verifier_role = ctx.guild.get_role(794318951235715113)
        if verifier_role not in ctx.author.roles:
            await ctx.send(
                "Sorry, only folks with the @{0.name} role can use this command.".format(
                    verifier_role
                )
            )
            return
        username = username.replace("@wind-up-birds.org", "")
        logging.info(
            "{0.command}: Marking user {1.display_name} as PB user {2}".format(
                ctx, member, username
            )
        )
        connection = puzzboss_interface.SQL.get_db_connection()
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
            solver = cursor.fetchone()
        logging.info("{0.command}: Found solver {1}".format(ctx, solver["fullname"]))
        if not solver:
            await ctx.send(
                "Error: Couldn't find a {0}@wind-up-birds.org, please try again.".format(
                    username
                )
            )
            return
        with connection.cursor() as cursor:
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
        member_role = ctx.guild.get_role(790341818885734430)
        if member_role not in member.roles:
            logging.info("{0.command}: Adding member role!".format(ctx))
            await member.add_roles(member_role)
        await ctx.send(
            "**{0.display_name}** is now verified as **{1}**!".format(
                member, solver["name"]
            )
        )

def setup(bot):
    cog = Puzzboss(bot)
    bot.add_cog(cog)
