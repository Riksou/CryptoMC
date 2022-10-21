from __future__ import annotations

from typing import TYPE_CHECKING

from discord.app_commands import AppCommandError

if TYPE_CHECKING:
    from utils.checks import CooldownType


class InvalidAmount(AppCommandError):
    pass


class NotEnoughFunds(AppCommandError):
    pass


class CommandOnCooldown(AppCommandError):

    def __init__(self, cooldown_type: CooldownType, retry_after: float) -> None:
        self.cooldown_type = cooldown_type
        self.retry_after = retry_after
        super().__init__(f"You are on cooldown. Try again in {retry_after:.2f}s")
