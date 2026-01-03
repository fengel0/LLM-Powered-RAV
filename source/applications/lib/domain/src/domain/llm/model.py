from dataclasses import dataclass
from typing import Literal


ChatRoles = Literal["user", "assistant", "system"]


@dataclass
class TextChatMessage:
    role: ChatRoles
    content: str
