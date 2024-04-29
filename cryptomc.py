from __future__ import annotations

import importlib
import json
import os
import random as random
from typing import Optional, TYPE_CHECKING

from redis import asyncio as aioredis
import discord
from discord.ext import commands

import utils.blackjack as blackjack
import utils.checks as checks
import utils.errors as errors
import utils.menus as menus

if TYPE_CHECKING:
    from cogs.mongodb import MongoDB

os.environ["JISHAKU_HIDE"] = "true"

with open("config.json", "r") as fic:
    config = dict(json.load(fic))


class CryptoMC(commands.Bot):
    """The Bot for the CryptoMC Discord bot."""

    def __init__(self):
        super().__init__(
            command_prefix=";;",
            intents=discord.Intents.all(),
            chunk_guilds_at_startup=True,
            case_insensitive=True,
            owner_id=212844004889329664
        )

        random._inst = random.SystemRandom()

        self.remove_command("help")

        self.config = config
        self.color = 0xf7ac1c

        self.redis = None

    @property
    def mongo(self) -> Optional[MongoDB]:
        return self.get_cog("MongoDB")

    """ Response utils. """

    async def embed(self, interaction: discord.Interaction, title: str, description: str, **kwargs) -> None:
        await interaction.response.send_message(
            embed=discord.Embed(
                title=title,
                description=description,
                color=self.color,
                timestamp=discord.utils.utcnow()
            ).set_footer(text=f"{interaction.user}", icon_url=interaction.user.display_avatar),
            **kwargs
        )

    """ Ready actions. """

    async def ready_actions(self) -> None:
        await self.wait_until_ready()

        print(f"Ready: {self.user} (ID: {self.user.id}).")

    """ Setup actions. """

    async def setup_hook(self) -> None:
        self.loop.create_task(self.ready_actions())

        self.redis = await aioredis.from_url(self.config["redis_con"], encoding="utf-8", decode_responses=True)

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")

        await self.load_extension("jishaku")

        await self.sync_guild()

    """ Helper functions. """

    async def sync_guild(self) -> None:
        guild = discord.Object(id=self.config["guild_id"])
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def reload_modules(self) -> None:
        importlib.reload(blackjack)
        importlib.reload(checks)
        importlib.reload(errors)
        importlib.reload(menus)

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.reload_extension(f"cogs.{filename[:-3]}")


if __name__ == "__main__":
    bot = CryptoMC()
    bot.run(config["bot_token"])
