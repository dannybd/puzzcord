""" Utility functions for getting information about discord channels, users, etc. """

import discord


GUILD_ID = 790341470171168800

VISITOR_ROLE = 795153098749771776
HUNT_MEMBER_ROLE = 790341818885734430
PUZZTECH_ROLE = 790341841916002335
PUZZBOSS_ROLE = 799032063725535242
BETABOSS_ROLE = 794351348295663616

WELCOME_LOBBY = 790341470602264576
PUZZTECH_CHANNEL = 790387626531225611
STATUS_CHANNEL = 790348440890507285
TABLE_REPORT_CHANNEL = 800167637354283038

PUZZLE_CATEGORY = 790343785804201984
SOLVED_PUZZLE_CATEGORY = 794869543448084491


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


def get_tables(ctx):
    return [
        channel
        for channel in ctx.guild.voice_channels
        if "tables" in str(channel.category).lower()
    ]
