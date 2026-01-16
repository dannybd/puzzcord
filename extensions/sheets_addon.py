""" Get an overview of the entire hunt status """
import aiohttp
from config import config
from db import SQL
from discord.ext import commands, tasks
from discord_info import STATUS_CHANNEL
import json
import logging


class SheetsAddon(commands.Cog):
    cookies = {}

    def __init__(self, bot):
        self.bot = bot
        # self.rotate_1psidts.start()
        self.cookies = config.sheets_addon.cookies
        try:
            with open(".1PSIDTS", "r") as file:
                self.cookies["__Secure-1PSIDTS"] = json.load(file)
        except Exception:
            pass

    def cog_unload(self):
        self.rotate_1psidts.cancel()

    @tasks.loop(seconds=60.0, reconnect=True)
    async def rotate_1psidts(self):
        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            url = "https://accounts.google.com/RotateCookies"
            headers = config.sheets_addon.refresh_headers
            data = '[283,"1575614563079730632"]'
            async with session.post(url, headers=headers, data=data) as response:
                if response.status == 401:
                    logging.error("SheetsAddon: Auth is lost! Requires manual fix.")
                if response.status == 429:
                    logging.error("SheetsAddon: 429 Too Many Requests; waiting.")
                    return
                response.raise_for_status()
                new_1psidts = response.cookies.get("__Secure-1PSIDTS")
                if not new_1psidts:
                    return
                if self.cookies["__Secure-1PSIDTS"] == new_1psidts:
                    return
                logging.info("SheetsAddon: Updated __Secure-1PSIDTS!")
                self.cookies["__Secure-1PSIDTS"] = new_1psidts
                with open(".1PSIDTS", "w") as file:
                    json.dump(new_1psidts, file)
                logging.info("SheetsAddon: Saved __Secure-1PSIDTS!")

    @commands.command(aliases=["activate"])
    async def activate_all(self, ctx):
        puzzles_to_activate = SQL.select_all(
            """
            SELECT
              drive_id
            FROM puzzle
            WHERE
              sheetenabled = 0
              AND status <> "Solved"
            """
        )
        sheets = [puzzle["drive_id"] for puzzle in puzzles_to_activate]
        msg = "Sheets to activate:\n\n"
        for sheet_id in sheets:
            msg += f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit\n"
        if ctx:
            await ctx.reply(msg)
        for sheet_id in sheets:
            await self.activate(ctx, sheet_id)

    async def activate(self, ctx, sheet_id):
        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            logging.info(f"SheetsAddon: Trying for {sheet_id=}")
            sid = config.sheets_addon.invoke_get_params.sid
            token = config.sheets_addon.invoke_get_params.token
            _rest = config.sheets_addon.invoke_get_params._rest
            url = (
                f"https://docs.google.com/spreadsheets/u/0/d/{sheet_id}/scripts/invoke"
                f"?id={sheet_id}&sid={sid}&token={token}{_rest}"
            )
            headers = config.sheets_addon.invoke_headers
            async with session.post(url, headers=headers) as response:
                if response.status == 401:
                    logging.error("SheetsAddon: Auth is lost!")
                response.raise_for_status()
                text = await response.text()
                text = "\n".join(text.split("\n")[1:]).strip()
                logging.info(f"SheetsAddon: Activated for {sheet_id=}, response={text}")
                if ctx:
                    await ctx.reply(f"Activated for {sheet_id=}")

    @commands.Cog.listener("on_message")
    async def activate_on_new_puzzle(self, message):
        if message.channel.id != STATUS_CHANNEL:
            return
        if message.author.id != self.bot.user.id:
            return
        if "🚨 New Puzzle 🚨" not in message.content:
            return
        embeds = message.embeds
        if not embeds or len(embeds) != 1:
            return
        for field in embeds[0].to_dict()["fields"]:
            if "https://docs.google.com/spreadsheets/d/" not in field["value"]:
                continue
            sheet_id = (
                field["value"]
                .split("https://docs.google.com/spreadsheets/d/")[1]
                .split("/")[0]
            )
            await self.activate(None, sheet_id)
            await message.add_reaction("🆕")


async def setup(bot):
    cog = SheetsAddon(bot)
    await bot.add_cog(cog)
    # await cog.activate_all(None)
