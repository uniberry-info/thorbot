from .base import Base
import sqlalchemy as s
import sqlalchemy.orm as o


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
