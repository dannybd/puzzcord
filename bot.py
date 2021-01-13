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
from pytz import timezone
from config import config
from discord_info import is_puzzle_channel

intents = discord.Intents.default()
intents.members = True
intents.presences = True

startup_extensions = ["solving_tools"]

default_help = commands.DefaultHelpCommand(
    no_category="Commands to try",
)

bot = commands.Bot(
    command_prefix="!",
    description="Controlling Puzzleboss via Discord",
    help_command=default_help,
    intents=intents,
)

@bot.event
async def on_ready():
    logging.info("Connected as {0.user} and ready!".format(bot))



@bot.listen("on_raw_reaction_add")
async def handle_reacts(payload):
    if payload.user_id == bot.user.id:
        return
    if not payload.guild_id:
        return
    emoji = str(payload.emoji)
    if emoji not in "🧩📌🧹":
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    channel = guild.get_channel(payload.channel_id)
    if not channel:
        return
    message = await channel.fetch_message(payload.message_id)
    if not message:
        return
    if emoji == "📌":
        if not message.pinned:
            await message.pin()
            await message.clear_reaction("🧹")
        return
    if emoji == "🧹":
        if message.pinned:
            await message.unpin()
            await message.clear_reaction("📌")
            await message.clear_reaction("🧹")
        return
    
if __name__ == "__main__":
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

    logging.info("Loading extensions...")
    for extension in glob.glob("bot_extensions/*.py"):
        try: 
            ext = extension[:-3]
            ext = ext.replace("/", ".")
            logging.info("Loading {}".format(ext))
            bot.load_extension(ext)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, traceback.format_exc())
            logging.warning('Failed to load extension {}\n{}'.format(extension, exc))
    logging.info("Starting!")
    bot.run(config["discord"]["botsecret"])
    logging.info("Done, closing out")
