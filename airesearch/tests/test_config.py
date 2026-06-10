from pathlib import Path

from airesearch.config import Settings


def test_settings_defaults_to_project_data(tmp_path: Path):
    project = tmp_path / "airesearch"
    project.mkdir()

    settings = Settings.from_env({}, project_root=project)

    assert settings.project_root == project
    assert settings.paper_db_path == project / "data" / "paperpipe"
    assert settings.sqlite_path == project / "data" / "airesearch.sqlite3"
    assert settings.papi_executable == "papi"


def test_settings_reads_environment_overrides(tmp_path: Path):
    env = {
        "PAPER_DB_PATH": str(tmp_path / "papers"),
        "AIRESEARCH_DB_PATH": str(tmp_path / "custom.sqlite3"),
        "AIRESEARCH_PAPI": "/x/papi",
    }

    settings = Settings.from_env(env, project_root=tmp_path)

    assert settings.paper_db_path == tmp_path / "papers"
    assert settings.sqlite_path == tmp_path / "custom.sqlite3"
    assert settings.papi_executable == "/x/papi"
