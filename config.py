import json
from munch import munchify

with open("config.json", "r") as f:
    config = munchify(json.load(f))
