from datetime import UTC, datetime
from uuid import UUID

from app.animals.models import Animal, AnimalStatus
from app.animals.repository import AnimalRepository
from app.animals.schemas import AnimalCreate, AnimalListParams, AnimalUpdate
from app.exceptions import ConflictError, NotFoundError


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AnimalService:
    """Business rules for animals. HTTP-agnostic: raises domain exceptions."""

    def __init__(self, repo: AnimalRepository) -> None:
        self.repo = repo

    def create(self, data: AnimalCreate) -> Animal:
        if self.repo.get_by_tag(data.type, data.tag) is not None:
            raise ConflictError(
                f"An animal with tag '{data.tag}' already exists for {data.type.value}."
            )
        animal = Animal(**data.model_dump())
        # Initial non-active status counts as the first transition.
        if animal.status != AnimalStatus.ACTIVE:
            animal.status_changed_at = _utcnow()
        return self.repo.add(animal)

    def get(self, animal_id: UUID) -> Animal:
        animal = self.repo.get(animal_id)
        if animal is None:
            raise NotFoundError(f"Animal {animal_id} not found.")
        return animal

    def list(self, params: AnimalListParams) -> tuple[list[Animal], int]:
        return self.repo.list(params)

    def update(self, animal_id: UUID, data: AnimalUpdate) -> Animal:
        animal = self.get(animal_id)
        changes = data.model_dump(exclude_unset=True)

        new_tag = changes.get("tag")
        if new_tag is not None and new_tag != animal.tag:
            existing = self.repo.get_by_tag(animal.type, new_tag)
            if existing is not None and existing.id != animal.id:
                raise ConflictError(
                    f"An animal with tag '{new_tag}' already exists for {animal.type.value}."
                )

        new_status = changes.get("status")
        status_changed = new_status is not None and new_status != animal.status

        for key, value in changes.items():
            setattr(animal, key, value)
        if status_changed:
            animal.status_changed_at = _utcnow()
        animal.updated_at = _utcnow()
        return self.repo.save(animal)

    def delete(self, animal_id: UUID) -> None:
        animal = self.get(animal_id)
        self.repo.soft_delete(animal)
