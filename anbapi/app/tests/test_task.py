import os
import subprocess

import pytest
from faker import Faker
from models import User, Video, VideoStatus
from security import hash_password
from workers import tasks

fake = Faker()


class _SubprocessCalls:
    def __init__(self):
        self.run_calls = []

    def fake_run(self, cmd, stdout=None, stderr=None, check=None):
        self.run_calls.append(cmd)


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
    db_session.refresh(u)
    return u


def _make_video(db_session, user, **extra):
    defaults = {
        "user_id": user.id,
        "title": "test",
        "original_url": "/tmp/fake.mp4",
        "status": VideoStatus.UPLOADED,
        "task_id": user.id,
    }

    defaults.update(extra)
    v = Video(**defaults)
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v


@pytest.fixture()
def patch_sessionlocal(monkeypatch, db_session):
    monkeypatch.setattr(tasks, "SessionLocal", lambda: db_session)


@pytest.fixture()
def patch_config(monkeypatch, tmp_path):
    processed = tmp_path / "processed"
    assets = tmp_path / "assets"
    processed.mkdir()
    assets.mkdir()
    monkeypatch.setattr(tasks.config, "PROCESSED_DIR", os.fspath(processed))
    monkeypatch.setattr(tasks.config, "ASSETS_DIR", os.fspath(assets))
    monkeypatch.setattr(tasks.config, "INTRO_SECONDS", 1)
    monkeypatch.setattr(tasks.config, "OUTRO_SECONDS", 1)
    return processed, assets


def test_run_ok(monkeypatch):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)
    tasks._run(["echo", "hi"])
    assert calls.run_calls and "echo" in calls.run_calls[0]


def test_run_raises(monkeypatch):
    def boom(cmd, **kw):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr=b"fail")

    monkeypatch.setattr(tasks.subprocess, "run", boom)
    with pytest.raises(subprocess.CalledProcessError):
        tasks._run(["ffmpeg"])


def test_ensure_file_creates(tmp_path):
    p = tmp_path / "sub" / "file.txt"
    tasks._ensure_file(os.fspath(p))
    assert p.exists()


def test_build_filter_contains_expected():
    vf = tasks._build_filter(1.0, 1.0, 33.0)
    assert "concat" in vf and "trim=0:33.0" in vf


def test_render_final_video_invokes_ffmpeg(monkeypatch, tmp_path):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks, "_run", calls.fake_run)
    src = tmp_path / "src.mp4"
    logo = tmp_path / "logo.jpg"
    out = tmp_path / "out.mp4"
    src.write_bytes(b"00")
    logo.write_bytes(b"11")
    tasks._render_final_video(str(src), str(logo), str(out), 1, 1)
    cmd = calls.run_calls[0]
    assert tasks.FFMPEG in cmd and "-filter_complex" in cmd
    assert "-preset" in cmd and "ultrafast" in cmd
    assert out.exists() is False or isinstance(cmd, list)


def test_render_simple_invokes_ffmpeg(monkeypatch, tmp_path):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks, "_run", calls.fake_run)
    src = tmp_path / "src.mp4"
    out = tmp_path / "out.mp4"
    src.write_bytes(b"00")
    tasks._render_simple(str(src), str(out))
    cmd = calls.run_calls[0]
    assert tasks.FFMPEG in cmd and "-vf" in cmd
    assert "-preset" in cmd and "ultrafast" in cmd


def test_process_video_not_found(monkeypatch, patch_sessionlocal):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)
    result = tasks.process_video("9999")
    assert result == "not-found"


def test_process_video_ok_with_logo(
    monkeypatch, patch_sessionlocal, patch_config, db_session
):
    processed, assets = patch_config
    user = _make_user(db_session)
    src = processed / "input.mp4"
    logo = assets / "logo.jpg"
    src.write_bytes(b"00")
    logo.write_bytes(b"11")
    vid = _make_video(db_session, user, original_url=str(src))
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)
    res = tasks.process_video(str(vid.id))
    assert res == "ok"
    v = db_session.get(Video, vid.id)
    assert v.status == VideoStatus.PROCESSED
    assert v.processed_at and v.processed_url
    assert tasks.FFMPEG in calls.run_calls[0]


def test_process_video_ok_without_logo(
    monkeypatch, patch_sessionlocal, patch_config, db_session
):
    processed, assets = patch_config
    user = _make_user(db_session)
    src = processed / "no_logo.mp4"
    src.write_bytes(b"00")
    (assets / "logo.jpg").unlink(missing_ok=True)
    vid = _make_video(db_session, user, original_url=str(src))
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)
    res = tasks.process_video(str(vid.id))
    assert res == "ok"
    v = db_session.get(Video, vid.id)
    assert v.status == VideoStatus.PROCESSED
    assert v.processed_url.endswith(".mp4")


def test_process_video_sets_failed(
    monkeypatch, patch_sessionlocal, patch_config, db_session
):
    processed, _ = patch_config
    user = _make_user(db_session)
    src = processed / "broken.mp4"
    src.write_bytes(b"00")
    vid = _make_video(db_session, user, original_url=str(src))

    def boom(cmd, **kw):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(tasks.subprocess, "run", boom)
    res = tasks.process_video(str(vid.id))
    v = db_session.get(Video, vid.id)
    assert res == "error"
    assert v.status == VideoStatus.FAILED


def test_run_handles_file_not_found(monkeypatch):
    def _boom(cmd, **kw):
        raise FileNotFoundError("missing ffmpeg")

    monkeypatch.setattr(tasks.subprocess, "run", _boom)
    with pytest.raises(FileNotFoundError):
        tasks._run(["ffmpeg"])


def test_process_video_logs_info(
    monkeypatch, patch_sessionlocal, patch_config, db_session, caplog
):
    processed, assets = patch_config
    user = _make_user(db_session)
    src = processed / "ok_log.mp4"
    logo = assets / "logo.jpg"
    src.write_bytes(b"00")
    logo.write_bytes(b"11")
    vid = _make_video(db_session, user, original_url=str(src))
    monkeypatch.setattr(tasks.subprocess, "run", lambda *a, **kw: None)

    with caplog.at_level("INFO"):
        res = tasks.process_video(str(vid.id))
    assert res == "ok"
    assert any("procesado correctamente" in m for m in caplog.messages)
