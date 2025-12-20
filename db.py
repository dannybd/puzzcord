""" Methods for interacting with the puzzbost REST api and SQL database """
import aiohttp
import discord
import logging
import pymysql
import re
from config import config
from discord_info import is_puzzle_channel
from munch import munchify


class REST:
    @staticmethod
    async def get(path):
        url = config.puzzledb["rest_url"] + path
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                logging.info(f"GET to {path} ; Response status = {response.status}")
                return response

    @staticmethod
    async def post(path, data=None):
        url = config.puzzledb["rest_url"] + path
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                logging.info(
                    f"POST to {path} ; "
                    f"Data = {data} ; "
                    f"Response status = {response.status}"
                )
                return response

    @staticmethod
    async def update_puzzle(puzzle_id, **parts):
        return await REST._post_parts("puzzles", puzzle_id, parts)

    @staticmethod
    async def update_round(round_id, **parts):
        return await REST._post_parts("rounds", round_id, parts)

    @staticmethod
    async def update_solver(solver_id, **parts):
        return await REST._post_parts("solvers", solver_id, parts)

    @staticmethod
    async def _post_parts(base_path, id, parts):
        for part in parts:
            response = await REST.post(f"/{base_path}/{id}/{part}", {part: parts[part]})
            if response.status != 200:
                break
        return response


class SQL:
    # Class variable to store connection once established
    connection = None

    @staticmethod
    def _get_db_connection():
        if SQL.connection:
            SQL.connection.ping(reconnect=True)
            return SQL.connection

        logging.info("[SQL] No connection found, creating new connection")
        creds = config.puzzledb
        connection = pymysql.connect(
            host=creds["host"],
            port=creds["port"],
            user=creds["user"].lower(),
            password=creds["passwd"],
            db=creds["db"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        SQL.connection = connection
        return connection

    @staticmethod
    def select_one(query: str, args=None):
        assert query.split()[0].upper() == "SELECT", "SELECT only!"
        connection = SQL._get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, args)
            return cursor.fetchone()

    @staticmethod
    def select_all(query: str, args=None):
        assert query.split()[0].upper() == "SELECT", "SELECT only!"
        connection = SQL._get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, args)
            return cursor.fetchall()

    @staticmethod
    def get_hunt_config():
        hunt_config = munchify(config.get("hunt_config", dict()))
        rows = SQL.select_all("SELECT `key`, val FROM config")
        hunt_config.update(**dict(row.values() for row in rows))
        return hunt_config

    @staticmethod
    def get_puzzle_for_channel(channel):
        rows = SQL.get_puzzles_for_channels([channel])
        return rows[channel.id] if channel.id in rows else None

    @staticmethod
    def get_puzzles_for_channels(channels):
        rows = SQL.select_all(
            """
            SELECT
                id,
                name,
                roundname AS round_name,
                puzzle_uri,
                drive_id,
                drive_uri,
                chat_channel_id AS channel_id,
                chat_channel_link,
                status,
                answer,
                xyzloc,
                comments
            FROM puzzle_view
            WHERE chat_channel_id IN ({})
            """.format(
                ",".join(["%s"] * len(channels))
            ),
            tuple([c.id for c in channels]),
        )
        return {int(row["channel_id"]): row for row in rows}

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
        except Exception:
            regex = re.compile(r"^$")
        query = query.replace(" ", "").lower()

        def puzzle_matches(name):
            if not name:
                return False
            if query in name.lower():
                return True
            return regex.search(name) is not None

        puzzles = SQL.select_all(
            """
            SELECT
                id,
                name,
                roundname AS round_name,
                puzzle_uri,
                drive_uri,
                chat_channel_id AS channel_id,
                status,
                answer,
                xyzloc,
                comments,
                cursolvers
            FROM puzzle_view
            """,
        )
        return next(
            (puzzle for puzzle in puzzles if puzzle_matches(puzzle["name"])),
            None,
        )

    @staticmethod
    def get_round_id_by_name(round_name):
        rows = SQL.select_one(
            """
            SELECT
                id
            FROM round_view
            WHERE
                name = %s
            """,
            (round_name,),
        )
        return row["id"] if row else None

    @staticmethod
    def get_solved_round_names():
        rows = SQL.select_all(
            """
            SELECT
                id,
                name
            FROM round_view
            WHERE
                name <> "mistakes"
                AND (
                    round_uri LIKE "%%#solved"
                    OR status = "Solved"
                )
            """,
        )
        return [row["name"] for row in rows]

    @staticmethod
    def get_meta_ids():
        rows = SQL.select_all(
            """
            SELECT
                id,
                meta_id
            FROM round_view
            WHERE
                name <> "mistakes"
            """,
        )
        return [row["meta_id"] for row in rows]

    @staticmethod
    def get_all_puzzles():
        return SQL.select_all(
            """
            SELECT
                id,
                name,
                roundname AS round_name,
                puzzle_uri,
                drive_uri,
                chat_channel_id AS channel_id,
                status,
                answer,
                xyzloc,
                comments
            FROM puzzle_view
            WHERE
                roundname <> "mistakes"
                AND status <> "[hidden]"
            """,
        )

    @staticmethod
    def get_hipri_puzzles():
        return SQL.select_all(
            """
            SELECT
                id,
                name,
                roundname AS round_name,
                chat_channel_id AS channel_id,
                status,
                xyzloc,
                comments
            FROM puzzle_view
            WHERE roundname <> "mistakes"
            AND status <> "[hidden]"
            AND status IN ("Critical", "Needs eyes", "WTF")
            ORDER BY status, id
            """,
        )

    @staticmethod
    def get_puzzles_at_table(table):
        return SQL.select_all(
            """
            SELECT
                id,
                name,
                status,
                chat_channel_id AS channel_id
            FROM puzzle_view
            WHERE xyzloc LIKE %s
            """,
            (table.name,),
        )

    @staticmethod
    def get_solver_from_member(member):
        row = SQL.select_one(
            """
            SELECT
                id,
                name
            FROM solver_view
            WHERE chat_uid = %s
            LIMIT 1
            """,
            (str(member.id),),
        )
        return row if row else None

    @staticmethod
    def get_all_solvers():
        return SQL.select_all(
            """
            SELECT
                id AS solver_id,
                name,
                fullname,
                chat_uid AS discord_id,
                chat_name AS discord_name
            FROM solver_view
            ORDER BY name
            """,
        )

    @staticmethod
    def get_solver_ids_since(time):
        rows = SQL.select_all(
            """
            SELECT
                DISTINCT solver_id
            FROM activity
            WHERE time > %s
            """,
            time,
        )
        return [row["solver_id"] for row in rows]
