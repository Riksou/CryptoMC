import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, menus

from cryptomc import CryptoMC
from utils.menus import InteractionViewMenu


class LeaderboardMenuSource(menus.ListPageSource):

    def __init__(self, data):
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page

        leaderboard_message = ""
        for place, member_data in enumerate(entries, start=offset):
            [member_data.setdefault(d, menu.bot.mongo.DEFAULT_USER_DATA[d]) for d in menu.bot.mongo.DEFAULT_USER_DATA]
            leaderboard_message += f"`{place + 1}.` <@{member_data['_id']}> • 🏦 **" \
                                   f"{member_data['bank']:,}** {menu.bot.config['coin']}\n"

        embed_top = discord.Embed(
            title=f"**Classement des utilisateurs**",
            description=leaderboard_message,
            color=menu.bot.color,
            timestamp=discord.utils.utcnow()
        )
        embed_top.set_footer(
            text=f"{menu.bot.user.name} • Page {(menu.current_page + 1)}/{self.get_max_pages()}",
            icon_url=menu.bot.user.display_avatar
        )

        return embed_top


class Profile(commands.Cog):
    """The Cog containing all the commands related to the users profile."""

    def __init__(self, client: CryptoMC):
        self.client = client

    @staticmethod
    def _get_game_ratio(win: int, loose: int) -> float:
        return win / (loose if loose > 0 else 1)

    @app_commands.command(name="profile")
    @app_commands.rename(user="utilisateur")
    @app_commands.describe(user="Utilisateur dont vous voulez afficher le profil")
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.User]):
        """Afficher votre profil ou celui d'un autre utilisateur."""
        if user is None:
            user = interaction.user

        user_data = await self.client.mongo.fetch_user_data(user.id)
        profile_embed = discord.Embed(
            title=f"**{user}**",
            description=f"🏦 **Banque**: {user_data['bank']:,} {self.client.config['coin']}\n"
                        f"💈 **Ratio roulette**: "
                        f"{self._get_game_ratio(user_data['roulette_won'], user_data['roulette_lost']):0.2f}\n"
                        f"🎰 **Ratio machine à Lulux Coins**: "
                        f"{self._get_game_ratio(user_data['slots_won'], user_data['slots_lost']):0.2f}\n"
                        f"🪙 **Ratio coinflip**: "
                        f"{self._get_game_ratio(user_data['coinflip_won'], user_data['coinflip_lost']):0.2f}\n",
            color=self.client.color,
            timestamp=discord.utils.utcnow()
        )
        profile_embed.set_thumbnail(url=user.display_avatar)
        profile_embed.set_footer(text=f"{user}", icon_url=user.display_avatar)

        await interaction.response.send_message(embed=profile_embed)

    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        """Afficher le classement des utilisateurs avec le plus de Lulux Coins."""
        pipeline = [{"$match": {"bank": {"$exists": True}}}, {"$project": {"bank": 1}}, {"$sort": {"bank": -1}}]
        cursor = self.client.mongo.db["user"].aggregate(pipeline)
        menu = InteractionViewMenu(
            source=LeaderboardMenuSource(await cursor.to_list(None)), clear_reactions_after=True, timeout=30.0
        )
        await menu.start(interaction, wait=True)

    @app_commands.command(name="pay")
    @app_commands.rename(target="utilisateur", amount="montant")
    @app_commands.describe(target="Utilisateur que vous souhaitez payer", amount="Montant du paiement")
    async def pay(self, interaction: discord.Interaction, target: discord.User, amount: int):
        """Payer un utilisateur."""
        if interaction.user.id == target.id:
            return await interaction.response.send_message("Vous ne pouvez pas vous payer vous-même.", ephemeral=True)

        if amount < 1:
            return await interaction.response.send_message(
                "Vous ne pouvez pas payer un montant inférieur à 1.", ephemeral=True
            )

        user_data = await self.client.mongo.fetch_user_data(interaction.user.id)
        if user_data["bank"] < amount:
            return await interaction.response.send_message(
                "Vous n'avez pas assez d'argent sur votre compte bancaire.", ephemeral=True
            )

        await self.client.mongo.update_user_data_document(interaction.user.id, {"$inc": {"bank": -amount}})
        await self.client.mongo.update_user_data_document(target.id, {"$inc": {"bank": amount}})

        await self.client.embed(
            interaction, "**💵 Paiement**",
            f"Vous venez de payer **{amount}** {self.client.config['coin']} à {target.mention}."
        )

    @app_commands.command(name="hourly")
    @app_commands.checks.cooldown(1, 60 * 60, key=lambda i: i.user.id)
    async def hourly(self, interaction: discord.Interaction):
        """Récupérer des Lulux Coins chaque heure."""
        earned = random.randint(100, 300)
        await self.client.mongo.update_user_data_document(interaction.user.id, {"$inc": {"bank": earned}})

        await self.client.embed(
            interaction, "**⏱ Récolte horaire**",
            f"Vous venez de gagner **{earned}** {self.client.config['coin']} grâce à votre récolte horaire."
        )

    @app_commands.command(name="daily")
    @app_commands.checks.cooldown(1, 60 * 60 * 24, key=lambda i: i.user.id)
    async def daily(self, interaction: discord.Interaction):
        """Récupérer des Lulux Coins chaque jour."""
        earned = random.randint(2000, 3000)
        await self.client.mongo.update_user_data_document(interaction.user.id, {"$inc": {"bank": earned}})

        await self.client.embed(
            interaction, "**⏰ Récolte quotidienne**",
            f"Vous venez de gagner **{earned}** {self.client.config['coin']} grâce à votre récolte quotidienne."
        )


async def setup(client):
    await client.add_cog(Profile(client))
