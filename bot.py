import os
import re
from typing import Dict, Union

import discord
from discord import Member, Message, TextChannel, colour
from discord.abc import GuildChannel
from discord.embeds import Embed
from discord.enums import Enum
from discord.guild import Guild
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

    # ignore messages outside of category
    if channel.category_id != CATEGORY_ID or author == client.user:
        return

    # messages from Mudae
    if author.id not in [OWN_USER_ID, MUDAE_USER_ID]:
        return

    if len(m.embeds) > 0:
        # check if character embed
        embed = m.embeds[0]
        character_name = str(embed.author.name)
        if not character_name:
            return

        CharacterEmbeds[character_name] = embed

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
                embed.set_author(name=user)
                embed.add_field(name="\u200B", value=f"[Jump to Message]({m.jump_url})")

            await Channels["Announcements"].send(
                content=f"👉 👉 **{user}** claimed **{waifu}**!", embed=embed
            )


client.run(TOKEN)
