import logging
import re
from collections import defaultdict
from typing import DefaultDict

from discord.ext import commands
from discord.ext.commands import Cog, Context

from ..bot import Inquisitor


LOGGER = logging.getLogger("inquisitor.turn_tracking")
COG_NAME = "Game Utilities"
NEIGHBOR_PATTERN = re.compile(r"#neighbour (\d+) (\d+)")


async def setup(bot: Inquisitor):
    await bot.add_cog(GameUtils(bot))


async def teardown(bot: Inquisitor):
    await bot.remove_cog(COG_NAME)


class GameUtils(Cog, name=COG_NAME):
    bot: Inquisitor

    def __init__(self, bot: Inquisitor) -> None:
        self.bot = bot

    @commands.command()
    async def neighbours(self, ctx: Context, threshold: int = 4):
        """List all provinces that fall below a certain neighbour count.

        Province data is read from a file, which must be attached to the message that this command is used with.

        This command takes one optional argument: the province threshold to search for. The threshold defaults to 4;
        meaning that, by default, only provinces with less than four neighbours will be reported.
        """

        if not ctx.message.attachments:
            return await ctx.send(
                "Province data must be attached as a file along with the command, but the command was used without "
                "any attachments"
            )

        try:
            content = (await ctx.message.attachments[0].read()).decode()
        except UnicodeDecodeError:
            raise RuntimeError("Unable to decode attachment as valid UTF-8 text; is the file corrupt?")

        adjacent: DefaultDict[int, set[int]] = defaultdict(set)

        for line in content.splitlines():
            match = NEIGHBOR_PATTERN.search(line)
            if not match:
                continue

            first, second = int(match[1]), int(match[2])
            adjacent[first].add(second)
            adjacent[second].add(first)

        below_threshold = [province for (province, bordering) in adjacent.items() if len(bordering) < threshold]
        formatted = ", ".join(f"`{province}`" for province in below_threshold)

        await ctx.send(f"{len(below_threshold)} provinces have less than {threshold} neighbours: {formatted}")
