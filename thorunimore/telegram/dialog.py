from __future__ import annotations

import logging
import os
import re

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


email_regex = re.compile(r"^([0-9]+)(?:@studenti\.unimore\.it)?$")


class Dialog:
    def __init__(self, bot: telethon.TelegramClient, entity: Entity, session: sqlalchemy.orm.Session):
        self.bot: telethon.TelegramClient = bot
        self.entity: Entity = entity
        self.session: sqlalchemy.orm.Session = session
        self.campaign: royalnet.campaigns.AsyncCampaign = ...

    @classmethod
    async def create(cls,
                     bot: telethon.TelegramClient,
                     entity: Entity,
                     session: sqlalchemy.orm.Session) -> Dialog:
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

    async def __message(self, msg, **kwargs):
        """Send a message to the specified entity."""
        return await self.bot.send_message(
            entity=self.entity,
            parse_mode="HTML",
            message=msg,
            buttons=self.bot.build_reply_markup(telethon.tl.custom.Button.clear()),
            **kwargs
        )

    async def __first(self) -> AsyncAdventure:
        """The generator which chooses the first dialog."""
        msg: telethon.tl.custom.Message = yield

        # If this is a text message
        if text := msg.message:
            if text.startswith("/whois"):
                yield self.__whois(text=text)

            elif text.startswith("/start"):
                if msg.is_private:
                    yield self.__start()
                else:
                    await self.__message(
                        f"⚠️ Questo comando funziona solo in chat privata (@{os.environ['TELEGRAM_BOT_USERNAME']})."
                    )

            elif text.startswith("/privacy"):
                if msg.is_private:
                    yield self.__privacy()
                else:
                    await self.__message(
                        f"⚠️ Questo comando funziona solo in chat privata (@{os.environ['TELEGRAM_BOT_USERNAME']})."
                    )

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
            f'👋 Ciao! Sono Thor, il bot-moderatore di Unimore Informatica.\n\n'
            f'Per entrare nel gruppo devi <a href="{os.environ["BASE_URL"]}/">effettuare la verifica '
            f'dell\'identità facendo il login qui con il tuo account Unimore</a>.\n\n'
            f'Se hai bisogno di aiuto, manda un messaggio a @Steffo.'
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

        if tg is not None:
            # The user is already registered
            if tg.st == st:
                await self.__message(
                    f'⭐️ Hai già effettuato la verifica dell\'identità.\n\n'
                    f'<a href="{os.environ["GROUP_URL"]}">Entra nel gruppo cliccando '
                    f'qui!</a>'
                )
                return
            # The account is connected to someone else
            else:
                await self.__message(
                    f"⚠️ Questo account Telegram è già connesso a <b>{tg.st.first_name} {tg.st.last_name}"
                    f"</b>.\n\n"
                )
                return

        # Ask for confirmation
        choice = yield Keyboard(
            message=f'❔ Tu sei {st.first_name} {st.last_name} <{st.email()}>, giusto?',
            choices=[["✅ Sì!", "❌ No."]]
        )
        if choice.message == "❌ No.":
            await self.__message(
                "↩️ Effettua il logout da tutti gli account Google sul tuo browser, poi ri-invia il comando /start!"
            )
            return

        # Ask for privacy mode
        choice = yield Keyboard(
            message="📝 Vuoi aggiungere il tuo nome e la tua email alla rubrica del gruppo?\n"
                    "\n"
                    "Questo li renderà visibili a tutti gli altri membri verificati.\n"
                    "\n"
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
            username=from_user.username,
            privacy=privacy,
            st=st,
        )

        # Commit the SQLAlchemy session
        self.session.add(tg)
        self.session.commit()

        # Send the link to the group
        await self.__message(
            f'✨ Hai completato la verifica dell\'identità.\n\n'
            f'<a href="{os.environ["GROUP_URL"]}">Entra nel gruppo cliccando qui!</a>'
        )
        return

    async def __privacy(self):
        msg: telethon.tl.custom.Message = yield

        from_user = await msg.get_sender()

        tg: Telegram = self.session.query(Telegram).filter_by(id=from_user.id).one_or_none()
        if tg is None:
            await self.__message(
                "⚠️ Non hai ancora effettuato la verifica dell'account!\n"
                "\n"
                "Invia /start per iniziare!"
            )
            return

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

        cmd, *args = text.split(" ", 1)
        args = " ".join(args)

        # Email
        if match := re.match(email_regex, args):
            email_prefix = match.group(1)
            yield self.__whois_email(email_prefix=email_prefix)

        # Real name
        elif " " in args:
            yield self.__whois_real_name(name=args)

        elif args.startswith("@"):
            username = args.lstrip("@")
            yield self.__whois_username(username=username)

        await self.__message(
            "⚠️ Non hai specificato correttamente cosa cercare.\n"
            "\n"
            "Puoi specificare un'username Telegram, un nome e cognome o un'email."
        )

    async def __whois_email(self, email_prefix: str):
        msg: telethon.tl.custom.Message = yield

        result = self.session.query(Student).filter_by(email_prefix=email_prefix).one_or_none()
        if result is None:
            await self.__message("⚠️ Nessuno studente trovato.")
        elif result.tg.privacy:
            await self.__message(
                "👤 Lo studente è registrato, ma ha deciso di manterere privati i dettagli del suo account."
            )
        else:
            await self.__message(result.message())

    async def __whois_real_name(self, name: str):
        msg: telethon.tl.custom.Message = yield

        sq = (
            self.session
            .query(
                Student,
                sqlalchemy.func.concat(Student.first_name, " ", Student.last_name).label("full_name")
            )
            .subquery()
        )
        result = (
            self.session
            .query(sq)
            .filter_by(full_name=name.upper())
            .all()
        )

        if len(result) == 0:
            await self.__message("⚠️ Nessuno studente trovato.")
            return

        # There might be more than a student with the same name!
        response: List[str] = []
        hidden: bool = False
        for student in result:
            if student.tg.privacy:
                hidden = True
                continue
            response.append(student.message())
        if hidden:
            response.append(
                "👤 Almeno uno studente ottenuto dalla ricerca è registrato, ma ha deciso di mantenere privati i "
                "dettagli del suo account."
            )

        await self.__message("\n\n".join(response))

    async def __whois_username(self, username: str):
        msg: telethon.tl.custom.Message = yield

        result = self.session.query(Telegram).filter_by(username=username).one_or_none()
        if result is None:
            await self.__message("⚠️ Nessuno studente trovato.")
        elif result.privacy:
            await self.__message(
                "👤 Lo studente è registrato, ma ha deciso di manterere privati i dettagli del suo account."
            )
        else:
            await self.__message(result.st.message())
