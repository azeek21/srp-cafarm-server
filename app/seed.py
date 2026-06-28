"""Seed the database with sample cattle. Run: uv run python -m app.seed"""

import random
from datetime import date, timedelta

from sqlmodel import Session

from app.animals.models import AnimalType, Gender
from app.animals.repository import AnimalRepository
from app.animals.schemas import AnimalCreate
from app.animals.service import AnimalService
from app.database import engine, init_db
from app.exceptions import ConflictError

BREEDS = [
    "Holstein",
    "Angus",
    "Hereford",
    "Jersey",
    "Charolais",
    "Simmental",
    "Limousin",
    "Brahman",
    "Guernsey",
    "Shorthorn",
]

STATUS_WEIGHTS = {
    "active": 0.8,
    "sold": 0.12,
    "deceased": 0.08,
}

NAMES = [
    "Bella", "Daisy", "Molly", "Rosie", "Maggie", "Buttercup", "Clover",
    "Hazel", "Ginger", "Pepper", "Duke", "Max", "Rocky", "Bruno", "Thor",
    "Luna", "Willow", "Poppy", "Coco", "Honey", "Ruby", "Olive", "Nala",
    "Apollo", "Zeus", "Atlas", "Diesel", "Bandit", "Shadow", "Romeo",
]

# Age buckets weighted so the analytics distribution lands ~25% calf, ~30%
# young, ~45% adult — every band visibly populated.
AGE_BUCKETS = [
    ((30, 330), 0.25),       # calf: < 1 year
    ((366, 2 * 365), 0.30),  # young: 1–2 years
    ((2 * 365 + 60, 10 * 365), 0.45),  # adult: > 2 years
]


def _random_dob() -> date:
    ranges = [r for r, _ in AGE_BUCKETS]
    weights = [w for _, w in AGE_BUCKETS]
    low, high = random.choices(ranges, weights=weights, k=1)[0]
    days = random.randint(low, high)
    return date.today() - timedelta(days=days)


def seed(count: int = 120) -> None:
    init_db()
    statuses = list(STATUS_WEIGHTS.keys())
    weights = list(STATUS_WEIGHTS.values())

    created = 0
    with Session(engine) as session:
        service = AnimalService(AnimalRepository(session))
        for i in range(count):
            tag = f"UK{random.randint(100000, 999999)}{i:05d}"
            payload = AnimalCreate(
                type=AnimalType.CATTLE,
                tag=tag,
                name=random.choice(NAMES) if random.random() < 0.7 else None,
                breed=random.choice(BREEDS),
                gender=random.choice(list(Gender)),
                date_of_birth=_random_dob(),
                status=random.choices(statuses, weights=weights, k=1)[0],
            )
            try:
                service.create(payload)
                created += 1
            except ConflictError:
                continue

    print(f"Seeded {created} animals.")


if __name__ == "__main__":
    seed()
