""" Get an overview of the entire hunt status """
import aiohttp
from config import config
import discord
from discord.ext import commands, tasks
import discord_info
import json
import logging
from common import plural, xyzloc_mention
import datetime
import typing


class SheetsAddon(commands.Cog):
    cookies = {}

    def __init__(self, bot):
        self.bot = bot
        self.rotate_1psidts.start()
        self.cookies = self.get_cookies()

    def cog_unload(self):
        self.rotate_1psidts.cancel()

    def get_cookies(self):
        cookies = config.sheets_addon.cookies
        try:
            cookies["__Secure-1PSIDTS"] = json.loads(".1PSIDTS")
        except:
            pass
        return cookies

    @tasks.loop(seconds=60.0, reconnect=True)
    async def rotate_1psidts(self):
        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            url = "https://accounts.google.com/RotateCookies"
            headers = config.sheets_addon.refresh_headers
            data = '[283,"1575614563079730632"]'
            async with session.post(url, headers=headers, data=data) as response:
                if response.status == 401:
                    logging.error("SheetsAddon: Auth is lost! Requires manual fix.")
                response.raise_for_status()
                new_1psidts = response.cookies.get("__Secure-1PSIDTS")
                if not new_1psidts:
                    logging.info("SheetsAddon: No new __Secure-1PSIDTS found")
                    return
                if self.cookies["__Secure-1PSIDTS"] == new_1psidts:
                    return
                logging.info("SheetsAddon: Updated __Secure-1PSIDTS!")
                self.cookies["__Secure-1PSIDTS"] = new_1psidts
                json.dumps(new_1psidts)
                logging.info("SheetsAddon: Saved __Secure-1PSIDTS!")




    # @commands.Cog.listener("on_message")
    # async def fix_hunt_emails(self, message):
    #     if message.author.id != 790401743669690428:
    #         return
    #     if "Unsubscribe: https://" not in message.content:
    #         return
    #     fixed = re.sub(r"Unsubscribe: https://\S+", "", x).strip()
    #     await message.channel.send(fixed)
    #     await message.delete()


async def setup(bot):
    cog = SheetsAddon(bot)
    await bot.add_cog(cog)
    await cog.rotate_1psidts()
