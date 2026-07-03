import pytest
from httpx import ASGITransport, AsyncClient

from achchaosmonkey.api.deps import get_db
from achchaosmonkey.main import app


@pytest.mark.asyncio
async def test_full_generate_validate_export_reimport_cycle(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            gen_resp = await ac.post(
                "/api/generate",
                json={"num_batches": 2, "entries_per_batch": 12, "chaos_level": "medium", "seed": 2026},
            )
            assert gen_resp.status_code == 200
            gen_body = gen_resp.json()
            file_id = gen_body["file_id"]
            assert gen_body["num_entries"] == 24

            val_resp = await ac.post("/api/validate", json={"file_id": file_id})
            assert val_resp.status_code == 200
            val_body = val_resp.json()
            assert val_body["num_entries"] == 24
            assert 0.0 <= val_body["evaluation"]["recall"] <= 1.0

            export_resp = await ac.get(f"/api/export/{file_id}", params={"format": "nacha"})
            assert export_resp.status_code == 200
            nacha_lines = export_resp.text.strip("\n").split("\n")
            assert len(nacha_lines) % 10 == 0

            import_resp = await ac.post(
                "/api/import", files={"file": ("reimported.ach", export_resp.content, "text/plain")}
            )
            assert import_resp.status_code == 200
            import_body = import_resp.json()
            assert import_body["num_entries"] == 24

            reval_resp = await ac.post("/api/validate", json={"file_id": import_body["file_id"]})
            assert reval_resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_csv_export_reimport_preserves_ground_truth(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            gen_resp = await ac.post(
                "/api/generate",
                json={"num_batches": 1, "entries_per_batch": 20, "chaos_level": "high", "seed": 4242},
            )
            gen_body = gen_resp.json()

            export_resp = await ac.get(f"/api/export/{gen_body['file_id']}", params={"format": "csv"})
            import_resp = await ac.post(
                "/api/import", files={"file": ("reimported.csv", export_resp.content, "text/csv")}
            )
            import_body = import_resp.json()

            assert import_body["num_entries"] == gen_body["num_entries"]
    finally:
        app.dependency_overrides.clear()
