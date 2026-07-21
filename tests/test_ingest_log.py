import tempfile
from pathlib import Path
from src.ingest_log import append_ingest_entry, read_ingest_log


def test_append_single_entry():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        append_ingest_entry(
            log_path=str(log_path),
            source_name="LSM.lv Latvija",
            source_tier=1,
            documents_added=5,
            documents_skipped=12,
            status="success",
        )
        text = log_path.read_text(encoding="utf-8")
        assert "LSM.lv Latvija" in text
        assert "5 new" in text
        assert "12 skipped" in text
        assert "success" in text


def test_append_preserves_existing():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        log_path.write_text("# Ingest Log\n\n", encoding="utf-8")
        append_ingest_entry(str(log_path), "LSM", 1, 3, 0, "success")
        append_ingest_entry(str(log_path), "Delfi", 2, 7, 2, "success")
        text = log_path.read_text(encoding="utf-8")
        assert "# Ingest Log" in text
        assert "LSM" in text
        assert "Delfi" in text


def test_append_with_error():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        append_ingest_entry(str(log_path), "LETA", 2, 0, 0, "failure", error="Timeout")
        text = log_path.read_text(encoding="utf-8")
        assert "FAILURE" in text or "failure" in text.lower()
        assert "Timeout" in text


def test_append_twitter_batch():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        append_ingest_entry(
            str(log_path),
            source_name="X/Twitter",
            source_tier=0,
            documents_added=23,
            documents_skipped=45,
            status="success",
            extra="12 politiķi",
        )
        text = log_path.read_text(encoding="utf-8")
        assert "X/Twitter" in text
        assert "12 politiķi" in text


def test_read_ingest_log_last_n():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log-ingest.md"
        for i in range(5):
            append_ingest_entry(str(log_path), f"Source-{i}", 1, i, 0, "success")
        entries = read_ingest_log(str(log_path), last_n=3)
        assert len(entries) == 3
        assert "Source-4" in entries[0]  # most recent first
