import discord

from hashlib import md5


def build_puzzle_embed(puzzle, guild):
    description = ""

    if "xyzloc" in puzzle and puzzle["xyzloc"]:
        description += "Being worked in: **{}**\n".format(
            xyzloc_mention(guild, puzzle["xyzloc"])
        )

    if "comments" in puzzle and puzzle["comments"]:
        description += "**Comments:** {comments}\n".format(**puzzle)

    name = discord.utils.escape_markdown(puzzle["name"])
    embed = discord.Embed(
        color=get_round_embed_color(puzzle["round_name"]),
        title=f"Puzzle: _`{name}`_",
        description=description,
    )

    status = puzzle["status"]
    if status == "Needs eyes":
        embed.add_field(
            name="Status",
            value="❗ {status} 👀".format(**puzzle),
            inline=False,
        )
    if status == "Critical":
        embed.add_field(
            name="Status",
            value="⚠️  {status} 🚨".format(**puzzle),
            inline=False,
        )
    if status == "Unnecessary":
        embed.add_field(
            name="Status",
            value="🤷 {status} 🤷".format(**puzzle),
            inline=False,
        )
    if status == "Solved":
        embed.add_field(
            name="Status",
            value="✅ {status}  ".format(**puzzle),
            inline=True,
        )
        embed.add_field(
            name="Answer",
            value="||`{answer}`||".format(**puzzle),
            inline=True,
        )
    if status == "WTF":
        embed.add_field(
            name="Status",
            value="☣️  {status} ☣️".format(**puzzle),
            inline=False,
        )

    def link_to(label, uri):
        return "[{}]({})".format(label, uri)

    embed.add_field(name="Puzzle URL", value=puzzle["puzzle_uri"], inline=False)
    embed.add_field(
        name="Google Doc",
        value=link_to("Spreadsheet 📃", puzzle["drive_uri"]),
        inline=True,
    )
    embed.add_field(name="Whiteboard", value="[run !wb]", inline=True)
    # spacer field to make it 2x2
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(
        name="Discord Channel", value="<#{channel_id}>".format(**puzzle), inline=True
    )
    embed.add_field(name="Round", value=puzzle["round_name"].title(), inline=True)
    # spacer field to make it 2x2
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    if "tags" in puzzle and puzzle["tags"]:
        embed.add_field(
            name="Tags",
            value=puzzle["tags"].replace(",", ", "),
            inline=False,
        )
    if "cursolvers" in puzzle and puzzle["cursolvers"]:
        embed.add_field(
            name="Current Solvers:",
            value=puzzle["cursolvers"].replace(",", ", "),
            inline=False,
        )
    return embed


def get_round_embed_color(round):
    hash = md5(round.encode("utf-8")).hexdigest()
    hue = int(hash, 16) / 16 ** len(hash)
    return discord.Color.from_hsv(hue, 0.655, 1)


def xyzloc_mention(guild, xyzloc):
    channel = discord.utils.get(guild.voice_channels, name=xyzloc)
    return channel.mention if channel else xyzloc


def plural(num, singular, plural=None):
    if num == 1:
        return "1 {}".format(singular)
    return "{} {}".format(num, plural or (singular + "s"))
