from typing import Any

from aiohttp import ClientSession
from asyncpg import Pool
from discord import Forbidden, Intents
from discord.ext import commands
from discord.ext.commands import Bot, Context, CommandError, CommandInvokeError, CommandNotFound

from .config import Config


DEFAULT_INTENTS = Intents.default() | Intents(message_content=True)


class Inquisitor(Bot):
    config: Config
    pool: Pool
    session: ClientSession

    def __init__(self, config: Config, pool: Pool, session: ClientSession, **kwargs: Any) -> None:
        self.config = config
        self.pool = pool
        self.session = session

        super().__init__(
            command_prefix=commands.when_mentioned_or("in!"),
            intents=kwargs.pop("intents", DEFAULT_INTENTS),
            **kwargs,
        )

    async def on_command_error(self, ctx: Context, exception: Exception | CommandError) -> None:
        exception = exception.original if isinstance(exception, CommandInvokeError) else exception

        if isinstance(exception, (Forbidden, CommandNotFound)):
            return

        await ctx.send(f"{type(exception).__name__}: {exception}")
