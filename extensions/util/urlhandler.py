import aiohttp
from urllib.parse import urlencode


async def get(url: str, params=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return await response.text()


def build(url: str, params=None):
    if params is None:
        return url
    return url + "?" + urlencode(params)
