import asyncio
import logging

import asyncpg
from aiohttp import ClientSession

from inquisitor import Config, Inquisitor


LOGGER = logging.getLogger("inquisitor")


async def main():
    logging.basicConfig(level=logging.INFO)

    try:
        config = Config.load()
    except Exception as error:
        return LOGGER.error("unable to load configuration", exc_info=error)

    async with (
        asyncpg.create_pool(**vars(config.database)) as pool,
        ClientSession() as session,
        Inquisitor(config, pool, session) as bot,
    ):
        await bot.load_extension("inquisitor.ext.turn_tracking")
        await bot.start(config.bot.token)


if __name__ == "__main__":
    asyncio.run(main())
