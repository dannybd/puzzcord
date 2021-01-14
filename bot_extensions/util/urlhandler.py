import aiohttp
import asyncio


async def get(url: str, params=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return await response.text()
