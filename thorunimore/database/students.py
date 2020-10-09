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

    tg = o.relationship("Telegram", back_populates="st", uselist=False)

    def email(self):
        return f"{self.email_prefix}@studenti.unimore.it"

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email()}>"

    def __repr__(self):
        return f"{self.__qualname__}({self.email_prefix=}, {self.first_name=}, {self.last_name=})"

    def message(self):
        return f"🎓 <b>{self.first_name} {self.last_name}</b>\n" \
               f"{self.email()}\n" \
               f"\n" \
               f"Sul gruppo:\n" \
               f"{self.tg.name_mention()}\n" \
               f"{self.tg.at_mention() or ''}"
