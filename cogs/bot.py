import datetime
import traceback

import discord
from discord import app_commands
from discord.ext import commands, tasks

import utils.errors as errors
from cryptomc import CryptoMC


class Bot(commands.Cog):
    """The Cog to handle anything related to the bot's internal stuff."""

    def __init__(self, client: CryptoMC):
        self.client = client
        self.client.tree.on_error = self.on_app_command_error

    async def cog_load(self) -> None:
        self.update_presence.start()

    async def cog_unload(self) -> None:
        self.update_presence.stop()

    @tasks.loop(minutes=5)
    async def update_presence(self) -> None:
        pipeline = [{"$match": {"bank": {"$exists": True}}}, {"$project": {"bank": 1}}, {"$sort": {"bank": -1}},
                    {"$limit": 1}]
        cursor = self.client.mongo.db["user"].aggregate(pipeline)
        leaderboard_list = await cursor.to_list(None)

        if len(leaderboard_list) == 0:
            return

        best_user_data = leaderboard_list[0]
        best_user = self.client.get_user(int(best_user_data["_id"]))
        if best_user is None:
            return

        await self.client.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name=f"{best_user} avec {best_user_data['bank']:,} $LLC"
            )
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        error = getattr(error, "original", error)

        if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
            return

        raise error

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        error = getattr(error, "original", error)

        if isinstance(error, (app_commands.CommandNotFound, discord.HTTPException, discord.NotFound)):
            return

        elif isinstance(error, (errors.CommandOnCooldown, app_commands.CommandOnCooldown)):
            retry = discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=error.retry_after), "R")
            await interaction.response.send_message(
                f"Vous êtes encore en cooldown pour cette commande, merci de réessayer {retry}.", ephemeral=True
            )

        elif isinstance(error, errors.InvalidAmount):
            await interaction.response.send_message("Votre mise ne peut pas être inférieure à 1.", ephemeral=True)

        elif isinstance(error, errors.NotEnoughFunds):
            await interaction.response.send_message(
                "Vous n'avez pas assez d'argent sur votre compte bancaire.", ephemeral=True
            )

        elif isinstance(error, app_commands.CheckFailure):
            return

        else:
            await interaction.response.send_message(
                "Nous sommes désolés mais une erreur inattendue s'est produite, le développeur du bot vient d'être "
                "notifié.", ephemeral=True
            )

            try:
                etype, exc, trace = error
            except TypeError:
                etype = type(error)
                exc = error
                trace = error.__traceback__

            formatted_error = "".join(traceback.format_exception(etype, exc, trace, 8))
            formatted_error = f"```\n{formatted_error[:1950]}\n```"

            owner = self.client.get_user(self.client.owner_id)
            await owner.send(formatted_error)


async def setup(client):
    await client.add_cog(Bot(client))
