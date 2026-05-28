import io


def test_upload_requires_file(client):
    response = client.post("/api/upload/")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False


def test_upload_accepts_file(client):
    data = {"file": (io.BytesIO(b"dummy"), "sample.wav")}
    response = client.post("/api/upload/", data=data, content_type="multipart/form-data")
    assert response.status_code == 202
    payload = response.get_json()
    assert payload["success"] is True
    assert "session_id" in payload["data"]
