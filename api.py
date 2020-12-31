#! /usr/bin/python3

import configparser
import discord
import json
import pymysql
import sys

config = configparser.ConfigParser()
config.read('config.ini')

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

GUILD_ID = 790341470171168800
PUZZTECH_CHANNEL = 790387626531225611
PUZZLE_CATEGORY = 790343785804201984
SOLVED_PUZZLE_CATEGORY = 790348578018820096

@client.event
async def on_ready():
    log('LOG: Connected as {0.user} and ready!'.format(client))
    log('LOG: Command: {0}, Args: {1}'.format(command, args))
    try:
        await gen_run()
    except Exception as e:
        log('ERROR:', e)
    finally:
        connection.close()
        await client.close()

async def gen_run():
    if command == 'create':
        name, *topic = args
        topic = ' '.join(topic)
        channel = await gen_create_channel(name, topic)
        print(channel.id)
        return

    if command == 'create_json':
        name, *topic = args
        topic = ' '.join(topic)
        channel = await gen_create_channel(name, topic)
        invite = await channel.create_invite()
        print(json.dumps({
            'id': channel.id,
            'name': channel.name,
            'mention': channel.mention,
            'url': invite.url,
        }))
        return

    if command == 'message':
        channel_id, *content = args
        content = ' '.join(content)
        message = await gen_message_channel(channel_id, content)
        print(message.jump_url)
        return

    if command == 'archive':
        channel_id, *solution = args
        solution = ' '.join(solution)
        await gen_archive_channel(channel_id, solution)
        return

    if command == 'stats':
        guild = client.get_guild(GUILD_ID)
        print('Server has', len(guild.members), 'members, including bots')
        return

    raise Exception('command {0} not supported!'.format(command))

@client.event
async def on_error(*args, **kwargs):
    connection.close()
    await client.close()

async def gen_create_channel(name, topic):
    category = await gen_channelx(PUZZLE_CATEGORY)
    channel = await category.create_text_channel(
        name=name,
        position=1,
        reason='New puzzle: "{0}"'.format(name),
        topic=topic,
    )
    log('LOG: Created #{0.name} puzzle channel'.format(channel))
    return channel

async def gen_message_channel(channel_id, content):
    channel = await gen_channelx(channel_id)
    message = await channel.send(content=content)
    log('LOG: Message sent to {0.name}'.format(channel))
    return message

async def gen_archive_channel(channel_id, solution):
    channel = await gen_channelx(channel_id)
    if solution:
        await channel.send(
            '**Puzzle solved!** Answer: ||`{0}`||'.format(solution) +
            '\nChannel will now be archived.'
        )

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

async def gen_channelx(channel_id):
    channel = None
    if isinstance(channel_id, int) or channel_id.isnumeric():
        guild = client.get_guild(GUILD_ID)
        channel = await client.fetch_channel(int(channel_id))
    if channel == None:
        channel = discord.utils.get(client.get_all_channels(), name=channel_id)
    if channel == None:
        error_msg = 'Channel ID {0} missing!'.format(channel_id)
        raise Exception(error_msg)
    return channel

def get_puzzle_from_db(puzzle_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
               name,
               round,
               puzzle_uri,
               drive_uri,
               slack_channel_id AS channel_id
            FROM puzzle_view
            WHERE name = %s
            LIMIT 1
            """,
            (puzzle_name,)
        )
        return cursor.fetchone()

def get_db_connection():
    creds = config['puzzledb']
    return pymysql.connect(
        host=creds['host'],
        port=creds.getint('port'),
        user=creds['user'].lower(),
        password=creds['passwd'],
        db=creds['db'],
        cursorclass=pymysql.cursors.DictCursor,
    )

def log(*a):
    print(*a, file=sys.stderr)

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 0:
        print('Usage: create | message | archive')
        sys.exit()
    command, *args = args
    connection = get_db_connection()
    client.run(config['discord']['botsecret'])
