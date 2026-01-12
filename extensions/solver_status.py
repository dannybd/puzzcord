""" Get an overview of the entire hunt status """
from discord.ext import commands
from discord_info import HUNT_MEMBER_ROLE
import logging


class SolverStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_raw_poll_vote_add")
    async def handle_hunting_location_poll(self, payload):
        logging.info(f"Vote!, {payload=}")
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            logging.info(f"Poll: no guild")
            return
        user = guild.get_member(payload.user_id)
        if not user:
            logging.info(f"Poll: no user")
            return
        if user.get_role(HUNT_MEMBER_ROLE) is None:
            logging.info(f"Poll: not hunt member")
            return
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            logging.info(f"Poll: no channel")
            return
        message = await channel.fetch_message(payload.message_id)
        if not message:
            logging.info(f"Poll: no message")
            return
        poll = message.poll
        logging.info(f"Poll: {poll=}")
        if not poll:
            logging.info(f"Poll: no poll")
            return
        if poll.multiple:
            logging.info(f"Poll: poll was multiple")
            return
        if "hunting from" not in poll.question.lower():
            logging.info(f"Poll: {poll.question}")
            return
        answer = poll.get_answer(payload.answer_id)
        if not answer:
            logging.info(f"Poll: no answer")
            return
        emoji = answer.emoji
        logging.info(f"Poll: {emoji=}")
        if not emoji:
            return
        member_role = guild.get_role(HUNT_MEMBER_ROLE)
        emoji_roles = {
            role.unicode_emoji: role
            for role in guild.roles
            if role < member_role and role.unicode_emoji is not None
        }
        logging.info(f"Poll: {emoji_roles=}")
        new_role = emoji_roles.get(emoji.name, None)
        if not new_role:
            logging.info(f"Poll: No new role")
            return
        old_roles = [
            guild.get_role(role)
            for role in emoji_roles.values()
            if role != new_role and user.get_role(role) is not None
        ]
        if old_roles:
            await user.remove_roles(old_roles)
        await user.add_roles(guild.get_role(new_role))


async def setup(bot):
    cog = SolverStatus(bot)
    await bot.add_cog(cog)
