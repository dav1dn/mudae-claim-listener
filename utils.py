import re

import discord


def strip_emojis(str):
    """
        Strips the id from Discord's Emoji repr

        <:kakera:3827472838237843748374827> -> <:kakera:>
    """
    return re.sub(r"\d+", "", str)


def get_emoji_by_name(client, name):
    return discord.utils.find(lambda e: e.name == name, client.emojis) or name
