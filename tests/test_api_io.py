import io


def test_export_unknown_file_404(client):
    response = client.get("/api/export/999999", params={"format": "nacha"})
    assert response.status_code == 404


def test_generate_export_import_nacha_round_trip(client):
    gen = client.post(
        "/api/generate", json={"num_batches": 1, "entries_per_batch": 5, "chaos_level": "none", "seed": 1}
    ).json()

    export_resp = client.get(f"/api/export/{gen['file_id']}", params={"format": "nacha"})
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"].startswith("text/plain")

    import_resp = client.post(
        "/api/import", files={"file": ("roundtrip.ach", export_resp.content, "text/plain")}
    )
    assert import_resp.status_code == 200
    body = import_resp.json()
    assert body["num_entries"] == 5


def test_generate_export_import_csv_round_trip(client):
    gen = client.post(
        "/api/generate", json={"num_batches": 1, "entries_per_batch": 5, "chaos_level": "medium", "seed": 2}
    ).json()

    export_resp = client.get(f"/api/export/{gen['file_id']}", params={"format": "csv"})
    assert export_resp.status_code == 200

    import_resp = client.post("/api/import", files={"file": ("roundtrip.csv", export_resp.content, "text/csv")})
    assert import_resp.status_code == 200
    assert import_resp.json()["num_entries"] == 5


def test_generate_export_import_xlsx_round_trip(client):
    gen = client.post(
        "/api/generate", json={"num_batches": 1, "entries_per_batch": 5, "chaos_level": "medium", "seed": 3}
    ).json()

    export_resp = client.get(f"/api/export/{gen['file_id']}", params={"format": "xlsx"})
    assert export_resp.status_code == 200

    import_resp = client.post(
        "/api/import",
        files={
            "file": (
                "roundtrip.xlsx",
                io.BytesIO(export_resp.content),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["num_entries"] == 5


def test_import_rejects_unsupported_extension(client):
    response = client.post("/api/import", files={"file": ("data.json", b"{}", "application/json")})
    assert response.status_code == 400


def test_export_rejects_unsupported_format(client):
    gen = client.post(
        "/api/generate", json={"num_batches": 1, "entries_per_batch": 2, "chaos_level": "none", "seed": 4}
    ).json()
    response = client.get(f"/api/export/{gen['file_id']}", params={"format": "pdf"})
    assert response.status_code == 400
