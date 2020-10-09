from __future__ import annotations

import logging
import os

import royalnet.campaigns
import sqlalchemy.orm
import telethon
import telethon.tl.custom
from royalnet.typing import *
from telethon.hints import *

from .challenges import *
from ..database import Student, Telegram
from ..deeplinking import DeepLinking

log = logging.getLogger(__name__)
dl = DeepLinking(os.environ["SECRET_KEY"])


class CampaignContainer:
    def __init__(self, bot: telethon.TelegramClient, entity: Entity, session: sqlalchemy.orm.Session):
        self.bot: telethon.TelegramClient = bot
        self.entity: Entity = entity
        self.session: sqlalchemy.orm.Session = session
        self.campaign: royalnet.campaigns.AsyncCampaign = ...

    @classmethod
    async def create(cls,
                     bot: telethon.TelegramClient,
                     entity: Entity,
                     session: sqlalchemy.orm.Session) -> CampaignContainer:
        menu = cls(bot=bot, entity=entity, session=session)
        menu.campaign = await royalnet.campaigns.AsyncCampaign.create(start=menu.__first())
        return menu

    async def next(self, msg: telethon.tl.custom.Message) -> None:
        try:
            log.debug(f"Advancing: {self}")
            await self.campaign.next(msg)
        except StopAsyncIteration:
            log.debug(f"Closing: {self}")
            self.session.close()
            raise
        else:
            log.debug(f"Sending: {self.campaign.challenge}")
            await self.campaign.challenge.send(bot=self.bot, entity=self.entity)

    async def __message(self, msg):
        """Send a message to the specified entity."""
        return await self.bot.send_message(entity=self.entity, parse_mode="HTML", message=msg)

    async def __first(self) -> AsyncAdventure:
        """The generator which chooses the first dialog."""
        msg: telethon.tl.custom.Message = yield

        # If this is a text message
        if text := msg.message:

            # Group chat commands
            if not msg.is_private:
                if text.startswith("/whois"):
                    yield self.__whois(text=text)

            # Private chat commands
            else:
                if text.startswith("/start"):
                    yield self.__start()
                elif text.startswith("/privacy"):
                    yield self.__privacy()

    async def __start(self):
        msg: telethon.tl.custom.Message = yield
        text: str = msg.message

        # Check whether this is a normal start or a deep-linked one
        split = text.split(" ", 1)
        if len(split) == 1:
            yield self.__normal_start()
        else:
            yield self.__deeplink_start(payload=split[1])

    async def __normal_start(self):
        msg: telethon.tl.custom.Message = yield
        await self.__message(
            '👋 Ciao! Sono Thor, il bot-moderatore di Unimore Informatica.\n\n'
            'Se vuoi entrare nel gruppo, <a href="http://lo.steffo.eu:30008/login">effettua la verifica '
            'della tua identità facendo il login qui con il tuo account Unimore</a>.\n\n'
            'Se hai bisogno di aiuto, manda un messaggio a @Steffo.'
        )

    async def __deeplink_start(self, payload: str):
        msg: telethon.tl.custom.Message = yield
        opcode, data = dl.decode(payload)

        # R: Register new account
        if opcode == "R":
            yield self.__register(email_prefix=data)

    async def __register(self, email_prefix: str) -> AsyncAdventure:
        msg: telethon.tl.custom.Message = yield
        from_user = await msg.get_sender()

        tg: Telegram = self.session.query(Telegram).filter_by(id=from_user.id).one_or_none()
        st: Student = self.session.query(Student).filter_by(email_prefix=email_prefix).one()

        # Check if the user is already registered
        if tg is not None:
            if tg.st == st:
                await self.__message(
                    f'⭐️ Hai già effettuato la verifica dell\'identità.\n\n'
                    f'<a href="https://t.me/joinchat/AYAGH08KHLjBe1QbxNHLwA">Entra nel gruppo cliccando '
                    f'qui!</a>'
                )
            else:
                await self.__message(
                    f"⚠️ Questo account Telegram è già connesso a <b>{tg.st.first_name} {tg.st.last_name}"
                    f"</b>.\n\n")
            return

        # Ask for confirmation
        choice = yield Keyboard(
            message=f'❔ Tu sei {st.first_name} {st.last_name} <{st.email()}>, giusto?',
            choices=[["✅ Sì!", "❌ No."]]
        )
        if choice.message == "❌ No.":
            await self.__message("↩️ Allora effettua il logout da tutti gli account Google sul tuo browser, "
                                 "poi riprova!")
            return

        # Ask for privacy mode
        choice = yield Keyboard(
            message="📝 Vuoi aggiungere il tuo nome e la tua email alla rubrica del gruppo?\n\n"
                    "Questo li renderà visibili a tutti gli altri membri verificati.\n\n"
                    "(Gli amministratori del gruppo vi avranno comunque accesso, e potrai cambiare idea in qualsiasi "
                    "momento con il comando /privacy.)",
            choices=[["✅ Sì!", "❌ No."]]
        )
        privacy = choice.message == "❌ No."

        # Create the SQL record
        tg = Telegram(
            id=from_user.id,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
            st=st,
        )
        # Set the privacy mode
        st.privacy = privacy

        # Commit the SQLAlchemy session
        self.session.add(tg)
        self.session.commit()

        # Send the link to the group
        await self.__message('✨ Hai completato la verifica dell\'identità.\n\n'
                             '<a href="https://t.me/joinchat/AYAGH08KHLjBe1QbxNHLwA">Entra nel gruppo cliccando '
                             'qui!</a>')
        return

    async def __privacy(self):
        msg: telethon.tl.custom.Message = yield
        from_user = await msg.get_sender()

        tg: Telegram = self.session.query(Telegram).filter_by(id=from_user.id).one_or_none()
        if tg is None:
            await self.__message("⚠️ Non hai ancora effettuato la verifica dell'account!\n\n"
                                 "Usa /start per iniziare!")

        # Ask for privacy mode
        choice = yield Keyboard(
            message="📝 Vuoi aggiungere il tuo nome e la tua email alla rubrica del gruppo?\n\n"
                    "Questo li renderà visibili a tutti gli altri membri verificati.\n\n"
                    "(Gli amministratori del gruppo vi avranno comunque accesso, e potrai cambiare idea in qualsiasi "
                    "momento con il comando /privacy.)",
            choices=[["✅ Sì!", "❌ No."]]
        )
        tg.privacy = choice.message == "❌ No."
        self.session.commit()

        if tg.privacy:
            await self.__message("❌ I tuoi dati ora sono nascosti dalla rubrica del gruppo.")
        else:
            await self.__message("✅ I tuoi dati ora sono visibili nella rubrica del gruppo!")

    async def __whois(self, text: str):
        msg: telethon.tl.custom.Message = yield

        # TODO: This command hasn't been implemented yet.
        await self.__message("🚧 Questo comando non è ancora disponibile. Riprova più avanti!")
