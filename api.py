#! /usr/bin/python3

import discord
import sys

client = discord.Client()

GUILD_ID = 790341470171168800
PUZZTECH_CHANNEL = 790387626531225611
PUZZLE_CATEGORY = 790343785804201984
SOLVED_PUZZLE_CATEGORY = 790348578018820096

@client.event
async def on_ready():
    log('LOG: Connected as {0.user} and ready!'.format(client))
    log('LOG: Command: {0}, Args: {1}'.format(command, args))
    if command == 'create':
        new_channel = await gen_create_channel(*args)
        print(new_channel.id)

    if command == 'message':
        message = await gen_message_channel(*args)
        print(message.jump_url)

    if command == 'archive':
        await gen_archive_channel(*args)

    await client.close()

@client.event
async def on_error(*args, **kwargs):
    log('ERROR:', args, kwargs)
    await client.close()

async def gen_create_channel(name, topic, *args):
    category = await gen_channelx(PUZZLE_CATEGORY)
    channel = await category.create_text_channel(
        name=name,
        position=1,
        reason='New puzzle: "{0}"'.format(name),
        topic=topic,
    )
    log('LOG: Created #{0.name} puzzle channel'.format(channel))
    return channel

async def gen_archive_channel(channel_id, *args):
    channel = await gen_channelx(channel_id)

    if channel.category_id == SOLVED_PUZZLE_CATEGORY:
        log('LOG: {0.name} ({0.id}) already solved'.format(channel))
        return

    solved_category = await gen_channelx(SOLVED_PUZZLE_CATEGORY)
    await channel.edit(
        category=solved_category,
        position=1,
        reason='Puzzle "{0.name} solved, archiving!'.format(channel),
    )
    log('LOG: Archived #{0.name} puzzle channel'.format(channel))

async def gen_message_channel(channel_id, message, *args):
    channel = await gen_channelx(channel_id)
    message = await channel.send(content=message)
    log('LOG: Message sent to {0.name}'.format(channel))
    return message

async def gen_channelx(channel_id):
    channel = await client.fetch_channel(channel_id)
    if channel == None:
        error_msg = 'Channel ID {0} missing!'.format(channel_id)
        raise Error(error_msg)
    return channel

def log(*a):
    print(*a, file=sys.stderr)

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 0:
        print('Usage: create | message | archive')
        sys.exit()
    command, *args = args
    if command not in ['create', 'message', 'archive']:
        print('Usage: create | message | archive')
        sys.exit()
    with open('.botsecret', 'r') as f:
        client.run(f.read())
