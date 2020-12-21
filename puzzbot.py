import discord

client = discord.Client()

GUILD_ID = 790341470171168800
PUZZTECH_CHANNEL = 790387626531225611
PUZZLE_CATEGORY = 790343785804201984
SOLVED_PUZZLE_CATEGORY = 790348578018820096

BOT_PREFIX = 'pb!'

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if not message.content.startswith(BOT_PREFIX):
        return
    command, *args = message.content.lstrip(BOT_PREFIX).split()
    src_channel = message.channel

    if src_channel.id == PUZZTECH_CHANNEL:
        if command == 'create':
            await gen_create_channel(src_channel, args)
            return
        if command == 'archive':
            await gen_archive_channel(src_channel, args)
            return

    if command == 'hello':
        await src_channel.send('Hi, {0.mention}! I\'m puzzbot.'.format(message.author))
        return

async def gen_create_channel(src_channel, args):
    if len(args) == 0:
        await src_channel.send('Unknown command, try `pb!create new_channel_name`')
        return
    name = ' '.join(args).lstrip('#')
    guild = src_channel.guild
    puzzle_category = guild.get_channel(PUZZLE_CATEGORY)
    existing = next((c for c in puzzle_category.channels if c.name == name), None)
    if existing:
        await src_channel.send(
            'Error: {0.mention} already exists in {1.name}!'.format(
                existing,
                existing.category,
            )
        )
        return
    solved_puzzle_category = guild.get_channel(SOLVED_PUZZLE_CATEGORY)
    existing = next((c for c in solved_puzzle_category.channels if c.name == name), None)
    if existing:
        await src_channel.send(
            'Error: {0.mention} already exists in {1.name}!'.format(
                existing,
                existing.category,
            )
        )
        return

    new_channel = await guild.create_text_channel(
        name=name,
        category=puzzle_category,
        position=0,
        reason='New puzzle!',
        topic='Working on {0}'.format(name),
    )
    print('LOG: Created #{0.name} puzzle channel'.format(new_channel))
    await src_channel.send('Created {0.mention}!'.format(new_channel))

async def gen_archive_channel(src_channel, args):
    if len(args) == 0:
        await src_channel.send('Unknown command, try `pb!archive #puzzle`')
        return
    mention = args[0]
    guild = src_channel.guild
    puzzle_category = guild.get_channel(PUZZLE_CATEGORY)
    channel = next((c for c in puzzle_category.channels if c.mention == mention), None)
    if not channel:
        await src_channel.send(
            'Error: {0} not found in {1.name}! Make sure you mention a channel name.'.format(
                mention,
                puzzle_category,
            )
        )
        return
    await channel.edit(
        category=guild.get_channel(SOLVED_PUZZLE_CATEGORY),
        position=0,
        reason='Puzzle solved, archiving!',
    )
    print('LOG: Archived #{0.name} puzzle channel'.format(channel))
    await src_channel.send(
        '{0.mention} is moved to {1.name}. Congrats!'.format(
            channel,
            channel.category,
        )
    )

with open('.botsecret', 'r') as f:
    client.run(f.read())
