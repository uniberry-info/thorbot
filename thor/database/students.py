from .base import Base
import sqlalchemy as s
import sqlalchemy.orm as o


class Student(Base):
    """
    A table that contains data related to an authenticated university student.
    """
    __tablename__ = "students"

    email_prefix = s.Column(s.String, nullable=False, primary_key=True)
    first_name = s.Column(s.String, nullable=False)
    last_name = s.Column(s.String, nullable=False)

    privacy = s.Column(s.Boolean, nullable=False, default=True, server_default="TRUE")
    """Whether or not the student has requested to keep his data hidden."""

    ac = o.relationship("Account", back_populates="st")

    def email(self):
        return f"{self.email_prefix}@studenti.unimore.it"
