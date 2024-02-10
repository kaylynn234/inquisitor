import asyncio
import logging

import asyncpg
from aiohttp import ClientSession
import cattrs

from . import Config, Inquisitor


LOGGER = logging.getLogger("inquisitor")


async def main():
    logging.basicConfig(level=logging.INFO)

    try:
        config = Config.load()
    except Exception as error:
        return LOGGER.error("unable to load configuration", exc_info=error)

    database_config = cattrs.unstructure(config.database)

    async with (
        asyncpg.create_pool(**database_config) as pool,
        ClientSession() as session,
        Inquisitor(config, pool, session) as bot,
    ):
        await bot.load_extension(".ext.turn_tracking", package="inquisitor")
        await bot.start(config.bot.token)


if __name__ == "__main__":
    asyncio.run(main())
