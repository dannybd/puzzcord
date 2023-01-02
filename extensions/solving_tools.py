""" Contains bot commands for things that are useful for solving puzzles """
import discord
from discord.ext import commands
import string
import aiohttp
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
        text = (
            "Run `!help tools` to see everything I support.\n\n"
            + "Popular links:\n"
            + "http://nutrimatic.org/ (see `!tools nu`)\n"
            + "https://tools.qhex.org/ \n"
            + "https://util.in/ \n"
            + "https://importanthuntpoll.org/scripts/ \n"
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
        embed.add_field(name="\u200B", value="\u200B", inline=True)
        embed.add_field(
            name="WUB Scripts",
            value="[Link](https://importanthuntpoll.org/scripts/)",
            inline=True,
        )
        embed.add_field(
            name="Puzzle Club Scripts",
            value="[Link](https://www.mit.edu/~puzzle/tools.html)",
            inline=True,
        )
        # spacer field to make it 2x2
        embed.add_field(name="\u200B", value="\u200B", inline=True)
        embed.add_field(
            name="Nutrimatic",
            value="[Link](http://nutrimatic.org/) (also see `!tools nu`)",
            inline=True,
        )
        await ctx.send("Run `!help tools` to see everything I support.", embed=embed)
        # TODO: Show something more useful here, like links to tools

    @commands.command(name="wb", aliases=["whiteboard"], hidden=True)
    async def wb_alias(self, ctx):
        """Creates a new whiteboard for you to use, each time you call it"""
        return await self.wb(ctx)

    @tools.command(name="wb", aliases=["whiteboard"])
    async def wb(self, ctx):
        """Creates a new whiteboard for you to use, each time you call it"""
        url = "https://cocreate.mehtank.com/api/roomNew"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.json()
                whiteboard_url = result["url"]
                await ctx.send(
                    (
                        "🎨 Generated a whiteboard for you: 🎨\n**{}**\n\n"
                        + "Direct everyone here! Re-running `!wb` will "
                        + "generate new whiteboards."
                    ).format(whiteboard_url),
                )

    @commands.command(name="stuck", aliases=["haveyoutried", "whatnow"], hidden=True)
    async def stuck_alias(self, ctx):
        """Suggests some tips from the Have You Tried? list"""
        return await self.stuck(ctx)

    @tools.command(name="stuck", aliases=["haveyoutried", "whatnow"])
    async def stuck(self, ctx):
        """Suggests some tips from the Have You Tried? list"""
        with open("haveyoutried.txt") as f:
            tips = [f"...{tip}" for tip in f.readlines()]
        random.shuffle(tips)

        content = "**Have You Tried...**\n{}".format("".join(tips[:6]))
        embed = discord.Embed(
            title="Have You Tried?",
            url="https://importanthuntpoll.org/wiki/index.php/Have_You_Tried",
        )
        await ctx.send(content=content, embed=embed)

    @commands.command(name="rot", aliases=["rotn"], hidden=True)
    async def rot_alias(self, ctx, *, msg: str):
        """Rotates a message through all rot N and displays the permutations
        Limited to the first 60 chars due to Discord message size limits.
        To rotate for a specific rotN, use something like `!rot13 foobar`"""
        return await self.rot(ctx, msg=msg)

    @tools.command(name="rot", aliases=["rotn"])
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
            await ctx.send(response)
        except:
            await ctx.send(
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
            await ctx.send(response)
        except:
            await ctx.send(
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
        # https://importanthuntpoll.org/scripts/cgi-bin/grep.cgi?dictionary=google-books-common-words.txt&word=%5Ef.ot.
        url = "https://importanthuntpoll.org/scripts/cgi-bin/grep.cgi"
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

    @commands.command(
        name="nutrimatic", aliases=["nu", "nut", "nutr", "nutri", "newt"], hidden=True
    )
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

    @tools.command(name="nutrimatic", aliases=["nu", "nut", "nutr", "nutri", "newt"])
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
        params = {"q": query}
        response = await urlhandler.get(url, params=params)
        soup = BeautifulSoup(response, "html.parser")
        result = (
            "```\n" + "\n".join([i.text for i in soup.find_all("span")][:10]) + "```"
        )
        await ctx.send(result)

    @commands.command(name="abc", aliases=["123", "abcd"], hidden=True)
    async def abc_alias(self, ctx, *args: str):
        """Converts letters A-Z to/from numbers 1-26
        Usage: !abc Hello world
        Usage: !abc 8 5 12 12 15
        """
        return await self.abc(ctx, *args)

    @tools.command(name="abc", aliases=["123", "abcd"])
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

        await ctx.send(" ".join([convert(i) for i in args]))

    @commands.command(name="morse", aliases=["morsecode"], hidden=True)
    async def morse_alias(self, ctx, *, text: str):
        """Convert to/from morse code (/ for word boundaries)
        Usage: !morse hello world
        Usage: !morse .... . .-.. .-.. ---/.-- --- .-. .-.. -..
        """
        return await self.morse(ctx, text=text)

    @tools.command(name="morse", aliases=["morsecode"])
    async def morse(self, ctx, *, text: str):
        """Convert to/from morse code (/ for word boundaries)
        Usage: !tools morse hello world
        Usage: !tools morse .... . .-.. .-.. ---/.-- --- .-. .-.. -..
        """
        if text[0] in ".-":
            text = text.replace("/", " / ").split()
            await ctx.send(
                "".join(
                    [
                        tables.morse2alpha[word] if word in tables.morse2alpha else word
                        for word in text
                    ]
                )
            )

        else:
            await ctx.send(
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
        await ctx.send(
            "```"
            + "\n".join([" ".join(x) for x in zip(braille_chars, alpha_chars)])
            + "```"
        )


def setup(bot):
    cog = SolvingTools(bot)
    bot.add_cog(cog)
