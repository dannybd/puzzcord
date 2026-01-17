"""Contains bot commands for things that are useful for solving puzzles"""

import discord
from discord.ext import commands
from db import SQL
import string
import random
import extensions.util.urlhandler as urlhandler
import extensions.util.tables as tables

from bs4 import BeautifulSoup


class SolvingTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=["tool"])
    async def tools(self, ctx):
        """[category] Assorted puzzle-solving tools and utilities"""
        if ctx.invoked_subcommand:
            return
        _text = (
            "Run `!help tools` to see everything I support.\n\n"
            + "Popular links:\n"
            + "http://nutrimatic.org/ (see `!tools nu`)\n"
            + "https://tools.qhex.org/ \n"
            + "https://util.in/ \n"
            + f"https://{self.bot.team_domain}/scripts/ \n"
            + "https://www.mit.edu/~puzzle/tools.html \n"
        )
        embed = discord.Embed(title="Popular links:", color=discord.Colour.greyple())
        embed.add_field(
            name="tools.qhex.org",
            value="[Link](https://tools.qhex.org/)",
            inline=True,
        )
        embed.add_field(
            name="util.in",
            value="[Link](https://util.in/)",
            inline=True,
        )
        # spacer field to make it 2x2
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(
            name="Team Scripts",
            value=f"[Link](https://{self.bot.team_domain}/scripts/)",
            inline=True,
        )
        embed.add_field(
            name="Puzzle Club Scripts",
            value="[Link](https://www.mit.edu/~puzzle/tools.html)",
            inline=True,
        )
        # spacer field to make it 2x2
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(
            name="Nutrimatic",
            value="[Link](http://nutrimatic.org/) (also see `!tools nu`)",
            inline=True,
        )
        embed.add_field(
            name="Qat word multi-matcher",
            value="[Link](https://www.quinapalus.com/qat.html) (also see `!tools qat`)",
            inline=True,
        )
        await ctx.reply("Run `!help tools` to see everything I support.", embed=embed)
        # TODO: Show something more useful here, like links to tools

    @commands.command(name="stuck", aliases=["haveyoutried"], hidden=True)
    async def stuck_alias(self, ctx):
        """Suggests some tips from the Have You Tried? list"""
        return await self.stuck(ctx)

    @tools.command(name="stuck", aliases=["haveyoutried"])
    async def stuck(self, ctx):
        """Suggests some tips from the Have You Tried? list"""
        with open("haveyoutried.txt") as f:
            tips = [f"...{tip}" for tip in f.readlines()]
        random.shuffle(tips)

        content = "**Have You Tried...**\n{}".format("".join(tips[:6]))
        embed = discord.Embed(
            title="Have You Tried?",
            url=f"https://{self.bot.team_domain}/wiki/index.php/Have_You_Tried",
        )
        await ctx.reply(content=content, embed=embed)

    @commands.command(name="julia", hidden=True)
    async def julia_alias(self, ctx):
        """Suggests the Julia Strategy to Puzzlesolving"""
        return await self.julia(ctx)

    @tools.command(name="julia", hidden=True)
    async def julia(self, ctx):
        """Suggests the Julia Strategy to Puzzlesolving"""
        await ctx.reply(
            "Have you tried reading the first letters of everything? "
            "Yes? Okay, try it again."
        )

    @commands.command(name="rot", hidden=True)
    async def rot_alias(self, ctx, *, msg: str):
        """Rotates a message through all rot N and displays the permutations
        Limited to the first 60 chars due to Discord message size limits.
        To rotate for a specific rotN, use something like `!rot13 foobar`"""
        return await self.rot(ctx, msg=msg)

    @tools.command(name="rot")
    async def rot(self, ctx, *, msg: str):
        """Rotates a message through all rot N and displays the permutations
        Limited to the first 60 chars due to Discord message size limits.
        To rotate for a specific rotN, use something like `!tools rot13 foobar`"""
        response = "```\n" + "ROT  -N   N   MESSAGE\n"
        upper = string.ascii_uppercase * 2
        i = 0
        for rot in self._all_rotn(msg):
            response += " {0}  {1:3d}  {2:2d}   {3}\n".format(
                upper[i + 25], i - 26, i, rot[:60]
            )
            i += 1
        response += "```"
        try:
            await ctx.reply(response)
        except Exception:
            await ctx.reply(
                "Sorry, response was too long for Discord. Try a shorter string"
            )

    @commands.command(
        name="rot0", aliases=[f"rot{n}" for n in range(1, 26)], hidden=True
    )
    async def rot_specific_alias(self, ctx, *, msg: str):
        """Rotates a message just by rotN"""
        return await self.rot_specific(ctx, msg=msg)

    @tools.command(name="rot0", aliases=[f"rot{n}" for n in range(1, 26)], hidden=True)
    async def rot_specific(self, ctx, *, msg: str):
        """Rotates a message just by rotN"""
        i = int(ctx.invoked_with[3:])
        all_rotn = self._all_rotn(msg)
        response = "```\n" + "ROT  -N   N   MESSAGE\n"
        upper = string.ascii_uppercase * 2
        response += " {0}  {1:3d}  {2:2d}   {3}\n".format(
            upper[i + 25], i - 26, i, all_rotn[i]
        )
        response += "```"
        try:
            await ctx.reply(response)
        except Exception:
            await ctx.reply(
                "Sorry, response was too long for Discord. Try a shorter string"
            )

    def _all_rotn(self, msg):
        lower = string.ascii_lowercase * 2
        upper = string.ascii_uppercase * 2
        chars = []
        for c in msg:
            if c in lower:
                chars.append(lower[lower.index(c) :][:26])
                continue
            if c in upper:
                chars.append(upper[upper.index(c) :][:26])
                continue
            chars.append(c * 26)
        return ["".join(x) for x in zip(*chars)]

    @commands.command(name="roll", hidden=True)
    async def roll_alias(self, ctx, dice: str):
        """Rolls a dice in NdN format."""
        return await self.roll(ctx, dice)

    @tools.command(name="roll")
    async def roll(self, ctx, dice: str):
        """Rolls a dice in NdN format."""
        try:
            rolls, limit = map(int, dice.split("d"))
        except Exception:
            await ctx.reply("Format has to be in NdN!")
            return
        if rolls > 100:
            await ctx.reply("Try 100 or fewer rolls.")
            return
        result = ", ".join(str(random.randint(1, limit)) for r in range(rolls))
        await ctx.reply(result)

    # TODO: Fix this

    @tools.command(hidden=True)
    async def search(self, ctx, *, word: str):
        # https://{self.bot.team_domain}/scripts/cgi-bin/grep.cgi?dictionary=google-books-common-words.txt&word=%5Ef.ot.
        url = f"https://{self.bot.team_domain}/scripts/cgi-bin/grep.cgi"
        params = {
            "dictionary": self.dictionary("english"),
            "word": word,
        }
        text = await urlhandler.get(url, params=params)
        await ctx.reply(text)

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
        """Queries nutrimatic.org
        Matches patterns against a dictionary of words and phrases mined from Wikipedia. Text is normalized to lowercase letters, numbers and spaces. More common results are returned first.

        See https://nutrimatic.org for syntax.

        Usage:
            !nutrimatic "C*aC*eC*iC*oC*uC*yC*"
                yields "facetiously"
            !nutrimatic 867-####
                yields "867-5309"
            !nutrimatic "_ ___ ___ _*burger"
                yields "i can has cheezburger"
        """
        return await self.nutrimatic(ctx, query=query)

    @tools.command(name="nutrimatic", aliases=["nut"])
    async def nutrimatic(self, ctx, *, query: str):
        """Queries nutrimatic.org
        Matches patterns against a dictionary of words and phrases mined from Wikipedia. Text is normalized to lowercase letters, numbers and spaces. More common results are returned first.

        See https://nutrimatic.org for syntax.


        Usage:
            !tools nutrimatic "C*aC*eC*iC*oC*uC*yC*"
                yields "facetiously"
            !tools nutrimatic 867-####
                yields "867-5309"
            !tools nutrimatic "_ ___ ___ _*burger"
                yields "i can has cheezburger"
        """
        url = "https://nutrimatic.org/"
        if "�" in query or "@" in query:
            solved_puzzle_uris = SQL.select_all(
                """
                  SELECT
                      puzzle_uri
                  FROM puzzle_view
                  WHERE
                      roundname = 'LandofNoName'
                      AND status = 'Solved'
                  """,
            )
            solved_slugs = [p["puzzle_uri"].split("/")[-1] for p in solved_puzzle_uris]
            letters = {
                "3842": "a",
                "9283": "b",
                "1736": "c",
                "6147": "d",
                "2074": "e",
                "4519": "f",
                "8063": "g",
                "1259": "h",
                "7642": "i",
                "3961": "j",
                "5823": "k",
                "9350": "l",
                "2871": "m",
                "6714": "n",
                "8402": "o",
                "4295": "p",
                "1906": "q",
                "3175": "r",
                "7480": "s",
                "6592": "t",
                "2843": "u",
                "9810": "v",
                "1037": "w",
                "5671": "x",
                "8904": "y",
                "2129": "z",
            }
            noname = (
                "["
                + "".join(letters[s] for s in letters if s not in solved_slugs)
                + "]"
            )
            query = query.replace("�", noname).replace("@", noname)
        params = {"q": query}
        response = await urlhandler.get(url, params=params)
        soup = BeautifulSoup(response, "html.parser")
        results = "\n".join([i.text for i in soup.find_all("span")][:10])
        if results:
            result = f"`!nut {query}` yields:\n```\n{results}```"
        else:
            params = {"q": query.lower()}
            response = await urlhandler.get(url, params=params)
            soup = BeautifulSoup(response, "html.parser")
            results = "\n".join([i.text for i in soup.find_all("span")][:10])
            result = (
                f"No results for `!nut {query}`, so assuming a case-error:\n"
                f"`!nut {query.lower()}` yields:\n```\n{results}```"
            )
        try:
            await ctx.reply(result)
        except Exception:
            await ctx.reply(
                "Sorry, response was too long for Discord. "
                + "Try a shorter string or go directly to the tool online here:\n"
                + urlhandler.build(url, params=params)
            )

    @commands.command(name="qat", hidden=True)
    async def qat_alias(self, ctx, *, query: str):
        """Queries Qat, a multi-pattern word searcher
        Qat lets you search for words matching a given pattern.

        See https://www.quinapalus.com/qat.html for syntax.
        """
        return await self.qat(ctx, query=query)

    @tools.command(name="qat")
    async def qat(self, ctx, *, query: str):
        """Queries Qat, a multi-pattern word searcher
        Qat lets you search for words matching a given pattern.

        See https://www.quinapalus.com/qat.html for syntax.
        """
        url = "https://www.quinapalus.com/cgi-bin/qat"
        params = {"pat": query.replace('"', "")}
        response = await urlhandler.get(url, params=params)
        soup = BeautifulSoup(response, "html.parser")
        form = soup.find("form", {"action": "qat"})
        result = (
            "".join(
                el.text for el in form.next_siblings if el.name not in ["i", "small"]
            )
            .strip()
            .replace("\xa0", "")
        )
        result = f"`!qat {query}` yields:\n```\n{result}\n```"
        try:
            await ctx.reply(result)
        except Exception:
            await ctx.reply(
                "Sorry, response was too long for Discord. "
                + "Try a shorter string or go directly to the tool online here:\n"
                + urlhandler.build(url, params=params)
            )

    @commands.command(name="abc", hidden=True)
    async def abc_alias(self, ctx, *args: str):
        """Converts letters A-Z to/from numbers 1-26
        Usage: !abc Hello world
        Usage: !abc 8 5 12 12 15
        """
        return await self.abc(ctx, *args)

    @tools.command(name="abc")
    async def abc(self, ctx, *args: str):
        """Converts letters A-Z to/from numbers 1-26
        Usage: !tools abc Hello world
        Usage: !tools abc 8 5 12 12 15
        """

        def convert(x: str):
            if x.isalpha():
                return ",".join([str(ord(char.lower()) - ord("a") + 1) for char in x])
            else:
                return chr(int(x) + ord("a") - 1)

        await ctx.reply(" ".join([convert(i) for i in args]))

    @commands.command(name="atbash", hidden=True)
    async def atbash_alias(self, ctx, *, text: str):
        """Atbash cipher: flips A-Z to Z-A
        Usage: !atbash Hello world
        """
        return await self.atbash(ctx, text)

    @tools.command(name="atbash")
    async def atbash(self, ctx, *, text: str):
        """Atbash cipher: flips A-Z to Z-A
        Usage: !tools atbash Hello world
        """
        lower = string.ascii_lowercase
        upper = string.ascii_uppercase
        lookup = dict(zip(upper + lower, upper[::-1] + lower[::-1]))
        await ctx.reply("".join(lookup.get(c, c) for c in text))

    @commands.command(name="morse", hidden=True)
    async def morse_alias(self, ctx, *, text: str):
        """Convert to/from morse code (/ for word boundaries)
        Usage: !morse hello world
        Usage: !morse .... . .-.. .-.. ---/.-- --- .-. .-.. -..
        """
        return await self.morse(ctx, text=text)

    @tools.command(name="morse")
    async def morse(self, ctx, *, text: str):
        """Convert to/from morse code (/ for word boundaries)
        Usage: !tools morse hello world
        Usage: !tools morse .... . .-.. .-.. ---/.-- --- .-. .-.. -..
        """
        if text[0] in ".-…—":
            text = (
                text.replace("/", " / ").replace("…", "...").replace("—", "--").split()
            )
            await ctx.reply(
                "".join(
                    [
                        tables.morse2alpha[word] if word in tables.morse2alpha else word
                        for word in text
                    ]
                )
            )

        else:
            await ctx.reply(
                "/".join(
                    [
                        tables.encode_with_table(tables.alpha2morse, word, sep=" ")
                        for word in text.split()
                    ]
                )
            )

    @commands.command(name="braille", hidden=True)
    async def braille_alias(self, ctx):
        """Print the braille alphabet"""
        return await self.braille(ctx)

    @tools.command(name="braille")
    async def braille(self, ctx):
        """Print the braille alphabet"""
        braille_chars = "'⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵"
        alpha_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        await ctx.reply(
            "```"
            + "\n".join([" ".join(x) for x in zip(braille_chars, alpha_chars)])
            + "```"
        )


async def setup(bot):
    cog = SolvingTools(bot)
    await bot.add_cog(cog)
