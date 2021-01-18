""" Methods for interacting with the puzzbost REST api and SQL database """
import aiohttp
import discord
import json
import logging
import pymysql
import re
from config import config
from discord_info import is_puzzle_channel


class REST:
    @staticmethod
    async def post(path, data=None):
        url = "https://wind-up-birds.org/puzzleboss/bin/pbrest.pl" + path
        if data:
            data = json.dumps(data)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                logging.info(
                    "POST to {} ; Data = {} ; Response status = {}".format(
                        path, data, response.status
                    )
                )
                return response


class SQL:
    @staticmethod
    def _get_db_connection(bot=None):
        if bot and bot.connection:
            bot.connection.ping(reconnect=True)
            return bot.connection

        logging.info("[SQL] No bot found, creating new connection")
        creds = config["puzzledb"]
        return pymysql.connect(
            host=creds["host"],
            port=creds.getint("port"),
            user=creds["user"].lower(),
            password=creds["passwd"],
            db=creds["db"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    @staticmethod
    def get_puzzle_for_channel(channel, bot=None):
        rows = SQL.get_puzzles_for_channels([channel], bot=bot)
        return rows[channel.id] if channel.id in rows else None

    @staticmethod
    def get_puzzles_for_channels(channels, bot=None):
        connection = SQL._get_db_connection(bot=bot)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    name,
                    round,
                    puzzle_uri,
                    drive_uri,
                    slack_channel_id AS channel_id,
                    status,
                    answer,
                    xyzloc,
                    comments
                FROM puzzle_view
                WHERE slack_channel_id IN ({})
                """.format(
                    ",".join(["%s"] * len(channels))
                ),
                tuple([c.id for c in channels]),
            )
            return {int(row["channel_id"]): row for row in cursor.fetchall()}

    @staticmethod
    def get_puzzle_for_channel_fuzzy(ctx, channel_or_query, bot=None):
        if not channel_or_query:
            if not is_puzzle_channel(ctx.channel):
                return None
            return SQL.get_puzzle_for_channel(ctx.channel, bot=bot)

        if isinstance(channel_or_query, discord.TextChannel):
            channel = channel_or_query
            return SQL.get_puzzle_for_channel(channel, bot=bot)

        query = channel_or_query
        try:
            regex = re.compile(query, re.IGNORECASE)
        except Exception as e:
            regex = re.compile(r"^$")
        query = query.replace(" ", "").lower()

        def puzzle_matches(name):
            if not name:
                return False
            if query in name.lower():
                return True
            return regex.search(name) is not None

        connection = SQL._get_db_connection(bot=bot)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    name,
                    round,
                    puzzle_uri,
                    drive_uri,
                    slack_channel_id AS channel_id,
                    status,
                    answer,
                    xyzloc,
                    comments
                FROM puzzle_view
                """,
            )
            puzzles = cursor.fetchall()
            return next(
                (puzzle for puzzle in puzzles if puzzle_matches(puzzle["name"])),
                None,
            )

    @staticmethod
    def get_solved_round_names(bot=None):
        connection = SQL._get_db_connection(bot=bot)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    name
                FROM round
                WHERE round_uri LIKE '%%#solved'
                AND name <> "mistakes"
                """,
            )
            return [row["name"] for row in cursor.fetchall()]

    @staticmethod
    def get_all_puzzles(bot=None):
        connection = SQL._get_db_connection(bot=bot)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    round,
                    puzzle_uri,
                    drive_uri,
                    slack_channel_id AS channel_id,
                    status,
                    answer,
                    xyzloc,
                    comments
                FROM puzzle_view
                WHERE round <> "mistakes"
                """,
            )
            return cursor.fetchall()

    @staticmethod
    def get_hipri_puzzles(bot=None):
        connection = SQL._get_db_connection(bot=bot)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    round,
                    slack_channel_id AS channel_id,
                    status,
                    xyzloc,
                    comments
                FROM puzzle_view
                WHERE round <> "mistakes"
                AND status IN ("Critical", "Needs eyes", "WTF")
                ORDER BY status, id
                """,
            )
            return cursor.fetchall()

    @staticmethod
    def get_puzzles_at_table(table, bot=None):
        connection = SQL._get_db_connection(bot=bot)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    name,
                    status,
                    slack_channel_id AS channel_id
                FROM puzzle_view
                WHERE xyzloc LIKE %s
                """,
                (table.name,),
            )
            return cursor.fetchall()

    @staticmethod
    def get_solver_name_for_member(member, bot=None):
        connection = SQL._get_db_connection(bot=bot)
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
