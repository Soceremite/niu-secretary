from __future__ import annotations

import fcntl
import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class ArchiveBusyError(RuntimeError):
    pass


@contextmanager
def paper_lock(lock_root: Path, paper_key: str) -> Iterator[None]:
    lock_root.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(paper_key.encode("utf-8")).hexdigest() + ".lock"
    with (lock_root / name).open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ArchiveBusyError(
                f"archive operation already running: {paper_key}"
            ) from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
