""" Get an overview of the entire hunt status """
import discord
from discord.ext import commands
import puzzboss_interface
import discord_info
from pytz import timezone
import datetime


class HuntStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["hunt"])
    async def status(self, ctx):
        """Hunt status update"""
        tables = [
            table
            for table in ctx.guild.voice_channels
            if table.category and table.category.name.startswith("🧊")
        ]
        table_sizes = {table.name: len(table.members) for table in tables}
        puzzles = puzzboss_interface.SQL.get_all_puzzles()
        rounds = {}
        for puzzle in puzzles:
            round = puzzle["round"]
            if round not in rounds:
                rounds[round] = {
                    "total": 0,
                    "Solved": 0,
                    "Other": 0,
                    "Needs eyes": 0,
                    "Critical": 0,
                    "WTF": 0,
                    "Unnecessary": 0,
                    "approx_solvers": 0,
                    "max_id": 0,
                }
            rounds[round]["total"] += 1
            status = puzzle["status"]
            if status in rounds[round]:
                rounds[round][status] += 1
            else:
                rounds[round]["Other"] += 1

            xyzloc = puzzle["xyzloc"]
            if xyzloc in table_sizes and status != "Solved":
                rounds[round]["approx_solvers"] += table_sizes[xyzloc]

            rounds[round]["max_id"] = max(rounds[round]["max_id"], int(puzzle["id"]))
        rounds = dict(
            sorted(
                rounds.items(),
                key=lambda item: -item[1]["max_id"],
            )
        )
        solved = [
            puzzle
            for puzzle in puzzles
            if puzzle["status"] == "Solved" and puzzle["answer"]
        ]
        tz = timezone("US/Eastern")
        now = datetime.datetime.now(tz)

        guild = ctx.guild if ctx.guild else self.bot.get_guild(discord_info.GUILD_ID)
        members = discord_info.get_team_members(guild)
        online_members = [
            member for member in members if member.status != discord.Status.offline
        ]
        embed = discord.Embed(
            title="Hunt Status 📈📊",
            timestamp=datetime.datetime.now(),
            description=(
                "🔄 Rounds: **{} opened**\n"
                + "🧩 Puzzles: **{} solved** out of **{} open**\n"
                + "👥 Hunters: **{} online** out of **{} total**\n"
                + "\n**Rounds:**"
            ).format(
                len(rounds),
                len(solved),
                len(puzzles),
                len(online_members),
                len(members),
            ),
        )

        solved_round_names = puzzboss_interface.SQL.get_solved_round_names()

        for name, round in rounds.items():
            if name in solved_round_names:
                continue
            value = "Out of **{total}** puzzles open:\n".format(**round)
            value += "🟢 New: **{Other}**\n".format(**round)
            if round["Needs eyes"]:
                value += "🔴 Needs eyes: **{}**\n".format(round["Needs eyes"])
            if round["Critical"]:
                value += "🔥 Critical: **{Critical}**\n".format(**round)
            if round["WTF"]:
                value += "☣️ WTF: **{WTF}**\n".format(**round)
            if round["Unnecessary"]:
                value += "⚪️ Unnecessary: **{Unnecessary}**\n".format(**round)
            if round["Solved"]:
                value += "🏁 Solved: **{Solved}**\n".format(**round)

            if round["approx_solvers"] and ctx.author.id == 276097439365201920:
                value += "👩‍💻 **`~{approx_solvers}`** solvers".format(**round)
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

        hunt_begins = datetime.datetime(2021, 1, 15, hour=13, tzinfo=tz)
        hours_in = (now - hunt_begins).total_seconds() / 3600
        embed.set_footer(
            text="T{0:+.1f} hours {1} Hunt".format(
                hours_in, "into" if hours_in >= 0 else "until"
            )
        )
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(aliases=["priorities", "urgent", "whatdoido", "highpri", "hifi"])
    async def hipri(self, ctx):
        """Show hipri puzzles"""
        puzzles = sorted(
            puzzboss_interface.SQL.get_hipri_puzzles(),
            key=lambda puzzle: (puzzle["status"], puzzle["id"]),
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
            if puzzle["xyzloc"]:
                response += " in **{xyzloc}**".format(**puzzle)
            if puzzle["comments"]:
                comments = puzzle["comments"].replace("`", "'")[:200]
                comments = discord.utils.escape_markdown(comments)
                response += "\n`        Comments: {}`".format(comments)
            response += "\n"
        await ctx.send(response)


def setup(bot):
    cog = HuntStatus(bot)
    bot.add_cog(cog)
