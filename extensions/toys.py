"""Contains some fun commands that aren't that useful"""

from discord.ext import commands
from common import plural


class Toys(commands.Cog):
    fun_reply_cooldowns = {}

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def huntyet(self, ctx):
        """Is it hunt yet?"""
        now = self.bot.now()
        timeleft = self.bot.hunt_begins - now
        if timeleft.days < 0:
            if now > self.bot.hunt_ends:
                await ctx.reply("Nope 😢 see y'all next year")
                return
            await ctx.reply("Yes! 🎉")
            return

        left = [
            plural(timeleft.days, "day"),
            plural(timeleft.seconds // 3600, "hour"),
            plural(timeleft.seconds // 60 % 60, "minute"),
            plural(timeleft.seconds % 60, "second"),
        ]
        await ctx.reply("No! " + ", ".join(left))

    @commands.command()
    async def zwsp(self, ctx):
        """Helper for getting a Zero Width Space"""
        await ctx.reply(
            "Here is a [zero-width space](<https://en.wikipedia.org/wiki/Zero-width_space>) "
            + "(ZWSP, U+200B): ```​``` "
            + "You can also copy one [here](<https://zerowidthspace.me/>)."
        )

    @commands.Cog.listener("on_message")
    async def fun_replies(self, message):
        if message.author == self.bot.user:
            return
        content = message.content.lower()
        channel = message.channel
        if "50/50" in content:
            if self.in_cooldown("50/50"):
                return
            await channel.reply("Roll up your sleeves!")
            return
        if "thanks obama" in content:
            if self.in_cooldown("thanks obama"):
                return
            await channel.reply("You're welcome!")
            return
        if "org chart" in content:
            if self.in_cooldown("org chart"):
                return
            await channel.reply("We had a plan, and we executed the plan.")
            return
        if "football" in content:
            if self.in_cooldown("football"):
                return
            await channel.reply("Football?  Really?")
            return
        if content.startswith("!backsolv"):
            if self.in_cooldown("!backsolve"):
                return
            message = await channel.reply(
                "It's only backsolving if it comes from the region of "
                + "actually understanding all the meta constraints, "
                + "otherwise it's just sparkling guessing."
            )
            await message.add_reaction("✨")
            await message.add_reaction("🔙")
            await message.add_reaction("🏁")

    def in_cooldown(self, key):
        last_send = self.fun_reply_cooldowns.get(key, None)
        now = self.bot.now()
        if last_send is not None:
            if (now - last_send).minutes < 1:
                return True
        self.fun_reply_cooldowns[key] = now
        return False

    @commands.command(hidden=True)
    async def hooray(self, ctx):
        await ctx.reply("🥳🎉🎊✨")


async def setup(bot):
    cog = Toys(bot)
    await bot.add_cog(cog)
