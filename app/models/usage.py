from datetime import date

from sqlalchemy import Integer, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Usage(Base):
    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(primary_key=True)

    api_key_id: Mapped[int] = mapped_column(
        ForeignKey("api_keys.id"),
        nullable=False,
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("api_key_id", "day", name="uq_usage_key_day"),
    )
