import datetime
from enum import Enum

import discord
from discord import app_commands

from utils.errors import CommandOnCooldown


class CooldownType(Enum):
    USER = "user"


def cooldown(cooldown_type: CooldownType, per: int):
    async def predicate(interaction: discord.Interaction) -> bool:
        cooldown_id = None
        if cooldown_type == CooldownType.USER:
            cooldown_id = interaction.user.id

        fmt = f"{cooldown_type.value}:{cooldown_id}:{interaction.command.name}"
        result = await interaction.client.redis.hget("cryptomc_cooldowns", fmt)
        if result:
            retry_after = datetime.datetime.fromtimestamp(float(result)) - datetime.datetime.utcnow()
            raise CommandOnCooldown(cooldown_type, retry_after.total_seconds())

        cooldown_end = datetime.datetime.utcnow() + datetime.timedelta(seconds=per)
        await interaction.client.redis.hset("cryptomc_cooldowns", fmt, str(cooldown_end.timestamp()))
        # Requires KeyDB.
        await interaction.client.redis.execute_command("EXPIREMEMBER", *["cryptomc_cooldowns", fmt, per])

        return False if result else True

    return app_commands.check(predicate)
