from .base import Base
import sqlalchemy as s
import sqlalchemy.orm as o


class Telegram(Base):
    """
    A table that contains data related to a specific Telegram account.
    """
    __tablename__ = "telegram"

    id = s.Column(s.BigInteger, primary_key=True)
    first_name = s.Column(s.String, nullable=False)
    last_name = s.Column(s.String)
    username = s.Column(s.String)

    st_email_prefix = s.Column(s.String, s.ForeignKey("students.email_prefix"), nullable=False)
    st = o.relationship("Student", back_populates="tg", uselist=False)
