from __future__ import annotations

import logging
import os
import re

import itsdangerous
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
        """
        Initialize an Dialog object.

        .. warning:: Do not use this, use the Dialog.create() method instead!
        """
        self.bot: telethon.TelegramClient = bot
        "The bot at one side of the Dialog."

        self.entity: Entity = entity
        "The entity (user, group) at the other side of the Dialog."

        self.session: sqlalchemy.orm.Session = session
        "The SQLAlchemy Session to be used exclusively for this dialog."

        self.campaign: royalnet.campaigns.AsyncCampaign = ...
        """
        The AsyncCampaign this dialog will use to track the back and forth (taking form of multiple AsyncAdventures).
        
        May be an instance of Ellipsis if the Dialog is not initialized.
        """

    @classmethod
    async def create(cls,
                     bot: telethon.TelegramClient,
                     entity: Entity,
                     session: sqlalchemy.orm.Session) -> Dialog:
        """
        Create a new Dialog object.

        :param bot: The bot at one side of the Dialog.
        :param entity: The entity (user, group) at the other side of the Dialog.
        :param session: The SQLAlchemy Session to be used exclusively for this dialog.
        :return: The created dialog.
        """
        menu = cls(bot=bot, entity=entity, session=session)
        menu.campaign = await royalnet.campaigns.AsyncCampaign.create(start=menu.__first())
        return menu

    async def next(self, msg: telethon.tl.custom.Message) -> None:
        """
        Advance to the next message of the Dialog.

        :param msg: The message to pass to the AsyncAdventure.
        """
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

    async def __message(self, msg, **kwargs) -> telethon.types.Message:
        """
        Send a Telegram message to the user at the other side of the dialog.

        It's a shortcut to self.bot.send_message.

        :param msg: The contents of the message.
        :param kwargs: Keyword arguments to pass to send_message.
        :return: The Message returned by send_message.
        """
        return await self.bot.send_message(
            entity=self.entity,
            parse_mode="HTML",
            message=msg,
            buttons=self.bot.build_reply_markup(telethon.tl.custom.Button.clear()),
            **kwargs
        )

    async def __first(self) -> AsyncAdventure:
        """What to do when the dialog is first opened."""
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
        """Disambiguation for the /start command."""
        msg: telethon.tl.custom.Message = yield

        text: str = msg.message

        # Check whether this is a normal start or a deep-linked one
        split = text.split(" ", 1)
        if len(split) == 1:
            yield self.__normal_start()
        else:
            yield self.__deeplink_start(payload=split[1])

    async def __normal_start(self):
        """The /start command, called without arguments."""
        msg: telethon.tl.custom.Message = yield

        await self.__message(
            f'👋 Ciao! Sono Thor, il bot-moderatore di Unimore Informatica.\n'
            f'\n'
            f'Se vuoi entrare nel gruppo, devi <b>dimostrare di essere uno studente dell\'Unimore</b>.\n'
            f'\n'
            f'<a href="">Fai il login con il tuo account universitario qui</a>, poi una volta tornato su Telegram '
            f'premi il tasto <i>AVVIA</i> in basso per ricevere il link! 😊'
        )

    async def __deeplink_start(self, payload: str):
        """The /start command, called with deep-linked arguments."""
        msg: telethon.tl.custom.Message = yield

        try:
            opcode, data = dl.decode(payload)
        except itsdangerous.exc.BadData:
            await self.__message("⚠️ I dati ricevuti non sono validi.")
            return

        # R: Register new account
        if opcode == "R":
            yield self.__register(email_prefix=data)

    async def __register(self, email_prefix: str) -> AsyncAdventure:
        """
        The /start command, called with a payload starting with R.

        Links a Telegram account to a real student.

        :param email_prefix: The prefix before @studenti.unimore.it
        """
        msg: telethon.tl.custom.Message = yield

        from_user = await msg.get_sender()

        tg: Telegram = self.session.query(Telegram).filter_by(id=from_user.id).one_or_none()
        st: Student = self.session.query(Student).filter_by(email_prefix=email_prefix).one()

        if tg is not None:
            # The user is already registered
            if tg in st.tg:
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
                    f"</b>."
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
        """The /privacy command, used to toggle between privacy states."""
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
