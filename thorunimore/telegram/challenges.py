from __future__ import annotations

import abc

import royalnet.campaigns as rc
import telethon
import telethon.tl.custom as tc
from royalnet.typing import *
from telethon.hints import *

__all__ = (
    "Question",
    "Keyboard",
)


class ThorChallenge(rc.AsyncChallenge, metaclass=abc.ABCMeta):
    """
    Like a Royalnet challenge, but also define an action to be taken by the TelegramClient if this becomes the new
    challenge.
    """

    @abc.abstractmethod
    async def send(self, bot: telethon.TelegramClient, entity: Entity) -> ThorChallenge:
        raise NotImplementedError()


class Question(ThorChallenge):
    """Send a message to the chat, and wait for anything."""

    def __init__(self, message: str, *message_args, **message_kwargs):
        super().__init__()
        self.message: str = message
        self.message_args = message_args
        self.message_kwargs = message_kwargs

    async def send(self, bot: telethon.TelegramClient, entity: Entity) -> Question:
        await bot.send_message(
            entity=entity,
            message=self.message,
            parse_mode="HTML",
            *self.message_args,
            **self.message_kwargs)
        return self

    async def filter(self, data: Any) -> bool:
        return True


class UnrestrictedKeyboard(Question):
    """Send a message and a custom keyboard to the chat, and wait for anything."""

    def __init__(self, message: str, choices: List[List[str]], *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.choices: List[List[str]] = choices

    def flat_choices(self) -> List[str]:
        """
        :return: The flattened choices list.
        """
        li = []
        for row in self.choices:
            for choice in row:
                li.append(choice)
        return li

    def buttons(self) -> List[List[ButtonLike]]:
        """
        :return: The list of choices, converted to telethon button objects.
        """
        new_rows = []
        for row in self.choices:
            new_row = []
            for choice in row:
                new_row.append(telethon.Button.text(choice))
            new_rows.append(new_row)
        return new_rows

    async def send(self, bot: telethon.TelegramClient, entity: Entity) -> UnrestrictedKeyboard:
        markup = bot.build_reply_markup(self.buttons())
        await bot.send_message(
            entity=entity,
            message=self.message,
            buttons=markup,
            parse_mode="HTML",
            *self.message_args,
            **self.message_kwargs)
        return self


class Keyboard(UnrestrictedKeyboard):
    """Send a message and a custom keyboard to the chat, and only allow one of the possible keyboard responses."""

    async def filter(self, data: tc.Message) -> bool:
        return data.message and data.message in self.flat_choices()
