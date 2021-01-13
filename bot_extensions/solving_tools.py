""" Contains bot commands for things that are useful for solving puzzles """
import discord
from discord.ext import commands
import string
import aiohttp
import random

class SolvingTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def tools(self, ctx):
        """[category] Assorted puzzle-solving tools and utilities"""
        # TODO: Show something more useful here, like links to tools


    @tools.command(aliases=["rotn"])
    async def rot(self, ctx, *, msg: str):
        """Rotates a message through all rot N and displays the permutations"""
        return await self._rot(ctx, msg)


    @commands.command(name="rot", aliases=["rotn"], hidden=True)
    async def do_rot(self, ctx, *, msg: str):
        """Rotates a message through all rot N and displays the permutations"""
        return await self._rot(ctx, msg)


    async def _rot(self, ctx, msg):
        lower = string.ascii_lowercase * 2
        upper = string.ascii_uppercase * 2
        chars = []
        for c in msg:
            if c in lower:
                chars.append(lower[lower.index(c):][:26])
                continue
            if c in upper:
                chars.append(upper[upper.index(c):][:26])
                continue
            chars.append(c * 26)
        rotn = [''.join(x) for x in zip(*chars)]
        response = (
            "```\n"
            + "ROT  -N   N   MESSAGE\n"
        )
        i = 0
        for rot in rotn:
            response += " {0}  {1:3d}  {2:2d}   {3}\n".format(upper[i], i-26, i, rot)
            i += 1
        response += "```"
        try:
            await ctx.send(response)
        except:
            await ctx.send("Sorry, response was too long for Discord. Try a shorter string")


    @tools.command()
    async def roll(self, ctx, dice: str):
        """Rolls a dice in NdN format."""
        return await self._roll(ctx, dice)


    @commands.command(name="roll", hidden=True)
    async def do_roll(self, ctx, dice: str):
        """Rolls a dice in NdN format."""
        return await self._roll(ctx, dice)


    async def _roll(self, ctx, dice):
        try:
            rolls, limit = map(int, dice.split("d"))
        except Exception:
            await ctx.send("Format has to be in NdN!")
            return
        if rolls > 100:
            await ctx.send("Try 100 or fewer rolls.")
            return
        result = ", ".join(str(random.randint(1, limit)) for r in range(rolls))
        await ctx.send(result)


    # TODO: Fix this
    @tools.command(hidden=True)
    async def search(self, ctx, *, word: str):
        # https://wind-up-birds.org/scripts/cgi-bin/grep.cgi?dictionary=google-books-common-words.txt&word=%5Ef.ot.
        url = "https://wind-up-birds.org/scripts/cgi-bin/grep.cgi"
        params = {
            "dictionary": self.dictionary("english"),
            "word": word,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                text = await response.text()
                await ctx.send(text)


    def dictionary(self, corpus):
        corpus = corpus.lower()
        if corpus in ["ud", "urban"]:
            return None
        if corpus in ["wiki", "wp", "wikipedia"]:
            return "wikipedia-titles3.txt"
        if corpus in ["words", "gw", "english"]:
            return "google-books-common-words.txt"
        return None


def setup(bot):
    cog = SolvingTools(bot)
    bot.add_cog(cog)
