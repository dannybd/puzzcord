"""Contains bot commands for relaying meta-information about puzzles (which ones need solving; where they're being solved; etc.)"""

import discord
from discord.ext import commands
from discord.ext.commands import guild_only
import puzzboss_interface
import discord_info
import logging
import typing
import re
from common import build_puzzle_embed


class PuzzleStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def puzzle(self, ctx, *, query: typing.Optional[str]):
        """Display current state of a puzzle.
        If no state is provided, we default to the current puzzle channel."""
        if not query:
            if not discord_info.is_puzzle_channel(ctx.channel):
                await ctx.send(
                    "You need to provide a search query, or run in a puzzle channel"
                )
                return
            puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(ctx.channel)
        else:
            try:
                regex = re.compile(query, re.IGNORECASE)
            except Exception as e:
                regex = re.compile(r"^$")
            query = query.replace(" ", "").lower()

            def puzzle_matches(name):
                if not name:
                    return False
                if query in name.lower():
                    return True
                return regex.search(name) is not None

            connection = puzzboss_interface.SQL._get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        name,
                        round,
                        puzzle_uri,
                        drive_uri,
                        slack_channel_id AS channel_id,
                        status,
                        answer
                    FROM puzzle_view
                    """,
                )
                puzzles = cursor.fetchall()
                puzzle = next(
                    (puzzle for puzzle in puzzles if puzzle_matches(puzzle["name"])),
                    None,
                )
        if not puzzle:
            await ctx.send(
                "Sorry, I couldn't find a puzzle for that query. Please try again."
            )
            return
        embed = build_puzzle_embed(puzzle)
        await ctx.send(embed=embed)

    @guild_only()
    @commands.command()
    async def tables(self, ctx):
        """What is happening at each table?
        Equivalent to calling `!location all` or `!whereis everything`"""
        return await self.location(ctx, "everything")

    @guild_only()
    @commands.command(aliases=["loc", "whereis"])
    async def location(self, ctx, *channel_mentions: str):
        """Find where discussion of a puzzle is happening.
        Usage:
            Current puzzle:   !location
            Other puzzle(s):  !location #puzzle1 #puzzle2
            All open puzzles: !location all
                            !whereis everything
        """
        if len(channel_mentions) == 1 and channel_mentions[0] in ["all", "everything"]:
            channels = [
                channel
                for channel in ctx.guild.text_channels
                if discord_info.is_puzzle_channel(channel)
            ]
            if not channels:
                await ctx.send("You don't have any puzzles")
                return
            xyzlocs = {}
            puzzles = puzzboss_interface.SQL.get_puzzles_for_channels(channels)
            for id, puzzle in puzzles.items():
                xyzloc = puzzle["xyzloc"]
                if not xyzloc:
                    continue
                if puzzle["status"] in ["Solved"]:
                    continue
                if xyzloc not in xyzlocs:
                    xyzlocs[xyzloc] = []
                xyzlocs[xyzloc].append("<#{0}>".format(id))
            if not xyzlocs:
                await ctx.send(
                    "There aren't any open puzzles being worked on at a table. "
                    + "Try joining a table and using `!joinus` in a puzzle channel."
                )
                return
            response = "Which puzzles are where:\n\n"
            for xyzloc, mentions in xyzlocs.items():
                response += "In **{0}**: {1}\n".format(xyzloc, ", ".join(mentions))
            await ctx.send(response)
            return
        logging.info(
            "{0.command}: Start with {1} channel mentions".format(
                ctx,
                len(channel_mentions),
            )
        )
        if not channel_mentions:
            channel_mentions = [ctx.channel.mention]
        channels = [
            channel
            for channel in ctx.guild.text_channels
            if channel.mention in channel_mentions
            and discord_info.is_puzzle_channel(channel)
        ]
        logging.info(
            "{0.command}: Found {1} puzzle channels".format(
                ctx,
                len(channels),
            )
        )
        if not channels:
            await ctx.send(
                "Sorry, I didn't find any puzzle channels in your command.\n"
                + "Try linking to puzzle channels by prefixing with #, like "
                + "#puzzle1"
            )
            return
        puzzles = puzzboss_interface.SQL.get_puzzles_for_channels(channels)
        logging.info("{0.command}: {1} puzzles found!".format(ctx, len(puzzles)))
        if not puzzles:
            await ctx.send(
                "Sorry, I didn't find any puzzle channels in your command.\n"
                + "Try linking to puzzle channels by prefixing with #, like "
                + "#puzzle1"
            )
            return
        response = ""
        if len(puzzles) > 1:
            response += "Found {} puzzles:\n\n".format(len(puzzles))
        for puzzle in puzzles.values():
            if puzzle["xyzloc"]:
                line = "**`{name}`** can be found in **{xyzloc}**\n".format(**puzzle)
            else:
                line = "**`{name}`** does not have a location set!\n".format(**puzzle)
            response += line
        await ctx.send(response)
        return

    @guild_only()
    @commands.command(aliases=["markas"])
    async def mark(
        self, ctx, channel: typing.Optional[discord.TextChannel], *, markas: str
    ):
        """Update a puzzle's state: needs eyes, critical, wtf, unnecessary
        Note: These all have shortcuts: (!eyes, !critical, etc.)
        """
        logging.info("{0.command}: Marking a puzzle as solved".format(ctx))
        markas = markas.lower().strip()
        if markas in ["eyes", "needs eyes", "needseyes"]:
            status = "Needs eyes"
        elif markas == "critical":
            status = "Critical"
        elif markas == "wtf":
            status = "WTF"
        elif markas in ["unnecessary", "unecessary", "unnecesary"]:
            status = "Unnecessary"
        else:
            await ctx.send("Usage: `!mark [needs eyes|critical|wtf|unnecessary]")
            return

        if not channel:
            channel = ctx.channel
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(channel)
        if not puzzle:
            await ctx.send(
                "Error: Could not find a puzzle for channel {0.mention}".format(channel)
            )
            return
        response = await puzzboss_interface.REST.post(
            "/puzzles/{name}/status".format(**puzzle), {"data": status}
        )

    @commands.command(hidden=True)
    async def eyes(self, ctx, channel: typing.Optional[discord.TextChannel]):
        """Update a puzzle's state to Needs Eyes"""
        return await self.mark(ctx, channel, markas="eyes")

    @commands.command(hidden=True)
    async def critical(self, ctx, channel: typing.Optional[discord.TextChannel]):
        """Update a puzzle's state to Critical"""
        return await self.mark(ctx, channel, markas="critical")

    @commands.command(hidden=True)
    async def wtf(self, ctx, channel: typing.Optional[discord.TextChannel]):
        """Update a puzzle's state to WTF"""
        return await self.mark(ctx, channel, markas="wtf")

    @commands.command(hidden=True)
    async def unnecessary(self, ctx, channel: typing.Optional[discord.TextChannel]):
        """Update a puzzle's state to Unnecessary"""
        return await self.mark(ctx, channel, markas="unnecessary")

    @commands.Cog.listener("on_raw_reaction_add")
    async def handle_workingon(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        if not payload.guild_id:
            return

        emoji = str(payload.emoji)
        if emoji != "🧩":
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)

        message = await channel.fetch_message(payload.message_id)
        if not message:
            return
        if message.author != self.bot.user:
            return
        if "please click the 🧩 reaction" not in message.content.lower():
            return

        member = payload.member
        if not member:
            return
        if not discord_info.is_puzzle_channel(channel):
            return
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(channel)
        if not puzzle:
            return
        name = puzzboss_interface.SQL.get_solver_name_for_member(member)
        if not name:
            return
        await puzzboss_interface.REST.post(
            "/solvers/{0}/puzz".format(name),
            {"data": puzzle["name"]},
        )
        logging.info("Marked {} as working on {}".format(name, puzzle["name"]))

    @guild_only()
    @commands.command()
    async def here(self, ctx):
        """Lets folks know this is the puzzle you're working on now."""
        if not discord_info.is_puzzle_channel(ctx.channel):
            await ctx.send("Sorry, the !here command only works in puzzle channels.")
            return
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(ctx.channel)
        name = puzzboss_interface.SQL.get_solver_name_for_member(ctx.author)
        if not name:
            await ctx.send(
                "Sorry, we can't find your wind-up-birds.org account. Please talk to "
                + "a @Role Verifier, then try again."
            )
            return
        response = await puzzboss_interface.REST.post(
            "/solvers/{0}/puzz".format(name),
            {"data": puzzle["name"]},
        )
        logging.info("Marked {} as working on {}".format(name, puzzle["name"]))
        if response.status != 200:
            await ctx.send(
                "Sorry, something went wrong. Please use Puzzleboss to select your puzzle."
            )
            return
        message = await ctx.send(
            (
                "Thank you, {0.mention}, for marking yourself as working on this puzzle.\n"
                + "Everyone else: please click the 🧩 reaction "
                + "on this message to also indicate that you're working on this puzzle."
            ).format(ctx.author)
        )
        await message.add_reaction("🧩")

    @guild_only()
    @commands.command()
    async def joinus(self, ctx):
        """Invite folks to work on the puzzle on your voice channel.
        If you have joined one of the table voice channels, you can use
        this command to set that table as the solve location for this puzzle,
        and announce as such within the puzzle channel, so everyone can see it.
        """
        if not discord_info.is_puzzle_channel(ctx.channel):
            await ctx.send("Sorry, the !joinus command only works in puzzle channels.")
            return
        table = discord_info.get_table(ctx.author)
        if not table:
            await ctx.send(
                "Sorry, you need to join one of the table voice chats before you can use the !joinus command."
            )
            return
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(ctx.channel)
        await puzzboss_interface.REST.post(
            "/puzzles/{name}/xyzloc".format(**puzzle),
            {"data": table.name},
        )


def setup(bot):
    cog = PuzzleStatus(bot)
    bot.add_cog(cog)
