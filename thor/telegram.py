import re

from royalnet.typing import *
import asyncio
import logging
import royalnet.alchemist
import royalnet.baron
import os
import telethon
import telethon.tl.custom
import itsdangerous
from .database.base import Base

logging.basicConfig(level="DEBUG")
log = logging.getLogger(__name__)


async def main():
    log.info("Starting Alchemist...")
    alchemist: royalnet.alchemist.Alchemist = royalnet.alchemist.Alchemist(
        engine_args=[os.environ["SQLALCHEMY_DATABASE_URI"]],
        engine_kwargs={}
    )
    log.debug("Mapping database tables...")
    alchemist.add_metadata(Base.metadata)

    log.debug("Creating telethon TelegramClient...")
    client = telethon.client.TelegramClient("bot", int(os.environ["TELEGRAM_API_ID"]), os.environ["TELEGRAM_API_HASH"])

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

    campaigns = {}
    serializer = itsdangerous.url_safe.URLSafeSerializer(os.environ["SECRET_KEY"])

    @bot.on(telethon.events.NewMessage(func=lambda e: e.is_private))
    async def on_private_message(event: telethon.events.NewMessage.Event):
        msg: telethon.tl.custom.Message
        if msg := event.message:
            if msg.message.startswith("/start"):
                split = msg.message.split(" ", 1)
                if len(split) == 1:
                    await bot.send_message(
                        entity=msg.from_id,
                        message='👋 Ciao! Sono Thor, il bot-moderatore di Unimore Informatica.\n\n'
                                'Se vuoi entrare nel gruppo, <a href="http://lo.steffo.eu:30008/login">effettua la '
                                'verifica della tua identità facendo il login qui con il tuo account Unimore</a>.',
                        parse_mode="HTML",
                    )
                else:
                    payload = split[1].replace("__", "%").replace("_", ".").replace("%", "_")
                    command, data, signature = payload.split(".")
                    data = serializer.loads(f"{data}.{signature}")
                    breakpoint()

    while True:
        await bot.catch_up()
        # noinspection PyProtectedMember
        await bot._run_until_disconnected()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
