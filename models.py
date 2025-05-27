# standard library
from datetime import datetime

# 3rd party libraries
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base for declarative mappings.
    """
    pass


class Record(Base):
    """
    Database single record corresponding to unique schema digest/field pair.
    """

    __tablename__ = "records"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    date_added  : Mapped[datetime] = mapped_column(DateTime, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    digest      : Mapped[str] = mapped_column(String(255), nullable=False)
    field       : Mapped[str] = mapped_column(String(255), nullable=False)
