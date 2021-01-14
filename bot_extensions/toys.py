""" Contains some fun commands that aren't that useful """


import discord
from discord.ext import commands
from discord.ext.commands import guild_only
import datetime


class Toys(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["huntyet"], hidden=True)
    async def isithuntyet(self, ctx):
        """Is it hunt yet?"""
        timeleft = datetime.datetime.fromtimestamp(1610730000) - datetime.datetime.now()
        if timeleft.days < 0:
            await ctx.send("Yes! 🎉")
            return

        def plural(num, noun):
            if num == 1:
                return "1 {}".format(noun)
            return "{} {}s".format(num, noun)

        left = [
            plural(timeleft.days, "day"),
            plural(timeleft.seconds // 3600, "hour"),
            plural(timeleft.seconds // 60 % 60, "minute"),
            plural(timeleft.seconds % 60, "second"),
        ]
        await ctx.send("No! " + ", ".join(left))

    @commands.Cog.listener("on_message")
    async def fun_replies(self, message):
        if message.author == self.bot.user:
            return
        content = message.content.lower()
        channel = message.channel
        if "50/50" in content:
            await channel.send("Roll up your sleeves!")
            return
        if "thanks obama" in content:
            await channel.send("You're welcome!")
            return

    @commands.command(hidden=True, aliases=["hurray"])
    async def hooray(self, ctx):
        await ctx.send("🥳🎉🎊✨")


def setup(bot):
    cog = Toys(bot)
    bot.add_cog(cog)
