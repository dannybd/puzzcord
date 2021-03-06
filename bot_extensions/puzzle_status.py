"""Contains bot commands for relaying meta-information about puzzles (which ones need solving; where they're being solved; etc.)"""

import asyncio
import datetime
import discord
from discord.ext import commands, tasks
from discord.ext.commands import guild_only
import puzzboss_interface
import discord_info
import logging
import typing
from common import build_puzzle_embed
from pytz import timezone


class PuzzleStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.table_report.start()

    def cog_unload(self):
        self.table_report.cancel()

    @tasks.loop(seconds=15.0, reconnect=True)
    async def table_report(self):
        guild = self.bot.get_guild(discord_info.GUILD_ID)
        if not guild:
            return
        channel = guild.get_channel(discord_info.TABLE_REPORT_CHANNEL)
        messages = await channel.history(limit=1).flatten()
        message = messages[0] if messages else None
        if not message or message.author != guild.me:
            message = await channel.send("Fetching table status...")

        content = self._tables(guild)
        content += "\n\nThis info auto-updates every 15 seconds."
        await message.edit(content=content, suppress=True)

    @commands.command(aliases=["puz", "puzz", "puzzl"])
    async def puzzle(
        self,
        ctx,
        *,
        channel_or_query: typing.Optional[typing.Union[discord.TextChannel, str]]
    ):
        """Display current state of a puzzle.
        If no channel is provided, we default to the current puzzle channel."""
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel_fuzzy(
            ctx, channel_or_query, bot=self.bot
        )
        if puzzle:
            embed = build_puzzle_embed(puzzle)
            await ctx.send(embed=embed)
            return
        if channel_or_query:
            await ctx.send(
                "Sorry, I couldn't find a puzzle for that query. "
                + "Please try again.\n"
                + "Usage: `!puzzle [query]`"
            )
            return
        if not discord_info.is_puzzle_channel(ctx.channel):
            await ctx.send(
                (
                    "`!puzzle` without any arguments tries to show the status "
                    + "of the puzzle channel you're currently in, "
                    + "but {0.mention} isn't recognized as a puzzle channel "
                    + "in Puzzleboss.\n"
                    + "Either go to that puzzle's channel and run `!puzzle` "
                    + "there, or run `!puzzle [query]`, with some substring "
                    + "or regex query for the puzzle's name."
                ).format(ctx.channel)
            )

    @guild_only()
    @commands.command(aliases=["table"])
    async def tables(self, ctx):
        """What is happening at each table?
        Equivalent to calling `!location all` or `!whereis everything`"""
        await ctx.send(self._tables(ctx.guild))

    def _tables(self, guild):
        tables = [
            table
            for table in guild.voice_channels
            if table.category and table.category.name.startswith("🧊")
        ]
        table_sizes = {table.name: len(table.members) for table in tables}
        xyzlocs = {table.name: [] for table in tables}
        puzzles = puzzboss_interface.SQL.get_all_puzzles(bot=self.bot)
        for puzzle in puzzles:
            xyzloc = puzzle["xyzloc"]
            if not xyzloc:
                continue
            if puzzle["status"] in ["Solved"]:
                continue
            if xyzloc not in xyzlocs:
                xyzlocs[xyzloc] = []
            xyzlocs[xyzloc].append("<#{channel_id}>".format(**puzzle))

        # Filter out empty tables
        xyzlocs = {k: v for k, v in xyzlocs.items() if v}
        if not xyzlocs:
            return (
                "There aren't any open puzzles being worked on at "
                + "any of the tables!\n"
                + "Try joining a table and using "
                + "`!joinus` in a puzzle channel."
            )

        tz = timezone("US/Eastern")
        now = datetime.datetime.now(tz)
        content = "Which puzzles are where (as of {}):\n\n".format(
            now.strftime("%A at %I:%M:%S%p %Z")
        )
        for xyzloc, mentions in xyzlocs.items():
            if xyzloc in table_sizes:
                prefix = "`{:2d}`👩‍💻 in".format(table_sizes[xyzloc])
            else:
                prefix = "In"
            content += "{0} **{1}**: {2}\n".format(prefix, xyzloc, ", ".join(mentions))

        return content

    @guild_only()
    @commands.command(aliases=["location", "loc", "where", "wheres"])
    async def whereis(
        self,
        ctx,
        *,
        channel_or_query: typing.Optional[typing.Union[discord.TextChannel, str]]
    ):
        """[aka !location] Find where discussion of a puzzle is happening.
        Usage:
            Current puzzle:   !whereis
            Other puzzle:  !whereis #puzzle1   OR !whereis puzzl
            All open puzzles: !whereis everything
        """
        if channel_or_query in ["all", "everything"]:
            return await self.tables(ctx)

        logging.info("{0.command}: Looking for {1}".format(ctx, channel_or_query))
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel_fuzzy(
            ctx, channel_or_query, bot=self.bot
        )
        if not puzzle:
            logging.info("{0.command}: No puzzle found, sending !tables.".format(ctx))
            return await self.tables(ctx)
        logging.info("{0.command}: Puzzle found!".format(ctx))
        if puzzle["xyzloc"]:
            line = "**`{name}`** can be found in **{xyzloc}**".format(**puzzle)
        else:
            line = "**`{name}`** does not have a location set!".format(**puzzle)
        await ctx.send(line)
        return

    @guild_only()
    @commands.command(aliases=["comment", "addnote", "addcomment"])
    async def note(
        self,
        ctx,
        channel: typing.Optional[discord.TextChannel],
        *,
        comments: typing.Optional[str]
    ):
        """Update a puzzle's comments in Puzzleboss
        These are visible on the Puzzleboss site, and when people run !puzzle"""
        channel = channel or ctx.channel
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(channel, bot=self.bot)
        if not puzzle:
            await ctx.send(
                "Error: Could not find a puzzle for channel {0.mention}".format(channel)
            )
            return
        response = await puzzboss_interface.REST.post(
            "/puzzles/{name}/comments".format(**puzzle), {"data": comments or ""}
        )
        if len(comments) > 200:
            await ctx.message.add_reaction("📕")
            await ctx.message.add_reaction("✍️")
            await ctx.channel.send(
                (
                    "Hey {0.mention}, I've set that as the puzzle note, "
                    + "but please consider re-adding it in a shorter (<200 char) "
                    + "form. Notes of that length tend to be less helpful, "
                    + "and make things like `!hipri` and `!puzzle` much harder "
                    + "to read.\n"
                    + "You should give all the context you want in the channel "
                    + "instead. Thanks!"
                ).format(ctx.author)
            )
            return
        await ctx.message.add_reaction("📃")
        await ctx.message.add_reaction("✍️")

    @guild_only()
    @commands.command(aliases=["markas"])
    async def mark(
        self, ctx, channel: typing.Optional[discord.TextChannel], *, markas: str
    ):
        """Update a puzzle's state: needs eyes, critical, wtf, unnecessary
        Note: These all have shortcuts: (!eyes, !critical, etc.)
        """
        logging.info("{0.command}: Marking a puzzle as {1}".format(ctx, markas))
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
            await ctx.send("Usage: `!mark [needs eyes|critical|wtf|unnecessary]`")
            return

        channel = channel or ctx.channel
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(channel, bot=self.bot)
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
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(channel, bot=self.bot)
        if not puzzle:
            return
        name = puzzboss_interface.SQL.get_solver_name_for_member(member, bot=self.bot)
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
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(
            ctx.channel, bot=self.bot
        )
        name = puzzboss_interface.SQL.get_solver_name_for_member(
            ctx.author, bot=self.bot
        )
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
        if response.status != 200:
            await ctx.send(
                "Sorry, something went wrong. "
                + "Please use the Puzzleboss website to select your puzzle."
            )
            return
        logging.info("Marked {} as working on {}".format(name, puzzle["name"]))
        message = await ctx.send(
            (
                "Thank you, {0.mention}, for marking yourself as working on this puzzle.\n"
                + "Everyone else: please click the 🧩 reaction "
                + "on this message to also indicate that you're working on this puzzle."
            ).format(ctx.author)
        )
        await message.add_reaction("🧩")

    @commands.command(aliases=["afk", "bed", "break"])
    async def away(self, ctx):
        """Lets folks know you're taking a break and not working on anything."""
        name = puzzboss_interface.SQL.get_solver_name_for_member(
            ctx.author, bot=self.bot
        )
        if not name:
            await ctx.send(
                "Sorry, we can't find your wind-up-birds.org account. Please talk to "
                + "a @Role Verifier, then try again."
            )
            return
        response = await puzzboss_interface.REST.post(
            "/solvers/{0}/puzz".format(name),
            {"data": ""},
        )
        if response.status != 200:
            await ctx.send(
                "Sorry, something went wrong. "
                + "Please use the Puzzleboss website to take a break."
            )
            return
        logging.info("Marked {} as taking a break".format(name))
        await ctx.message.add_reaction("🛌")
        await ctx.message.add_reaction("💤")

    @guild_only()
    @commands.command(aliases=["join"])
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
                "Sorry, you need to join one of the table voice chats "
                + "before you can use the !joinus command."
            )
            return
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel(
            ctx.channel, bot=self.bot
        )
        if not puzzle:
            await ctx.send(
                "Sorry, I can't find this channel in the "
                + "Puzzleboss database, so !joinus won't work."
            )
            return
        await puzzboss_interface.REST.post(
            "/puzzles/{name}/xyzloc".format(**puzzle),
            {"data": table.name},
        )
        if discord_info.is_puzzboss(ctx.author):
            return
        name = puzzboss_interface.SQL.get_solver_name_for_member(
            ctx.author, bot=self.bot
        )
        if not name:
            return
        response = await puzzboss_interface.REST.post(
            "/solvers/{0}/puzz".format(name),
            {"data": puzzle["name"]},
        )
        if response.status != 200:
            logging.error(
                "Failed to mark {} as working on {}".format(name, puzzle["name"])
            )
            return
        logging.info("Marked {} as working on {}".format(name, puzzle["name"]))

    @guild_only()
    @commands.command()
    async def leaveus(
        self,
        ctx,
        *,
        channel_or_query: typing.Optional[typing.Union[discord.TextChannel, str]]
    ):
        """Unmark a channel as being worked anywhere.
        If no channel is provided, we default to the current puzzle channel."""
        puzzle = puzzboss_interface.SQL.get_puzzle_for_channel_fuzzy(
            ctx, channel_or_query, bot=self.bot
        )
        if not puzzle:
            await ctx.send(
                "Sorry, I couldn't find a puzzle for that query. Please try again."
            )
            return
        await puzzboss_interface.REST.post(
            "/puzzles/{name}/xyzloc".format(**puzzle),
            {"data": ""},
        )
        await ctx.message.add_reaction("👋")
        await ctx.message.add_reaction("🔚")

    @commands.Cog.listener("on_voice_state_update")
    async def handle_workingon(self, member, before, after):
        # Only run if they were previously in a channel,
        if not before.channel:
            return
        # and if they changed channels
        if before.channel == after.channel:
            return

        table = before.channel

        # Ensure it's a table channel
        if not table.category:
            return
        if not table.category.name.startswith("🧊"):
            return

        # Still occupied? That's fine then
        if table.members:
            return

        try:
            await self.bot.wait_for(
                "on_voice_state_update",
                # TODO: This should have a larger timeout, but for some reason
                # this isn't firing at all, so for now let's make it immediate
                timeout=0.0,
                check=lambda _: bool(table.members),
            )
            logging.info(
                (
                    "{0.display_name} returned to table {1} "
                    + " within the grace window"
                ).format(member, table)
            )
            return
        except asyncio.TimeoutError:
            puzzles = puzzboss_interface.SQL.get_puzzles_at_table(table, bot=self.bot)
            for puzzle in puzzles:
                name = puzzle["name"]
                logging.info("Removing {0} from {1.name}".format(name, table))
                await puzzboss_interface.REST.post(
                    "/puzzles/{0}/xyzloc".format(name),
                    {"data": ""},
                )
                if puzzle["status"] == "Solved":
                    continue
                try:
                    puzzle_channel = table.guild.get_channel(int(puzzle["channel_id"]))
                    await puzzle_channel.send(
                        (
                            "Everyone left **{0.name}**, so this puzzle is "
                            + "no longer considered in progress.\n"
                            + "If you're working on this at a table, "
                            + "please run the `!joinus` command."
                        ).format(table)
                    )
                except:
                    continue


def setup(bot):
    cog = PuzzleStatus(bot)
    bot.add_cog(cog)
