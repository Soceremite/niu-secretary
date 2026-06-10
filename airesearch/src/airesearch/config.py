from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    project_root: Path
    paper_db_path: Path
    sqlite_path: Path
    papi_executable: str

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        project_root: Path | None = None,
    ) -> "Settings":
        values = os.environ if env is None else env
        root = project_root or Path(__file__).resolve().parents[2]
        paper_db_path = Path(values.get("PAPER_DB_PATH", root / "data" / "paperpipe"))
        sqlite_path = Path(values.get("AIRESEARCH_DB_PATH", root / "data" / "airesearch.sqlite3"))
        papi_executable = values.get("AIRESEARCH_PAPI", "papi")
        return cls(
            project_root=root,
            paper_db_path=paper_db_path,
            sqlite_path=sqlite_path,
            papi_executable=papi_executable,
        )
