import asyncio
import os
import re
import logging

from typing import Dict, List, Union, TypedDict

import discord
import pendulum
from discord import Member, Message, TextChannel, colour
from discord.embeds import Embed, EmptyEmbed
from expiringdict import ExpiringDict
from pprint import pprint

logging.basicConfig(level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())
logging.getLogger().addHandler(logging.FileHandler("out.log"))


logger = logging.getLogger(__name__)

client = discord.Client()

TOKEN = os.getenv("DISCORD_TOKEN")

# CONFIG
CATEGORY_ID = 854500814592409661
ANNOUNCEMENTS_CHANNEL_ID = 860401332086636554
ROLLS_CHANNEL_ID = 853839598906900494
# ROLLS_CHANNEL_ID = 858475878094864414
MUDAE_USER_ID = 432610292342587392
OWN_USER_ID = 54422593528143872

MARRIAGE_REGEXES = list(
    map(
        re.compile,
        [
            r"\*\*(?P<name>.+)\*\* and \*\*(?P<waifu>.+)\*\* are now married!",
            r"\*\*(?P<name>.+)\*\* respects \*\*(?P<waifu>.+)\*\*",
            r"\*\*(?P<waifu>.+)\*\* stepped on \*\*(?P<name>.+)\*\*",
        ],
    )
)

TIMER_REGEX = re.compile(r"\*\*(?P<hours>\d{1,2}h)?\s?(?P<minutes>\d{1,2})\*\*\smin\.")
KAKERA_IN_DESCRIPTION_REGEX = re.compile(r"\*\*\+?(?P<value>\d{2,4})\*\*")
BELONGS_TO_FOOTER_REGEX = re.compile(r"Belongs to (?P<owner>.*)")
KEY_REGEX = re.compile(
    r"(?P<key_type>(gold|silver|bronze|chaos)key):\d+>\s\((?P<num_keys>\d{1,2})\)"
)

Channels = {
    "Announcements": None,
    "Rolls": None,
}


def strip_emojis(str):
    return re.sub(r"\d+", "", str)


class RecentRoll(TypedDict):
    name: str
    kakera_value: int
    message_url: str
    is_kakera_react: Union[str, bool]
    belongs_to: Union[str, None]


CharacterEmbeds: Dict[str, Embed] = ExpiringDict(max_len=300, max_age_seconds=600)
RecentRolls: Dict[int, RecentRoll] = ExpiringDict(
    max_len=30, max_age_seconds=120
)  # message_id to roll

ALMOST_DONE_ROLLING = False
ROLLS_LEFT = 3


@client.event
async def on_ready():
    Channels["Announcements"] = client.get_channel(860401332086636554)
    Channels["Rolls"] = client.get_channel(ROLLS_CHANNEL_ID)


def get_emoji_by_name(name):
    return discord.utils.find(lambda e: e.name == name, client.emojis) or name


@client.event
async def on_message(m: Message):
    global ALMOST_DONE_ROLLING
    global ROLLS_LEFT

    channel: TextChannel = m.channel
    author: Member = m.author
    content = str(m.content)

    # ignore messages outside of category
    if channel.category_id != CATEGORY_ID or author == client.user:
        return

    if author.id in [MUDAE_USER_ID, 880010191830134795]:
        logger.info("Got message [%s] from author [%s]", m.id, author.id)
        if len(m.embeds) > 0:
            logger.info("Found embed")
            # check if message has a character embed
            embed = m.embeds[0]
            character_name = str(embed.author.name)
            description = embed.description

            if not character_name:
                return

            CharacterEmbeds[character_name] = embed

            # rolls channel
            if channel == Channels["Rolls"]:
                if isinstance(description, str) and (
                    match := KAKERA_IN_DESCRIPTION_REGEX.search(description)
                ):

                    ka_value = match.group("value")
                    logger.info(
                        "Rolled [%s] in message_id=[%s]",
                        character_name,
                        m.id,
                        extra={"ka": ka_value},
                    )
                    footer = embed.footer

                    kakera_react = False
                    belongs_to = None
                    if (
                        footer != EmptyEmbed
                        and footer.text
                        and (match := BELONGS_TO_FOOTER_REGEX.search(footer.text))
                    ):
                        belongs_to = match.group("owner")
                        kakera_react = True

                        if match := KEY_REGEX.search(description):
                            key_type = match.group("key_type")
                            num_keys = int(match.group("num_keys"))
                            logger.info(
                                "Received key for [%s]: [%s], [%s]!",
                                character_name,
                                key_type,
                                num_keys,
                                extra={"description": description},
                            )
                            emoji = get_emoji_by_name(key_type)
                            if num_keys >= 5:
                                await Channels["Announcements"].send(
                                    content=f"**{belongs_to}** rolled a {str(emoji)} ({num_keys}) for {character_name}!"
                                )

                        def check(reaction, user):
                            return user == author and "kakera" in str(reaction.emoji)

                        try:
                            reaction, user = await client.wait_for(
                                "reaction_add", timeout=2.0, check=check
                            )
                            kakera_react = get_emoji_by_name(reaction.emoji.name)
                            logger.info("Rolled a Kakera react [%s]", str(kakera_react))
                        except:
                            pass

                    roll: RecentRoll = {
                        "name": character_name,
                        "kakera_value": int(ka_value),
                        "message_url": m.jump_url,
                        "is_kakera_react": kakera_react,
                        "belongs_to": belongs_to,
                    }

                    RecentRolls[m.id] = roll

                    if footer != EmptyEmbed and footer.text and "2 ROLLS LEFT" in footer.text:
                        ALMOST_DONE_ROLLING = True

                    if ALMOST_DONE_ROLLING:
                        ROLLS_LEFT = ROLLS_LEFT - 1

                    if ROLLS_LEFT <= 0:
                        rolls = RecentRolls.values()
                        claimable_rolls = [
                            roll for roll in rolls if roll["is_kakera_react"] is False
                        ]
                        kakera_rolls = [
                            roll for roll in rolls if roll["is_kakera_react"]
                        ]

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

                        claimables_embed = discord.Embed(
                            description=claimable_rolls_text
                        )

                        kakera_rolls_embed = discord.Embed(
                            description=kakera_rolls_text
                        )

                        await Channels["Rolls"].send(
                            content=f"**Nice rolls!**\n", embed=claimables_embed
                        )
                        if len(kakera_rolls) > 0:
                            await Channels["Rolls"].send(embed=kakera_rolls_embed)

                        ALMOST_DONE_ROLLING = False
                        ROLLS_LEFT = 3
                        RecentRolls.clear()

        # check if message is a marriage
        for regex in MARRIAGE_REGEXES:
            if match := regex.search(m.content):
                user = str(match.group("name"))
                waifu = str(match.group("waifu"))

                if not all([user, waifu]):
                    return

                embed: Embed = discord.Embed(
                    title=f"{waifu}",
                    colour=colour.Colour.red(),
                    type="rich",
                    url=m.jump_url,
                )
                embed.set_author(name=user)

                cached_character: Union[Embed, None] = CharacterEmbeds.get(waifu)

                if cached_character:
                    embed.description = re.sub(
                        r"<:\S+:\d+>",
                        "",
                        re.sub(
                            r"<:kakera:\d+>",
                            " Ka",
                            str(cached_character.description).replace(
                                "React with any emoji to claim!", ""
                            ),
                        ),
                    )
                    embed.set_image(url=cached_character.image.url)
                    embed.add_field(
                        name="\u200B", value=f"[Jump to Message]({m.jump_url})"
                    )

                await Channels["Announcements"].send(
                    content=f"👉 👉 **{user}** claimed **{waifu}**!", embed=embed
                )

    if content.startswith("-clear"):
        ALMOST_DONE_ROLLING = False
        ROLLS_LEFT = 3
        RecentRolls.clear()
        return

    # check if asking for timers
    if content.startswith("$tu f"):
        try:
            mudae_reply = await client.wait_for(
                "message", check=lambda x: x.author.id == MUDAE_USER_ID, timeout=5.0
            )
        except asyncio.TimeoutError:
            return

        if not isinstance(mudae_reply, Message):
            return

        lines_to_send = []

        message_lines = mudae_reply.content.split("\n")
        for line in message_lines:

            def repl(match):
                full_match = match.group(0).replace("\n", "")
                hour = (
                    match.group("hours").replace("h", "") if match.group("hours") else 0
                )
                minutes = match.group("minutes")

                return f"{full_match} [{pendulum.now().add(hours=int(hour), minutes=int(minutes)).in_tz('America/Los_Angeles').format('ddd M/D h:mmA zz')}]"

            line = re.sub(TIMER_REGEX, repl, line)
            line = re.sub(r"<:kakera:\d+>", " Ka", line)
            lines_to_send.append(line)

        if lines_to_send:
            await m.channel.send(content="\n".join(lines_to_send))
            await mudae_reply.delete()


client.run(TOKEN)
