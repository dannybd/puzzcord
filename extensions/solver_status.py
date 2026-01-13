""" Get an overview of the entire hunt status """
from discord.ext import commands
from discord_info import HUNT_MEMBER_ROLE, get_emoji_roles
import logging


class SolverStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_raw_poll_vote_add")
    async def handle_hunting_location_poll(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        user = guild.get_member(payload.user_id)
        if not user:
            return
        if user.get_role(HUNT_MEMBER_ROLE) is None:
            return
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        message = await channel.fetch_message(payload.message_id)
        if not message:
            return
        poll = message.poll
        if not poll:
            return
        if poll.multiple:
            return
        if "hunting from" not in poll.question.lower():
            logging.info(f"Poll: {poll.question}")
            return
        answer = poll.get_answer(payload.answer_id)
        if not answer:
            return
        emoji = answer.emoji
        if not emoji:
            return
        member_role = guild.get_role(HUNT_MEMBER_ROLE)
        emoji_roles = get_emoji_roles()
        new_role = emoji_roles.get(emoji.name, None)
        if not new_role:
            logging.info(f"Poll: No new role for emoji {emoji.name}")
            return
        old_roles = [
            role
            for role in emoji_roles.values()
            if role != new_role and user.get_role(role.id) is not None
        ]
        if len(old_roles) > 0:
            await user.remove_roles(*old_roles)
        await user.add_roles(new_role)


async def setup(bot):
    cog = SolverStatus(bot)
    await bot.add_cog(cog)
