import json
from pathlib import Path

import pytest

from airesearch.static_publish import write_static_deploy_scripts, publish_static_site, write_static_host_config


def make_site(tmp_path: Path) -> Path:
    site = tmp_path / "bundle"
    site.mkdir()
    (site / "index.html").write_text("<!doctype html><title>AIResearch</title>\n", encoding="utf-8")
    (site / "manifest.json").write_text('{"artifact_count": 1}\n', encoding="utf-8")
    (site / "report.md").write_text("# Report\n", encoding="utf-8")
    return site


def test_publish_static_site_copies_site_and_writes_manifest(tmp_path: Path):
    source = make_site(tmp_path)
    out_dir = tmp_path / "site-current"

    result = publish_static_site(source, out_dir)

    assert result.out_dir == out_dir
    assert result.entrypoint == out_dir / "index.html"
    assert result.manifest_path == out_dir / "publish.json"
    assert result.diff_path == out_dir / "publish-diff.json"
    assert result.file_count == 5
    assert (out_dir / "index.html").read_text(encoding="utf-8").startswith("<!doctype")
    manifest = json.loads((out_dir / "publish.json").read_text(encoding="utf-8"))
    assert manifest["source_dir"] == str(source)
    assert manifest["entrypoint"] == str(out_dir / "index.html")
    assert manifest["file_count"] == 5
    assert manifest["files"] == ["index.html", "manifest.json", "publish-diff.json", "publish.json", "report.md"]
    diff = json.loads((out_dir / "publish-diff.json").read_text(encoding="utf-8"))
    assert diff["added"] == ["index.html", "manifest.json", "report.md"]
    assert diff["removed"] == []
    assert diff["changed"] == []


def test_publish_static_site_cleans_stale_files_by_default(tmp_path: Path):
    source = make_site(tmp_path)
    out_dir = tmp_path / "site-current"
    out_dir.mkdir()
    (out_dir / "stale.txt").write_text("old\n", encoding="utf-8")

    publish_static_site(source, out_dir)

    assert not (out_dir / "stale.txt").exists()


def test_publish_static_site_writes_diff_against_previous_publish(tmp_path: Path):
    source = make_site(tmp_path)
    out_dir = tmp_path / "site-current"
    publish_static_site(source, out_dir)
    (source / "report.md").write_text("# Report\n\nUpdated\n", encoding="utf-8")
    (source / "new.md").write_text("# New\n", encoding="utf-8")

    publish_static_site(source, out_dir)

    diff = json.loads((out_dir / "publish-diff.json").read_text(encoding="utf-8"))
    assert diff["added"] == ["new.md"]
    assert diff["removed"] == []
    assert diff["changed"] == ["report.md"]
    assert "index.html" in diff["unchanged"]


def test_publish_static_site_requires_index_and_manifest(tmp_path: Path):
    source = tmp_path / "bundle"
    source.mkdir()
    (source / "index.html").write_text("<!doctype html>\n", encoding="utf-8")

    with pytest.raises(ValueError, match="manifest.json"):
        publish_static_site(source, tmp_path / "site-current")


def test_publish_static_site_rejects_output_inside_source(tmp_path: Path):
    source = make_site(tmp_path)

    with pytest.raises(ValueError, match="inside the source"):
        publish_static_site(source, source / "published")


def test_write_static_host_config_writes_nginx_config_and_manifest(tmp_path: Path):
    site = make_site(tmp_path)
    out_dir = tmp_path / "deploy"
    deploy_root = tmp_path / "www" / "niu-secretary" / "airesearch"

    result = write_static_host_config(
        site,
        out_dir,
        base_path="/niu-secretary/airesearch/",
        deploy_root=deploy_root,
    )

    assert result.config_path == out_dir / "airesearch.nginx.conf"
    assert result.manifest_path == out_dir / "static-host.json"
    config = result.config_path.read_text(encoding="utf-8")
    assert "location = /niu-secretary/airesearch" in config
    assert "location /niu-secretary/airesearch/" in config
    assert f"alias {deploy_root.resolve(strict=False)}/;" in config
    assert "try_files $uri $uri/ /niu-secretary/airesearch/index.html;" in config
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["site_dir"] == str(site)
    assert manifest["base_path"] == "/niu-secretary/airesearch/"
    assert manifest["deploy_root"] == str(deploy_root.resolve(strict=False))


def test_write_static_host_config_requires_valid_site(tmp_path: Path):
    site = tmp_path / "missing"

    with pytest.raises(ValueError, match="does not exist"):
        write_static_host_config(site, tmp_path / "deploy")


def test_write_static_deploy_scripts_writes_deploy_and_rollback_scripts(tmp_path: Path):
    site = make_site(tmp_path)
    out_dir = tmp_path / "deploy"
    deploy_root = tmp_path / "www" / "niu-secretary" / "airesearch"
    snapshot_root = tmp_path / "snapshots"

    result = write_static_deploy_scripts(
        site,
        out_dir,
        deploy_root=deploy_root,
        snapshot_root=snapshot_root,
    )

    assert result.deploy_script_path == out_dir / "deploy-airesearch.sh"
    assert result.rollback_script_path == out_dir / "rollback-airesearch.sh"
    assert result.manifest_path == out_dir / "static-deploy-scripts.json"
    assert result.deploy_script_path.stat().st_mode & 0o111
    assert result.rollback_script_path.stat().st_mode & 0o111
    deploy_script = result.deploy_script_path.read_text(encoding="utf-8")
    rollback_script = result.rollback_script_path.read_text(encoding="utf-8")
    assert 'rsync -a --delete "$DEPLOY_ROOT"/ "$SNAPSHOT_DIR"/' in deploy_script
    assert 'rsync -a --delete "$SITE_DIR"/ "$DEPLOY_ROOT"/' in deploy_script
    assert "deploy-manifest.json" in deploy_script
    assert 'SNAPSHOT="${1:-latest}"' in rollback_script
    assert 'rsync -a --delete "$SNAPSHOT_DIR"/ "$DEPLOY_ROOT"/' in rollback_script
    assert "rollback-manifest.json" in rollback_script
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["deploy_root"] == str(deploy_root.resolve(strict=False))
    assert manifest["snapshot_root"] == str(snapshot_root.resolve(strict=False))
    assert manifest["rollback_command"].endswith("rollback-airesearch.sh latest")


def test_write_static_deploy_scripts_requires_valid_site(tmp_path: Path):
    with pytest.raises(ValueError, match="does not exist"):
        write_static_deploy_scripts(tmp_path / "missing", tmp_path / "deploy")
