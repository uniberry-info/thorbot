from royalnet.typing import *
import sqlalchemy as s
import sqlalchemy.orm as o
import html

from .base import Base


class Telegram(Base):
    """
    A table that contains data related to the second step of the student verification process (Telegram menu).
    """
    __tablename__ = "telegram"

    id = s.Column(s.BigInteger, primary_key=True)
    first_name = s.Column(s.String, nullable=False)
    last_name = s.Column(s.String)
    username = s.Column(s.String)

    st_email_prefix = s.Column(s.String, s.ForeignKey("students.email_prefix"), nullable=False)
    st = o.relationship("Student", back_populates="tg", uselist=False)

    is_admin = s.Column(s.Boolean, nullable=False, default=False, server_default="FALSE")

    def __repr__(self):
        return f"{self.__qualname__}({self.id=}, {self.first_name=}, {self.last_name=}, {self.username=}, " \
               f"{self.st_email_prefix=})"

    def __str__(self):
        """
        :return: The Telegram account's full name
        """
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        else:
            return self.first_name

    def name_mention(self) -> str:
        """
        Create a Telegram name mention.

        :return: The mention.
        """
        return f'<a href="tg://user?id={self.id}">{html.escape(str(self))}</a>'

    def at_mention(self) -> Optional[str]:
        """
        Create a Telegram username mention.

        :return: The mention, or None if the user has no username.
        """
        if self.username:
            return f"@{self.username}"
        else:
            return None

    def whois(self) -> str:
        """Compose the whois message for this student, respecting privacy settings."""
        return self.st.whois()

    def whois_message(self) -> str:
        """Compose the whois message for this student, ignoring privacy settings."""
        return self.st.whois_message()

    def minimessage(self) -> str:
        """Compose the whois message subsection for this Telegram account."""
        return f"📱 {self.name_mention()}\n" \
               f"{self.at_mention() or ''}\n"
