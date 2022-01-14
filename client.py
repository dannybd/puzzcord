#! /usr/bin/python3

import asyncio
import configparser
import discord
import json
import logging
import nest_asyncio
import os
import pymysql
import sys

from common import *
from config import config
from datetime import datetime, timedelta

nest_asyncio.apply()

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

GUILD_ID = 790341470171168800
STATUS_CHANNEL = 790348440890507285
PUZZLE_CATEGORY = 790343785804201984
SOLVED_PUZZLE_CATEGORY = 794869543448084491


@client.event
async def on_ready():
    logging.info("Connected as {0.user} and ready!".format(client))
    try:
        loop = asyncio.get_event_loop()
        coro = asyncio.start_server(
            gen_handle_server_request,
            host=config["asyncio_server"]["host"],
            port=config["asyncio_server"]["port"],
            loop=loop,
        )
        server = loop.run_until_complete(coro)

        # Serve requests until Ctrl+C is pressed
        logging.info("Serving on {}".format(server.sockets[0].getsockname()))
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

        # Close the server
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()
    except Exception as e:
        logging.error(e, exc_info=e)
        raise
    finally:
        await client.close()


async def gen_handle_server_request(reader, writer):
    response = None
    try:
        data = await reader.read()
        message = data.decode()
        if message:
            logging.info("Recv: %r" % message)
            command, *args = message.split()
            response = await gen_run(command, args) + "\n"
    except Exception as e:
        logging.error(e, exc_info=e)
    finally:
        if response:
            logging.info("Send: %r" % response)
            writer.write(response.encode())
        await writer.drain()
        writer.close()


async def gen_run(command, args):
    global guild, status_channel
    guild = client.get_guild(GUILD_ID)
    status_channel = client.get_channel(STATUS_CHANNEL)

    if command == "create" or command == "create_json":
        name, *topic = args
        topic = " ".join(topic)
        channel = await gen_create_channel(name, topic)
        invite = await channel.create_invite()
        return (
            json.dumps(
                {
                    "id": channel.id,
                    "name": channel.name,
                    "mention": channel.mention,
                    "url": invite.url,
                }
            )
            + "\n"
        )

    if command == "message":
        channel_id, *content = args
        content = " ".join(content)
        message = await gen_message_channel(channel_id, content)
        return message.jump_url

    # DB Commands
    rest_of_args = " ".join(args)

    if command == "_new":
        puzzle_name = rest_of_args
        return await gen_announce_new(puzzle_name)

    if command == "_solve":
        puzzle_name = rest_of_args
        return await gen_announce_solve(puzzle_name)

    if command == "_attention":
        puzzle_name = rest_of_args
        return await gen_announce_attention(puzzle_name)

    if command == "_round":
        round_name = rest_of_args
        return await gen_announce_round(round_name)

    # Helper methods
    if command == "stats":
        return await gen_stats()

    if command == "cleanup":
        justification = rest_of_args
        return await gen_cleanup(justification)

    raise Exception("command {0} not supported!".format(command))


@client.event
async def on_error(*args, **kwargs):
    await client.close()


async def gen_announce_new(puzzle_name):
    puzzle, channel = get_puzzle_and_channel(puzzle_name)
    round_category = await gen_or_create_round_category(puzzle["round_name"])
    await channel.edit(
        category=round_category,
        position=0,
    )
    content = "**🚨 New Puzzle 🚨 _`{name}`_ ADDED!**".format(**puzzle)
    embed = build_puzzle_embed(puzzle, channel.guild)
    message = await channel.send(content=content, embed=embed)
    await message.pin()
    await status_channel.send(content=content, embed=embed)
    here = await channel.send(
        "**Please click the 🧩 reaction** on this message to indicate "
        + "that you're working on this puzzle."
    )
    await here.add_reaction("🧩")
    return "Puzzle created"


async def gen_announce_solve(puzzle_name):
    puzzle, channel = get_puzzle_and_channel(puzzle_name)
    await gen_archive_channel(puzzle, channel)
    await channel.send(
        "**Puzzle solved!** Answer: ||`{answer}`||".format(**puzzle)
        + "\nChannel is now archived."
    )
    content = (
        "**🎉 Puzzle _`{name}`_ has been solved! 🥳**\n"
        + "(Answer: ||`{answer}`||)\n"
        + "Way to go team! 🎉"
    ).format(**puzzle)
    await status_channel.send(content=content)
    return "Solve announced"


async def gen_announce_attention(puzzle_name):
    puzzle, channel = get_puzzle_and_channel(puzzle_name)

    status = puzzle["status"]

    channel_name_prefix = ""
    content = None
    embed = None

    if status == "Needs eyes":
        channel_name_prefix = "🔴 "
        content = "**❗️ Puzzle _`{name}`_ NEEDS EYES! 👀**".format(**puzzle)
        embed = build_puzzle_embed(puzzle, channel.guild)

    if status == "Critical":
        channel_name_prefix = "🔥 "
        content = "**🚨 Puzzle _`{name}`_ IS CRITICAL! ⚠️**".format(**puzzle)
        embed = build_puzzle_embed(puzzle, channel.guild)

    if status == "Unnecessary":
        channel_name_prefix = "⚪️ "
        content = "**🤷 Puzzle _`{name}`_ is now UNNECESSARY! 🤷**".format(**puzzle)
        embed = None

    if status == "WTF":
        channel_name_prefix = "💣 "
        content = "**💣Puzzle _`{name}` is WTF! ☣️**".format(**puzzle)
        embed = None

    if content:
        await status_channel.send(content=content, embed=embed)
        message = await channel.send(content=content, embed=embed)
        await message.pin()

    # We need to check for whether this bot has edited this channel's
    # name too recently. If it has, we'll be rate limited. So instead,
    # let's check and skip in that case.
    rate_limit_range = datetime.now() - timedelta(minutes=10)
    recent_channel_update_by_bot = await guild.audit_logs(
        limit=None,
        user=guild.me,
        action=discord.AuditLogAction.channel_update,
        after=rate_limit_range,
    ).find(
        lambda entry: entry.target == channel and entry.created_at >= rate_limit_range,
    )

    if recent_channel_update_by_bot:
        logging.warning(
            (
                "Channel #{0.name} was auto-updated too recently! "
                + "Bot will be rate-limited if we try, existing early. "
                + "If you need to change the name, do it manually. "
                + "(Channel last auto-updated at {1.created_at})"
            ).format(channel, recent_channel_update_by_bot)
        )
        return "Warning: too recent update"
    await channel.edit(name=channel_name_prefix + puzzle["name"])
    return "Puzzle change announced"


async def gen_announce_round(round_name):
    await gen_or_create_round_category(round_name)
    content = "🆕🔄 **New Round added! _`{0}`_**".format(round_name)
    embed = discord.Embed(
        color=get_round_embed_color(round_name),
        title="Round: _`{0}`_".format(round_name),
    )
    await status_channel.send(content=content, embed=embed)
    return "Round announced"


async def gen_or_create_round_category(round_name, is_solved=False):
    category_name = ("🏁 Solved from: {0}" if is_solved else "🧩 {0}").format(round_name)
    existing_categories = [c for c in guild.categories if c.name == category_name]
    category = discord.utils.find(
        lambda category: len(category.channels) < 50,
        existing_categories,
    )
    if category:
        logging.info('Existing category "{0.name}" found'.format(category))
        return category

    if is_solved:
        # 🏁 Solved Puzzles: 🏁
        source_category = client.get_channel(SOLVED_PUZZLE_CATEGORY)
    else:
        # 🧩 Puzzles below here: 🧩
        source_category = client.get_channel(PUZZLE_CATEGORY)
    position = source_category.position + 1

    if existing_categories:
        # If this is an overflow category, position it just above the
        # other categories it belongs to
        position = min(category.position for category in existing_categories)

    logging.info("Creating new category: {0}".format(category_name))
    category = await source_category.clone(name=category_name)
    await category.edit(position=position)
    return category


async def gen_create_channel(name, topic):
    category = client.get_channel(PUZZLE_CATEGORY)
    channel = await category.create_text_channel(
        name=name,
        position=1,
        reason='New puzzle: "{0}"'.format(name),
        topic=topic,
    )
    logging.info("Created #{0.name} puzzle channel".format(channel))
    return channel


async def gen_message_channel(channel_id, content):
    channel = get_channelx(channel_id)
    if " is being worked on at " in content:
        first, table = content.split(" is being worked on at ")
        table = table.strip()
        if not table or table == "":
            return
        content = "{} is being worked on at {}".format(
            first, xyzloc_mention(channel.guild, table)
        )
    message = await channel.send(content=content)
    logging.info("Message sent to {0.name}".format(channel))
    return message


async def gen_archive_channel(puzzle, channel):
    start_category = channel.category
    if start_category.name.startswith("🏁"):
        logging.warning("{0.name} ({0.id}) already solved".format(channel))
        return

    solved_category = await gen_or_create_round_category(
        round_name=puzzle["round_name"],
        is_solved=True,
    )
    await channel.edit(
        category=solved_category,
        position=0,
        reason='Puzzle "{0.name}" solved, archiving!'.format(channel),
    )
    logging.info("Archived #{0.name} puzzle channel".format(channel))

    if start_category.id in [PUZZLE_CATEGORY, SOLVED_PUZZLE_CATEGORY]:
        return
    if not start_category.channels:
        logging.info("Puzzle category {0.name} now empty, deleting".format(channel))
        await start_category.delete()


async def gen_stats():
    response = "Server has {0} members, including bots\n".format(len(guild.members))
    connection = get_db_connection()
    logging.info("Connected to DB!")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                name,
                roundname AS round_name,
                status
            FROM puzzle_view
            ORDER BY id
            """,
        )
        rounds = {}
        for puzzle in cursor.fetchall():
            round_name = puzzle["round_name"]
            if round_name not in rounds:
                rounds[round_name] = []
            rounds[round_name].append(puzzle)
        response += json.dumps(rounds) + "\n"
        for round_name, puzzles in rounds.items():
            response += "~~~~~\n"
            response += round_name + ":\n"
            response += "  {0} puzzles opened so far".format(len(puzzles)) + "\n"
            response += (
                "  {0} puzzles solved".format(
                    len([p for p in puzzles if p["status"] == "Solved"])
                )
                + "\n"
            )
            response += (
                "  {0} puzzles unsolved".format(
                    len([p for p in puzzles if p["status"] != "Solved"])
                )
                + "\n"
            )
            response += (
                "  {0} puzzles need eyes".format(
                    len([p for p in puzzles if p["status"] == "Needs eyes"])
                )
                + "\n"
            )
            response += (
                "  {0} puzzles critical".format(
                    len([p for p in puzzles if p["status"] == "Critical"])
                )
                + "\n"
            )
            response += (
                "  {0} puzzles WTF".format(
                    len([p for p in puzzles if p["status"] == "WTF"])
                )
                + "\n"
            )
    logging.info("Closing DB connection!")
    connection.close()
    return response


async def gen_cleanup(justification):
    discord_channels = [
        channel
        for channel in guild.text_channels
        if channel.category
        and (
            channel.category.name.startswith("🧩")
            or channel.category.name.startswith("🏁")
        )
    ]
    logging.info("Found {0} puzzle channels on Discord".format(len(discord_channels)))
    connection = get_db_connection()
    logging.info("Connected to DB!")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
               chat_channel_id AS channel_id
            FROM puzzle_view
            """,
        )
        db_channel_ids = set(int(row["channel_id"]) for row in cursor.fetchall())
        logging.info("Found {0} puzzle channels in the DB".format(len(db_channel_ids)))
    logging.info("Closing DB!")
    connection.close()
    unknown_channels = [
        channel for channel in discord_channels if channel.id not in db_channel_ids
    ]
    logging.info(
        "Found {0} puzzle channels on Discord NOT in the DB: {1}".format(
            len(unknown_channels),
            {c.id: c.name for c in unknown_channels},
        )
    )
    if "no really" not in justification:
        logging.info("Execute not used, exiting.")
        return "You need to call this with 'no really' to actually delete"

    if "purge" in justification:
        await status_channel.purge(limit=1000)

    if "everything" in justification:
        channels_to_delete = discord_channels
    else:
        channels_to_delete = unknown_channels

    for channel in channels_to_delete:
        logging.warning("Deleting {0.name} ({0.id})!".format(channel))
        await channel.delete()
    empty_categories = [
        category
        for category in guild.categories
        if not category.channels
        and category.id not in [PUZZLE_CATEGORY, SOLVED_PUZZLE_CATEGORY]
        and (category.name.startswith("🧩") or category.name.startswith("🏁"))
    ]
    logging.info("Found {0} empty puzzle categories".format(len(empty_categories)))
    for category in empty_categories:
        logging.warning("Deleting {0.name} ({0.id})!".format(category))
        await category.delete()


def get_channelx(channel_id):
    channel = None
    if isinstance(channel_id, int) or channel_id.isnumeric():
        channel = client.get_channel(int(channel_id))
    if channel == None:
        channel = discord.utils.get(client.get_all_channels(), name=channel_id)
    if channel == None:
        raise Exception("Channel ID {0} missing!".format(channel_id))
    return channel


def get_puzzle_and_channel(puzzle_name):
    puzzle = _get_puzzle_from_db(puzzle_name)
    if puzzle is None:
        raise Exception('Puzzle "{0}" not found'.format(puzzle_name))
    return (puzzle, client.get_channel(int(puzzle["channel_id"])))


def _get_puzzle_from_db(puzzle_name):
    connection = get_db_connection()
    logging.info("Connected to DB!")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                name,
                roundname AS round_name,
                puzzle_uri,
                chat_channel_id AS channel_id,
                drive_uri,
                status,
                answer,
                xyzloc,
                comments
            FROM puzzle_view
            WHERE name = %s
            LIMIT 1
            """,
            (puzzle_name,),
        )
        logging.info("Closing DB!")
        connection.close()
        return cursor.fetchone()


def get_db_connection():
    creds = config["puzzledb"]
    return pymysql.connect(
        host=creds["host"],
        port=creds["port"],
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
    client.run(config["discord"]["botsecret"])
    logging.info("Done, closing out")
