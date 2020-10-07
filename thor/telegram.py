from royalnet.typing import *
import asyncio
import logging
import royalnet.alchemist
import royalnet.baron
import os
import telethon
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

    @bot.on(telethon.events.NewMessage(func=lambda e: e.is_private))
    def on_private_message(event: telethon.events.NewMessage.Event):
        print(event)

    while True:
        await bot.catch_up()
        # noinspection PyProtectedMember
        await bot._run_until_disconnected()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
