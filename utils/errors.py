from discord.app_commands import AppCommandError


class InvalidAmount(AppCommandError):
    pass


class NotEnoughFunds(AppCommandError):
    pass
