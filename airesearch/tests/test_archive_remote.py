from pathlib import Path

import pytest

from airesearch.archive_remote import RcloneRemote, RemoteCommandError


FAKE_RCLONE = r'''#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path

root = Path(os.environ["FAKE_RCLONE_ROOT"])
root.mkdir(parents=True, exist_ok=True)
with (root / "commands.jsonl").open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\n")

if os.environ.get("FAKE_RCLONE_FAIL") == "1":
    print("oauth token super-secret unauthorized", file=sys.stderr)
    raise SystemExit(9)

command, *args = sys.argv[1:]

def is_remote(value):
    return ":" in value and not value.startswith("/")

def resolve(value):
    if not is_remote(value):
        return Path(value)
    _, remote_path = value.split(":", 1)
    return root / "objects" / remote_path.lstrip("/")

if command == "version":
    print("rclone v1.fake")
elif command == "copyto":
    source, destination = map(resolve, args[:2])
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
elif command == "moveto":
    source, destination = map(resolve, args[:2])
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.replace(destination)
elif command == "lsjson":
    target = resolve(args[0])
    if not target.is_file():
        print("not found", file=sys.stderr)
        raise SystemExit(3)
    print(json.dumps([{"Name": target.name, "Size": target.stat().st_size}]))
elif command == "deletefile":
    resolve(args[0]).unlink()
else:
    print("unsupported command", file=sys.stderr)
    raise SystemExit(4)
'''


def make_fake_rclone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    executable = tmp_path / "rclone"
    executable.write_text(FAKE_RCLONE, encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setenv("FAKE_RCLONE_ROOT", str(tmp_path / "remote"))
    return executable


def test_rclone_adapter_uploads_promotes_stats_and_downloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    executable = make_fake_rclone(tmp_path, monkeypatch)
    local_archive = tmp_path / "paper.tar"
    local_archive.write_bytes(b"archive")
    restored_archive = tmp_path / "download" / "paper.tar"
    remote = RcloneRemote(
        executable=str(executable),
        remote_root="gdrive:niu-secretary/airesearch/v1",
    )

    remote.check()
    remote.upload(local_archive, "tmp/paper_a.tar")
    remote.promote("tmp/paper_a.tar", "papers/paper_a/hash.tar")
    stat = remote.stat("papers/paper_a/hash.tar")
    remote.download("papers/paper_a/hash.tar", restored_archive)

    assert stat.exists is True
    assert stat.size_bytes == local_archive.stat().st_size
    assert restored_archive.read_bytes() == local_archive.read_bytes()
    assert remote.stat("papers/missing/hash.tar").exists is False


def test_rclone_adapter_redacts_remote_error_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    executable = make_fake_rclone(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_RCLONE_FAIL", "1")
    remote = RcloneRemote(executable=str(executable), remote_root="gdrive:archive")

    with pytest.raises(RemoteCommandError) as error:
        remote.check()

    assert error.value.category == "authentication_failed"
    assert "super-secret" not in str(error.value)
    assert "token" not in str(error.value).lower()


@pytest.mark.parametrize(
    "relative_path",
    ["", "/absolute.tar", "../escape.tar", "dir/../../escape.tar", "dir\\file.tar"],
)
def test_rclone_adapter_rejects_unsafe_remote_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
):
    executable = make_fake_rclone(tmp_path, monkeypatch)
    remote = RcloneRemote(executable=str(executable), remote_root="gdrive:archive")

    with pytest.raises(ValueError, match="unsafe remote archive path"):
        remote.stat(relative_path)


def test_rclone_adapter_limits_deletion_to_integration_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    executable = make_fake_rclone(tmp_path, monkeypatch)
    remote = RcloneRemote(executable=str(executable), remote_root="gdrive:archive")

    with pytest.raises(ValueError, match="restricted"):
        remote.delete_test_object("papers/paper_a/hash.tar")
