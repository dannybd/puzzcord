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
                    "max_id": 0
                }
            rounds[round]["total"] += 1
            status = puzzle["status"]
            if status in rounds[round]:
                rounds[round][status] += 1
            else:
                rounds[round]["Other"] += 1
            rounds[round]["max_id"] = max(rounds[round]["max_id"], int(puzzle["id"]))
        rounds = dict(sorted(
            rounds.items(),
            key=lambda item: -item[1]["max_id"],
        ))
        solved = [
            puzzle for puzzle in puzzles
            if puzzle["status"] == "Solved" and puzzle["answer"]
        ]
        tz = timezone('US/Eastern')
        now = datetime.datetime.now(tz)

        guild = ctx.guild if ctx.guild else self.bot.get_guild(discord_info.GUILD_ID)
        members = guild.get_role(790341818885734430).members
        online_members = [
            member for member in members
            if member.status != discord.Status.offline
        ]
        embed = discord.Embed(
            title="Hunt Status 📈📊",
            timestamp=datetime.datetime.now(),
            description=(
                "🔄 Rounds: **{} opened**\n"
                + "🧩 Puzzles: **{} solved** out of **{} open**\n"
                + "👥 Hunters: **{} online** out of **{} total**\n"
                + "\n**Rounds:**"
            ).format(len(rounds), len(solved), len(puzzles), len(online_members), len(members))
        )
        for name, round in rounds.items():
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
                value += "✅ Solved: **{Solved}**\n".format(**round)
            embed.add_field(name=name, value=value, inline=True)
        hunt_begins = datetime.datetime(2021, 1, 15, hour=13, tzinfo=tz)
        hours_in = (now - hunt_begins).total_seconds() / 3600
        embed.set_footer(text="T{0:+.1f} hours into Hunt".format(hours_in))
        await ctx.send(embed=embed)


def setup(bot):
    cog = HuntStatus(bot)
    bot.add_cog(cog)
