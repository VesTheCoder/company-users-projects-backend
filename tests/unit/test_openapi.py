from app.main import create_app


def test_openapi_documents_cookie_csrf_and_problem_details(settings):
    schema = create_app(settings).openapi()
    operation = schema["paths"]["/api/v1/companies"]["post"]
    assert operation["security"] == [{"SessionCookie": []}]
    assert any(p["name"] == "X-CSRF-Token" for p in operation["parameters"])
    assert "application/problem+json" in operation["responses"]["422"]["content"]
