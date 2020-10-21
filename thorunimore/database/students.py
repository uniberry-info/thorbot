import sqlalchemy as s
import sqlalchemy.orm as o

from .base import Base


class Student(Base):
    """
    A table that contains data related to the first step of the student verification process (Google sign in).
    """
    __tablename__ = "students"

    email_prefix = s.Column(s.String, nullable=False, primary_key=True)
    first_name = s.Column(s.String, nullable=False)
    last_name = s.Column(s.String, nullable=False)

    privacy = s.Column(s.Boolean, nullable=False, default=True, server_default="TRUE")
    """Whether or not the student has requested to keep his data hidden from all users."""

    tg = o.relationship("Telegram", back_populates="st")

    def email(self):
        """
        Compose the full email of the student.

        :return: The email in form of a str.
        """
        return f"{self.email_prefix}@studenti.unimore.it"

    def __str__(self) -> str:
        """
        :return: The full name of the user and their email in classic form (Stefano Pigozzi <ste.pigozzi@gmail.com>).
        """
        return f"{self.first_name} {self.last_name} <{self.email()}>"

    def __repr__(self):
        return f"{self.__qualname__}({self.email_prefix=}, {self.first_name=}, {self.last_name=}, {self.privacy=})"

    def whois(self) -> str:
        """
        Compose the whois message for this student, respecting privacy settings.

        :return: The composed message.
        """
        if self.privacy:
            return "👤 Lo studente è registrato, ma ha deciso di manterere privati i dettagli del suo account."
        return self.whois_message()

    def whois_message(self):
        """
        Compose the whois message for this student, ignoring privacy settings.

        :return: The composed message.
        """

        emoji = "👤" if self.privacy else "🎓"

        rows = [
            f"{emoji} <b>{self.first_name} {self.last_name}</b>",
            f"{self.email()}",
            ""
        ]

        tgs = [tg for tg in self.tg]
        for tg in tgs:
            rows.append(tg.minimessage())
            rows.append("")

        return "\n".join(rows)
