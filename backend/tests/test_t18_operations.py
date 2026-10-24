import subprocess
import sys

from fastapi.testclient import TestClient
from antecipe.adapters.http import create_app
from antecipe.adapters.contract import validator
from antecipe.settings import Settings


def test_cli_available_and_validates_chunk_size():
    command = [sys.executable, "-m", "antecipe.cli"]
    result = subprocess.run(command + ["--help"], capture_output=True, text=True)
    assert result.returncode == 0 and "import-registry" in result.stdout and "worker" in result.stdout
    result = subprocess.run(
        command + ["worker", "--batch-size", "10", "--once"], capture_output=True, text=True
    )
    assert result.returncode != 0 and "1000" in result.stderr


def test_unavailable_database_readiness_envelope(tmp_path):
    settings = Settings(
        database_url="postgresql+psycopg://antecipe:antecipe@127.0.0.1:1/antecipe_test?connect_timeout=1",
        storage=tmp_path,
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        validator("ErroResponse").validate(response.json())
        assert response.json()["erro"]["retry_permitido"]
        assert client.get("/api/v1/health/live").status_code == 200
