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
    def _get_db_connection():
        creds = config["puzzledb"]
        return pymysql.connect(
            host=creds["host"],
            port=creds.getint("port"),
            user=creds["user"].lower(),
            password=creds["passwd"],
            db=creds["db"],
            cursorclass=pymysql.cursors.DictCursor,
        )

    @staticmethod
    def get_puzzle_for_channel(channel):
        rows = SQL.get_puzzles_for_channels([channel])
        return rows[channel.id] if channel.id in rows else None

    @staticmethod
    def get_puzzles_for_channels(channels):
        connection = SQL._get_db_connection()
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
    def get_puzzle_for_channel_fuzzy(ctx, channel_or_query):
        if not channel_or_query:
            if not is_puzzle_channel(ctx.channel):
                return None
            return SQL.get_puzzle_for_channel(ctx.channel)

        if isinstance(channel_or_query, discord.TextChannel):
            channel = channel_or_query
            return SQL.get_puzzle_for_channel(channel)

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

        connection = SQL._get_db_connection()
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
    def get_all_puzzles():
        connection = SQL._get_db_connection()
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
                """,
            )
            return cursor.fetchall()

    @staticmethod
    def get_solver_name_for_member(member):
        connection = SQL._get_db_connection()
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
