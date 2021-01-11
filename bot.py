#! /usr/bin/python3

import aiohttp
import configparser
import discord
import json
import logging
import os
import pymysql
import random
import sys
import typing

from discord.ext import commands

config = configparser.ConfigParser()
config.read("config.ini")

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

bot = commands.Bot(
    command_prefix='!',
    description="Controlling Puzzleboss via Discord",
    intents=intents,
)

GUILD_ID = 790341470171168800
PUZZTECH_CHANNEL = 790387626531225611
STATUS_CHANNEL = 790348440890507285
PUZZLE_CATEGORY = 790343785804201984
SOLVED_PUZZLE_CATEGORY = 794869543448084491


@bot.event
async def on_ready():
    logging.info("Connected as {0.user} and ready!".format(bot))


@bot.command()
async def roll(ctx, dice: str):
    """Rolls a dice in NdN format."""
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await ctx.send('Format has to be in NdN!')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await ctx.send(result)


@bot.command(aliases=["loc", "whereis"])
async def location(ctx, *channel_mentions: str):
    """Find where discussion of a puzzle is happening.
    Usage:
        Current puzzle:  !location
        Other puzzle(s): !location #puzzle1 #puzzle2
    """
    logging.info(
        "{0.command}: Start with {1} channel mentions".format(
            ctx,
            len(channel_mentions),
        )
    )
    if not channel_mentions:
        channel_mentions = [ctx.channel.mention]
    channels = [
        channel for channel in ctx.guild.text_channels if
            channel.mention in channel_mentions and
            is_puzzle_channel(channel)
    ]
    logging.info(
        "{0.command}: Found {1} puzzle channels".format(
            ctx,
            len(channels),
        )
    )
    if not channels:
        await ctx.send(
            "Sorry, I didn't find any puzzle channels in your command.\n" +
            "Try linking to puzzle channels by prefixing with #, like " +
            "#puzzle1"
        )
        return
    puzzles = get_puzzles_for_channels(channels)
    logging.info("{0.command}: {1} puzzles found!".format(ctx, len(puzzles)))
    if not puzzles:
        await ctx.send(
            "Sorry, I didn't find any puzzle channels in your command.\n" +
            "Try linking to puzzle channels by prefixing with #, like " +
            "#puzzle1"
        )
        return
    response = ""
    if len(puzzles) > 1:
        response += "Found {} puzzles:\n\n".format(len(puzzles))
    for puzzle in puzzles:
        if puzzle["xyzloc"]:
            line = "**`{name}`** can be found in **{xyzloc}**\n".format(**puzzle)
        else:
            line = "**`{name}`** does not have a location set!\n".format(**puzzle)
        response += line
    await ctx.send(response)
    return


@bot.command()
async def here(ctx):
    """Lets folks know this is the puzzle you're working on now."""
    if not is_puzzle_channel(ctx.channel):
        await ctx.send("Sorry, the !here command only works in puzzle channels.")
        return
    puzzle = get_puzzle_for_channel(ctx.channel)
    name = get_solver_name_for_member(ctx.author)
    response = await gen_pbrest(
        "/solvers/{0}/puzz".format(name),
        {"data": puzzle["name"]},
    )
    if response.status == 200:
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
        return
    await ctx.send("Sorry, something went wrong. Please use Puzzleboss to select your puzzle.")


@bot.command()
async def joinus(ctx):
    """Announces to a puzzle channel, inviting folks to join on a voice channel"""
    if not is_puzzle_channel(ctx.channel):
        await ctx.send("Sorry, the !joinus command only works in puzzle channels.")
        return
    table = get_table(ctx.author)
    if not table:
        await ctx.send("Sorry, you need to join one of the table voice chats before you can use the !joinus command.")
        return
    puzzle = get_puzzle_for_channel(ctx.channel)
    await gen_pbrest(
        "/puzzles/{name}/xyzloc".format(**puzzle),
        {"data": table.name},
    )


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
        channel for channel in ctx.guild.voice_channels
        if "tables" in str(channel.category).lower()
    ]


# PUZZBOSS ONLY COMMANDS


def puzzboss_only():
    async def predicate(ctx):
        # TODO: Make this more open to whoever's puzzbossing
        return 790341841916002335 in [role.id for role in ctx.author.roles]
    return commands.check(predicate)


@puzzboss_only()
@bot.command(hidden=True, aliases=["nr"])
async def newround(ctx, *, round_name: str):
    """[puzztech only] Creates a new round"""
    logging.info("{0.command}: Creating a new round: {1}".format(ctx, round_name))
    response = await gen_pbrest("/rounds/" + round_name)
    status = response.status
    if status == 200:
        await ctx.send("Round created!")
        return
    if status == 500:
        await ctx.send("Error. This is likely because the round already exists.")
        return
    await ctx.send("Error. Something weird happened, try the PB UI directly.")


@puzzboss_only()
@bot.command(hidden=True)
async def solved(ctx, channel: typing.Optional[discord.TextChannel], *, answer: str):
    """[puzztech only] Mark a puzzle as solved and archive its channel"""
    logging.info("{0.command}: Marking a puzzle as solved".format(ctx))
    apply_to_self = channel is None
    if apply_to_self:
        channel = ctx.channel
    puzzle = get_puzzle_for_channel(channel)
    if not puzzle:
        await ctx.send("Error: Could not find a puzzle for channel {0.mention}".format(channel))
        await ctx.message.delete()
        return
    response = await gen_pbrest(
        "/puzzles/{name}/answer".format(**puzzle),
        {"data": answer.upper()}
    )
    if apply_to_self:
        await ctx.message.delete()


@puzzboss_only()
@bot.command(hidden=True)
async def unverified(ctx):
    """Lists not-yet-verified team members"""
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                DISTINCT discord_id
            FROM discord_users
            """,
        )
        verified_discord_ids = [int(row["discord_id"]) for row in cursor.fetchall()]
    member_role = ctx.guild.get_role(790341818885734430)
    members = [
        "{0.name}#{0.discriminator} ({0.display_name})".format(member) for member in ctx.guild.members
        if member_role in member.roles and member.id not in verified_discord_ids
    ]
    await ctx.send("Folks needing verification ({0}):\n\n{1}".format(len(members), "\n".join(members)))


@bot.command()
async def verify(ctx, member: discord.Member, *, username: str):
    """Verifies a team member with their email
    Usage: !verify @member username[@wind-up-birds.org]
    """
    verifier_role = ctx.guild.get_role(794318951235715113)
    if verifier_role not in ctx.author.roles:
        await ctx.send("Sorry, only folks with the @{0.name} role can use this command.".format(verifier_role))
        return
    username = username.replace("@wind-up-birds.org", "")
    logging.info("{0.command}: Marking user {1.display_name} as PB user {2}".format(ctx, member, username))
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, fullname
            FROM solver
            WHERE name LIKE %s
            LIMIT 1
            """,
            (username,),
        )
        solver = cursor.fetchone()
    logging.info("{0.command}: Found solver {1}".format(ctx, solver["fullname"]))
    if not solver:
        await ctx.send("Error: Couldn't find a {0}@wind-up-birds.org, please try again.".format(username))
        return
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO discord_users
                (solver_id, solver_name, discord_id, discord_name)
            VALUES
                (%s, %s, %s, %s)
            """,
            (
                solver["id"],
                solver["name"],
                str(member.id),
                "{0.name}#{0.discriminator}".format(member)
            ),
        )
        logging.info("{0.command}: Committing row".format(ctx))
        connection.commit()
        logging.info("{0.command}: Committed row successfully!".format(ctx))
    member_role = ctx.guild.get_role(790341818885734430)
    if member_role not in member.roles:
        logging.info("{0.command}: Adding member role!".format(ctx))
        await member.add_roles([member_role])
    await ctx.send("**{0.display_name}** is now verified as **{1}**!".format(member, solver["name"]))


async def gen_pbrest(path, data=None):
    url = "https://wind-up-birds.org/puzzleboss/bin/pbrest.pl" + path
    if data:
        data = json.dumps(data)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            logging.info("POST to {} ; Data = {} ; Response status = {}".format(path, data, response.status))
            return response


def get_puzzle_for_channel(channel):
    rows = get_puzzles_for_channels([channel])
    return rows[channel.id] if channel.id in rows else None


def get_puzzles_for_channels(channels):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM puzzle_view
            WHERE slack_channel_id IN ({})
            """.format(",".join(["%s"] * len(channels))),
            tuple([c.id for c in channels]),
        )
        return {int(row["slack_channel_id"]): row for row in cursor.fetchall()}


def get_solver_name_for_member(member):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT solver_name
            FROM discord_users
            WHERE discord_id = %s
            """,
            (str(member.id),),
        )
        row = cursor.fetchone()
    return row["solver_name"] if row else None


def get_db_connection():
    creds = config["puzzledb"]
    return pymysql.connect(
        host=creds["host"],
        port=creds.getint("port"),
        user=creds["user"].lower(),
        password=creds["passwd"],
        db=creds["db"],
        cursorclass=pymysql.cursors.DictCursor,
    )


def is_puzzle_channel(channel):
    category = channel.category
    if not category:
        return False
    return category.name.startswith("🧩") or channel.category.name.startswith("🏁")


if __name__ == "__main__":
    # Define logging levels
    loglevel = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(
        format="%(asctime)s [%(process)d][%(name)s - %(levelname)s] - %(message)s",
        level=loglevel,
        handlers=[
            logging.FileHandler("logs/client.log"),
            logging.StreamHandler(),
        ],
    )
    if loglevel == "INFO":
        logging.getLogger("discord").setLevel(logging.WARNING)

    logging.info("Starting!")
    bot.run(config["discord"]["botsecret"])
    logging.info("Done, closing out")
