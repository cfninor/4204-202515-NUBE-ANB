import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from faker import Faker
from models import User, Video, VideoStatus
from security import hash_password
from sqlalchemy import select
from workers import tasks

fake = Faker()


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


@pytest.fixture()
def patch_sessionlocal(monkeypatch, db_session):
    monkeypatch.setattr(tasks, "SessionLocal", lambda: db_session)


@pytest.fixture()
def patch_config_dirs(monkeypatch, tmp_path):
    processed = tmp_path / "processed"
    assets = tmp_path / "assets"
    processed.mkdir()
    assets.mkdir()

    monkeypatch.setattr(tasks.config, "PROCESSED_DIR", os.fspath(processed))
    monkeypatch.setattr(tasks.config, "ASSETS_DIR", os.fspath(assets))
    monkeypatch.setattr(tasks.config, "INTRO_SECONDS", 1)
    monkeypatch.setattr(tasks.config, "OUTRO_SECONDS", 1)
    return processed, assets


def test_run_calls_subprocess(monkeypatch):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)
    tasks._run(["echo", "hello"])
    assert calls.run_calls and calls.run_calls[0][0] == ("echo", "hello")


def test_has_audio_stream_true(monkeypatch):
    calls = _SubprocessCalls()

    def _fake_probe(args, stderr=None):
        calls.check_output_calls.append(tuple(args))
        return b"0\n"

    monkeypatch.setattr(tasks.subprocess, "check_output", _fake_probe)
    result = subprocess.check_output(
        [
            tasks.FFPROBE,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            "/tmp/file.mp4",
        ],
        stderr=subprocess.STDOUT,
    )
    assert result.strip() == b"0"
    assert calls.check_output_calls and calls.check_output_calls[0][0] == tasks.FFPROBE


def test_has_audio_stream_false(monkeypatch):
    calls = _SubprocessCalls()

    def _fake_probe(args, stderr=None):
        from subprocess import CalledProcessError

        calls.check_output_calls.append(tuple(args))
        raise CalledProcessError(returncode=1, cmd=args)

    monkeypatch.setattr(tasks.subprocess, "check_output", _fake_probe)
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_output(
            [
                tasks.FFPROBE,
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                "/tmp/file.mp4",
            ],
            stderr=subprocess.STDOUT,
        )
    assert calls.check_output_calls and calls.check_output_calls[0][0] == tasks.FFPROBE


def test_x264_video_args_and_fast_flag():
    args = tasks._x264_args()
    assert "-c:v" in args and "libx264" in args
    assert "-movflags" in args and tasks.FAST in args
    assert "-r" in args and "30" in args
    assert "-fps_mode" in args and "cfr" in args
    assert "-preset" in args and "veryfast" in args
    assert "-crf" in args and "23" in args
    assert "-pix_fmt" in args and "yuv420p" in args


def test_build_vf_main():
    vf = tasks._build_vf_main()
    assert "scale=w=1280:h=720" in vf
    assert "force_original_aspect_ratio=decrease" in vf
    assert "pad=1280:720" in vf
    assert "format=rgba" in vf


def test_render_main_with_logo(monkeypatch, tmp_path):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks, "_run", calls.fake_run)
    src = tmp_path / "src.mp4"
    logo = tmp_path / "logo.jpg"
    out = tmp_path / "out.mp4"
    src.write_bytes(b"\x00" * 10)
    logo.write_bytes(b"\x00")
    tasks._render_main(os.fspath(src), 5.0, os.fspath(logo), os.fspath(out))
    assert calls.run_calls, "No llamó a ffmpeg"
    cmd, _ = calls.run_calls[0]
    assert cmd[0] == tasks.FFMPEG
    assert "-i" in cmd and os.fspath(src) in cmd
    assert "-i" in cmd and os.fspath(logo) in cmd
    assert any("overlay=" in c for c in cmd)
    assert "-an" in cmd


def test_render_main_without_logo(monkeypatch, tmp_path):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks, "_run", calls.fake_run)
    src = tmp_path / "src.mp4"
    out = tmp_path / "out.mp4"
    src.write_bytes(b"\x00" * 10)
    tasks._render_main(os.fspath(src), 7.5, None, os.fspath(out))
    cmd, _ = calls.run_calls[0]
    assert cmd[0] == tasks.FFMPEG
    assert "-vf" in cmd
    assert "-an" in cmd


def test_render_color(monkeypatch, tmp_path):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks, "_run", calls.fake_run)
    out = tmp_path / "color.mp4"
    tasks._render_color(2.0, os.fspath(out))
    cmd, _ = calls.run_calls[0]
    assert "-f" in cmd and "lavfi" in cmd
    assert "-i" in cmd and tasks.COLOR in cmd
    assert "-an" in cmd


def test_render_logo(monkeypatch, tmp_path):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks, "_run", calls.fake_run)
    logo = tmp_path / "logo.jpg"
    out = tmp_path / "logo_clip.mp4"
    logo.write_bytes(b"\x00")
    tasks._render_logo(3.0, os.fspath(logo), os.fspath(out))
    cmd, _ = calls.run_calls[0]
    assert "-loop" in cmd
    assert any("overlay=" in c for c in cmd)
    assert "-an" in cmd


def test_render_stub(monkeypatch, tmp_path):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks, "_run", calls.fake_run)
    out = tmp_path / "stub.mp4"
    tasks._render_stub(os.fspath(out))
    cmd, _ = calls.run_calls[0]
    assert "-t" in cmd and "0.033" in cmd
    assert "-an" in cmd


def test_concat_segments(monkeypatch, tmp_path):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks, "_run", calls.fake_run)
    intro = tmp_path / "i.mp4"
    main_ = tmp_path / "m.mp4"
    outro = tmp_path / "o.mp4"
    dest = tmp_path / "dest.mp4"
    for f in (intro, main_, outro):
        f.write_bytes(b"\x00")
    tasks._concat_segments(
        os.fspath(intro), os.fspath(main_), os.fspath(outro), os.fspath(dest)
    )
    cmd, _ = calls.run_calls[0]
    assert any("concat=n=3:v=1:a=0" in c for c in cmd)


def test_process_video_not_found_returns_not_found(
    patch_sessionlocal, patch_config_dirs, monkeypatch
):
    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)
    result = tasks.process_video("999999")
    assert result == "not-found"
    assert calls.run_calls == []


def test_process_video_ok_with_audio_and_logo(
    patch_sessionlocal, patch_config_dirs, monkeypatch, db_session
):
    processed_dir, assets_dir = patch_config_dirs
    u = _make_user(db_session)
    src_file = os.path.join(os.fspath(processed_dir), "src.mp4")
    Path(src_file).write_bytes(b"\x00" * 10)
    v = _make_video(db_session, u, original_url=src_file)
    Path(os.path.join(assets_dir, "logo.jpg")).write_bytes(b"\x00")

    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)

    res = tasks.process_video(v.id)
    assert res == "ok"

    v2 = db_session.execute(select(Video).where(Video.id == v.id)).scalar_one()
    assert v2.status == VideoStatus.PROCESSED
    assert v2.processed_url.startswith(os.fspath(processed_dir))
    assert isinstance(v2.processed_at, datetime)
    assert len(calls.run_calls) >= 3


def test_process_video_ok_without_audio_no_logo(
    patch_sessionlocal, patch_config_dirs, monkeypatch, db_session
):
    processed_dir, assets_dir = patch_config_dirs
    u = _make_user(db_session)
    src_file = os.path.join(os.fspath(processed_dir), "src2.mp4")
    Path(src_file).write_bytes(b"\x00" * 10)
    v = _make_video(db_session, u, original_url=src_file)

    logo_path = Path(os.path.join(assets_dir, "logo.jpg"))
    if logo_path.exists():
        logo_path.unlink()

    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)

    res = tasks.process_video(v.id)
    assert res == "ok"

    v2 = db_session.get(Video, v.id)
    assert v2.status == VideoStatus.PROCESSED
    assert v2.processed_url.startswith(os.fspath(processed_dir))
    assert v2.processed_at is not None


def test_process_video_ok_intro_outro_zero_use_stub(
    patch_sessionlocal, patch_config_dirs, monkeypatch, db_session
):
    processed_dir, _ = patch_config_dirs

    monkeypatch.setattr(tasks.config, "INTRO_SECONDS", 0.0)
    monkeypatch.setattr(tasks.config, "OUTRO_SECONDS", 0.0)

    u = _make_user(db_session)
    src_file = os.path.join(os.fspath(processed_dir), "src3.mp4")
    Path(src_file).write_bytes(b"\x00" * 10)
    v = _make_video(db_session, u, original_url=src_file)

    calls = _SubprocessCalls()
    monkeypatch.setattr(tasks.subprocess, "run", calls.fake_run)

    res = tasks.process_video(v.id)
    assert res == "ok"

    v2 = db_session.get(Video, v.id)
    assert v2.status == VideoStatus.PROCESSED
    assert v2.processed_url.startswith(os.fspath(processed_dir))

    joined = " ".join(" ".join(map(str, c[0])) for c in calls.run_calls)
    assert "0.033" in joined


def test_process_video_error_sets_failed(
    patch_sessionlocal, patch_config_dirs, monkeypatch, db_session
):
    processed_dir, _ = patch_config_dirs
    u = _make_user(db_session)
    src_file = os.path.join(os.fspath(processed_dir), "broken.mp4")
    Path(src_file).write_bytes(b"\x00")
    v = _make_video(db_session, u, original_url=src_file)

    def _boom(cmd, check=True):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(tasks.subprocess, "run", _boom)

    res = tasks.process_video(v.id)
    assert res == "error"

    v2 = db_session.get(Video, v.id)
    assert v2.status == VideoStatus.FAILED
