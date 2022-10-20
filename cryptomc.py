from __future__ import annotations

import json
import os
from typing import Optional, TYPE_CHECKING

import discord
from discord.ext import commands

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

        self.remove_command("help")

        self.config = config

        self.color = 0xf7ac1c

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

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")

        await self.load_extension("jishaku")

        await self.sync_guild()

    async def sync_guild(self) -> None:
        guild = discord.Object(id=self.config["guild_id"])
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


if __name__ == "__main__":
    bot = CryptoMC()
    bot.run(config["bot_token"])
