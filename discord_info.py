"""Utility functions for getting information about discord channels, users, etc."""

import discord

from config import config

GUILD_ID = int(config.guild.id)

VISITOR_ROLE = int(config.guild.roles.visitor)
HUNT_MEMBER_ROLE = int(config.guild.roles.hunt_member)
PUZZTECH_ROLE = int(config.guild.roles.puzztech)
PUZZBOSS_ROLE = int(config.guild.roles.puzzboss)
BETABOSS_ROLE = int(config.guild.roles.betaboss)

WELCOME_LOBBY = int(config.guild.channels.welcome_lobby)
PUZZTECH_CHANNEL = int(config.guild.channels.puzztech)
STATUS_CHANNEL = int(config.guild.channels.status)
TABLE_REPORT_CHANNEL = int(config.guild.channels.table_report)

PUZZLE_CATEGORY = int(config.guild.categories.puzzles)
SOLVED_PUZZLE_CATEGORY = int(config.guild.categories.solved_puzzles)


def get_team_members(guild):
    return guild.get_role(HUNT_MEMBER_ROLE).members


def is_puzzboss(member):
    return PUZZBOSS_ROLE in [role.id for role in member.roles]


def is_puzzle_channel(channel):
    if channel.type != discord.ChannelType.text:
        return False
    category = channel.category
    if not category:
        return False
    catname = category.name
    return catname.startswith("🧩") or catname.startswith("🏁") or catname.startswith("🚫")


def get_table(member):
    voice = member.voice
    if not voice:
        return None
    channel = voice.channel
    if not is_table_channel(channel):
        return None
    return channel


def is_table_channel(channel):
    if not channel:
        return False
    category = channel.category
    if not category:
        return False
    if "tables" not in category.name.lower():
        return False
    return True


def get_tables(guild):
    return [channel for channel in guild.voice_channels if is_table_channel(channel)]
