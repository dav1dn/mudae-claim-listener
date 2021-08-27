import asyncio
import logging
import os
import re
from typing import Dict, TypedDict, Union, cast

from discord import member
from utils import get_member_by_name

import discord
import pendulum
from discord import Member, Message, TextChannel, colour
from discord.embeds import Embed, EmptyEmbed
from expiringdict import ExpiringDict

from handlers import done_rolling, handle_roll
from state import (
    CATEGORY_ID,
    MARRIAGE_REGEXES,
    MUDAE_USER_ID,
    ROLLS_CHANNEL_ID,
    TIMER_REGEX,
    Channels,
    CharacterEmbeds,
)

logging.basicConfig(level=logging.INFO)
logging.getLogger().addHandler(logging.FileHandler("out.log"))

logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

TOKEN = os.getenv("DISCORD_TOKEN")


@client.event
async def on_ready():
    Channels["Announcements"] = client.get_channel(860401332086636554)
    Channels["Rolls"] = client.get_channel(ROLLS_CHANNEL_ID)


@client.event
async def on_message(msg: Message):
    global ALMOST_DONE_ROLLING
    global ROLLS_LEFT

    channel: TextChannel = msg.channel
    author: Member = msg.author
    content = str(msg.content)

    # ignore messages outside of category
    if channel.category_id != CATEGORY_ID or author == client.user:
        return

    if author.id in [MUDAE_USER_ID, 880010191830134795]:
        logger.info("Got message [%s] from author [%s]", msg.id, author.id)
        if len(msg.embeds) > 0 and msg.channel == Channels["Rolls"]:
            embed = msg.embeds[0]
            character_name = str(embed.author.name)
            await handle_roll(client, msg, character_name, embed)

    # check if message is a marriage
    for regex in MARRIAGE_REGEXES:
        if match := regex.search(msg.content):
            user = str(match.group("name"))
            waifu = str(match.group("waifu"))

            if not all([user, waifu]):
                return

            embed: Embed = discord.Embed(
                title=f"Claimed **{waifu}**!\n",
                colour=colour.Colour.random(seed=user),
                type="rich",
                url=msg.jump_url,
            )

            # try to get Member
            possible_member = get_member_by_name(msg.guild, user)
            embed.set_author(
                name=user,
                icon_url=possible_member.avatar_url if possible_member else EmptyEmbed,
            )
            cached_character: Union[Embed, None] = CharacterEmbeds.get(waifu)

            if cached_character:
                embed.description = re.sub(
                    r"<:kakera:\d+>",
                    " <:kakera:879969751231791194>",
                    str(cached_character.description).replace(
                        "React with any emoji to claim!", ""
                    ),
                )
                embed.set_thumbnail(url=cached_character.image.url)

            res = Channels["Announcements"].send(embed=embed)

    # check if hard-reset rolling
    if content.startswith("-done"):
        await done_rolling()

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
            line = re.sub(r"<:kakera:\d+>", " <:kakera:879969751231791194>", line)
            lines_to_send.append(line)

        if lines_to_send:
            await msg.channel.send(content="\n".join(lines_to_send))
            await mudae_reply.delete()


client.run(TOKEN)
