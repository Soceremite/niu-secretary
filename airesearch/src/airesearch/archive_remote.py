from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class RemoteStat:
    exists: bool
    size_bytes: int


class RemoteCommandError(RuntimeError):
    def __init__(self, command: str, exit_code: int, category: str) -> None:
        self.command = command
        self.exit_code = exit_code
        self.category = category
        super().__init__(f"rclone {command} failed ({exit_code}): {category}")


def classify_error(stderr: str) -> str:
    lowered = stderr.lower()
    if "not found" in lowered:
        return "not_found"
    if "oauth" in lowered or "token" in lowered or "unauthorized" in lowered:
        return "authentication_failed"
    if "quota" in lowered:
        return "quota_exceeded"
    if "timeout" in lowered:
        return "timeout"
    return "remote_command_failed"


class RcloneRemote:
    def __init__(
        self,
        *,
        executable: str,
        remote_root: str,
        timeout_seconds: int = 3600,
    ) -> None:
        remote_name, separator, remote_path = remote_root.partition(":")
        if not separator or not remote_name or not remote_path:
            raise ValueError("archive remote must be an rclone remote path")
        self.executable = executable
        self.remote_root = remote_root.rstrip("/")
        self.remote_name = remote_name
        self.timeout_seconds = timeout_seconds

    def _target(self, relative_path: str) -> str:
        path = PurePosixPath(relative_path)
        if (
            not relative_path
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in relative_path
        ):
            raise ValueError("unsafe remote archive path")
        return f"{self.remote_root}/{path.as_posix()}"

    def _run(
        self,
        *args: str,
        allow_missing: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                [self.executable, *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise RemoteCommandError(args[0], 127, "executable_missing") from exc
        except subprocess.TimeoutExpired as exc:
            raise RemoteCommandError(args[0], 124, "timeout") from exc
        if result.returncode:
            category = classify_error(result.stderr)
            if not (allow_missing and category == "not_found"):
                raise RemoteCommandError(args[0], result.returncode, category)
        return result

    def check(self) -> None:
        self._run("version")

    def upload(self, local_path: Path, temporary_path: str) -> None:
        self._run("copyto", str(local_path), self._target(temporary_path))

    def promote(self, temporary_path: str, final_path: str) -> None:
        self._run(
            "moveto",
            self._target(temporary_path),
            self._target(final_path),
        )

    def stat(self, remote_path: str) -> RemoteStat:
        result = self._run(
            "lsjson",
            self._target(remote_path),
            "--files-only",
            allow_missing=True,
        )
        if result.returncode:
            return RemoteStat(exists=False, size_bytes=0)
        try:
            rows = json.loads(result.stdout or "[]")
            size_bytes = int(rows[0]["Size"]) if rows else 0
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RemoteCommandError("lsjson", 2, "invalid_remote_response") from exc
        return RemoteStat(exists=bool(rows), size_bytes=size_bytes)

    def download(self, remote_path: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._run("copyto", self._target(remote_path), str(local_path))

    def delete_test_object(self, remote_path: str) -> None:
        if not remote_path.startswith("integration-test/"):
            raise ValueError("remote deletion is restricted to integration-test objects")
        self._run("deletefile", self._target(remote_path))
