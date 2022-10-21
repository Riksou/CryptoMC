import functools
import os
import random
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import List, Tuple

import discord
from PIL import Image

ABS_PATH = Path(os.getcwd())

SUITS = ["clubs", "diamonds", "hearts", "spades"]
VALUES = {11: "jack", 12: "queen", 13: "king", 14: "ace"}


class Result(Enum):
    WON = 1
    LOST = 2
    TIE = 3
    CONTINUE = 4


class Action(Enum):
    HIT = 1
    STAY = 2


class Card:

    def __init__(self, suit: str, value: int):
        self.suit = suit
        self.value = value

        self.down = False
        self.symbol = self.name[0].upper() if self.name != "10" else "10"

    @property
    def name(self) -> str:
        if self.value <= 10:
            return str(self.value)
        else:
            return VALUES[self.value]

    @property
    def image(self):
        return f"{self.symbol}{self.suit[0].upper()}.png" if not self.down else "red_back.png"

    def flip(self):
        self.down = not self.down
        return self


class Player:

    def __init__(self, dealer: bool = False):
        self.dealer = dealer

        self.hand: List[Card] = []
        self.score = 0

        self.standing = False

    def calculate_hand(self) -> None:
        non_aces = [c for c in self.hand if c.symbol != "A"]
        aces = [c for c in self.hand if c.symbol == "A"]

        total = 0

        for card in non_aces:
            if card.down:
                continue

            if card.symbol in "JQK":
                total += 10
            else:
                total += card.value

        for card in aces:
            if card.down:
                continue

            if total <= 10:
                total += 11
            else:
                total += 1

        self.score = total

    def add_card(self, card: Card) -> None:
        self.hand.append(card)
        self.calculate_hand()


class PlayBlackjackView(discord.ui.View):

    def __init__(self, game):
        super().__init__()
        self.game = game

    @discord.ui.button(label="Tirer", emoji="➕", style=discord.ButtonStyle.gray)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.game.interaction.user.id:
            return await interaction.response.send_message("Ce boutton ne vous cible pas.", ephemeral=True)

        await self.game.process_turn(interaction, Action.HIT)

    @discord.ui.button(label="Rester", emoji="❌", style=discord.ButtonStyle.gray)
    async def stay(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.game.interaction.user.id:
            return await interaction.response.send_message("Ce boutton ne vous cible pas.", ephemeral=True)

        await self.game.process_turn(interaction, Action.STAY)


class BlackjackReplay(discord.ui.View):

    def __init__(self, author_id: int, amount: int):
        super().__init__(timeout=60.0)
        self.author_id = author_id
        self.amount = amount

    @discord.ui.button(label="Rejouer", emoji="🔁", style=discord.ButtonStyle.blurple)
    async def replay(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("Ce boutton ne vous cible pas.", ephemeral=True)

        slots_command = interaction.client.tree.get_command("blackjack")
        cog = interaction.client.get_cog("Games")
        await slots_command.callback(cog, interaction, self.amount)


class BlackjackGame:

    def __init__(self, interaction: discord.Interaction, bet_amount: int):
        self.interaction = interaction
        self.bet_amount = bet_amount

        self.players: List[Player] = []
        self.deck: List[Card] = []

    @staticmethod
    def _hand_to_images(hand: List[Card]) -> List[Image.Image]:
        return [Image.open(os.path.join(ABS_PATH, "assets/cards/", card.image)) for card in hand]

    @staticmethod
    def _center(hands: List[List[Image.Image]]) -> Image.Image:
        bg = Image.open(os.path.join(ABS_PATH, "assets/", "table.png"))
        bg_center_x = bg.size[0] // 2
        bg_center_y = bg.size[1] // 2

        img_w = hands[0][0].size[0]
        img_h = hands[0][0].size[1]

        start_y = bg_center_y - (((len(hands) * img_h) + ((len(hands) - 1) * 15)) // 2)
        hands.reverse()
        for hand in hands:
            start_x = bg_center_x - (((len(hand) * img_w) + ((len(hand) - 1) * 10)) // 2)
            for card in hand:
                bg.alpha_composite(card, (start_x, start_y))
                start_x += img_w + 10
            start_y += img_h + 15
        return bg

    def _get_output(self) -> BytesIO:
        bg = self._center([self._hand_to_images(player.hand) for player in self.players])
        output_buffer = BytesIO()
        bg.save(output_buffer, "png")
        output_buffer.seek(0)
        return output_buffer

    async def _out_table(self, interaction: discord.Interaction, title: str, description: str = "",
                         view: discord.ui.View = None) -> None:
        get_output_func = functools.partial(self._get_output)
        output_buffer = await self.interaction.client.loop.run_in_executor(None, get_output_func)

        player = self.players[0]
        dealer = self.players[1]

        blackjack_embed = discord.Embed(
            title=title,
            description=f"Votre main: **{player.score}**.\n"
                        f"Main du dealer: **{dealer.score}**.\n\n" + description,
            color=self.interaction.client.color,
            timestamp=discord.utils.utcnow()
        )
        blackjack_embed.set_footer(text=f"{self.interaction.user}", icon_url=self.interaction.user.display_avatar)
        blackjack_embed.set_image(url=f"attachment://blackjack_endmc.png")

        if view:
            await interaction.response.send_message(
                embed=blackjack_embed, file=discord.File(fp=output_buffer, filename="blackjack_endmc.png"), view=view
            )
        else:
            await interaction.response.send_message(
                embed=blackjack_embed,
                file=discord.File(fp=output_buffer, filename="blackjack_endmc.png"),
                view=BlackjackReplay(self.interaction.user.id, self.bet_amount)
            )

    async def _process_result(self, interaction: discord.Interaction, result: Tuple[str, Result]) -> None:
        if result[1] == Result.WON:
            await self.interaction.client.mongo.update_user_data_document(
                self.interaction.user.id, {"$inc": {"bank": self.bet_amount * 2, "blackjack_won": 1}}
            )
            desc = f"Vous gagnez **{self.bet_amount * 2}** {self.interaction.client.config['coin']}."
        elif result[1] == Result.LOST:
            await self.interaction.client.mongo.update_user_data_document(
                self.interaction.user.id, {"$inc": {"blackjack_lost": 1}}
            )
            desc = f"Vous perdez **{self.bet_amount}** {self.interaction.client.config['coin']}."
        else:
            await self.interaction.client.mongo.update_user_data_document(
                self.interaction.user.id, {"$inc": {"bank": self.bet_amount}}
            )
            desc = "Vous ne perdez pas votre argent."

        await self._out_table(interaction, result[0], description=desc)

    async def process_turn(self, interaction: discord.Interaction, action: Action = None):
        player = self.players[0]
        dealer = self.players[1]

        if action == Action.STAY:
            dealer.hand[1].flip()
            dealer.calculate_hand()

            while dealer.score < 17:
                dealer.add_card(self.deck.pop())

            result = None
            if dealer.score == 21:
                result = ("Blackjack du croupier", Result.LOST)
            elif dealer.score > 21:
                result = ("Le croupier brûle", Result.WON)
            elif dealer.score == player.score:
                result = ("Égalité", Result.TIE)
            elif dealer.score > player.score:
                result = ("Vous perdez", Result.LOST)
            elif dealer.score < player.score:
                result = ("Vous gagnez", Result.WON)

            return await self._process_result(interaction, result)
        else:
            if action == Action.HIT:
                player.add_card(self.deck.pop())

        if player.score == 21:
            result = ("Blackjack !", Result.WON)
        elif player.score > 21:
            result = ("Vous brûlez", Result.LOST)
        else:
            result = ("", Result.CONTINUE)

        if result[1] != Result.CONTINUE:
            dealer.hand[1].flip()
            return await self._process_result(interaction, result)

        await self._out_table(
            interaction,
            "À vous de jouer",
            view=PlayBlackjackView(self),
        )

    async def start(self):
        # Removing the amount bet.
        await self.interaction.client.mongo.update_user_data_document(
            self.interaction.user.id, {"$inc": {"bank": -self.bet_amount}}
        )

        # Creating our players.
        player = Player()
        dealer = Player(dealer=True)

        self.players.append(player)
        self.players.append(dealer)

        # Generating the deck.
        self.deck = [Card(suit, value) for value in range(2, 15) for suit in SUITS]
        random.shuffle(self.deck)

        player.add_card(self.deck.pop())
        player.add_card(self.deck.pop())
        dealer.add_card(self.deck.pop())
        dealer.add_card(self.deck.pop().flip())

        await self.process_turn(self.interaction)
