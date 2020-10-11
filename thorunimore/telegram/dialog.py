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
                yield self.__whois()

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

    async def __start(self) -> AsyncAdventure:
        """Disambiguation for the /start command."""
        msg: telethon.tl.custom.Message = yield

        text: str = msg.message

        # Check if the user is already registered
        from_user = await msg.get_sender()
        tg: Telegram = self.session.query(Telegram).filter_by(id=from_user.id).one_or_none()
        if tg is not None:
            await self.__message(
                f'⭐️ Hai già effettuato la verifica dell\'identità.\n\n'
                f'<a href="{os.environ["GROUP_URL"]}">Entra nel gruppo cliccando '
                f'qui!</a>'
            )
            return

        # Check whether this is a normal start or a deep-linked one
        split = text.split(" ", 1)
        if len(split) == 1:
            yield self.__normal_start()
        else:
            yield self.__deeplink_start(payload=split[1])

    async def __normal_start(self) -> AsyncAdventure:
        """The /start command, called without arguments."""
        msg: telethon.tl.custom.Message = yield

        await self.__message(
            f'👋 Ciao! Sono Thor, il bot-moderatore di Unimore Informatica.\n'
            f'\n'
            f'Se vuoi entrare nel gruppo, devi <b>dimostrare di essere uno studente dell\'Unimore</b>.\n'
            f'\n'
            f'<a href="{os.environ["BASE_URL"]}">Fai il login con il tuo account universitario qui</a>, poi una volta '
            f'tornato su Telegram premi il tasto <i>AVVIA</i> in basso per ricevere il link! 😊'
        )

    async def __deeplink_start(self, payload: str) -> AsyncAdventure:
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
        else:
            await self.__message("⚠️ Ricevuto un opcode sconosciuto.")

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

        # Ask for confirmation
        choice = yield Keyboard(
            message=f'❔ Tu sei {st.first_name} {st.last_name} <{st.email()}>, giusto?',
            choices=[["❌ No.", "✅ Sì!"]]
        )
        if choice.message == "❌ No.":
            await self.__message(
                "↩️ Effettua il logout da tutti gli account Google sul tuo browser, poi ri-invia il comando /start!"
            )
            return

        # Ask for privacy mode
        choice = yield Keyboard(
            message="📝 Vuoi permettere agli altri studenti verificati di visualizzare il tuo <b>vero nome</b> e la tua "
                    "<b>email istituzionale</b> attraverso il comando /whois?\n\n"
                    "(Gli amministratori del gruppo vi avranno comunque accesso, e potrai cambiare idea in qualsiasi "
                    "momento con il comando /privacy.)",
            choices=[["👤 Nascondi.", "📱 Mostra!"]]
        )
        st.privacy = choice.message == "👤 Nascondi."

        # Create the SQL record
        tg = Telegram(
            id=from_user.id,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
            username=from_user.username,
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

    async def __privacy(self) -> AsyncAdventure:
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
            message="📝 Vuoi permettere agli altri studenti verificati di visualizzare il tuo <b>vero nome</b> e la tua "
                    "<b>email istituzionale</b> attraverso il comando /whois?\n\n"
                    "(Gli amministratori del gruppo vi avranno comunque accesso, e potrai cambiare idea in qualsiasi "
                    "momento con il comando /privacy.)",
            choices=[["👤 Nascondi.", "📱 Mostra!"]],
        )
        tg.st.privacy = choice.message == "👤 Nascondi."
        self.session.commit()

        if tg.st.privacy:
            await self.__message("👤 I tuoi dati ora sono nascosti.")
        else:
            await self.__message("📱 I tuoi dati ora sono visibili attraverso il comando /whois!")

    async def __whois(self) -> AsyncAdventure:
        """The /whois command, used to fetch information about a certain student or Telegram account."""
        msg: telethon.tl.custom.Message = yield

        cmd, *args = msg.message.split(" ", 1)
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

        # TODO: Match telegram mentions
        # TODO: Match telegram name

        await self.__message(
            "⚠️ Non hai specificato correttamente cosa cercare.\n"
            "\n"
            "Puoi specificare un'username Telegram, un nome e cognome o un'email.\n"
            "<code>/whois Stefano Pigozzi</code>\n"
            "<code>/whois @Steffo</code>\n"
            "<code>/whois 256895@studenti.unimore.it</code>\n"
            "\n"
            "🚧 La funzionalità di ricerca tramite name-mention di Telegram non è ancora stata implementata."
        )

    async def __whois_email(self, email_prefix: str):
        """The /whois command, called with an email."""
        msg: telethon.tl.custom.Message = yield

        st: Optional[Student] = self.session.query(Student).filter_by(email_prefix=email_prefix).one_or_none()
        if st is None:
            await self.__message("⚠️ Nessuno studente trovato.")
            return

        await self.__message(st.whois())

    async def __whois_real_name(self, name: str) -> AsyncAdventure:
        """The /whois command, called with a first name and a last name."""
        msg: telethon.tl.custom.Message = yield

        students = (
            self.session
            .query(Student)
            .filter(
                sqlalchemy.or_(
                    sqlalchemy.func.concat(Student.first_name, " ", Student.last_name) == name.upper(),
                    sqlalchemy.func.concat(Student.last_name, " ", Student.first_name) == name.upper(),
                )
            )
            .all()
        )

        if len(students) == 0:
            await self.__message("⚠️ Nessuno studente trovato.")
            return

        # There might be more than a student with the same name!
        response: List[str] = []
        for student in students:
            response.append(student.whois())

        await self.__message("\n\n".join(response))

    async def __whois_username(self, username: str) -> AsyncAdventure:
        """The /whois command, called with a Telegram username."""
        msg: telethon.tl.custom.Message = yield

        tg: Optional[Telegram] = self.session.query(Telegram).filter_by(username=username).one_or_none()
        if tg is None:
            await self.__message("⚠️ Nessuno studente trovato.")
            return

        await self.__message(tg.st.whois())
