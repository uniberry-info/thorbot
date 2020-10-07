from .base import Base
import sqlalchemy as s
import sqlalchemy.orm as o


class Student(Base):
    """
    A table that contains data related to an authenticated university student.
    """
    __tablename__ = "students"

    # Student personal data fields
    id = s.Column(s.Integer, primary_key=True)  # "Matricola"
    first_name = s.Column(s.String)
    last_name = s.Column(s.String)

    privacy = s.Column(s.Boolean, server_default="TRUE")
    """Whether or not the student has requested to keep his data hidden."""

    ac = o.relationship("Account", back_populates="st")
