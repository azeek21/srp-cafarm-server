from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.animals.models import AnimalStatus, AnimalType, Gender

SortBy = str  # one of: tag|breed|date_of_birth|status|created_at
SortOrder = str  # asc|desc


class AnimalCreate(BaseModel):
    type: AnimalType = AnimalType.CATTLE
    tag: str = Field(min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=128)
    breed: str = Field(min_length=1, max_length=128)
    gender: Gender
    date_of_birth: date
    status: AnimalStatus = AnimalStatus.ACTIVE
    note: str | None = Field(default=None, max_length=2000)


class AnimalUpdate(BaseModel):
    tag: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=128)
    breed: str | None = Field(default=None, min_length=1, max_length=128)
    gender: Gender | None = None
    date_of_birth: date | None = None
    status: AnimalStatus | None = None
    note: str | None = Field(default=None, max_length=2000)


class AnimalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: AnimalType
    tag: str
    name: str | None
    breed: str
    gender: Gender
    date_of_birth: date
    status: AnimalStatus
    status_changed_at: datetime | None = None
    note: str | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def age_years(self) -> int:
        today = date.today()
        dob = self.date_of_birth
        years = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            years -= 1
        return max(years, 0)


class AnimalListParams(BaseModel):
    type: AnimalType | None = None
    search: str | None = None
    breed: str | None = None
    gender: Gender | None = None
    status: AnimalStatus | None = None
    born_after: date | None = None
    born_before: date | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20


class AnimalListResponse(BaseModel):
    items: list[AnimalRead]
    total: int
    page: int
    page_size: int
