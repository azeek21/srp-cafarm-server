"""Tests for status_changed_at stamping and the note field."""

from tests.conftest import make_animal


def _create(client, **overrides) -> dict:
    resp = client.post("/api/animals/", json=make_animal(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---- status_changed_at -------------------------------------------------------


def test_create_active_has_null_status_changed_at(client):
    animal = _create(client, tag="ST-1", status="active")
    assert animal["status_changed_at"] is None


def test_create_non_active_stamps_status_changed_at(client):
    animal = _create(client, tag="ST-2", status="sold")
    assert animal["status_changed_at"] is not None


def test_patch_status_change_stamps(client):
    animal = _create(client, tag="ST-3", status="active")
    assert animal["status_changed_at"] is None
    resp = client.patch(f"/api/animals/{animal['id']}", json={"status": "deceased"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status_changed_at"] is not None


def test_patch_without_status_does_not_stamp(client):
    animal = _create(client, tag="ST-4", status="active")
    resp = client.patch(f"/api/animals/{animal['id']}", json={"name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["status_changed_at"] is None


def test_patch_same_status_does_not_restamp(client):
    animal = _create(client, tag="ST-5", status="sold")
    first = animal["status_changed_at"]
    assert first is not None
    resp = client.patch(f"/api/animals/{animal['id']}", json={"status": "sold"})
    assert resp.status_code == 200
    assert resp.json()["status_changed_at"] == first


# ---- note --------------------------------------------------------------------


def test_create_with_note(client):
    animal = _create(client, tag="NOTE-1", note="Limping on left hind leg")
    assert animal["note"] == "Limping on left hind leg"


def test_note_defaults_null(client):
    animal = _create(client, tag="NOTE-2")
    assert animal["note"] is None


def test_patch_note(client):
    animal = _create(client, tag="NOTE-3")
    resp = client.patch(f"/api/animals/{animal['id']}", json={"note": "Vaccinated"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["note"] == "Vaccinated"
