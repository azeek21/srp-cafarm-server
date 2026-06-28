"""Tier 1/2: analytics aggregates + age-bucket boundaries via the API."""

from datetime import date, timedelta

from tests.conftest import make_animal


def _create(client, **overrides) -> dict:
    resp = client.post("/api/animals/", json=make_animal(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _dob_years_ago(years: int) -> str:
    """Exact calendar-year-ago DOB -> age == years today."""
    t = date.today()
    return t.replace(year=t.year - years).isoformat()


def _dob_months_ago(months: int) -> str:
    return (date.today() - timedelta(days=months * 30)).isoformat()


def test_empty_db_summary_no_zero_division(client):
    summary = client.get("/api/analytics/summary?type=cattle").json()
    assert summary["total"] == 0
    assert summary["active_total"] == 0
    assert summary["average_age_years"] == 0.0
    assert summary["age_distribution"] == {"calf": 0, "young": 0, "adult": 0}


def test_counts_by_dimensions(client):
    _create(client, tag="AN-1", status="active", gender="male", breed="Angus")
    _create(client, tag="AN-2", status="sold", gender="female", breed="Angus")
    _create(client, tag="AN-3", status="active", gender="female", breed="Jersey")
    s = client.get("/api/analytics/summary?type=cattle").json()
    assert s["total"] == 3
    assert s["active_total"] == 2
    assert s["by_status"] == {"active": 2, "sold": 1}
    assert s["by_gender"] == {"male": 1, "female": 2}
    assert s["by_breed"] == {"Angus": 2, "Jersey": 1}


def test_age_buckets_boundaries(client):
    # calf < 1y ; young 1-2y inclusive ; adult > 2y
    _create(client, tag="AGE-calf", date_of_birth=_dob_months_ago(6))
    _create(client, tag="AGE-1y", date_of_birth=_dob_years_ago(1))
    _create(client, tag="AGE-2y", date_of_birth=_dob_years_ago(2))
    _create(client, tag="AGE-adult", date_of_birth=_dob_years_ago(3))
    dist = client.get("/api/analytics/summary?type=cattle").json()["age_distribution"]
    assert dist == {"calf": 1, "young": 2, "adult": 1}
