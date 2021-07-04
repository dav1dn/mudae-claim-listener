import asyncio
import os
import re
from typing import Dict, Union

import discord
import pendulum
from discord import Member, Message, TextChannel, colour
from discord.embeds import Embed
from expiringdict import ExpiringDict

client = discord.Client()

TOKEN = os.getenv("DISCORD_TOKEN")

# CONFIG
CATEGORY_ID = 854500814592409661
ANNOUNCEMENTS_CHANNEL_ID = 860401332086636554
MUDAE_USER_ID = 432610292342587392
OWN_USER_ID = 54422593528143872

MARRIAGE_REGEXES = list(
    map(
        re.compile,
        [
            r"\*\*(?P<name>.+)\*\* and \*\*(?P<waifu>.+)\*\* are now married!",
            r"\*\*(?P<name>.+)\*\* respects \*\*(?P<waifu>.+)\*\*",
        ],
    )
)

TIMER_REGEX = re.compile(r"\*\*(?P<hours>\d{1,2}h)?\s?(?P<minutes>\d{1,2})\*\*\smin\.")

Channels = {
    "Announcements": None,
}

CharacterEmbeds: Dict[str, Embed] = ExpiringDict(max_len=300, max_age_seconds=600)


@client.event
async def on_ready():
    Channels["Announcements"] = client.get_channel(860401332086636554)


@client.event
async def on_message(m: Message):
    channel: TextChannel = m.channel
    author: Member = m.author
    content = str(m.content)

    # ignore messages outside of category
    if channel.category_id != CATEGORY_ID or author == client.user:
        return

    if author.id == MUDAE_USER_ID:
        if len(m.embeds) > 0:
            # check if message has a character embed
            embed = m.embeds[0]
            character_name = str(embed.author.name)
            if not character_name:
                return

            CharacterEmbeds[character_name] = embed

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
