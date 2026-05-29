from backend.app.workers.upload_pipeline import get_pipeline_stages


def test_worker_pipeline_stages():
    stages = get_pipeline_stages()
    assert "pending" in stages
    assert "preprocessing" in stages
    assert "transcribing" in stages
    assert "completed" in stages
