from achchaosmonkey.db import models


def test_validate_requires_existing_scope(client):
    response = client.post("/api/validate", json={"file_id": 999999})
    assert response.status_code == 404


def test_generate_then_validate_persists_results(client, db_session):
    gen_response = client.post(
        "/api/generate",
        json={"num_batches": 1, "entries_per_batch": 15, "chaos_level": "medium", "seed": 77},
    )
    file_id = gen_response.json()["file_id"]

    val_response = client.post("/api/validate", json={"file_id": file_id})
    assert val_response.status_code == 200
    body = val_response.json()
    assert body["num_entries"] == 15
    assert 0.0 <= body["evaluation"]["precision"] <= 1.0
    assert 0.0 <= body["evaluation"]["recall"] <= 1.0

    run = db_session.get(models.ValidationRun, body["run_id"])
    assert run is not None
    assert len(run.results) == 15


def test_validate_clean_file_has_no_structural_failures(client):
    gen_response = client.post(
        "/api/generate",
        json={"num_batches": 1, "entries_per_batch": 10, "chaos_level": "none", "seed": 88},
    )
    file_id = gen_response.json()["file_id"]

    val_response = client.post("/api/validate", json={"file_id": file_id})
    body = val_response.json()
    # chaos=none means no structural corruption was injected, so nothing should fail structural rules.
    assert body["evaluation"]["false_negatives"] == 0
