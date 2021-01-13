# puzzcord, a Discord bot for Mystery Hunt

* `bot.py` is a Discord bot which interfaces with Puzzleboss and provides solving tools to hunters
* `client.py` runs a local server you can `ncat` to and ask it for specific channel creation/announcement/management commands

## Usage
```
cp config.ini-template config.ini
# set up your configuration to the DB, asyncio_server ports, etc.
nano config.ini
```

Then, run `./bot.py` to start the bot.
Talk to `client.py` using `./puzzcord`. You may need to adjust the port information in `./puzzcord` based on your particular `config.ini`.
