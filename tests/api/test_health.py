from unittest.mock import AsyncMock


async def test_readiness_reports_dependency_degradation(
    client, application, monkeypatch
):
    assert (await client.get("/health/ready")).status_code == 200
    monkeypatch.setattr(
        application.state.redis, "ping", AsyncMock(side_effect=ConnectionError)
    )
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["rate_limiter"] == "unavailable"
    assert (await client.get("/health/live")).status_code == 200


async def test_metrics_use_route_templates(authenticated):
    company = await authenticated.post("/api/v1/companies", json={"name": "Metrics"})
    await authenticated.get(company.headers["location"])
    metrics = await authenticated.get("/metrics")
    assert metrics.status_code == 200
    assert "/api/v1/companies/{company_id}" in metrics.text
    assert company.json()["id"] not in metrics.text
