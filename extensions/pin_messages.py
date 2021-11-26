""" Lets users pin and unpin messages with emoji reacts """
import discord
from discord.ext import commands


class PinMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_raw_reaction_add")
    async def handle_reacts(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        if not payload.guild_id:
            return
        emoji = str(payload.emoji)
        if emoji not in "📌🧹":
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        message = await channel.fetch_message(payload.message_id)
        if not message:
            return
        if emoji == "📌":
            if not message.pinned:
                await message.pin()
                await message.clear_reaction("🧹")
            return
        if emoji == "🧹":
            if message.pinned:
                await message.unpin()
                await message.clear_reaction("📌")
                await message.clear_reaction("🧹")
            return


def setup(bot):
    cog = PinMessages(bot)
    bot.add_cog(cog)
