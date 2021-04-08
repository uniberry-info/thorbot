import sqlalchemy as s
import sqlalchemy.orm as o

from .base import Base


class Token(Base):
    """
    A table that contains API tokens to check if an user is registered or not in the database.
    """
    __tablename__ = "tokens"

    id = s.Column(s.Integer, nullable=False, primary_key=True)
    token = s.Column(s.String, nullable=False)

    owner_id = s.Column(s.BigInteger, s.ForeignKey("telegram.id"), nullable=False)
    owner = o.relationship("Telegram", backref="tokens")

    def __repr__(self):
        return f"{self.__qualname__}({self.id=}, {self.token=}, {self.owner_id=})"
