""" Get an overview of the entire hunt status """
import discord
from discord.ext import commands, tasks
import puzzboss_interface
import discord_info
import logging
from common import xyzloc_mention
import datetime
import typing


class HuntStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_metrics.start()

    def cog_unload(self):
        self.log_metrics.cancel()

    @tasks.loop(seconds=60.0, reconnect=True)
    async def log_metrics(self):
        guild = self.bot.get_guild(discord_info.GUILD_ID)
        if not guild:
            return
        now = self.bot.now()
        if now > self.bot.hunt_ends:
            return
        members = discord_info.get_team_members(guild)
        online_members = [
            member for member in members if member.status != discord.Status.offline
        ]
        puzzles = puzzboss_interface.SQL.get_all_puzzles(bot=self.bot)
        solved = [
            puzzle
            for puzzle in puzzles
            if puzzle["status"] == "Solved" and puzzle["answer"]
        ]
        logging.info(
            f"<<<METRICS>>> {self.bot.now().strftime('%Y-%m-%dT%H:%M:%S')}: "
            f"{len(online_members)}/{len(members)} members online; "
            f"{len(solved)}/{len(puzzles)} puzzles solved"
        )

    @commands.command()
    async def help(self, ctx, category: typing.Optional[str]):
        if category == "tools":
            await ctx.send(
                """
```
!tools

Assorted puzzle-solving tools and utilities. (These all work as !tools abc or just !abc.)

Commands:
  abc        Converts letters A-Z to/from numbers 1-26
  braille    Print the braille alphabet
  morse      Convert to/from morse code (/ for word boundaries)
  nutrimatic Queries nutrimatic.org
  qat        Queries Qat, a multi-pattern word searcher
  roll       Rolls a dice in NdN format.
  rot        Rotates a message through all rot N and displays the permutations
  stuck      Suggests some tips from the Have You Tried? list
```
"""
            )
            return
        domain = self.bot.hunt_team["domain"]
        if category == "admin":
            await ctx.send(
                f"""
See Admin commands here: https://{domain}/wiki/index.php/Hunting_in_Discord:_A_Guide#Puzzboss_Extras
"""
            )
            return
        await ctx.send(
            f"""
```
Get the state of things:
  !hunt     Hunt status update
  !puzzle   Current state of a puzzle
  !tables   Which tables are tackling which puzzles?
            [NOTE: This live-updates in the #🪴-tables channel]

  !whereis  Where is discussion of a specific puzzle?

As you work on puzzles (use in puzzle channels):
  !joinus   Invite folks to work on the puzzle at your table
  !here     Indicate which puzzle you're working on
            [NOTE: Please use this! It's especially important in a hybrid hunt.]

  !mark     Update a puzzle's status: needs eyes, critical, wtf, unnecessary
            Note, these work too: !eyes !critical !wtf !unnecessary

  !note     Update a puzzle's comments field in Puzzleboss

Help with puzzle solving (use anywhere, including DMs):
  !tools    [category] Assorted puzzle-solving tools and utilities

When you're stepping away:
  !leaveus  Unmark a puzzle as being worked anywhere at any table.
  !away     Lets us know you're taking a break and not working on anything.

Other commands:
  !huntyet  Is it hunt yet?
  !help     Shows this info (but formatted far less well.
```

See all commands here: https://{domain}/wiki/index.php/Hunting_in_Discord:_A_Guide

Thanks, and happy hunting! 🕵️‍♀️🧩
"""
        )

    @commands.command(aliases=["wrapped"])
    async def wrapup(self, ctx):
        """What puzzles you worked on, with links so you can go leave feedback"""
        if self.bot.now() < self.bot.hunt_ends:
            await ctx.send("Shhh, not yet :)")
            return

        author = ctx.author
        connection = puzzboss_interface.SQL._get_db_connection(bot=self.bot)
        domain = self.bot.hunt_team["domain"]
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    puzzles
                FROM solver_view
                WHERE chat_uid = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(author.id),),
            )
            solver = cursor.fetchone()
            if not solver:
                await ctx.send(
                    (
                        "Sorry, {0.mention}, I couldn't find your {1} "
                        + "account! Did you register? *Did you even hunt with us?*"
                    ).format(author, domain)
                )
                return
            puzzles = (solver["puzzles"] or "").split(",")
            if not puzzles:
                await ctx.send(
                    (
                        "Sorry, {0.mention}, I couldn't find any puzzles recorded "
                        + "to your {1} account. "
                        + "Maybe try using the `!here` and `!joinus` commands "
                        + "next year 😛"
                    ).format(author, domain)
                )
                return
            cursor.execute(
                """
                SELECT
                    name,
                    roundname AS round_name,
                    puzzle_uri
                FROM puzzle_view
                WHERE name IN ({})
                ORDER BY id
                """.format(
                    ",".join(["%s"] * len(puzzles))
                ),
                tuple(puzzles),
            )
            puzzles = cursor.fetchall()

        def plural(num, noun):
            return "{} {}{}".format(num, noun, "" if num == 1 else "s")

        def link(uri, label):
            return f"[`{label}`]({uri})"

        rounds = {}
        for puzzle in puzzles:
            round_name = puzzle["round_name"]
            if round_name not in rounds:
                rounds[round_name] = []
            rounds[round_name].append(link(puzzle["puzzle_uri"], puzzle["name"]))

        descriptions = []
        description = "Here are **{}** you worked on:\n\n".format(
            plural(len(puzzles), "puzzle")
        )
        for round_name, puzzles in rounds.items():
            if len(description) >= 1000:
                description += "\n(continued...)"
                descriptions.append(description)
                description = ""
            description += "**{}:** {}\n".format(round_name.title(), ", ".join(puzzles))
        description += (
            "\nThanks for a great Hunt; it's been a lot of fun "
            + "making this happen. Now go write some feedback! 💌"
        )
        descriptions.append(description)

        embed = discord.Embed(
            title="🧩 Your ~~Spotify~~ Mystery Hunt Wrapped 🎁",
            description=descriptions[0],
        )
        # TODO: Update for 2024
        embed.set_thumbnail(url="https://i.imgur.com/dnWoHz7.jpeg")
        embed.set_footer(
            text="based on approximate data, assembled hastily with love by danny"
        )
        await ctx.send(content="{0.mention}:".format(author), embed=embed)
        if len(descriptions) == 1:
            return
        for description in descriptions[1:]:
            await ctx.send(embed=discord.Embed(description=description))

    @commands.command(aliases=["hunt"])
    async def status(self, ctx):
        """Hunt status update"""
        tables = [
            table
            for table in ctx.guild.voice_channels
            if table.category and table.category.name.startswith("🪴")
        ]
        table_sizes = {table.name: len(table.members) for table in tables}
        puzzles = puzzboss_interface.SQL.get_all_puzzles(bot=self.bot)
        meta_ids = puzzboss_interface.SQL.get_meta_ids(bot=self.bot)
        rounds = {}
        for puzzle in puzzles:
            round_name = puzzle["round_name"]
            if round_name not in rounds:
                rounds[round_name] = {
                    "total": 0,
                    "Solved": 0,
                    "Other": 0,
                    "Needs eyes": 0,
                    "Critical": 0,
                    "WTF": 0,
                    "Unnecessary": 0,
                    "approx_solvers": 0,
                    "solver_tables": [],
                    "num_metas": 0,
                    "num_metas_solved": 0,
                    "max_id": 0,
                }
            rounds[round_name]["total"] += 1
            status = puzzle["status"]
            if status in rounds[round_name]:
                rounds[round_name][status] += 1
            else:
                rounds[round_name]["Other"] += 1

            xyzloc = puzzle["xyzloc"]
            if xyzloc in table_sizes and status != "Solved":
                if xyzloc not in rounds[round_name]["solver_tables"]:
                    rounds[round_name]["approx_solvers"] += table_sizes[xyzloc]
                    rounds[round_name]["solver_tables"].append(xyzloc)

            if puzzle["id"] in meta_ids or round_name == "Capstones":
                rounds[round_name]["num_metas"] += 1
                if status == "Solved":
                    rounds[round_name]["num_metas_solved"] += 1

            rounds[round_name]["max_id"] = max(
                rounds[round_name]["max_id"], int(puzzle["id"])
            )
        rounds = dict(
            sorted(
                rounds.items(),
                key=lambda item: (-item[1]["approx_solvers"], -item[1]["max_id"]),
            )
        )
        solved = [
            puzzle
            for puzzle in puzzles
            if puzzle["status"] == "Solved" and puzzle["answer"]
        ]

        guild = ctx.guild if ctx.guild else self.bot.get_guild(discord_info.GUILD_ID)
        members = discord_info.get_team_members(guild)
        online_members = [
            member for member in members if member.status != discord.Status.offline
        ]
        embed = discord.Embed(
            title="Hunt Status 📈📊",
            timestamp=self.bot.now(),
            description=(
                "🔄 Rounds: **{} opened**\n"
                + "🧩 Puzzles: **{} solved** out of **{} open**\n"
                + "👥 Hunters: **{} online**\n"
                + "\n**Rounds:**"
            ).format(
                len(rounds),
                len(solved),
                len(puzzles),
                len(online_members),
                # len(members),
            ),
        )

        solved_round_names = []

        for name, round in rounds.items():
            if (
                round["num_metas"] > 0
                and round["num_metas"] == round["num_metas_solved"]
                and round["Other"] == 0
                and round["Needs eyes"] == 0
                and round["Critical"] == 0
                and round["WTF"] == 0
                and round["approx_solvers"] == 0
            ):
                solved_round_names.append(name)
                continue
            if name == "Events" and round["Solved"] == 4:
                solved_round_names.append(name)
                continue
            value = "Out of **{total}** puzzles open:\n".format(**round)

            if round["Other"]:
                value += "🟢 New: **{Other}**\n".format(**round)
            if round["Needs eyes"]:
                value += "🔴 Needs eyes: **{}**\n".format(round["Needs eyes"])
            if round["Critical"]:
                value += "🔥 Critical: **{Critical}**\n".format(**round)
            if round["WTF"]:
                value += "☣️ WTF: **{WTF}**\n".format(**round)
            if round["Unnecessary"]:
                value += "⚪️ Unnecessary: **{Unnecessary}**\n".format(**round)
            if round["num_metas"]:
                value += (
                    "🎖 Metas: **{num_metas_solved}/{num_metas} solved**\n"
                ).format(**round)
            if round["Solved"]:
                value += "🏁 Solved: **{Solved}**\n".format(**round)
            if round["approx_solvers"]:
                value += "👩‍💻 **`≈{approx_solvers}`** solvers".format(**round)
            embed.add_field(name=name.title(), value=value, inline=True)

        solved_rounds = []
        for name in solved_round_names:
            if name not in rounds:
                continue
            round = rounds[name]
            solved_rounds.append("`{}` ({Solved}/{total})".format(name, **rounds[name]))
        if solved_rounds:
            embed.add_field(
                name="Completed ({}):".format(len(solved_rounds)),
                value="\n".join(solved_rounds),
                inline=True,
            )

        now = self.bot.now()
        hunt_begins = self.bot.hunt_begins
        hunt_ends = self.bot.hunt_ends
        hours_in = (min(now, hunt_ends) - hunt_begins).total_seconds() / 3600
        embed.set_footer(
            text="T{0:+.1f} hours {1} Hunt{2}".format(
                hours_in,
                "into" if hours_in >= 0 else "until",
                " [FINAL]" if now > hunt_ends else "",
            )
        )
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command()
    async def hipri(self, ctx):
        """Show hipri puzzles"""
        puzzles = sorted(
            puzzboss_interface.SQL.get_hipri_puzzles(bot=self.bot),
            key=lambda puzzle: (puzzle["status"], -1 * puzzle["ismeta"], puzzle["id"]),
        )
        response = "**Priority Puzzles ({}):**\n".format(len(puzzles))
        prefixes = {
            "Critical": "🔥",
            "Needs eyes": "🔴",
            "WTF": "☣️",
        }
        status = None
        for puzzle in puzzles:
            if status != puzzle["status"]:
                response += "\n"
            status = puzzle["status"]
            response += prefixes[status]
            response += " {status}: `{name}` (<#{channel_id}>)".format(**puzzle)
            if puzzle["ismeta"]:
                response += " [**META** 🏅]"
            if puzzle["xyzloc"]:
                response += " in **{}**".format(
                    xyzloc_mention(ctx.guild, puzzle["xyzloc"])
                )
            if puzzle["comments"]:
                comments = puzzle["comments"].replace("`", "'")[:200]
                comments = discord.utils.escape_markdown(comments)
                response += "\n`        Comments: {}`".format(comments)
            response += "\n"
        await ctx.send(response)


async def setup(bot):
    cog = HuntStatus(bot)
    await bot.add_cog(cog)
