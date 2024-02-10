import logging
import re
from asyncio import TaskGroup
from enum import Enum

import attrs
import cattrs
from bs4 import BeautifulSoup, Tag
from discord import Role
from discord.abc import Messageable
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Context
from discord.ext.tasks import Loop
from yarl import URL


from ..bot import Inquisitor
from ..error import *


LOGGER = logging.getLogger("inquisitor.turn_tracking")
COG_NAME = "Turn-tracking"
SERVER_URL = URL("http://ulm.illwinter.com/dom6/server")
TURN_PATTERN = re.compile(r".*?, turn (\d+)")


async def setup(bot: Inquisitor):
    await bot.add_cog(TurnTracking(bot))


async def teardown(bot: Inquisitor):
    await bot.remove_cog(COG_NAME)


class TurnTracking(Cog, name=COG_NAME):
    bot: Inquisitor
    update_loop: Loop

    def __init__(self, bot: Inquisitor) -> None:
        self.bot = bot
        self.update_loop = tasks.loop(minutes=bot.config.bot.refresh_frequency)(_update_loop)

    async def cog_load(self) -> None:
        self.update_loop.start(self.bot)

    async def cog_unload(self) -> None:
        self.update_loop.stop()

    @commands.command()
    @commands.guild_only()
    async def track(self, ctx: Context, game_name: str, role: Role | None):
        """Start tracking a Dominions 6 game in this channel.

        This command takes two arguments; a game name, and an optional role to ping when it is time for a new turn.

        The "game name" argument must be specified, and is case-sensitive. Type exactly what appears in-game!

        The "role" argument is optional, and can be specified using a role name, a role ping, or a role ID. Role names
        are case sensitive, and must be enclosed in quotes if they are longer than one word.

        If the specified game is already being tracked, this command will overwrite any previous configuration.
        """

        try:
            turn = await _check_turn_status(self.bot, game_name, 0)
        except GameError as error:
            await ctx.send(f"Unable to track game: {error}")

        query = """
            INSERT INTO inquisitor.tracked_games
               (game_name,
                current_turn,
                guild_id,
                announcement_channel,
                announcement_role)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT DO UPDATE
            SET current_turn = $2, guild_id = $3, announcement_channel = $4, announcement_role = $5
        """

        assert ctx.guild is not None

        await self.bot.pool.execute(
            query,
            game_name,
            turn.number,
            ctx.guild.id,
            ctx.channel.id,
            role.id if role else None,
        )

        role_message = f'The "{role.name}" role will be mentioned when new turns can be played.' if role else ""

        await ctx.send(f"Now tracking `{game_name}` in this channel. {role_message}")

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    async def untrack(self, ctx: Context, game_name: str):
        """Stop tracking a Dominions 6 game.

        This command take a single argument: a game name to cease tracking for.
        The "game name" argument must be specified, and is case-sensitive.

        To prevent abuse, this command can only be used by members with the "Manage Roles" permission.
        """

        query = """
            DELETE FROM inquisitor.tracked_games
            WHERE game_name = $1
        """

        tag = await self.bot.pool.execute(query, game_name)

        # No roles were affected, which means the game name wasn't found.
        if tag == "DELETE 0":
            await ctx.send(f"No game named `{game_name}` found")
        else:
            await ctx.send(f"No longer tracking `{game_name}`")

    @commands.command()
    @commands.guild_only()
    async def show(self, ctx: Context):
        """Show all Dominions 6 games currently being tracked in this server.

        This command takes no arguments.
        """

        query = """
            SELECT game_name
            FROM inquisitor.tracked_games
            WHERE guild_id = $1
        """

        assert ctx.guild is not None

        records = await self.bot.pool.fetch(query, ctx.guild.id)
        names = [record["game_name"] for record in records]
        formatted_names = ", ".join(f"`{name}`" for name in names)

        if not names:
            await ctx.send("No games are being tracked in this server.")
        else:
            await ctx.send(f"Currently tracking **{len(names)}** games in this server: {formatted_names}")


@attrs.define()
class Game:
    """A tracked Dominions 6 game."""

    game_name: str
    current_turn: int
    guild_id: int
    announcement_channel: int
    announcement_role: int | None


# We use `True`/`False` as the enum values to easily construct variants from a comparison result
class TurnStatus(Enum):
    """The status of the current turn."""

    in_progress = False
    """This turn is still in progress; other players must play their turn."""

    finished = True
    """This turn has finished, and the game has advanced to the next turn."""


@attrs.define()
class Turn:
    """Basic information about a single Dominions 6 turn."""

    status: TurnStatus
    number: int


async def _check_turn_status(bot: Inquisitor, game_name: str, current_turn: int) -> Turn:
    url = SERVER_URL / f"{game_name}.html"

    async with bot.session.get(url) as response:
        if response.status == 404:
            raise GameNotFound(game_name)

        response.raise_for_status()
        page = BeautifulSoup(await response.text())

    turn_element = page.find(class_="blackbolddata")

    if not isinstance(turn_element, Tag):
        raise StatusParseError(game_name)

    match = TURN_PATTERN.match(turn_element.text)
    if match is None:
        raise StatusParseError(game_name)

    new_turn = int(match.group(1))
    status = TurnStatus(new_turn > current_turn)

    return Turn(status, new_turn)


# We wrap this in a try-except block to avoid cancelling all tasks in a group if a single task fails.
async def _update_task(bot: Inquisitor, game: Game):
    try:
        await _raw_update_task(bot, game)
    except Exception as error:
        LOGGER.exception("updating game status failed", exc_info=error)


async def _raw_update_task(bot: Inquisitor, game: Game):
    try:
        turn = await _check_turn_status(bot, game.game_name, game.current_turn)
    except Exception as error:
        return LOGGER.error("failed to check turn status for %s", game.game_name, exc_info=error)

    # There's nothing to do if the turn is still in progress
    if turn.status is TurnStatus.in_progress:
        return

    query = """
        UPDATE inquisitor.tracked_games
        WHERE game_name = $1
        SET current_turn = $2
    """

    await bot.pool.execute(query, game.game_name, turn.number)

    guild = bot.get_guild(game.guild_id)
    if not guild:
        return LOGGER.error("can't access guild %d; no announcement was made", game.guild_id)

    channel = guild.get_channel(game.announcement_channel)
    if not channel:
        return LOGGER.error(
            "can't access channel %d in guild %s; no announcement was made",
            game.announcement_channel,
            guild.name,
        )

    role = guild.get_role(game.announcement_role) if game.announcement_role else None
    role_mention = f"{role.mention}, " if role else ""
    message = f"`{game.game_name}` has progressed to turn {turn.number}. Players can now submit their turns."

    assert isinstance(channel, Messageable)

    await channel.send(f"{role_mention}{message}")


# This is wrapped in a `Loop` later, when we have the refresh frequency value available.
async def _update_loop(bot: Inquisitor):
    query = """
        SELECT game_name, current_turn, guild_id, announcement_channel, announcement_role
        FROM inquisitor.tracked_games
    """

    records = await bot.pool.fetch(query)
    tracked_games = cattrs.structure(records, list[Game])

    async with TaskGroup() as group:
        for game in tracked_games:
            group.create_task(_update_task(bot, game))
