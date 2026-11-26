import gzip
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_SCRIPT = ROOT / "scripts" / "migrate-db.sh"
BACKUP_SCRIPT = ROOT / "scripts" / "backup.sh"


MOCK_DOCKER = r"""#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
with open(os.environ["MOCK_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\n")

if args == ["compose", "version"]:
    sys.exit(0 if os.environ.get("MOCK_COMPOSE_V2", "1") == "1" else 1)

if args and args[0] == "inspect":
    sys.stdout.write("true\n" if os.environ.get("MOCK_RUNNING", "1") == "1" else "false\n")
    sys.exit(0)

if args and args[0] == "compose":
    args = args[1:]
    if args and args[0] == "--env-file":
        args = args[2:]
elif os.path.basename(sys.argv[0]) == "docker-compose":
    if args and args[0] == "--env-file":
        args = args[2:]
else:
    sys.exit(2)

if args == ["config", "--quiet"]:
    sys.exit(int(os.environ.get("MOCK_CONFIG_STATUS", "0")))

if args[:2] == ["ps", "-q"]:
    if os.environ.get("MOCK_RUNNING", "1") == "1":
        sys.stdout.write("mock-container\n")
    sys.exit(0)

if args[:2] == ["exec", "-T"]:
    service = args[2]
    command = args[3:]
    if service == "postgres" and command[:2] == ["sh", "-c"]:
        shell_command = command[2]
        if "pg_isready" in shell_command:
            sys.exit(0 if os.environ.get("MOCK_READY", "1") == "1" else 1)
        if "pg_dump" in shell_command:
            sys.stdout.write("CREATE TABLE isolated_mock (id integer);\n")
            sys.exit(int(os.environ.get("MOCK_PGDUMP_STATUS", "0")))
        if "psql" in shell_command:
            sql = sys.stdin.read()
            with open(os.environ["MOCK_SQL_LOG"], "w", encoding="utf-8") as output:
                output.write(sql)
            if os.environ.get("MOCK_PSQL_STATUS", "0") != "0":
                sys.stderr.write("ERROR: mocked SQL execution failure\n")
                sys.exit(int(os.environ["MOCK_PSQL_STATUS"]))
            sys.exit(0)
    if service == "api" and command[:1] == ["alembic"]:
        sys.stdout.write("MOCK ALEMBIC OUTPUT\n")
        sys.exit(int(os.environ.get("MOCK_ALEMBIC_STATUS", "0")))

sys.exit(2)
"""

MOCK_DOCKER_COMPOSE = r"""#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
with open(os.environ["MOCK_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(["docker-compose"] + args) + "\n")
if args and args[0] == "--env-file":
    args = args[2:]
if args == ["config", "--quiet"]:
    sys.exit(int(os.environ.get("MOCK_CONFIG_STATUS", "0")))
if args[:2] == ["ps", "-q"]:
    if os.environ.get("MOCK_RUNNING", "1") == "1":
        sys.stdout.write("mock-container\n")
    sys.exit(0)
if args[:2] == ["exec", "-T"] and args[2] == "postgres" and "pg_isready" in args[-1]:
    sys.exit(0 if os.environ.get("MOCK_READY", "1") == "1" else 1)
if args[:2] == ["exec", "-T"] and args[2] == "api" and args[3:5] == ["alembic", "upgrade"]:
    sys.stdout.write("MOCK ALEMBIC OUTPUT\n")
    sys.exit(int(os.environ.get("MOCK_ALEMBIC_STATUS", "0")))
sys.exit(2)
"""


@pytest.fixture
def script_env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(MOCK_DOCKER, encoding="utf-8")
    docker.chmod(0o755)
    docker_compose = bin_dir / "docker-compose"
    docker_compose.write_text(MOCK_DOCKER_COMPOSE, encoding="utf-8")
    docker_compose.chmod(0o755)

    env_file = tmp_path / "compose.env"
    env_file.write_text("POSTGRES_USER=mock\nPOSTGRES_DB=mock\n", encoding="utf-8")
    log_file = tmp_path / "commands.jsonl"
    sql_log = tmp_path / "restored.sql"
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "MOCK_LOG": str(log_file),
            "MOCK_SQL_LOG": str(sql_log),
            "MOCK_COMPOSE_V2": "1",
        }
    )
    return tmp_path, env_file, log_file, sql_log, env


def run_script(script, cwd, env, *args, input_text=None):
    return subprocess.run(
        [str(script), *map(str, args)],
        cwd=cwd,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def logged_commands(log_file):
    return [json.loads(line) for line in Path(log_file).read_text(encoding="utf-8").splitlines()]


def alembic_calls(log_file):
    calls = logged_commands(log_file)
    return [call[call.index("exec") :] for call in calls if "alembic" in call]


def test_migration_normal_path_runs_alembic_upgrade_head_only(script_env):
    cwd, env_file, log_file, _, env = script_env
    result = run_script(MIGRATION_SCRIPT, cwd, env, "--env-file", env_file)

    assert result.returncode == 0, result.stderr
    assert alembic_calls(log_file)[0] == ["exec", "-T", "api", "alembic", "upgrade", "head"]
    assert "init_db" not in result.stdout + result.stderr


def test_migration_dry_run_never_applies_migrations(script_env):
    cwd, env_file, log_file, _, env = script_env
    result = run_script(MIGRATION_SCRIPT, cwd, env, "--env-file", env_file, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert alembic_calls(log_file)[0] == [
        "exec", "-T", "api", "alembic", "upgrade", "--sql", "head"
    ]
    assert "no changes will be applied" in result.stdout


def test_rollback_dry_run_generates_sql_without_downgrading(script_env):
    cwd, env_file, log_file, _, env = script_env
    result = run_script(
        MIGRATION_SCRIPT, cwd, env, "--env-file", env_file, "--rollback", "-1", "--dry-run"
    )

    assert result.returncode == 0, result.stderr
    assert alembic_calls(log_file)[0] == [
        "exec", "-T", "api", "alembic", "downgrade", "--sql", "head:-1"
    ]


def test_rollback_apply_is_blocked_to_preserve_live_history(script_env):
    cwd, env_file, log_file, _, env = script_env
    result = run_script(MIGRATION_SCRIPT, cwd, env, "--env-file", env_file, "--rollback", "base")

    assert result.returncode != 0
    assert "Database downgrades are disabled" in result.stderr
    assert not any("downgrade" in call for call in alembic_calls(log_file))


def test_migration_supports_compose_v1_fallback(script_env):
    cwd, env_file, log_file, _, env = script_env
    env["MOCK_COMPOSE_V2"] = "0"
    result = run_script(MIGRATION_SCRIPT, cwd, env, "--env-file", env_file)

    assert result.returncode == 0, result.stderr
    assert any(call[0] == "docker-compose" for call in logged_commands(log_file))


def test_migration_reports_stopped_services(script_env):
    cwd, env_file, _, _, env = script_env
    env["MOCK_RUNNING"] = "0"
    result = run_script(MIGRATION_SCRIPT, cwd, env, "--env-file", env_file)

    assert result.returncode != 0
    assert "API service is not running" in result.stderr


def test_migration_fails_closed_on_invalid_compose_configuration(script_env):
    cwd, env_file, log_file, _, env = script_env
    env["MOCK_CONFIG_STATUS"] = "1"

    result = run_script(MIGRATION_SCRIPT, cwd, env, "--env-file", env_file)

    assert result.returncode != 0
    assert "Invalid Docker Compose configuration" in result.stderr
    assert not alembic_calls(log_file)


def test_backup_creates_compressed_dump(script_env):
    cwd, env_file, _, _, env = script_env
    backup_dir = cwd / "backups"

    result = run_script(
        BACKUP_SCRIPT, cwd, env, "--backup", "--backup-dir", backup_dir, "--env-file", env_file
    )

    assert result.returncode == 0, result.stderr
    backups = list(backup_dir.glob("*.sql.gz"))
    assert len(backups) == 1
    with gzip.open(backups[0], "rt", encoding="utf-8") as dump:
        assert dump.read() == "CREATE TABLE isolated_mock (id integer);\n"


def test_backup_fails_closed_on_invalid_compose_configuration(script_env):
    cwd, env_file, _, _, env = script_env
    env["MOCK_CONFIG_STATUS"] = "1"
    backup_dir = cwd / "backups"

    result = run_script(
        BACKUP_SCRIPT, cwd, env, "--backup", "--backup-dir", backup_dir, "--env-file", env_file
    )

    assert result.returncode != 0
    assert "Invalid Docker Compose configuration" in result.stderr
    assert not backup_dir.exists()


def test_failed_backup_removes_partial_dump(script_env):
    cwd, env_file, _, _, env = script_env
    env["MOCK_PGDUMP_STATUS"] = "1"
    backup_dir = cwd / "backups"

    result = run_script(
        BACKUP_SCRIPT, cwd, env, "--backup", "--backup-dir", backup_dir, "--env-file", env_file
    )

    assert result.returncode != 0
    assert "Backup failed" in result.stderr
    assert list(backup_dir.iterdir()) == []


def test_restore_success_reports_completion(script_env):
    cwd, env_file, _, sql_log, env = script_env
    backup = cwd / "restore.sql"
    backup.write_text("SELECT 1;\n", encoding="utf-8")

    result = run_script(
        BACKUP_SCRIPT, cwd, env, "--restore", backup, "--env-file", env_file, input_text="yes\n"
    )

    assert result.returncode == 0, result.stderr
    assert "Database restored successfully" in result.stdout
    assert sql_log.read_text(encoding="utf-8") == "SELECT 1;\n"


@pytest.mark.parametrize("compressed", [False, True])
def test_restore_fails_loudly_on_sql_errors(script_env, compressed):
    cwd, env_file, _, sql_log, env = script_env
    backup = cwd / ("restore.sql.gz" if compressed else "restore.sql")
    if compressed:
        with gzip.open(backup, "wt", encoding="utf-8") as output:
            output.write("SELECT 1;\n")
    else:
        backup.write_text("SELECT 1;\n", encoding="utf-8")
    env["MOCK_PSQL_STATUS"] = "3"

    result = run_script(
        BACKUP_SCRIPT, cwd, env, "--restore", backup, "--env-file", env_file, input_text="yes\n"
    )

    assert result.returncode != 0
    assert "Database restore failed" in result.stderr
    assert "mocked SQL execution failure" in result.stderr
    restore_command = " ".join(" ".join(call) for call in logged_commands(env["MOCK_LOG"]))
    assert "ON_ERROR_STOP=1" in restore_command
    assert "--single-transaction" in restore_command
    assert sql_log.read_text(encoding="utf-8") == "SELECT 1;\n"
    assert "restored successfully" not in result.stdout


def test_restore_honors_decompression_pipeline_failure(script_env):
    cwd, env_file, _, _, env = script_env
    invalid_gzip = cwd / "not-really-gzipped.sql.gz"
    invalid_gzip.write_text("invalid compressed data", encoding="utf-8")

    result = run_script(
        BACKUP_SCRIPT,
        cwd,
        env,
        "--restore",
        invalid_gzip,
        "--env-file",
        env_file,
        input_text="yes\n",
    )

    assert result.returncode != 0
    assert "Database restore failed" in result.stderr
    assert "restored successfully" not in result.stdout


def test_prune_removes_expired_backups_under_strict_shell_mode(script_env):
    cwd, _, _, _, env = script_env
    backup_dir = cwd / "backups"
    backup_dir.mkdir()
    expired = backup_dir / "old.sql"
    recent = backup_dir / "recent.sql.gz"
    expired.write_text("old", encoding="utf-8")
    recent.write_text("recent", encoding="utf-8")
    old_time = time.time() - 40 * 24 * 60 * 60
    os.utime(expired, (old_time, old_time))

    result = run_script(
        BACKUP_SCRIPT, cwd, env, "--prune", "--backup-dir", backup_dir, "--retention", "30"
    )

    assert result.returncode == 0, result.stderr
    assert not expired.exists()
    assert recent.exists()
    assert "Pruned 1 backup(s)" in result.stdout


@pytest.fixture
def disposable_postgres(tmp_path):
    if os.environ.get("RUN_DISPOSABLE_POSTGRES_SCRIPT_TESTS") != "1":
        pytest.skip(
            "set RUN_DISPOSABLE_POSTGRES_SCRIPT_TESTS=1 to run disposable PostgreSQL acceptance"
        )

    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Docker is not installed")
    compose_version = subprocess.run(
        [docker, "compose", "version"], capture_output=True, text=True, check=False
    )
    if compose_version.returncode != 0:
        pytest.skip("Docker Compose v2 is not available")

    project = f"tenga-recovery-{uuid.uuid4().hex[:12]}"
    env_file = tmp_path / "postgres.env"
    env_file.write_text(
        "POSTGRES_USER=recovery_test\n"
        "POSTGRES_PASSWORD=disposable-recovery-password\n"
        "POSTGRES_DB=recovery_test\n",
        encoding="utf-8",
    )
    compose_file = tmp_path / "compose.yaml"
    compose_file.write_text(
        """services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: recovery_test
      POSTGRES_PASSWORD: disposable-recovery-password
      POSTGRES_DB: recovery_test
    ports:
      - "127.0.0.1::5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U recovery_test -d recovery_test"]
      interval: 2s
      timeout: 2s
      retries: 30
""",
        encoding="utf-8",
    )
    common = [
        docker,
        "compose",
        "--env-file",
        str(env_file),
        "--file",
        str(compose_file),
        "--project-name",
        project,
    ]
    started = subprocess.run(
        [*common, "up", "--detach", "--wait", "postgres"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if started.returncode != 0:
        subprocess.run(
            [*common, "down", "--volumes", "--remove-orphans"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        pytest.fail(f"Disposable PostgreSQL did not start:\n{started.stdout}\n{started.stderr}")

    port_result = subprocess.run(
        [*common, "port", "postgres", "5432"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert port_result.returncode == 0, port_result.stderr
    host_port = port_result.stdout.strip().rsplit(":", 1)[-1]
    script_env = os.environ.copy()
    script_env["PATH"] = os.defpath + os.pathsep + os.environ.get("PATH", "")
    script_env["COMPOSE_FILE"] = str(compose_file)
    script_env["COMPOSE_PROJECT_NAME"] = project

    try:
        yield {
            "compose": common,
            "cwd": tmp_path,
            "env_file": env_file,
            "port": int(host_port),
            "script_env": script_env,
            "user": "recovery_test",
            "password": "disposable-recovery-password",
            "database": "recovery_test",
        }
    finally:
        stopped = subprocess.run(
            [*common, "down", "--volumes", "--remove-orphans"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert stopped.returncode == 0, stopped.stderr


def postgres_query(postgres, sql):
    result = subprocess.run(
        [
            *postgres["compose"],
            "exec",
            "-T",
            "postgres",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            postgres["user"],
            "-d",
            postgres["database"],
            "-At",
            "-c",
            sql,
        ],
        cwd=postgres["cwd"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_disposable_postgres_backup_restore_and_migrations(disposable_postgres):
    postgres = disposable_postgres
    postgres_query(
        postgres,
        "CREATE TABLE recovery_records (id integer PRIMARY KEY, label text NOT NULL); "
        "INSERT INTO recovery_records VALUES (1, 'legacy-stock'), (2, 'closed-sale');",
    )
    expected_checksum = postgres_query(
        postgres,
        "SELECT md5(string_agg(id::text || ':' || label, ',' ORDER BY id)) "
        "FROM recovery_records;",
    )

    backup_dir = postgres["cwd"] / "backups"
    backup = run_script(
        BACKUP_SCRIPT,
        postgres["cwd"],
        postgres["script_env"],
        "--backup",
        "--backup-dir",
        backup_dir,
        "--env-file",
        postgres["env_file"],
    )
    assert backup.returncode == 0, backup.stderr
    backup_files = list(backup_dir.glob("*.sql.gz"))
    assert len(backup_files) == 1
    postgres_query(
        postgres,
        "UPDATE recovery_records SET label = 'overwritten' WHERE id = 1; "
        "INSERT INTO recovery_records VALUES (3, 'must-be-removed');",
    )
    restore = run_script(
        BACKUP_SCRIPT,
        postgres["cwd"],
        postgres["script_env"],
        "--restore",
        backup_files[0],
        "--env-file",
        postgres["env_file"],
        input_text="yes\n",
    )
    assert restore.returncode == 0, restore.stderr
    assert postgres_query(postgres, "SELECT count(*) FROM recovery_records;") == "2"
    assert postgres_query(
        postgres,
        "SELECT md5(string_agg(id::text || ':' || label, ',' ORDER BY id)) "
        "FROM recovery_records;",
    ) == expected_checksum

    invalid_restore = postgres["cwd"] / "invalid.sql"
    invalid_restore.write_text(
        "DELETE FROM recovery_records; SELECT 1 / 0;\n",
        encoding="utf-8",
    )
    failed_restore = run_script(
        BACKUP_SCRIPT,
        postgres["cwd"],
        postgres["script_env"],
        "--restore",
        invalid_restore,
        "--env-file",
        postgres["env_file"],
        input_text="yes\n",
    )
    assert failed_restore.returncode != 0
    assert "Database restore failed" in failed_restore.stderr
    assert postgres_query(
        postgres,
        "SELECT md5(string_agg(id::text || ':' || label, ',' ORDER BY id)) "
        "FROM recovery_records;",
    ) == expected_checksum

    database_url = URL.create(
        "postgresql+psycopg",
        username=postgres["user"],
        password=postgres["password"],
        host="127.0.0.1",
        port=postgres["port"],
        database=postgres["database"],
    )
    engine = create_engine(database_url)
    try:
        config = Config()
        config.set_main_option("script_location", str(ROOT / "src" / "migrations"))
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("DATABASE_URL", database_url.render_as_string(hide_password=False))
            command.upgrade(config, "head")
            inspector = inspect(engine)
            assert {"organization", "product", "employee", "payment_attempt"} <= set(
                inspector.get_table_names()
            )
            with engine.connect() as connection:
                assert connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one() == ScriptDirectory.from_config(config).get_current_head()

            command.downgrade(config, "setup_imports_v001")
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO organization "
                        "(id, name, code, is_active, created_at, updated_at) "
                        "VALUES (1, 'Legacy PG', 'LEGACY_PG', true, '2026-01-01', '2026-01-01')"
                    )
                )
                connection.execute(
                    text(
                        'INSERT INTO "user" '
                        "(id, organization_id, email, username, password_hash, role, "
                        "is_active, created_at, updated_at) "
                        "VALUES (1, 1, 'owner@example.test', 'owner', 'hash', 'admin', "
                        "true, '2026-01-01', '2026-01-01')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO location "
                        "(id, organization_id, code, name, is_active, created_at, updated_at) "
                        "VALUES (1, 1, 'MAIN', 'Main', true, '2026-01-01', '2026-01-01')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO product "
                        "(id, organization_id, sku, name, price, cost, is_active, created_at, updated_at) "
                        "VALUES (1, 1, 'SKU-1', 'Item', 10, 4, true, '2026-01-01', '2026-01-01')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO till "
                        "(id, organization_id, location_id, code, name, is_active, created_at, updated_at) "
                        "VALUES (1, 1, 1, 'T1', 'Till 1', true, '2026-01-01', '2026-01-01')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO sale "
                        "(id, organization_id, till_id, cashier_id, total_amount, discount_amount, "
                        "tax_amount, payment_method, status, till_session_id, source_type, "
                        "created_at, updated_at) "
                        "VALUES (1, 1, 1, 1, 10, 0, 0, 'cash', 'completed', NULL, "
                        "'LIVE', '2026-01-01', '2026-01-01')"
                    )
                )

            command.upgrade(config, "head")
            with engine.connect() as connection:
                assert connection.execute(
                    text("SELECT total_amount FROM sale WHERE id = 1")
                ).scalar_one() == 10
                assert connection.execute(
                    text("SELECT currency_code FROM organization WHERE id = 1")
                ).scalar_one() is None
                assert connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one() == ScriptDirectory.from_config(config).get_current_head()
    finally:
        engine.dispose()
