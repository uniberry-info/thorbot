from __future__ import annotations
from royalnet.typing import *
from telethon.hints import *
import telethon
import telethon.tl.custom
import sqlalchemy.orm
import os
import royalnet.campaigns
import logging
from .challenges import *
from ..deeplinking import DeepLinking
from ..database import Student, Telegram

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
        menu.campaign = await royalnet.campaigns.AsyncCampaign.create(start=menu.__start())
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

    async def __start(self) -> AsyncAdventure:
        """The generator which chooses the first dialog."""
        msg = yield
        if not msg.is_private:
            return
        if text := msg.message:
            if text.startswith("/start"):
                split = text.split(" ", 1)
                if len(split) == 1:
                    await self.__message(
                        '👋 Ciao! Sono Thor, il bot-moderatore di Unimore Informatica.\n\n'
                        'Se vuoi entrare nel gruppo, <a href="http://lo.steffo.eu:30008/login">effettua la verifica '
                        'della tua identità facendo il login qui con il tuo account Unimore</a>.\n\n'
                        'Se hai bisogno di aiuto, manda un messaggio a @Steffo.'
                    )
                else:
                    opcode, email_prefix = dl.decode(split[1])
                    if opcode == "R":
                        yield self.__after_registration(email_prefix=email_prefix)

    async def __after_registration(self, email_prefix: str) -> AsyncAdventure:
        msg: telethon.tl.custom.Message = yield
        from_user = await msg.get_sender()

        st: Student = self.session.query(Student).filter_by(email_prefix=email_prefix).one()
        choice = yield Keyboard(
            message=f'❔ Quindi sei {st.first_name} {st.last_name}, giusto?',
            choices=[["✅ Sì!", "❌ No."]]
        )

        if choice.message == "❌ No.":
            await self.__message("↩️ Allora effettua il logout da tutti gli account Google sul tuo browser, "
                                 "poi riprova!")
            return

        tg: Telegram = self.session.query(Telegram).filter_by(id=from_user.id).one_or_none()
        if tg is not None:
            if tg.st == st:
                await self.__message(
                    f'⭐️ Hai già effettuato la verifica dell\'identità.\n\n'
                    f'<a href="https://t.me/joinchat/AYAGH08KHLjBe1QbxNHLwA">Entra nel gruppo cliccando '
                    f'qui!</a>'
                )
            else:
                await self.__message(f"⚠️ Questo account Telegram è già connesso a <b>{tg.st.first_name} {tg.st.last_name}"
                                     f"</b>.\n\n")
            return

        choice = yield Keyboard(
            message="📝 Vuoi permettere agli altri studenti del gruppo di vedere il tuo vero nome e la tua "
                    "email universitaria?\n\n"
                    "(Gli amministratori del gruppo vi avranno comunque accesso.)",
            choices=[["✅ Sì!", "❌ No."]]
        )

        privacy = choice.message == "✅ Sì!"

        tg = Telegram(
            id=from_user.id,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
            st=st,
        )
        st.privacy = privacy

        self.session.add(tg)
        self.session.commit()

        await self.__message('✨ Hai completato la verifica dell\'identità.\n\n'
                             '<a href="https://t.me/joinchat/AYAGH08KHLjBe1QbxNHLwA">Entra nel gruppo cliccando '
                             'qui!</a>')
        return
