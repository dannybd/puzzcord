""" Methods for interacting with the puzzbost REST api and SQL database """
import json
import aiohttp
import logging
import pymysql
from config import config


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
                    xyzloc
                FROM puzzle_view
                WHERE slack_channel_id IN ({})
                """.format(
                    ",".join(["%s"] * len(channels))
                ),
                tuple([c.id for c in channels]),
            )
            return {int(row["channel_id"]): row for row in cursor.fetchall()}


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
                    xyzloc
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
