"""Tier 1 integration tests: soft-delete invariant, conflicts, list query correctness."""

from tests.conftest import make_animal


def _create(client, **overrides) -> dict:
    resp = client.post("/api/animals/", json=make_animal(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---- Soft-delete invariant ---------------------------------------------------


def test_delete_then_get_is_404(client):
    animal = _create(client, tag="DEL-1")
    assert client.delete(f"/api/animals/{animal['id']}").status_code == 204
    assert client.get(f"/api/animals/{animal['id']}").status_code == 404


def test_deleted_absent_from_list(client):
    a = _create(client, tag="LIVE-1")
    b = _create(client, tag="DEAD-1")
    client.delete(f"/api/animals/{b['id']}")
    body = client.get("/api/animals/").json()
    ids = {item["id"] for item in body["items"]}
    assert a["id"] in ids
    assert b["id"] not in ids
    assert body["total"] == 1


def test_deleted_absent_from_analytics(client):
    _create(client, tag="A-1")
    dead = _create(client, tag="A-2")
    client.delete(f"/api/animals/{dead['id']}")
    summary = client.get("/api/analytics/summary?type=cattle").json()
    assert summary["total"] == 1


def test_recreate_same_tag_after_delete(client):
    a = _create(client, tag="REUSE-1")
    client.delete(f"/api/animals/{a['id']}")
    # Partial unique index excludes soft-deleted rows -> tag is reusable.
    resp = client.post("/api/animals/", json=make_animal(tag="REUSE-1"))
    assert resp.status_code == 201, resp.text


def test_delete_twice_is_404(client):
    a = _create(client, tag="DT-1")
    assert client.delete(f"/api/animals/{a['id']}").status_code == 204
    assert client.delete(f"/api/animals/{a['id']}").status_code == 404


# ---- Conflict / duplicate tag ------------------------------------------------


def test_create_duplicate_tag_is_409(client):
    _create(client, tag="DUP-1")
    resp = client.post("/api/animals/", json=make_animal(tag="DUP-1"))
    assert resp.status_code == 409
    assert "detail" in resp.json()


def test_update_tag_collision_is_409(client):
    _create(client, tag="C-1")
    other = _create(client, tag="C-2")
    resp = client.patch(f"/api/animals/{other['id']}", json={"tag": "C-1"})
    assert resp.status_code == 409


def test_update_to_own_tag_is_ok(client):
    a = _create(client, tag="SELF-1", name="Old")
    resp = client.patch(f"/api/animals/{a['id']}", json={"tag": "SELF-1", "name": "New"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "New"


def test_patch_missing_is_404(client):
    resp = client.patch(
        "/api/animals/00000000-0000-0000-0000-000000000000", json={"name": "X"}
    )
    assert resp.status_code == 404


def test_get_missing_is_404(client):
    assert client.get("/api/animals/00000000-0000-0000-0000-000000000000").status_code == 404


# ---- List: filter / search / sort / pagination -------------------------------


def test_total_is_full_filtered_count_not_page_len(client):
    for i in range(5):
        _create(client, tag=f"PG-{i}")
    body = client.get("/api/animals/?page_size=2").json()
    assert len(body["items"]) == 2
    assert body["total"] == 5


def test_pagination_pages_differ(client):
    for i in range(4):
        _create(client, tag=f"PGN-{i}")
    p1 = client.get("/api/animals/?page=1&page_size=2&sort_by=tag&sort_order=asc").json()
    p2 = client.get("/api/animals/?page=2&page_size=2&sort_by=tag&sort_order=asc").json()
    ids1 = {i["id"] for i in p1["items"]}
    ids2 = {i["id"] for i in p2["items"]}
    assert ids1.isdisjoint(ids2)


def test_search_ilike_across_fields_case_insensitive(client):
    _create(client, tag="SR-AAA", name="Daisy", breed="Hereford")
    _create(client, tag="SR-BBB", name="Max", breed="Angus")
    # matches breed, case-insensitive
    body = client.get("/api/animals/?search=hereFORD").json()
    assert body["total"] == 1
    assert body["items"][0]["tag"] == "SR-AAA"
    # matches name
    body = client.get("/api/animals/?search=max").json()
    assert body["total"] == 1


def test_filter_status_gender_breed(client):
    _create(client, tag="F-1", status="active", gender="male", breed="Jersey")
    _create(client, tag="F-2", status="sold", gender="female", breed="Angus")
    assert client.get("/api/animals/?status=sold").json()["total"] == 1
    assert client.get("/api/animals/?gender=male").json()["total"] == 1
    assert client.get("/api/animals/?breed=Jersey").json()["total"] == 1


def test_filter_born_range(client):
    _create(client, tag="B-1", date_of_birth="2020-01-01")
    _create(client, tag="B-2", date_of_birth="2024-01-01")
    body = client.get("/api/animals/?born_after=2023-01-01").json()
    assert body["total"] == 1 and body["items"][0]["tag"] == "B-2"
    body = client.get("/api/animals/?born_before=2021-01-01").json()
    assert body["total"] == 1 and body["items"][0]["tag"] == "B-1"


def test_sort_order(client):
    _create(client, tag="S-A")
    _create(client, tag="S-C")
    _create(client, tag="S-B")
    asc = client.get("/api/animals/?sort_by=tag&sort_order=asc").json()["items"]
    desc = client.get("/api/animals/?sort_by=tag&sort_order=desc").json()["items"]
    assert [i["tag"] for i in asc] == ["S-A", "S-B", "S-C"]
    assert [i["tag"] for i in desc] == ["S-C", "S-B", "S-A"]


def test_invalid_sort_params_rejected(client):
    assert client.get("/api/animals/?sort_by=evil").status_code == 422
    assert client.get("/api/animals/?sort_order=sideways").status_code == 422
    assert client.get("/api/animals/?page_size=999").status_code == 422


# ---- Validation --------------------------------------------------------------


def test_empty_required_fields_rejected(client):
    assert client.post("/api/animals/", json=make_animal(tag="")).status_code == 422
    assert client.post("/api/animals/", json=make_animal(breed="")).status_code == 422
