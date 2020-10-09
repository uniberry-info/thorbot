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

    privacy = s.Column(s.Boolean, nullable=False, default=True, server_default="TRUE")
    """Whether or not the student has requested to keep his data hidden from all users."""

    st_email_prefix = s.Column(s.String, s.ForeignKey("students.email_prefix"), nullable=False)
    st = o.relationship("Student", back_populates="tg", uselist=False)

    def __repr__(self):
        return f"{self.__qualname__}({self.id=}, {self.first_name=}, {self.last_name=}, {self.username=}, " \
               f"{self.privacy=}, {self.st_email_prefix=})"

    def __str__(self):
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        else:
            return self.first_name

    def name_mention(self) -> str:
        return f'<a href="tg://user?id={self.id}">{html.escape(str(self))}</a>'

    def at_mention(self) -> Optional[str]:
        if self.username:
            return f"@{self.username}"
        else:
            return None
