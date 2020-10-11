import asyncio
import logging
import os

import coloredlogs
import royalnet.alchemist
import royalnet.campaigns
import telethon
import telethon.tl.custom
import sys
import traceback
from royalnet.typing import *

from .dialog import Dialog
from ..database import Telegram
from ..database.base import Base

log = logging.getLogger(__name__)

log.info("Creating Alchemist...")
alchemist: royalnet.alchemist.Alchemist = royalnet.alchemist.Alchemist(
    engine_args=[os.environ["SQLALCHEMY_DATABASE_URI"]],
    engine_kwargs={}
)
log.debug("Mapping database tables...")
alchemist.add_metadata(Base.metadata)

log.debug("Creating telethon TelegramClient...")
client = telethon.client.TelegramClient("bot", int(os.environ["TELEGRAM_API_ID"]), os.environ["TELEGRAM_API_HASH"])


async def main():
    logging.root.setLevel(os.environ["LOG_LEVEL"])
    stream_handler = logging.StreamHandler()
    stream_handler.formatter = coloredlogs.ColoredFormatter(os.environ["LOG_FORMAT"].replace("\\t", "\t"), style="{")
    logging.root.addHandler(stream_handler)
    log.debug("Logging setup successfully!")

    log.debug("Starting telethon TelegramClient...")
    # noinspection PyProtectedMember
    bot = await client._start(
        phone=None,
        password=None,
        bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        force_sms=False,
        code_callback=None,
        first_name='Thor Bot',
        last_name='',
        max_attempts=3)

    me = await bot.get_me()
    log.debug(f"Logged in as: {me.first_name} <{me.id}>")

    menus: Dict[int, Dialog] = {}

    @bot.on(telethon.events.ChatAction())
    async def on_chat_action(event: telethon.events.ChatAction.Event):
        if event.user_joined:
            users = await event.get_users()
            chat = await event.get_chat()
            assert len(users) == 1
            user = users[0]
            session = alchemist.Session()
            tg = session.query(Telegram).filter_by(id=user.id).one_or_none()
            if tg is None:
                await bot.kick_participant(entity=chat, user=user)
            else:
                await bot.send_message(
                    entity=chat,
                    parse_mode="HTML",
                    message=tg.st.whois()
                )

    @bot.on(telethon.events.NewMessage())
    async def on_message(event: telethon.events.NewMessage.Event):
        msg: telethon.tl.custom.Message = event.message
        log.debug(f"Received message: {msg}")
        if msg.chat_id not in menus:
            log.debug(f"Creating a new Menu for {msg.chat_id}")
            menus[msg.chat_id] = await Dialog.create(bot=bot, entity=msg.chat, session=alchemist.Session())
        menu = menus[msg.chat_id]
        try:
            await menu.next(msg)
        except StopAsyncIteration:
            del menus[msg.chat_id]
        except Exception as e:
            log.error("".join(traceback.format_exception(*sys.exc_info())))
            await bot.send_message(
                entity=msg.chat,
                message="☢️ Si è verificato un errore critico e la conversazione è stata annullata.\n"
                        "\n"
                        "L'errore è stato salvato nei log del server.")

    while True:
        log.info(f"Catching up...")
        await bot.catch_up()

        log.info(f"Running!")
        # noinspection PyProtectedMember
        await bot._run_until_disconnected()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
