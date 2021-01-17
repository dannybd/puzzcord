import discord

from hashlib import md5


def build_puzzle_embed(puzzle):

    description = ""

    if "xyzloc" in puzzle and puzzle["xyzloc"]:
        description += "Being worked in: **{xyzloc}**\n".format(**puzzle)

    if "comments" in puzzle and puzzle["comments"]:
        description += "**Comments:** {comments}\n".format(**puzzle)

    embed = discord.Embed(
        color=get_round_embed_color(puzzle["round"]),
        title="Puzzle: _`{name}`_".format(**puzzle),
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
    whiteboard_uri = (
        "https://cocreate.mehtank.com/api/slug?slug=wchyyom21-{name}".format(**puzzle)
    )
    embed.add_field(
        name="Whiteboard", value=link_to("Whiteboard 🎨", whiteboard_uri), inline=True
    )
    # spacer field to make it 2x2
    embed.add_field(name="\u200B", value="\u200B", inline=True)
    embed.add_field(
        name="Discord Channel", value="<#{channel_id}>".format(**puzzle), inline=True
    )
    embed.add_field(name="Round", value=puzzle["round"].title(), inline=True)
    # spacer field to make it 2x2
    embed.add_field(name="\u200B", value="\u200B", inline=True)
    return embed


def get_round_embed_color(round):
    hash = md5(round.encode("utf-8")).hexdigest()
    hue = int(hash, 16) / 16 ** len(hash)
    return discord.Color.from_hsv(hue, 0.655, 1)
