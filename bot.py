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
            (
                channel.category.name.startswith("🧩")
                or channel.category.name.startswith("🏁")
            )
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
    connection = get_db_connection()
    logging.info("{0.command}: Connected to DB!".format(ctx))
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                name,
                xyzloc
            FROM puzzle_view
            WHERE slack_channel_id IN ({})
            """.format(",".join(["%s"] * len(channels))),
            tuple([c.id for c in channels]),
        )
        rows = cursor.fetchall()
    logging.info("{0.command}: {1} rows found!".format(ctx, len(rows)))
    if not rows:
        await ctx.send(
            "Sorry, I didn't find any puzzle channels in your command.\n" +
            "Try linking to puzzle channels by prefixing with #, like " +
            "#puzzle1"
        )
        return
    response = ""
    if len(rows) > 1:
        response += "Found {} puzzles:\n\n".format(len(rows))
    for row in rows:
        if row["xyzloc"]:
            line = "**`{name}`** can be found in **{xyzloc}**\n".format(**row)
        else:
            line = "**`{name}`** does not have a location set!\n".format(**row)
        response += line
    await ctx.send(response)
    return


@bot.command()
async def here(ctx):
    """Lets folks know this is the puzzle you're working on now."""
    # url = "https://wind-up-birds.org//" + "TODO"
    # async with aiohttp.ClientSession() as session:
    #     async with session.post(url) as response:
    #         logging.info("Sent!")
    #         print(response)
    await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')


# PUZZTECH ONLY COMMANDS


def puzztech_only():
    async def predicate(ctx):
        return 790341841916002335 in [role.id for role in ctx.author.roles]
    return commands.check(predicate)


@puzztech_only()
@bot.command(hidden=True, aliases=["nr"])
async def newround(ctx, *, round_name: str):
    """[puzztech only] Creates a new round"""
    logging.info("Creating a new round: {}".format(round_name))
    url_root = "https://wind-up-birds.org/puzzleboss/bin/pbrest.pl"
    url = url_root + "/rounds/" + round_name
    async with aiohttp.ClientSession() as session:
        async with session.post(url) as response:
            status = response.status
            logging.info("Sent! Response = {}".format(status))
            if status == 200:
                await ctx.send("Round created!")
                return
            if status == 500:
                await ctx.send("Error. This is likely because the round already exists.")
                return
            await ctx.send("Error. Something weird happened, try the PB UI directly.")


@puzztech_only()
@bot.command(hidden=True)
async def solved(ctx, *, channel: typing.Optional[discord.TextChannel]=None, answer: str):
    """[puzztech only] Mark a puzzle as solved and archive its channel"""
    # TODO: Implement me!
    return


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
