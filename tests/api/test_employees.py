async def test_employee_crud_and_company_email_uniqueness(authenticated):
    client = authenticated
    companies = [
        (await client.post("/api/v1/companies", json={"name": name})).headers[
            "location"
        ]
        for name in ["One", "Two"]
    ]
    data = {
        "full_name": "Employee",
        "start_date": "2026-01-01",
        "work_email": "Work@Example.com",
    }
    created = await client.post(companies[0] + "/employees", json=data)
    assert created.status_code == 201, created.text
    path = created.headers["location"]
    duplicate = await client.post(
        companies[0] + "/employees", json=data | {"work_email": "work@example.com"}
    )
    assert duplicate.status_code == 409
    assert (
        await client.post(companies[1] + "/employees", json=data)
    ).status_code == 201
    assert (
        await client.get(companies[1] + "/employees/" + created.json()["id"])
    ).status_code == 404
    invalid = await client.patch(
        path, json={"status": "terminated"}, headers={"If-Match": '"v1"'}
    )
    assert invalid.status_code == 422
    changed = await client.patch(
        path,
        json={"status": "terminated", "end_date": "2026-09-01"},
        headers={"If-Match": '"v1"'},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 2
    assert (await client.delete(path, headers={"If-Match": '"v2"'})).status_code == 204


async def test_employee_validation_rejects_mass_assignment(authenticated):
    company = (
        await authenticated.post("/api/v1/companies", json={"name": "Validation"})
    ).headers["location"]
    response = await authenticated.post(
        company + "/employees",
        json={"full_name": "Test", "start_date": "2026-01-01", "version": 100},
    )
    assert response.status_code == 422
