import os
import subprocess
from pathlib import Path

import pytest
from faker import Faker
from models import User, Video, VideoStatus
from security import hash_password
from workers import tasks

fake = Faker()


class FakeStorage:
    def __init__(self, base):
        self.base = base
        self.saved = {}

    def download_to_path(self, key, path):
        Path(path).write_bytes(b"00")

    def save(self, key, f):
        data = f.read()
        self.saved[key] = data

    def url(self, key):
        return f"http://fake/{key}"


@pytest.fixture()
def patch_storage(monkeypatch, tmp_path):
    storage = FakeStorage(tmp_path)
    monkeypatch.setattr(tasks, "get_storage", lambda: storage)
    return storage


@pytest.fixture()
def patch_sessionlocal(monkeypatch, db_session):
    monkeypatch.setattr(tasks, "SessionLocal", lambda: db_session)


@pytest.fixture()
def patch_config(monkeypatch, tmp_path):
    processed = tmp_path / "processed"
    assets = tmp_path / "assets"
    processed.mkdir()
    assets.mkdir()
    (assets / "watermark.png").write_bytes(b"wm")

    monkeypatch.setattr(tasks.config, "PROCESSED_DIR", os.fspath(processed))
    monkeypatch.setattr(tasks.config, "ASSETS_DIR", os.fspath(assets))
    monkeypatch.setattr(tasks.config, "INTRO_SECONDS", 1)
    monkeypatch.setattr(tasks.config, "OUTRO_SECONDS", 1)
    return processed, assets


def _make_user(db_session, **extra):
    u = User(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.unique.email(),
        user_name=fake.user_name(),
        hashed_password=hash_password(fake.password()),
        city=fake.city(),
        country=fake.country(),
        **extra,
    )
    db_session.add(u)
    db_session.commit()
    return u


def _make_video(db_session, user, **extra):
    defaults = {
        "user_id": user.id,
        "title": "t",
        "original_url": "/tmp/fake.mp4",
        "status": VideoStatus.UPLOADED,
        "task_id": user.id,
    }
    defaults.update(extra)
    v = Video(**defaults)
    db_session.add(v)
    db_session.commit()
    return v


def test_run_ok(monkeypatch):
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd)

    monkeypatch.setattr(tasks.subprocess, "run", fake)
    tasks._run(["echo"])
    assert calls and "echo" in calls[0]


def test_run_raises(monkeypatch):
    def boom(cmd, **kw):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr=b"fail-msg")

    monkeypatch.setattr(tasks.subprocess, "run", boom)

    with pytest.raises(subprocess.CalledProcessError):
        tasks._run(["ffmpeg"])


def test_run_handles_file_not_found(monkeypatch):
    def boom(cmd, **kw):
        raise FileNotFoundError("ffmpeg missing")

    monkeypatch.setattr(tasks.subprocess, "run", boom)

    with pytest.raises(FileNotFoundError):
        tasks._run(["ffmpeg"])


def test_ensure_file_creates(tmp_path):
    p = tmp_path / "sub" / "file.txt"
    tasks._ensure_file(os.fspath(p))
    assert p.exists()


def test_build_filter_ok():
    v = tasks._build_filter(1, 1, 30)
    assert "concat" in v
    assert "trim=0:30" in v


def test_render_simple_invokes_ffmpeg(monkeypatch, tmp_path):
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd)

    monkeypatch.setattr(tasks, "_run", fake)

    src = tmp_path / "s.mp4"
    out = tmp_path / "o.mp4"
    src.write_bytes(b"00")

    tasks._render_simple(str(src), str(out))

    cmd = calls[0]
    assert tasks.FFMPEG in cmd
    assert "-vf" in cmd
    assert "superfast" in cmd


def test_render_final_video_invokes_ffmpeg(monkeypatch, tmp_path, patch_config):
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd)

    monkeypatch.setattr(tasks, "_run", fake)
    monkeypatch.setattr(tasks, "get_duration", lambda x: 40.0)

    processed, assets = patch_config
    src = processed / "a.mp4"
    logo = assets / "logo.jpg"
    src.write_bytes(b"00")
    logo.write_bytes(b"11")

    out = processed / "out.mp4"

    tasks._render_final_video(str(src), str(logo), str(out), 1, 1)

    cmd = calls[0]
    assert tasks.FFMPEG in cmd
    assert "-filter_complex" in cmd
    assert "superfast" in cmd


def test_process_video_not_found(monkeypatch, patch_sessionlocal, patch_storage):
    monkeypatch.setattr(tasks, "get_duration", lambda x: 30)
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: None)
    res = tasks.process_video("9999")
    assert res == "not-found"


def test_process_video_short(
    monkeypatch, patch_sessionlocal, patch_config, patch_storage, db_session
):
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: None)
    monkeypatch.setattr(tasks, "get_duration", lambda x: 10)

    processed, _ = patch_config
    user = _make_user(db_session)
    src = processed / "x.mp4"
    src.write_bytes(b"00")

    v = _make_video(db_session, user, original_url=str(src))

    res = tasks.process_video(str(v.id))
    assert res == "error"

    vv = db_session.get(Video, v.id)
    assert vv.status == VideoStatus.FAILED


def test_process_video_long(
    monkeypatch, patch_sessionlocal, patch_config, patch_storage, db_session
):
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: None)
    monkeypatch.setattr(tasks, "get_duration", lambda x: 80)

    processed, _ = patch_config
    user = _make_user(db_session)
    src = processed / "x.mp4"
    src.write_bytes(b"00")

    v = _make_video(db_session, user, original_url=str(src))

    res = tasks.process_video(str(v.id))
    assert res == "error"

    vv = db_session.get(Video, v.id)
    assert vv.status == VideoStatus.FAILED


def test_process_video_cortinillas_invalid(
    monkeypatch, patch_sessionlocal, patch_storage, db_session, tmp_path
):
    monkeypatch.setattr(tasks, "get_duration", lambda x: 30)
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: None)

    user = _make_user(db_session)

    monkeypatch.setattr(tasks.config, "INTRO_SECONDS", 4)
    monkeypatch.setattr(tasks.config, "OUTRO_SECONDS", 3)

    src = tmp_path / "a.mp4"
    src.write_bytes(b"00")

    v = _make_video(db_session, user, original_url=str(src))

    res = tasks.process_video(str(v.id))
    assert res == "error"

    vv = db_session.get(Video, v.id)
    assert vv.status == VideoStatus.FAILED


def test_process_video_ok(
    monkeypatch, patch_sessionlocal, patch_config, patch_storage, db_session
):
    processed, assets = patch_config

    monkeypatch.setattr(tasks, "get_duration", lambda x: 40)
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: None)

    user = _make_user(db_session)

    src = processed / "v.mp4"
    logo = assets / "logo.jpg"
    src.write_bytes(b"00")
    logo.write_bytes(b"11")

    v = _make_video(db_session, user, original_url=str(src))

    res = tasks.process_video(str(v.id))
    assert res == "ok"

    vv = db_session.get(Video, v.id)
    assert vv.status == VideoStatus.PROCESSED
    assert vv.processed_url.endswith(".mp4")
    assert vv.processed_at is not None


def test_process_video_logs(
    monkeypatch, patch_sessionlocal, patch_config, patch_storage, db_session, caplog
):
    processed, assets = patch_config

    monkeypatch.setattr(tasks, "get_duration", lambda x: 40)
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: None)

    user = _make_user(db_session)

    src = processed / "lg.mp4"
    logo = assets / "logo.jpg"
    src.write_bytes(b"00")
    logo.write_bytes(b"11")

    v = _make_video(db_session, user, original_url=str(src))

    with caplog.at_level("INFO"):
        res = tasks.process_video(str(v.id))

    assert res == "ok"
    assert any("procesado correctamente" in m for m in caplog.messages)


def test_get_duration_ok(monkeypatch, tmp_path):
    class Result:
        stdout = b"12.34"

    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: Result())

    dur = tasks.get_duration("any.mp4")
    assert dur == 12.34


def test_get_duration_error(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("ffprobe fail")

    monkeypatch.setattr(tasks.subprocess, "run", boom)

    dur = tasks.get_duration("x.mp4")
    assert dur == 0.0


def test_process_video_processed_url_not_callable(
    monkeypatch, patch_sessionlocal, patch_config, patch_storage, db_session
):
    processed, assets = patch_config
    monkeypatch.setattr(patch_storage, "url", "NOT_CALLABLE")

    monkeypatch.setattr(tasks, "get_duration", lambda x: 40)
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: None)

    user = _make_user(db_session)
    src = processed / "v2.mp4"
    logo = assets / "logo.jpg"
    src.write_bytes(b"00")
    logo.write_bytes(b"11")

    v = _make_video(db_session, user, original_url=str(src))

    res = tasks.process_video(str(v.id))
    assert res == "ok"

    vv = db_session.get(Video, v.id)
    assert vv.processed_url.endswith(".mp4")


def test_process_video_storage_save_fails(
    monkeypatch, patch_sessionlocal, patch_config, patch_storage, db_session
):
    processed, assets = patch_config

    monkeypatch.setattr(tasks, "get_duration", lambda x: 40)
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: None)

    def boom(*a, **kw):
        raise RuntimeError("save fail")

    monkeypatch.setattr(patch_storage, "save", boom)

    user = _make_user(db_session)
    src = processed / "x2.mp4"
    logo = assets / "logo.jpg"
    src.write_bytes(b"00")
    logo.write_bytes(b"11")

    v = _make_video(db_session, user, original_url=str(src))

    res = tasks.process_video(str(v.id))
    assert res == "error"

    vv = db_session.get(Video, v.id)
    assert vv.status == VideoStatus.FAILED
