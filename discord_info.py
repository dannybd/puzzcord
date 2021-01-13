""" Utility functions for getting information about discord channels, users, etc. """

import discord


GUILD_ID = 790341470171168800
PUZZTECH_CHANNEL = 790387626531225611
STATUS_CHANNEL = 790348440890507285
PUZZLE_CATEGORY = 790343785804201984
SOLVED_PUZZLE_CATEGORY = 794869543448084491


def is_puzzle_channel(channel):
    if channel.type != discord.ChannelType.text:
        return False
    category = channel.category
    if not category:
        return False
    return category.name.startswith("🧩") or channel.category.name.startswith("🏁")

def get_table(member):
    voice = member.voice
    if not voice:
        return None
    channel = voice.channel
    if not channel:
        return None
    category = channel.category
    if not category:
        return None
    if "tables" not in category.name.lower():
        return None
    return channel


def get_tables(ctx):
    return [
        channel
        for channel in ctx.guild.voice_channels
        if "tables" in str(channel.category).lower()
    ]

