#! /usr/bin/python3

import asyncio
import datetime
import discord
import json
import logging
import os
import pymysql
import random
import re
import sys
import typing
import traceback
import glob

from common import *
from discord.ext import commands
from discord.ext.commands import guild_only
from config import config
from discord_info import GUILD_ID, WELCOME_LOBBY, get_team_members
from puzzboss_interface import SQL
from pytz import timezone

# Define logging levels
loglevel = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s [%(process)d][%(name)s - %(levelname)s] - %(message)s",
    level=loglevel,
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler(),
    ],
)
if loglevel == "INFO":
    logging.getLogger("discord").setLevel(logging.WARNING)


intents = discord.Intents.all()
intents.members = True
intents.presences = True
intents.voice_states = True


class PuzzcordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        SQL._get_db_connection()
        self.hunt_team = config["hunt_team"]
        self.tz = timezone("US/Eastern")
        # TODO: Update for 2025
        self.hunt_begins = datetime.datetime(
            2024, 1, 12, hour=13, minute=20, tzinfo=self.tz
        )
        self.hunt_ends = datetime.datetime(2024, 1, 15, hour=12, tzinfo=self.tz)

    def now(self):
        return datetime.datetime.now(self.tz)


bot = PuzzcordBot(
    command_prefix="!",
    description="Controlling Puzzleboss via Discord",
    help_command=None,
    intents=intents,
)


@bot.event
async def on_ready():
    logging.info("Connected as {0.user} and ready!".format(bot))


class NotInTheWelcomeLobby(commands.CheckFailure):
    pass


@bot.check
async def members_only(ctx):
    guild = bot.get_guild(GUILD_ID)
    if ctx.guild and ctx.guild != guild:
        return False

    if ctx.channel.id != WELCOME_LOBBY:
        return True

    ALLOWED_LOBBY_COMMANDS = [
        "huntyet",
        "isithuntyet",
        "hooray",
        "onboard",
        "admin onboard",
        "verify",
        "admin verify",
    ]
    if ctx.invoked_with in ALLOWED_LOBBY_COMMANDS:
        return True

    msg = "No spoilers! Can't run this in {0.mention}".format(ctx.channel)
    await ctx.send(msg)
    raise NotInTheWelcomeLobby(msg)


async def main():
    async with bot:
        logging.info("Loading extensions...")
        for extension in glob.glob("extensions/*.py"):
            try:
                ext = extension[:-3]
                ext = ext.replace("/", ".")
                logging.info("Loading {}".format(ext))
                await bot.load_extension(ext)
            except Exception as e:
                exc = "{}: {}".format(type(e).__name__, traceback.format_exc())
                logging.warning(
                    "Failed to load extension {}\n{}".format(extension, exc)
                )
        logging.info("Starting!")
        await bot.start(config["discord"]["botsecret"])
        logging.info("Done, closing out")


asyncio.run(main())
