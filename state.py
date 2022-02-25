from discord import TextChannel
from expiringdict import ExpiringDict
from discord.embeds import Embed, EmptyEmbed

import re
from typing import Dict, TypedDict, Union

# CONFIG

CATEGORY_ID = 854500814592409661
ANNOUNCEMENTS_CHANNEL_ID = 860401332086636554
ROLLS_CHANNEL_ID = 853839598906900494
MUDAE_USER_ID = 432610292342587392
OWN_USER_ID = 54422593528143872

DEFAULT_KAKERA_REACT = "<:KakeraUnknown:905536936536571935>"

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
KAKERA_IN_DESCRIPTION_REGEX = re.compile(r"\*\*(?P<add>\+)?(?P<value>\d{2,5})\*\*")
BELONGS_TO_FOOTER_REGEX = re.compile(r"Belongs to (?P<owner>.*)")
KEY_REGEX = re.compile(
    r"(?P<key_type>(gold|silver|bronze|chaos)key):\d+>\s\(\*{2}?(?P<num_keys>\d{1,2})\*{2}?\)"
)

Channels: Dict[str, Union[TextChannel, None]] = {
    "Announcements": None,
    "Rolls": None,
}

# state
CharacterEmbeds: Dict[str, Embed] = ExpiringDict(max_len=300, max_age_seconds=600)
RecentRolls: Dict[int, "handlers.RecentRoll"] = ExpiringDict(
    max_len=30, max_age_seconds=120
)  # dict of message_id to Roll
ALMOST_DONE_ROLLING = False
ROLLS_LEFT = 3
# end state
