from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def test_request_id_and_problem_details(settings):
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://localhost"
    ) as client:
        request_id = str(uuid4())
        response = await client.get("/missing", headers={"X-Request-ID": request_id})
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json()["request_id"] == request_id
        response = await client.get("/health/live", headers={"X-Request-ID": "invalid"})
        assert str(UUID(response.headers["x-request-id"])) != "invalid"


async def test_body_limit_preserves_cors_headers(settings):
    app = create_app(settings)
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://localhost"
    ) as client:
        response = await client.post(
            "/missing",
            content=b"x" * 65537,
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 413
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:5173"
        )
