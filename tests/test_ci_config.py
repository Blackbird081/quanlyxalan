from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_quality_gate_uses_matching_postgres_17_client_and_service():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "image: postgres:17" in workflow
    assert "sudo apt-get install -y postgresql-client-17" in workflow
    assert 'echo "/usr/lib/postgresql/17/bin" >> "$GITHUB_PATH"' in workflow
    assert "pg_dump --version | grep -E ' 17\\.'" in workflow
