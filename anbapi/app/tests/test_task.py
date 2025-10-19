import os
from datetime import datetime

import pytest
from faker import Faker
from models import User, Video, VideoStatus
from security import hash_password
from sqlalchemy import select
from workers import tasks

fake = Faker()


def _make_user(db_session, **overrides):
    first = fake.first_name()
    last = fake.last_name()
    username = f"{first.lower()}.{last.lower()}"
    email = fake.unique.email()
    password = fake.password(length=12)
    city = fake.city()
    country = fake.country()
    hashed_pwd = hash_password(password)
    data = {
        "first_name": first,
        "last_name": last,
        "email": email,
        "user_name": username,
        "hashed_password": hashed_pwd,
        "city": city,
        "country": country,
    }
    data.update(overrides)
    u = User(**data)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _make_video(db_session, user, original_url="/tmp/fake.mp4", **overrides):
    v = Video(
        user_id=user.id,
        title="demo",
        original_url=original_url,
        status=VideoStatus.UPLOADED,
        task_id=user.id,
        **overrides,
    )
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)
    return v


class _SubprocessCalls:
    def __init__(self):
        self.run_calls = []
        self.check_output_calls = []

    def fake_run(self, cmd, check=True):
        self.run_calls.append((tuple(cmd), bool(check)))

    def fake_check_output_audio(self, args, stderr=None):
        self.check_output_calls.append(tuple(args))
        return b"0\n"

    def fake_check_output_noaudio(self, args, stderr=None):
        from subprocess import CalledProcessError

        self.check_output_calls.append(tuple(args))
        raise CalledProcessError(returncode=1, cmd=args)


@pytest.fixture()
def patch_sessionlocal(monkeypatch, db_session):
    monkeypatch.setattr(tasks, "SessionLocal", lambda: db_session)


@pytest.fixture()
def patch_config_dirs(monkeypatch, tmp_path):
    processed = tmp_path / "processed"
    assets = tmp_path / "assets"
    processed.mkdir()
    monkeypatch.setattr(tasks.config, "PROCESSED_DIR", str(processed))
    monkeypatch.setattr(tasks.config, "ASSETS_DIR", str(assets))
    monkeypatch.setattr(tasks.config, "INTRO_SECONDS", 1)
    monkeypatch.setattr(tasks.config, "OUTRO_SECONDS", 1)
    return processed, assets


def test_process_video_not_found_returns_not_found(
    patch_sessionlocal, patch_config_dirs, monkeypatch
):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)
    monkeypatch.setattr(tasks.subprocess, "check_output", calls.fake_check_output_audio)

    result = tasks.process_video("999999")
    assert result == "not-found"
    assert calls.run_calls == []


def test_process_video_ok_with_audio(
    patch_sessionlocal, patch_config_dirs, monkeypatch, db_session
):
    processed_dir, assets_dir = patch_config_dirs
    u = _make_user(db_session)
    src_file = os.path.join(os.fspath(processed_dir), "src.mp4")
    open(src_file, "wb").write(b"\x00" * 10)
    v = _make_video(db_session, u, original_url=src_file)

    os.makedirs(assets_dir, exist_ok=True)
    open(os.path.join(assets_dir, "logo.jpg"), "wb").write(b"\x00")

    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)
    monkeypatch.setattr(tasks.subprocess, "check_output", calls.fake_check_output_audio)

    res = tasks.process_video(v.id)
    assert res == "ok"

    v2 = db_session.execute(select(Video).where(Video.id == v.id)).scalar_one()
    assert v2.status == VideoStatus.PROCESSED
    assert v2.processed_url.startswith(os.fspath(processed_dir))
    assert isinstance(v2.processed_at, datetime)


def test_process_video_ok_without_audio(
    patch_sessionlocal, patch_config_dirs, monkeypatch, db_session
):
    processed_dir, _ = patch_config_dirs
    u = _make_user(db_session)
    src_file = os.path.join(os.fspath(processed_dir), "src2.mp4")
    open(src_file, "wb").write(b"\x00" * 10)
    v = _make_video(db_session, u, original_url=src_file)
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)
    monkeypatch.setattr(
        tasks.subprocess, "check_output", calls.fake_check_output_noaudio
    )

    res = tasks.process_video(v.id)
    assert res == "ok"

    v2 = db_session.get(Video, v.id)
    assert v2.status == VideoStatus.PROCESSED
    assert v2.processed_url.startswith(os.fspath(processed_dir))
    assert v2.processed_at is not None


def test_process_video_error_sets_failed(
    patch_sessionlocal, patch_config_dirs, monkeypatch, db_session
):
    processed_dir, _ = patch_config_dirs
    u = _make_user(db_session)
    src_file = os.path.join(os.fspath(processed_dir), "broken.mp4")
    open(src_file, "wb").write(b"\x00")
    v = _make_video(db_session, u, original_url=src_file)

    def _boom(cmd, check=True):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(tasks.subprocess, "run", _boom)
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "check_output", calls.fake_check_output_audio)

    res = tasks.process_video(v.id)
    assert res == "error"

    v2 = db_session.get(Video, v.id)
    assert v2.status == VideoStatus.FAILED
