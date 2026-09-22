import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from app.config import Settings
from app.infrastructure.database import create_engine


def test_docker_login_crud_and_logout():
    password = os.environ.get("SMOKE_PASSWORD")
    if not password:
        pytest.skip("Set SMOKE_PASSWORD after seeding the Compose environment")
    with httpx.Client(
        base_url=os.environ.get("SMOKE_BASE_URL", "http://localhost:8080")
    ) as client:
        assert client.get("/health/ready").status_code == 200
        response = client.post(
            "/api/v1/auth/login",
            json={"login": "owner@demo.example", "password": password},
            headers={"Origin": "http://localhost:8080", "X-CSRF-Protection": "1"},
        )
        assert response.status_code == 200, response.text
        client.headers.update(
            {
                "Origin": "http://localhost:8080",
                "X-CSRF-Token": response.json()["csrf_token"],
            }
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


async def test_runtime_database_role_has_no_schema_creation_privilege():
    if not os.environ.get("SMOKE_PASSWORD"):
        pytest.skip("Compose smoke environment is not enabled")
    engine = create_engine(Settings())
    try:
        async with engine.connect() as connection:
            assert not await connection.scalar(
                text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
            )
            assert await connection.scalar(
                text(
                    "SELECT has_table_privilege(current_user, 'users', "
                    "'SELECT,INSERT,UPDATE,DELETE')"
                )
            )
    finally:
        await engine.dispose()
