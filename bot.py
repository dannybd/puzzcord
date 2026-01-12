#! /usr/bin/python3

import asyncio
from datetime import datetime
import discord
import logging
import math
import os
import traceback
import glob

from discord.ext import commands
from config import config
from db import SQL
from discord_info import GUILD_ID, WELCOME_LOBBY
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

        self.hunt_config = SQL.get_hunt_config()
        self.tz = timezone(self.hunt_config.timezone)
        self.hunt_begins = self.from_iso(self.hunt_config.hunt_begins)
        self.hunt_ends = self.from_iso(self.hunt_config.hunt_ends)
        self.team_domain = self.hunt_config.team_domain

    def now(self):
        return datetime.now(self.tz)

    def from_iso(self, iso):
        return datetime.fromisoformat(iso).replace(tzinfo=self.tz)


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
        "verify",
    ]
    if ctx.invoked_with in ALLOWED_LOBBY_COMMANDS:
        return True

    msg = "No spoilers! Can't run this in {0.mention}".format(ctx.channel)
    await ctx.send(msg)
    raise NotInTheWelcomeLobby(msg)


async def main():
    async with bot:
        logging.info("Loading extensions...")
        extensions = glob.glob("extensions/*.py")
        for i, extension in enumerate(extensions):
            try:
                ext = extension[:-3]
                ext = ext.replace("/", ".")
                logging.info(
                    "[{i: >{width}}/{n: >{width}}] Loading {ext}".format(
                        i=i + 1,
                        n=len(extensions),
                        width=int(math.log10(len(extensions))),
                        ext=ext,
                    )
                )
                await bot.load_extension(ext)
            except Exception as e:
                exc = "{}: {}".format(type(e).__name__, traceback.format_exc())
                logging.warning(
                    "Failed to load extension {}\n{}".format(extension, exc)
                )
        logging.info(f"Starting! Discord Version {discord.__version__}")
        await bot.start(config.discord.botsecret)
        logging.info("Done, closing out")


asyncio.run(main())
