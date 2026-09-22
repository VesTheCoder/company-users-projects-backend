import os
import subprocess
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pytest


def test_docker_login_crud_and_logout():
    password = os.environ.get("SMOKE_PASSWORD")
    if not password:
        pytest.skip("Set SMOKE_PASSWORD after seeding the Compose environment")
    base_url = os.environ.get("SMOKE_BASE_URL", "http://localhost:8080")
    parsed_base_url = urlsplit(base_url)
    origin = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"
    with httpx.Client(base_url=base_url) as client:
        assert client.get("/health/ready").status_code == 200
        response = client.post(
            "/api/v1/auth/login",
            json={"login": "owner@demo.example", "password": password},
            headers={"Origin": origin, "X-CSRF-Protection": "1"},
        )
        assert response.status_code == 200, response.text
        client.headers.update(
            {"Origin": origin, "X-CSRF-Token": response.json()["csrf_token"]}
        )
        response = client.post("/api/v1/companies", json={"name": f"Smoke {uuid4()}"})
        assert response.status_code == 201, response.text
        location = response.headers["location"]
        assert client.get(location).status_code == 200
        assert (
            client.delete(
                location, headers={"If-Match": response.headers["etag"]}
            ).status_code
            == 204
        )
        assert client.post("/api/v1/auth/logout").status_code == 204


def test_runtime_database_role_has_no_schema_creation_privilege():
    if not os.environ.get("SMOKE_PASSWORD"):
        pytest.skip("Compose smoke environment is not enabled")
    query = """
PGPASSWORD="$DB_PASSWORD" psql -AtX -v ON_ERROR_STOP=1 \
  --host=127.0.0.1 \
  --username="$DB_USER" \
  --dbname="$POSTGRES_DB" \
  --command="SELECT has_schema_privilege(current_user, 'public', 'CREATE'), \
    has_table_privilege(current_user, 'users', 'SELECT,INSERT,UPDATE,DELETE');"
"""
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "sh", "-c", query],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "f|t"
