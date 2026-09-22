import pytest


@pytest.mark.parametrize("name", [123, [], {}, None, "   "])
async def test_invalid_name_types_return_validation_errors(authenticated, name):
    response = await authenticated.post("/api/v1/companies", json={"name": name})
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "validation_error"


async def test_null_patch_and_cookie_flags(authenticated, account):
    company = await authenticated.post("/api/v1/companies", json={"name": "Null patch"})
    response = await authenticated.patch(
        company.headers["location"], json={"name": None}, headers={"If-Match": '"v1"'}
    )
    assert response.status_code == 422
    response = await authenticated.post(
        "/api/v1/auth/login",
        json={"login": account["login"], "password": account["password"]},
        headers={"X-CSRF-Protection": "1"},
    )
    cookie = response.headers["set-cookie"]
    assert (
        "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=28800" in cookie
    )
    assert "Domain=" not in cookie
