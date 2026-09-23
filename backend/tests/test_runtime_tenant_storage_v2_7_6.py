from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_container_prepares_writable_tenant_root_before_dropping_privileges():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    startup = (ROOT / "start_hosting.sh").read_text(encoding="utf-8")

    assert "mkdir -p /data/tenants" in dockerfile
    assert "chown -R appuser:appuser /data" in dockerfile
    assert 'mkdir -p "$DATA_DIR/tenants"' in startup
    assert 'chown -R appuser:appuser "$DATA_DIR"' in startup


def test_runtime_prepare_keeps_tenant_root_present():
    runtime_prepare = (ROOT / "backend" / "runtime_prepare.py").read_text(
        encoding="utf-8"
    )

    assert 'data_dir / "tenants"' in runtime_prepare
