import asyncio
import logging
from typing import TypedDict, Union, cast

import discord
from discord import colour
from discord.client import Client
from discord.embeds import Embed, EmptyEmbed
from discord.message import Message

from state import (
    ALMOST_DONE_ROLLING,
    BELONGS_TO_FOOTER_REGEX,
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
        if footer_text and (match := BELONGS_TO_FOOTER_REGEX.search(footer_text)):
            belongs_to = match.group("owner")
            kakera_react = True

            try:
                reaction, _user = await client.wait_for(
                    "reaction_add",
                    timeout=10.0,
                    check=lambda reaction, user: user == msg.author
                    and "kakera" in str(reaction.emoji)
                    and reaction.message.id == msg.id,
                )
                kakera_react = get_emoji_by_name(client, reaction.emoji.name)
                logger.info("Rolled a Kakera react [%s]", str(kakera_react))
            except:
                pass

            if match := KEY_REGEX.search(description):
                matches_iter = KEY_REGEX.finditer(description)
                for match in matches_iter:
                    key_type = match.group("key_type")
                    num_keys = int(match.group("num_keys"))
                    logger.info(
                        "Received key for [%s]: [%s], [%s]!",
                        character_name,
                        key_type,
                        num_keys,
                        extra={"description": description},
                    )
                    emoji = get_emoji_by_name(client, key_type)
                    if num_keys >= 5:
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
                        rolled_key_embed.description = f"{str(emoji)} ({num_keys})"
                        await Channels["Announcements"].send(embed=rolled_key_embed)

        roll: RecentRoll = {
            "name": character_name,
            "kakera_value": int(ka_value),
            "message_url": msg.jump_url,
            "is_kakera_react": kakera_react,
            "belongs_to": belongs_to,
        }

        RecentRolls[msg.id] = roll

        if footer_text and "2 ROLLS LEFT" in footer_text:
            ALMOST_DONE_ROLLING = True

        if ALMOST_DONE_ROLLING:
            ROLLS_LEFT = ROLLS_LEFT - 1

        if ROLLS_LEFT <= 0:
            await done_rolling()


async def done_rolling():
    global ALMOST_DONE_ROLLING
    global ROLLS_LEFT

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
            f"{'[[**%s**](%s)' % (roll['name'], roll['message_url']) if roll['kakera_value'] > average_kakera_value else '[**%s**' % roll['name']} \t {roll['kakera_value']} <:kakera:879969751231791194> \t ]"
            for roll in claimable_rolls
        ]
    )
    kakera_rolls_text = "\n".join(
        [
            f"[**{roll['name']}**]({roll['message_url']})\t<{roll['is_kakera_react']}> ({roll['belongs_to']})"
            for roll in kakera_rolls
        ]
    )

    claimables_embed = discord.Embed(description=claimable_rolls_text)

    kakera_rolls_embed = discord.Embed(description=kakera_rolls_text)

    await Channels["Rolls"].send(content=f"**Nice rolls!**\n", embed=claimables_embed)
    if len(kakera_rolls) > 0:
        await Channels["Rolls"].send(embed=kakera_rolls_embed)

    ALMOST_DONE_ROLLING = False
    ROLLS_LEFT = 3
    RecentRolls.clear()

async def do_timer(minutes: int, msg: Message):
    logger.info("Starting timer for [%s] for [%s] minutes.", msg.author.display_name, minutes)
    await msg.add_reaction('👍')
    await asyncio.sleep(minutes * 60)
    await msg.reply("Your timer's up!")
