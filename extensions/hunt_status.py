"""Get an overview of the entire hunt status"""

from db import REST, SQL
import discord
from discord.ext import commands, tasks
import discord_info
import json
import logging
from quickchart import QuickChart
import re
from common import plural, xyzloc_mention
from datetime import timedelta
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
        if now < self.bot.hunt_begins - timedelta(days=1):
            return
        if now > self.bot.hunt_ends:
            return
        members = discord_info.get_team_members(guild)
        online_members = [
            member for member in members if member.status != discord.Status.offline
        ]
        puzzles = SQL.get_all_puzzles()
        rounds = set(puzzle["round_name"] for puzzle in puzzles)
        solved = [
            puzzle
            for puzzle in puzzles
            if puzzle["status"] == "Solved" and puzzle["answer"]
        ]
        active_in_voice = set()
        tables_in_use = set()
        tables = [
            channel
            for channel in guild.voice_channels
            if "tables" in str(channel.category).lower()
        ]
        for table in tables:
            for user in table.members:
                if user in members and user.voice != discord.VoiceState.self_deaf:
                    active_in_voice.add(user.id)
                    tables_in_use.add(table.id)

        time_window_start = now - timedelta(minutes=15.0)
        last_loop_snowflake = (
            discord.utils.time_snowflake(now - timedelta(seconds=60.0), high=False) - 1
        )

        active_in_text = set()
        messages_per_minute = 0
        for channel in guild.text_channels:
            last_message_id = channel.last_message_id
            if not last_message_id:
                continue
            last_message_time = discord.utils.snowflake_time(last_message_id)
            if last_message_time < time_window_start:
                continue
            async for message in channel.history(after=time_window_start):
                if message.author in members:
                    active_in_text.add(message.author.id)
                    if message.id >= last_loop_snowflake:
                        messages_per_minute += 1

        active_in_sheets = set()
        solvers = SQL.get_all_solvers()
        recent_solvers = SQL.get_solver_ids_since(time=time_window_start)
        for solver in solvers:
            if solver["solver_id"] not in recent_solvers:
                continue
            active_in_sheets.add(int(solver["discord_id"] or solver["solver_id"]))

        emoji_roles = discord_info.get_emoji_roles(guild)
        in_person_role = emoji_roles.get("🏛️", None)
        if in_person_role is not None:
            in_person_members = set(member.id for member in in_person_role.members)
        else:
            in_person_members = set()
        active_anywhere = set().union(active_in_text, active_in_voice, active_in_sheets)

        metrics_payload = {
            "time": self.bot.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "hours_in": self.get_hunt_hours_clock(),
            "puzzles": {
                "total": len(puzzles),
                "solved": len(solved),
                "rounds": len(rounds),
            },
            "members": {
                "total": len(members),
                "online": len(online_members),
                "active_in_voice": len(active_in_voice),
                "active_in_text": len(active_in_text),
                "active_in_sheets": len(active_in_sheets),
                "active_in_discord": len(
                    set().union(
                        active_in_text,
                        active_in_voice,
                    )
                ),
                "active_anywhere": len(active_anywhere),
                "active_in_person": len(
                    active_anywhere.intersection(in_person_members)
                ),
            },
            "messages_per_minute": messages_per_minute,
            "tables_in_use": len(tables_in_use),
        }

        logging.info(
            f"<<<METRICS_SNAPSHOT>>> {self.bot.now().strftime('%Y-%m-%dT%H:%M:%S')}: "
            f"{json.dumps(metrics_payload)}"
        )

        members_metrics = metrics_payload["members"]
        botstats = {
            "puzzcord_members_total": members_metrics["total"],
            "puzzcord_members_online": members_metrics["online"],
            "puzzcord_members_active_in_voice": members_metrics["active_in_voice"],
            "puzzcord_members_active_in_text": members_metrics["active_in_text"],
            "puzzcord_members_active_in_sheets": members_metrics["active_in_sheets"],
            "puzzcord_members_active_in_discord": members_metrics["active_in_discord"],
            "puzzcord_members_active_anywhere": members_metrics["active_anywhere"],
            "puzzcord_members_active_in_person": members_metrics["active_in_person"],
            "puzzcord_messages_per_minute": metrics_payload["messages_per_minute"],
            "puzzcord_tables_in_use": metrics_payload["tables_in_use"],
        }
        for key, val in botstats.items():
            await REST.post(f"/botstats/{key}", data={"val": val})

    @commands.command()
    async def help(self, ctx, category: typing.Optional[str]):
        if category == "tools":
            await ctx.reply(
                """
```
!tools

Assorted puzzle-solving tools and utilities. (These all work as !tools abc or just !abc.)

Commands:
  abc        Converts letters A-Z to/from numbers 1-26
  atbash     Atbash cipher: flips A-Z to Z-A
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

        await ctx.reply(
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

See all commands here: https://{self.bot.team_domain}/wiki/index.php/Hunting_in_Discord:_A_Guide

Thanks, and happy hunting! 🕵️‍♀️🧩
"""
        )

    @commands.command()
    async def wifi(self, ctx):
        """Get the relevant WiFi login info"""
        config = self.bot.hunt_config
        wifi_url = f"https://{self.bot.team_domain}/wiki/index.php/WiFi"
        embed = discord.Embed(
            title="🛜 Connect to on-campus WiFi 🧑‍💻",
            url=wifi_url,
            description="Use the credentials below, or scan this QR code:",
            color=0x0033FF,
        )
        embed.set_thumbnail(url=config.wifi_qr)
        embed.add_field(name="Network", value=f"`{config.wifi_network}`", inline=True)
        embed.add_field(name="Password", value=f"`{config.wifi_password}`", inline=True)
        await ctx.reply(
            content=f"""
Student? Use **MIT SECURE**.
Alumni? Use **MIT**. Generate your password at [wifi.mit.edu](https://wifi.mit.edu)
Everyone else: **Do not use MIT GUEST.**

MIT GUEST is really slow and [has had Discord issues in the past]({wifi_url}).
It will give you a lot of pain. Instead, use this:
            """,
            embed=embed,
        )

    @commands.command()
    async def printer(self, ctx):
        """Get the relevant printer setup info"""
        await ctx.reply(
            content="""
If you're on campus, we have a printer in {hq_room} you can use.

You can [set up cloud printing]({printer_setup_link}) from your laptop/phone, but if that's a pain you can also walk up to the Zoom laptop and try printing directly.
            """.format(
                **self.bot.hunt_config
            ),
        )

    @commands.command()
    async def zoom(self, ctx):
        """Get the team Zoom link"""
        await ctx.reply(
            content="""
Our Zoom hangout: **<{zoom_link}>**
There's a live stream of {hq_room} throughout Hunt there.
We'll use it for team meetings & HQ interactions, but it's also fun to stay connected on mute while solving.
            """.format(
                **self.bot.hunt_config
            ),
        )

    @commands.command(aliases=["wrapped"])
    async def wrapup(self, ctx):
        """What puzzles you worked on, with links so you can go leave feedback"""
        if self.bot.now() < self.bot.hunt_ends:
            await ctx.reply("Shhh, not yet :)")
            return

        author = ctx.author
        solver = SQL.select_one(
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
        if not solver:
            await ctx.reply(
                (
                    f"Sorry, {author.mention}, I couldn't find your "
                    f"{self.bot.team_domain} account! "
                    f"Did you register? *Did you even hunt with us?*"
                )
            )
            return
        puzzles = (solver["puzzles"] or "").split(",")
        if not puzzles:
            await ctx.reply(
                (
                    f"Sorry, {author.mention}, I couldn't find any puzzles "
                    f"recorded to your {self.bot.team_domain} account. "
                    f"Maybe try using the `!here` and `!joinus` commands "
                    f"next year 😛"
                )
            )
            return
        puzzles = SQL.select_all(
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
        embed.set_thumbnail(url=self.bot.hunt_config.wrapped_icon)
        embed.set_footer(
            text="based on approximate data, assembled hastily with love by danny"
        )
        await ctx.reply(content="{0.mention}:".format(author), embed=embed)
        if len(descriptions) == 1:
            return
        for description in descriptions[1:]:
            await ctx.reply(embed=discord.Embed(description=description))

    @commands.command(aliases=["hunt"])
    async def status(self, ctx):
        """Hunt status update"""
        tables = discord_info.get_tables(ctx.guild)
        table_sizes = {table.name: len(table.members) for table in tables}
        puzzles = SQL.get_all_puzzles()
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

            if puzzle["ismeta"]:
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

        solved_round_names = SQL.get_solved_round_names()

        for name, round in rounds.items():
            if name in solved_round_names:
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

        embed.set_footer(text=self.get_hunt_hours_clock())
        await ctx.reply(embed=embed)

    def get_hunt_hours_clock(self):
        now = self.bot.now()
        hunt_begins = self.bot.hunt_begins
        hunt_ends = self.bot.hunt_ends
        hours_in = (min(now, hunt_ends) - hunt_begins).total_seconds() / 3600
        return "T{0:+.1f} hours {1} Hunt{2}".format(
            hours_in,
            "into" if hours_in >= 0 else "until",
            " [FINAL]" if now > hunt_ends else "",
        )

    @commands.command()
    async def progress(self, ctx):
        """Build graph of solve progress (vs. prior years)"""
        qc = QuickChart()
        qc.width = 1000
        qc.height = 600
        ordered_solve_times = SQL.select_all(
            """
            SELECT
                a.solve_time
            FROM (
                SELECT
                    puzzle_id,
                    MAX(time) - INTERVAL 5 HOUR AS solve_time
                FROM activity
                WHERE type = 'solve'
                GROUP BY puzzle_id
            ) a
            JOIN (SELECT id FROM puzzle_view WHERE status = 'Solved') p
                ON (a.puzzle_id = p.id)
            ORDER BY
                a.solve_time
            """,
        )
        current_json = json.dumps(
            [
                {"x": r["solve_time"].strftime("%d@%H:%M"), "y": i + 1}
                for (i, r) in enumerate(ordered_solve_times)
            ]
            + [
                {
                    "x": self.bot.now().strftime("%d@%H:%M"),
                    "y": len(ordered_solve_times),
                }
            ]
        )
        with open("progress-chart.json", "r") as f:
            chart_config_json = f.read().replace("[]", current_json)
        qc.config = json.loads(chart_config_json)
        await ctx.reply(qc.get_short_url())

    @progress.error
    async def progress_error(self, ctx, error):
        await ctx.reply(f"[progress] Error! {error}")
        raise error

    @commands.guild_only()
    @commands.command()
    async def hipri(self, ctx):
        """Show hipri puzzles"""
        puzzles = sorted(
            SQL.get_hipri_puzzles(),
            key=lambda puzzle: (
                puzzle["status"],
                -1 * int(puzzle["ismeta"]),
                puzzle["id"],
            ),
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
        await ctx.reply(response)

    @commands.Cog.listener("on_message")
    async def fix_hunt_emails(self, message):
        if message.author.id != 790401743669690428:
            return
        if "Unsubscribe: https://" not in message.content:
            return
        fixed = re.sub(r"Unsubscribe: https://\S+", "", message.content).strip()
        await message.channel.send(fixed)
        await message.delete()


async def setup(bot):
    cog = HuntStatus(bot)
    await bot.add_cog(cog)
