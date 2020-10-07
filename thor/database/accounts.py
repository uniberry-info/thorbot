from .base import Base
import sqlalchemy as s
import sqlalchemy.orm as o


class Account(Base):
    """
    A table that maps a Telegram user to a Student.
    """
    __tablename__ = "accounts"

    tg_id = s.Column(s.BigInteger, s.ForeignKey("telegram.id"), primary_key=True)
    st_email = s.Column(s.String, s.ForeignKey("students.email"), primary_key=True)

    tg = o.relationship("Telegram", back_populates="ac")
    st = o.relationship("Student", back_populates="ac")
