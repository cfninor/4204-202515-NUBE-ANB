from datetime import datetime

from services.video import to_iso


def test_to_iso_none():
    assert to_iso(None) is None


def test_to_iso():
    naive = datetime(2025, 1, 2, 3, 4, 5)
    s = to_iso(naive)
    assert s.endswith("Z")
    assert "T03:04:05" in s
