""" Contains bot commands for things that are useful for solving puzzles """
import discord
from discord.ext import commands
import string
import aiohttp
import random
import bot_extensions.util.urlhandler as urlhandler
import bot_extensions.util.tables as tables

from bs4 import BeautifulSoup


class SolvingTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def tools(self, ctx):
        """[category] Assorted puzzle-solving tools and utilities"""
        # TODO: Show something more useful here, like links to tools

    @tools.command(aliases=["rotn"])
    async def rot(self, ctx, *, msg: str):
        """Rotates a message through all rot N and displays the permutations
        Limited to the first 60 chars due to Discord message size limits.
        To rotate for a specific rotN, use something like `!tools rot13 foobar`"""
        return await self._rot(ctx, msg)

    @commands.command(name="rot", aliases=["rotn"], hidden=True)
    async def do_rot(self, ctx, *, msg: str):
        """Rotates a message through all rot N and displays the permutations
        Limited to the first 60 chars due to Discord message size limits.
        To rotate for a specific rotN, use something like `!rot13 foobar`"""
        return await self._rot(ctx, msg)

    async def _rot(self, ctx, msg):
        response = (
            "```\n"
            + "ROT  -N   N   MESSAGE\n"
        )
        upper = string.ascii_uppercase * 2
        i = 0
        for rot in self._all_rotn(msg):
            response += " {0}  {1:3d}  {2:2d}   {3}\n".format(
                upper[i + 25], i-26, i, rot[:60])
            i += 1
        response += "```"
        try:
            await ctx.send(response)
        except:
            await ctx.send("Sorry, response was too long for Discord. Try a shorter string")

    @tools.command(name="rot0", aliases=[f"rot{n}" for n in range(1, 26)], hidden=True)
    async def specific_rot(self, ctx, *, msg: str):
        """Rotates a message just by rotN"""
        return await self._specific_rot(ctx, msg)

    @commands.command(name="rot0", aliases=[f"rot{n}" for n in range(1, 26)], hidden=True)
    async def do_specific_rot(self, ctx, *, msg: str):
        """Rotates a message just by rotN"""
        return await self._specific_rot(ctx, msg)

    async def _specific_rot(self, ctx, msg):
        i = int(ctx.invoked_with[3:])
        all_rotn = self._all_rotn(msg)
        response = (
            "```\n"
            + "ROT  -N   N   MESSAGE\n"
        )
        upper = string.ascii_uppercase * 2
        response += " {0}  {1:3d}  {2:2d}   {3}\n".format(
            upper[i + 25], i-26, i, all_rotn[i])
        response += "```"
        try:
            await ctx.send(response)
        except:
            await ctx.send("Sorry, response was too long for Discord. Try a shorter string")

    def _all_rotn(self, msg):
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
        return [''.join(x) for x in zip(*chars)]

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

    @commands.command(name="nutrimatic", aliases=["nut"], hidden=True)
    async def nutrimatic_alias(self, ctx, *, query: str):
        return await self.nutrimatic(ctx, query=query)

    @tools.command(name="nutrimatic", aliases=["nut"])
    async def nutrimatic(self, ctx, *, query: str):
        """Queries nutrimatic.org"""
        url = "https://nutrimatic.org/?q={}".format(query)
        response = await urlhandler.get(url)
        soup = BeautifulSoup(response, 'html.parser')
        result = "```" + \
            "\n".join([i.text for i in soup.find_all('span')][:10]) + "```"
        await ctx.send(result)

    @commands.command(name="abc", aliases=["123"], hidden=True)
    async def abc_alias(self, ctx, *args):
        return await self.abc(ctx, *args)

    @tools.command(name="abc", aliases=["123"])
    async def abc(self, ctx, *args):
        """Converts letters A-Z to/from numbers 1-26"""
        def convert(x: str):
            if (x.isalpha()):
                return ",".join([str(ord(char.lower()) - ord('a') + 1) for char in x])
            else:
                return chr(int(x) + ord('a') - 1)
        await ctx.send(" ".join([convert(i) for i in args]))

    @commands.command(name="morse", hidden=True)
    async def morse_alias(self, ctx, *args):
        return await self.morse(ctx, *args)

    @tools.command(name="morse")
    async def morse(self, ctx, *args):
        """ Convert to/from morse code (/ for word boundaries) """
        if args[0][0] in [".", "-"]:
            await ctx.send("".join([tables.morse2alpha[arg] for arg in args]))

        else:
            await ctx.send("/".join([tables.encode_with_table(tables.alpha2morse, arg, sep=" ") for arg in args]))

    @commands.command(name="braille", hidden=True)
    async def braille_alias(self, ctx, *args):
        return await self.braille(ctx, *args)
    @tools.command(name="braille")
    async def braille(self, ctx, *args):
        """ Print the braille alphabet """
        braille_chars = "'⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵"
        alpha_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        await ctx.send("```" + "\n".join([" ".join(x) for x in zip(braille_chars, alpha_chars)])
                       + "```")


def setup(bot):
    cog = SolvingTools(bot)
    bot.add_cog(cog)
