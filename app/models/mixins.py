# app/models/mixins.py
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime
from sqlalchemy.sql import func


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )


class UpdatedAtMixin:
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=datetime.utcnow,
        nullable=False
    )


class TimestampMixin(CreatedAtMixin, UpdatedAtMixin):
    """Shortcut para modelos que necesitan ambos."""
    pass