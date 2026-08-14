from pathlib import Path

import pytest

from airesearch.config import Settings


def test_settings_defaults_to_project_data(tmp_path: Path):
    project = tmp_path / "airesearch"
    project.mkdir()

    settings = Settings.from_env({}, project_root=project)

    assert settings.project_root == project
    assert settings.paper_db_path == project / "data" / "paperpipe"
    assert settings.sqlite_path == project / "data" / "airesearch.sqlite3"
    assert settings.papi_executable == "papi"
    assert settings.archive_remote == ""
    assert settings.archive_staging_path == project / "data" / "archive-staging"
    assert settings.rclone_executable == "rclone"
    assert settings.archive_workers == 2
    assert settings.archive_cache_gb == 1


def test_settings_reads_environment_overrides(tmp_path: Path):
    env = {
        "PAPER_DB_PATH": str(tmp_path / "papers"),
        "AIRESEARCH_DB_PATH": str(tmp_path / "custom.sqlite3"),
        "AIRESEARCH_PAPI": "/x/papi",
        "AIRESEARCH_ARCHIVE_REMOTE": "gdrive:niu-secretary/airesearch/v1/",
        "AIRESEARCH_ARCHIVE_STAGING": str(tmp_path / "staging"),
        "AIRESEARCH_RCLONE": "/opt/bin/rclone",
        "AIRESEARCH_ARCHIVE_WORKERS": "3",
        "AIRESEARCH_ARCHIVE_CACHE_GB": "4",
    }

    settings = Settings.from_env(env, project_root=tmp_path)

    assert settings.paper_db_path == tmp_path / "papers"
    assert settings.sqlite_path == tmp_path / "custom.sqlite3"
    assert settings.papi_executable == "/x/papi"
    assert settings.archive_remote == "gdrive:niu-secretary/airesearch/v1"
    assert settings.archive_staging_path == tmp_path / "staging"
    assert settings.rclone_executable == "/opt/bin/rclone"
    assert settings.archive_workers == 3
    assert settings.archive_cache_gb == 4


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("AIRESEARCH_ARCHIVE_WORKERS", "0", "must be at least 1"),
        ("AIRESEARCH_ARCHIVE_CACHE_GB", "-1", "must be non-negative"),
    ],
)
def test_settings_rejects_invalid_archive_limits(
    tmp_path: Path,
    name: str,
    value: str,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        Settings.from_env({name: value}, project_root=tmp_path)
