from achchaosmonkey.db import models


def test_generate_endpoint_persists_clean_file(client, db_session):
    response = client.post(
        "/api/generate",
        json={"num_batches": 1, "entries_per_batch": 5, "chaos_level": "none", "seed": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["num_entries"] == 5
    assert body["num_fraud"] == 0
    assert body["num_miscoded"] == 0

    db_file = db_session.get(models.AchFile, body["file_id"])
    assert db_file is not None
    assert db_file.source == models.SOURCE_GENERATED
    assert len(db_file.batches[0].entries) == 5


def test_generate_endpoint_with_high_chaos_labels_entries(client):
    response = client.post(
        "/api/generate",
        json={"num_batches": 2, "entries_per_batch": 20, "chaos_level": "high", "seed": 11},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["num_fraud"] + body["num_miscoded"] > 0


def test_generate_endpoint_validates_request_bounds(client):
    response = client.post("/api/generate", json={"num_batches": 0})
    assert response.status_code == 422
