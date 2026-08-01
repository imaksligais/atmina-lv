"""Tests for src/confidence_drift.py — confidence inflation detection."""

import sqlite3
import tempfile
import os
import pytest
from datetime import datetime, timedelta
from src.confidence_drift import check_confidence_drift, print_drift_report


@pytest.fixture
def drift_db():
    """Create a temp DB with claims table and test data."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.execute("""
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY,
            topic TEXT,
            confidence REAL,
            source_url TEXT,
            stated_at TEXT,
            claim_type TEXT NOT NULL DEFAULT 'position'
        )
    """)

    now = datetime.now()
    # First half: 5 days ago, lower confidence
    first_half_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")
    # Second half: 1 day ago, higher confidence
    second_half_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    # Topic with drift: confidence rises from ~0.6 to ~0.85, same source
    for i in range(5):
        db.execute(
            "INSERT INTO claims (topic, confidence, source_url, stated_at) VALUES (?,?,?,?)",
            ("NATO", 0.55 + i * 0.02, "https://source-a.lv", first_half_date),
        )
    for i in range(5):
        db.execute(
            "INSERT INTO claims (topic, confidence, source_url, stated_at) VALUES (?,?,?,?)",
            ("NATO", 0.80 + i * 0.02, "https://source-a.lv", second_half_date),
        )

    # Topic without drift: confidence stays stable
    for i in range(4):
        db.execute(
            "INSERT INTO claims (topic, confidence, source_url, stated_at) VALUES (?,?,?,?)",
            ("Budžets", 0.70, f"https://source-{i}.lv", first_half_date),
        )
    for i in range(4):
        db.execute(
            "INSERT INTO claims (topic, confidence, source_url, stated_at) VALUES (?,?,?,?)",
            ("Budžets", 0.72, f"https://source-{i+10}.lv", second_half_date),
        )

    db.commit()
    db.close()
    yield path
    os.unlink(path)


@pytest.fixture
def empty_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.execute("""
        CREATE TABLE claims (
            id INTEGER PRIMARY KEY,
            topic TEXT,
            confidence REAL,
            source_url TEXT,
            stated_at TEXT,
            claim_type TEXT NOT NULL DEFAULT 'position'
        )
    """)
    db.commit()
    db.close()
    yield path
    os.unlink(path)


class TestCheckConfidenceDrift:
    def test_detects_drift(self, drift_db):
        alerts = check_confidence_drift(db_path=drift_db, days=7, threshold=0.15)
        assert len(alerts) >= 1
        nato_alert = next(a for a in alerts if a["topic"] == "NATO")
        assert nato_alert["drift"] > 0.15
        assert nato_alert["source_growth"] <= 1

    def test_no_drift_for_stable_topic(self, drift_db):
        alerts = check_confidence_drift(db_path=drift_db, days=7, threshold=0.15)
        budget_alerts = [a for a in alerts if a["topic"] == "Budžets"]
        assert len(budget_alerts) == 0

    def test_empty_db_returns_no_alerts(self, empty_db):
        alerts = check_confidence_drift(db_path=empty_db, days=7)
        assert alerts == []

    def test_high_threshold_no_alerts(self, drift_db):
        alerts = check_confidence_drift(db_path=drift_db, days=7, threshold=0.99)
        assert alerts == []

    def test_alerts_sorted_by_drift_descending(self, drift_db):
        alerts = check_confidence_drift(db_path=drift_db, days=7, threshold=0.01)
        if len(alerts) > 1:
            for i in range(len(alerts) - 1):
                assert alerts[i]["drift"] >= alerts[i + 1]["drift"]


class TestPrintDriftReport:
    def test_no_alerts(self, capsys):
        print_drift_report([])
        captured = capsys.readouterr()
        assert "Nav konstatēta" in captured.out

    def test_with_alerts(self, capsys):
        alerts = [{
            "topic": "NATO",
            "drift": 0.25,
            "first_half_avg": 0.6,
            "second_half_avg": 0.85,
            "first_half_claims": 5,
            "second_half_claims": 5,
            "source_growth": 0,
        }]
        print_drift_report(alerts)
        captured = capsys.readouterr()
        assert "NATO" in captured.out
        assert "1 tēmas" in captured.out
