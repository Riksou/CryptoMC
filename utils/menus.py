from typing import Union

import discord
from discord.ext.menus.views import ViewMenuPages


class InteractionViewMenu(ViewMenuPages):

    def __init__(self, source, **kwargs):
        super().__init__(source, **kwargs)
        self.interaction = None

    async def send_initial_message(self, interaction: discord.Interaction,
                                   channel: Union[discord.TextChannel, discord.VoiceChannel]):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        view = self.build_view()
        if view:
            if interaction.response.is_done():
                await interaction.followup.send(**kwargs, view=view)
            else:
                await interaction.response.send_message(**kwargs, view=view)
        else:
            if interaction.response.is_done():
                await interaction.followup.send(**kwargs)
            else:
                await interaction.response.send_message(**kwargs)
        return await interaction.original_response()

    async def start(self, interaction: discord.Interaction, *,
                    channel: Union[discord.TextChannel, discord.VoiceChannel] = None, wait: bool = False):
        self.interaction = interaction

        try:
            del self.buttons
        except AttributeError:
            pass

        self.bot = bot = interaction.client
        self._author_id = interaction.user.id
        channel = channel or interaction.channel
        is_guild = hasattr(channel, "guild")
        me = channel.guild.me if is_guild else bot.user
        permissions = channel.permissions_for(me)
        self._verify_permissions(interaction, channel, permissions)
        self._event.clear()
        msg = self.message
        if msg is None:
            self.message = msg = await self.send_initial_message(interaction, channel)

        self.__tasks = []

        if self.should_add_reactions():
            for task in self.__tasks:
                task.cancel()
            self.__tasks.clear()

            self._running = True
            self.__tasks.append(bot.loop.create_task(self._internal_loop()))

            if wait:
                await self._event.wait()
