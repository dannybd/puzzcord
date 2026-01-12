# puzzcord, a Discord bot for Mystery Hunt

* `bot.py` is a Discord bot which interfaces with Puzzleboss and provides solving tools to hunters
* `client.py` runs a local server you can `ncat` to and ask it for specific channel creation/announcement/management commands

## Usage
```
cp config.json-template config.json
# set up your configuration to the DB, asyncio_server ports, etc.
nano config.json
```

Then, run `./bot.py` to start the bot.
Talk to `client.py` using `./puzzcord`. You may need to adjust the port information in `./puzzcord` based on your particular `config.json`.

## Upgrading Requirements

We really only work on this once a year, and requirements change in ways we may want.
```
# Force requirements to upgrade from requirements.txt
cd ~/puzzcord
python3 -m pip install --upgrade -r requirements.txt
# Update requirements.txt to match
pipreqs . --force --mode compat
hg commit -m "Upgrading requirements.txt"
hg push
pc

# Update elsewhere
cd /production/puzzcord
sudo su
pip3 install -r requirements.txt
```
