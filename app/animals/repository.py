from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, asc, col, desc, or_, select

from app.animals.models import Animal, AnimalStatus, AnimalType
from app.animals.schemas import AnimalListParams

SORTABLE_COLUMNS = {
    "tag": Animal.tag,
    "breed": Animal.breed,
    "date_of_birth": Animal.date_of_birth,
    "status": Animal.status,
    "created_at": Animal.created_at,
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AnimalRepository:
    """All data access for animals. Every read excludes soft-deleted rows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _live(self):
        """Base SELECT restricted to non-deleted rows."""
        return select(Animal).where(col(Animal.deleted_at).is_(None))

    # ---- CRUD ----------------------------------------------------------------

    def add(self, animal: Animal) -> Animal:
        self.session.add(animal)
        self.session.commit()
        self.session.refresh(animal)
        return animal

    def get(self, animal_id: UUID) -> Animal | None:
        statement = self._live().where(Animal.id == animal_id)
        return self.session.exec(statement).first()

    def get_by_tag(self, type_: AnimalType, tag: str) -> Animal | None:
        statement = self._live().where(Animal.type == type_, Animal.tag == tag)
        return self.session.exec(statement).first()

    def save(self, animal: Animal) -> Animal:
        self.session.add(animal)
        self.session.commit()
        self.session.refresh(animal)
        return animal

    def soft_delete(self, animal: Animal) -> None:
        now = _utcnow()
        animal.deleted_at = now
        animal.updated_at = now
        self.session.add(animal)
        self.session.commit()

    # ---- Listing -------------------------------------------------------------

    def _apply_filters(self, statement, params: AnimalListParams):
        if params.type is not None:
            statement = statement.where(Animal.type == params.type)
        if params.search:
            pattern = f"%{params.search}%"
            statement = statement.where(
                or_(
                    col(Animal.tag).ilike(pattern),
                    col(Animal.name).ilike(pattern),
                    col(Animal.breed).ilike(pattern),
                )
            )
        if params.breed:
            statement = statement.where(Animal.breed == params.breed)
        if params.gender is not None:
            statement = statement.where(Animal.gender == params.gender)
        if params.status is not None:
            statement = statement.where(Animal.status == params.status)
        if params.born_after is not None:
            statement = statement.where(Animal.date_of_birth >= params.born_after)
        if params.born_before is not None:
            statement = statement.where(Animal.date_of_birth <= params.born_before)
        return statement

    def list(self, params: AnimalListParams) -> tuple[list[Animal], int]:
        base = self._apply_filters(self._live(), params)

        total = self.session.exec(
            select(func.count()).select_from(base.subquery())
        ).one()

        column = SORTABLE_COLUMNS.get(params.sort_by, Animal.created_at)
        direction = asc if params.sort_order == "asc" else desc
        offset = (params.page - 1) * params.page_size
        statement = base.order_by(direction(column)).offset(offset).limit(params.page_size)

        items = list(self.session.exec(statement).all())
        return items, total

    # ---- Aggregates ----------------------------------------------------------

    def _count_live(self, *filters) -> int:
        statement = select(func.count()).select_from(Animal).where(
            col(Animal.deleted_at).is_(None)
        )
        for f in filters:
            statement = statement.where(f)
        return self.session.exec(statement).one()

    def total(self, type_: AnimalType | None = None) -> int:
        filters = [] if type_ is None else [Animal.type == type_]
        return self._count_live(*filters)

    def active_total(self, type_: AnimalType | None = None) -> int:
        filters = [Animal.status == AnimalStatus.ACTIVE]
        if type_ is not None:
            filters.append(Animal.type == type_)
        return self._count_live(*filters)

    def count_by(self, column, type_: AnimalType | None = None) -> dict[str, int]:
        statement = (
            select(column, func.count())
            .where(col(Animal.deleted_at).is_(None))
            .group_by(column)
        )
        if type_ is not None:
            statement = statement.where(Animal.type == type_)
        result: dict[str, int] = {}
        for key, count in self.session.exec(statement).all():
            result[key.value if hasattr(key, "value") else str(key)] = count
        return result

    def count_by_status(self, type_: AnimalType | None = None) -> dict[str, int]:
        return self.count_by(Animal.status, type_)

    def count_by_breed(self, type_: AnimalType | None = None) -> dict[str, int]:
        return self.count_by(Animal.breed, type_)

    def count_by_gender(self, type_: AnimalType | None = None) -> dict[str, int]:
        return self.count_by(Animal.gender, type_)

    def age_aggregates(self, type_: AnimalType | None = None) -> list:
        """Return raw date_of_birth values for live animals (age shaped in service)."""
        statement = self._live()
        if type_ is not None:
            statement = statement.where(Animal.type == type_)
        return [a.date_of_birth for a in self.session.exec(statement).all()]
