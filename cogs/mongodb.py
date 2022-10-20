from typing import Dict, Any

import motor.motor_asyncio
import ujson
from discord.ext import commands

from cryptomc import CryptoMC


class MongoDB(commands.Cog):
    """The Cog to interact with the MongoDB database."""

    DEFAULT_USER_DATA = {
        "_id": 0,
        "bank": 0,
        "roulette_won": 0,
        "roulette_lost": 0,
        "slots_won": 0,
        "slots_lost": 0,
        "coinflip_won": 0,
        "coinflip_lost": 0
    }

    def __init__(self, client: CryptoMC):
        self.client = client
        self.db = motor.motor_asyncio.AsyncIOMotorClient(self.client.config["mongodb_uri"])["cryptomc"]

    @staticmethod
    def _set_default_dict(current_dict, default_dict) -> Dict[str, Any]:
        for default_key, default_value in default_dict.items():
            if default_key not in current_dict.keys():
                current_dict[default_key] = ujson.loads(ujson.dumps(default_value))

            if isinstance(default_value, dict):
                for default_key_2, default_value_2 in default_value.items():
                    if default_key_2 not in current_dict[default_key].keys():
                        current_dict[default_key][default_key_2] = ujson.loads(ujson.dumps(default_value_2))

        return current_dict

    """ User collection. """

    async def fetch_user_data(self, user_id: int) -> Dict[str, int]:
        user = await self.db["user"].find_one({"_id": str(user_id)})
        if user is not None:
            user = self._set_default_dict(user, self.DEFAULT_USER_DATA)
        else:
            user = ujson.loads(ujson.dumps(self.DEFAULT_USER_DATA))

        user["_id"] = int(user_id)

        return user

    async def update_user_data_document(self, user_id: int, query: Dict[str, Any]) -> None:
        await self.db["user"].update_one({"_id": str(user_id)}, query, upsert=True)


async def setup(client):
    await client.add_cog(MongoDB(client))
