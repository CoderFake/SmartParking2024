import enum
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ----------------------------------------------------------------
# Account
# ----------------------------------------------------------------
class Account(Base):
    __tablename__ = "account"

    id: Mapped[str] = mapped_column(primary_key=True)
    login_id: Mapped[str]
    name: Mapped[str]
    email: Mapped[str]
    created_at: Mapped[datetime]
    modified_at: Mapped[datetime]
    last_login: Mapped[datetime]


