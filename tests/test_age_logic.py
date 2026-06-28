"""Tier 2 unit tests: pure age math (no DB)."""

from datetime import date

import pytest

from app.analytics.service import _age_years
from app.animals.schemas import AnimalRead


@pytest.mark.parametrize(
    "dob, today, expected",
    [
        (date(2024, 6, 28), date(2024, 6, 28), 0),  # born today
        (date(2023, 6, 29), date(2024, 6, 28), 0),  # day before 1st birthday
        (date(2023, 6, 28), date(2024, 6, 28), 1),  # on 1st birthday
        (date(2020, 2, 29), date(2024, 2, 28), 3),  # leap-year DOB, before 29th
        (date(2020, 2, 29), date(2024, 3, 1), 4),   # leap-year DOB, after
    ],
)
def test_age_years(dob, today, expected):
    assert _age_years(dob, today) == expected


def test_animal_read_age_years_never_negative():
    # Future DOB (data glitch) must not yield a negative age.
    future = date.today().replace(year=date.today().year + 1)
    read = AnimalRead(
        id="00000000-0000-0000-0000-000000000001",
        type="cattle",
        tag="X",
        name=None,
        breed="Angus",
        gender="female",
        date_of_birth=future,
        status="active",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    assert read.age_years == 0
