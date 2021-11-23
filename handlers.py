import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional, TypedDict, Union, cast

import discord
from discord import colour
from discord.client import Client
from discord.embeds import Embed, EmptyEmbed
from discord.message import Message

from state import (
    ALMOST_DONE_ROLLING,
    BELONGS_TO_FOOTER_REGEX,
    DEFAULT_KAKERA_REACT,
    KAKERA_IN_DESCRIPTION_REGEX,
    KEY_REGEX,
    ROLLS_LEFT,
    Channels,
    CharacterEmbeds,
    RecentRolls,
)
from utils import get_emoji_by_name, get_member_by_name

logger = logging.getLogger(__name__)


class RecentRoll(TypedDict):
    name: str
    kakera_value: int
    message_url: str
    is_kakera_react: Union[str, bool]
    belongs_to: Union[str, None]
    num_keys: Optional[int]
    key_type: Optional[str]
    should_decrement_counter: bool  # if the roll is on or after the '2 rolls remaining!' text and should decrement the counter


async def handle_roll(client: Client, msg: Message, character_name: str, embed: Embed):
    global ALMOST_DONE_ROLLING
    global ROLLS_LEFT
    description = embed.description
    CharacterEmbeds[character_name] = embed

    if isinstance(description, str) and (
        match := KAKERA_IN_DESCRIPTION_REGEX.search(description)
    ):

        ka_value = match.group("value")
        logger.info(
            "Rolled [%s] in message_id=[%s]",
            character_name,
            msg.id,
            extra={"ka": ka_value},
        )
        footer = embed.footer
        footer_text = None
        if footer.text != EmptyEmbed and footer.text:
            footer_text = cast(str, footer.text)

        kakera_react = False
        belongs_to = None

        roll: RecentRoll = {
            "name": character_name,
            "kakera_value": int(ka_value),
            "message_url": msg.jump_url,
            "is_kakera_react": kakera_react,
            "belongs_to": belongs_to,
            "num_keys": None,
            "key_type": None,
            "should_decrement_counter": False,
        }

        if footer_text and "2 ROLLS LEFT" in footer_text:
            ALMOST_DONE_ROLLING = True

        if ALMOST_DONE_ROLLING:
            roll["should_decrement_counter"] = True

        if footer_text and (match := BELONGS_TO_FOOTER_REGEX.search(footer_text)):
            belongs_to = match.group("owner")
            kakera_react = DEFAULT_KAKERA_REACT
            roll["belongs_to"] = belongs_to

            try:
                reaction, _user = await client.wait_for(
                    "reaction_add",
                    timeout=3.0,
                    check=lambda reaction, user: user == msg.author
                    and "kakera" in str(reaction.emoji)
                    and reaction.message.id == msg.id,
                )
                kakera_react = get_emoji_by_name(client, reaction.emoji.name)
                logger.info("Rolled a Kakera react [%s]", str(kakera_react))
                if "kakeraY" in reaction.emoji.name:
                    asyncio.create_task(msg.add_reaction('🍋'))
                elif "kakeraO" in reaction.emoji.name:
                    asyncio.create_task(msg.add_reaction('🟧'))
                elif "kakeraR" in reaction.emoji.name:
                    asyncio.create_task(msg.add_reaction('🔥'))
                elif "kakeraW" in reaction.emoji.name:
                    asyncio.create_task(msg.add_reaction('🌈'))
                elif "kakeraL" in reaction.emoji.name:
                    asyncio.create_task(msg.add_reaction('💎'))
            except:
                pass

            roll["is_kakera_react"] = kakera_react

            if match := KEY_REGEX.search(description):
                matches_iter = KEY_REGEX.finditer(description)
                for match in matches_iter:
                    key_type = match.group("key_type")
                    num_keys = int(match.group("num_keys"))
                    roll["num_keys"] = num_keys
                    roll["key_type"] = key_type
                    logger.info(
                        "Received key for [%s]: [%s], [%s]!",
                        character_name,
                        key_type,
                        num_keys,
                        extra={"description": description},
                    )
                    emoji = get_emoji_by_name(client, key_type)
                    if num_keys > 6:
                        rolled_key_embed = discord.Embed(
                            type="rich",
                            colour=colour.Colour.random(seed=belongs_to),
                            title=f"Rolled a key for **{character_name}**!",
                            url=msg.jump_url,
                        )
                        member = get_member_by_name(msg.guild, belongs_to)
                        rolled_key_embed.set_author(
                            name=belongs_to,
                            icon_url=member.avatar_url if member else EmptyEmbed,
                        )
                        rolled_key_embed.set_thumbnail(url=embed.image.url)
                        rolled_key_embed.description = f"{str(emoji)} ({num_keys})\n<:kakera:879969751231791194> (+{ka_value})"
                        await Channels["Announcements"].send(embed=rolled_key_embed)

        RecentRolls[msg.id] = roll

        if roll["should_decrement_counter"]:
            ROLLS_LEFT = ROLLS_LEFT - 1

        if ROLLS_LEFT <= 0:
            await done_rolling(client)


async def done_rolling(client: Client):
    global ALMOST_DONE_ROLLING
    global ROLLS_LEFT

    ALMOST_DONE_ROLLING = False
    ROLLS_LEFT = 3

    rolls = RecentRolls.values()
    claimable_rolls = [roll for roll in rolls if not roll["is_kakera_react"]]
    kakera_rolls = [roll for roll in rolls if roll["is_kakera_react"]]

    average_kakera_value = sum(
        [roll["kakera_value"] for roll in claimable_rolls]
    ) / len(claimable_rolls)

    logger.info(
        "Finishing rolling. Rolled [%s] characters, of which [%s] were Kakera reacts.",
        len(rolls),
        len(kakera_rolls),
        extra={"rolls": rolls},
    )

    claimable_rolls = sorted(
        claimable_rolls,
        key=lambda roll: roll["kakera_value"],
        reverse=True,
    )

    claimable_rolls_text = "\n".join(
        [
            (
                "[**%s**](%s)" % (roll["name"], roll["message_url"])
                if roll["kakera_value"] > average_kakera_value or i < 6
                else "**%s**" % roll["name"]
            )
            + f" {roll['kakera_value']} <:kakera:879969751231791194> \t "
            for i, roll in enumerate(claimable_rolls)
        ]
    )

    possible_key_text: Callable[[RecentRoll], str] = (
        lambda roll: f"<{get_emoji_by_name(client, roll['key_type'])} : {roll['num_keys']}>"
        if roll["key_type"]
        else ""
    )
    kakera_rolls_text = "\n".join(
        [
            f"[**{roll['name']}**]({roll['message_url']})\t<{roll['is_kakera_react']}> {possible_key_text(roll)} ({roll['belongs_to']})"
            for roll in kakera_rolls
        ]
    )

    claimables_embed = discord.Embed(description=claimable_rolls_text)

    kakera_rolls_embed = discord.Embed(description=kakera_rolls_text)

    await Channels["Rolls"].send(content=f"**Nice rolls!**\n", embed=claimables_embed)
    if len(kakera_rolls) > 0:
        await Channels["Rolls"].send(embed=kakera_rolls_embed)

    RecentRolls.clear()


async def do_timer(minutes: int, msg: Message):
    try:
        seconds_to_wait = (
            (datetime.now() + timedelta(minutes=minutes)).replace(second=0, microsecond=0) - datetime.now()
        ).total_seconds()

        if seconds_to_wait < 0:
            raise ValueError("inappropriate time sent")

        logger.info(
            "Starting timer for [%s] for [%s] minutes, adjusted to [%s]s",
            msg.author.display_name,
            minutes,
            seconds_to_wait,
        )

        await msg.add_reaction("👍")
        await asyncio.sleep(seconds_to_wait)
        await msg.reply("Your timer's up!")
    except:
        logger.exception(
            "Error setting timer for [%s] for [%s] minutes.",
            msg.author.display_name,
            minutes,
        )
        await msg.add_reaction("❌")
