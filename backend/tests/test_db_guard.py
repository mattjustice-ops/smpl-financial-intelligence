import pytest

from app.core.db_guard import assert_local_database_target, describe_target

LOCAL = "postgresql+psycopg://sfi:pw@localhost:5432/sfi"
REMOTE = "postgresql+psycopg://owner:pw@ep-cool-moon.aws.neon.tech/neondb?sslmode=require"


def _env_file(tmp_path, url):
    path = tmp_path / ".env"
    path.write_text(f"OTHER=1\nDATABASE_URL={url}\n", encoding="utf-8")
    return path


def test_local_target_passes_without_env_file(tmp_path):
    status = assert_local_database_target(LOCAL, env_path=tmp_path / "missing.env")
    assert status.startswith("local ")


def test_remote_target_blocked_when_env_file_declares_local(tmp_path):
    with pytest.raises(RuntimeError) as exc:
        assert_local_database_target(
            REMOTE, env_path=_env_file(tmp_path, LOCAL), allow_remote=False
        )
    assert "Refusing to start" in str(exc.value)


def test_remote_target_allowed_with_explicit_override(tmp_path):
    status = assert_local_database_target(
        REMOTE, env_path=_env_file(tmp_path, LOCAL), allow_remote=True
    )
    assert "SMPL_ALLOW_REMOTE_DB" in status


def test_deployed_environment_has_no_env_file_so_remote_is_fine(tmp_path):
    status = assert_local_database_target(REMOTE, env_path=tmp_path / "missing.env")
    assert status.startswith("remote ")


def test_env_file_declaring_remote_does_not_block(tmp_path):
    status = assert_local_database_target(
        REMOTE, env_path=_env_file(tmp_path, REMOTE), allow_remote=False
    )
    assert status.startswith("remote ")


def test_describe_target_omits_credentials():
    described = describe_target(REMOTE)
    assert "pw" not in described and "owner" not in described
    assert described == "ep-cool-moon.aws.neon.tech/neondb"
