#! /usr/bin/python3

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
import puzzboss_interface

from common import *
from discord.ext import commands
from discord.ext.commands import guild_only
from config import config
from discord_info import GUILD_ID, WELCOME_LOBBY, get_team_members

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


intents = discord.Intents.default()
intents.members = True
intents.presences = True

default_help = commands.DefaultHelpCommand(
    no_category="Other Commands",
)


class PuzzcordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.connection = puzzboss_interface.SQL._get_db_connection()


bot = PuzzcordBot(
    command_prefix="!",
    description="Controlling Puzzleboss via Discord",
    help_command=default_help,
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

    if ctx.invoked_with in ["huntyet", "isithuntyet", "hooray"]:
        return True

    msg = "No spoilers! Can't run this in {0.mention}".format(ctx.channel)
    await ctx.send(msg)
    raise NotInTheWelcomeLobby(msg)


logging.info("Loading extensions...")
for extension in glob.glob("bot_extensions/*.py"):
    try:
        ext = extension[:-3]
        ext = ext.replace("/", ".")
        logging.info("Loading {}".format(ext))
        bot.load_extension(ext)
    except Exception as e:
        exc = "{}: {}".format(type(e).__name__, traceback.format_exc())
        logging.warning("Failed to load extension {}\n{}".format(extension, exc))
logging.info("Starting!")
bot.run(config["discord"]["botsecret"])
logging.info("Done, closing out")
