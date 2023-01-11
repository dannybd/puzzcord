""" Contains some fun commands that aren't that useful """


import discord
from discord.ext import commands
from discord.ext.commands import guild_only


class Toys(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["huntyet"], hidden=True)
    async def isithuntyet(self, ctx):
        """Is it hunt yet?"""
        timeleft = self.bot.hunt_begins - self.bot.now()
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
        if content == "!julia":
            await channel.send(
                "Have you tried reading the first letters of everything? "
                + "Yes? Okay, try it again."
            )
            return
        if "50/50" in content:
            await channel.send("Roll up your sleeves!")
            return
        if "thanks obama" in content:
            await channel.send("You're welcome!")
            return
        if content.startswith("!backsolv"):
            message = await channel.send(
                "It's only backsolving if it comes from the region of "
                + "actually understanding all the meta constraints, "
                + "otherwise it's just sparkling guessing."
            )
            await message.add_reaction("✨")
            await message.add_reaction("🔙")
            await message.add_reaction("🏁")

    @commands.command(hidden=True, aliases=["hurray"])
    async def hooray(self, ctx):
        await ctx.send("🥳🎉🎊✨")


async def setup(bot):
    cog = Toys(bot)
    await bot.add_cog(cog)
