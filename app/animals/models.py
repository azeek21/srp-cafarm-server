from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class AnimalType(StrEnum):
    CATTLE = "cattle"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class AnimalStatus(StrEnum):
    ACTIVE = "active"
    SOLD = "sold"
    DECEASED = "deceased"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Animal(SQLModel, table=True):
    __tablename__ = "animal"

    __table_args__ = (
        # One live animal per (type, tag); soft-deleted rows are excluded so a tag
        # can be reused after deletion.
        Index(
            "uq_animal_type_tag_live",
            "type",
            "tag",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: AnimalType = Field(index=True)
    tag: str
    name: str | None = None
    breed: str = Field(index=True)
    gender: Gender
    date_of_birth: date
    status: AnimalStatus = Field(default=AnimalStatus.ACTIVE, index=True)
    # Stamped by the service whenever `status` changes; null until first transition.
    status_changed_at: datetime | None = Field(default=None)
    note: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    deleted_at: datetime | None = Field(default=None, index=True)
